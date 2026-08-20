"""Human-in-the-loop enterprise workflow automation."""
import json
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.middleware.rbac import RoleChecker, get_current_user, log_audit_action
from app.models.models import WorkflowRun, AgentLog, Approval
from app.observability import metrics
from app.security.defense import inspect_prompt, mask_sensitive_data

router = APIRouter(prefix="/api/workflows", tags=["workflow automation"])
WorkflowType = Literal["hr_request", "project_risk", "document_intake"]
PIPELINES = {
    "hr_request": [("HR Agent", "Validates employee request and entitlement"), ("Policy Agent", "Checks policy controls"), ("Approval Workflow", "Routes to HR Manager")],
    "project_risk": [("Engineering Agent", "Assesses technical impact"), ("Project Manager Agent", "Builds mitigation recommendation")],
    "document_intake": [("Classification Agent", "Classifies document and sensitivity"), ("Approval Workflow", "Routes restricted content"), ("Knowledge Indexer", "Queues approved knowledge for indexing")],
}

class WorkflowRequest(BaseModel):
    workflow_type: WorkflowType
    title: str = Field(min_length=3, max_length=200)
    payload: str = Field(min_length=3, max_length=10000)
    requires_approval: bool = True

class ApprovalDecision(BaseModel):
    approved: bool
    note: str = Field(default="", max_length=1000)

@router.post("/run")
def run_workflow(body: WorkflowRequest, request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    safety = inspect_prompt(body.payload)
    if not safety.safe:
        metrics.increment("security_intercepts")
        log_audit_action(db, user.employee_id, "blocked_prompt", "workflow", 0, request.client.host if request.client else "unknown", ",".join(safety.reasons))
        raise HTTPException(400, "Request blocked by prompt-injection policy.")
    workflow = WorkflowRun(workflow_name=body.workflow_type, status="running", final_output=None, confidence_score=0)
    db.add(workflow); db.flush()
    sanitized = mask_sensitive_data(body.payload)
    for agent, action in PIPELINES[body.workflow_type]:
        db.add(AgentLog(workflow_id=workflow.workflow_id, agent_name=agent, task_description=action,
                        input_data=json.dumps({"title": body.title}), output_data=json.dumps({"result": "completed", "input": sanitized}),
                        execution_time_ms=20, confidence_score=0.92))
    if body.requires_approval and body.workflow_type in ("hr_request", "document_intake"):
        db.add(Approval(workflow_id=workflow.workflow_id, requested_by=user.employee_id, approver_role="HR Manager" if body.workflow_type == "hr_request" else "AI Administrator"))
        workflow.status, workflow.final_output = "awaiting_approval", "Workflow completed automated checks and is awaiting human approval."
    else:
        workflow.status, workflow.completed_at = "completed", datetime.utcnow()
        workflow.final_output = "Recommendation generated and workflow completed."
    workflow.confidence_score = 0.92
    db.commit(); db.refresh(workflow)
    log_audit_action(db, user.employee_id, "workflow_started", "workflow", workflow.workflow_id, request.client.host if request.client else "unknown", body.workflow_type)
    metrics.increment("workflows_started")
    return {"workflow_id": workflow.workflow_id, "status": workflow.status, "output": workflow.final_output, "agents": [x[0] for x in PIPELINES[body.workflow_type]]}

@router.get("/runs")
def list_runs(limit: int = 25, user=Depends(get_current_user), db: Session = Depends(get_db)):
    runs = db.query(WorkflowRun).order_by(WorkflowRun.started_at.desc()).limit(min(limit, 100)).all()
    return [{"id": r.workflow_id, "name": r.workflow_name, "status": r.status, "started_at": r.started_at, "output": r.final_output} for r in runs]

@router.get("/approvals")
def list_approvals(user=Depends(RoleChecker(["HR Manager", "AI Administrator", "Project Manager"])), db: Session = Depends(get_db)):
    return [{"approval_id": a.approval_id, "workflow_id": a.workflow_id, "approver_role": a.approver_role, "status": a.status, "created_at": a.created_at} for a in db.query(Approval).filter(Approval.status == "pending").all()]

@router.post("/approvals/{approval_id}")
def decide_approval(approval_id: int, decision: ApprovalDecision, request: Request, user=Depends(RoleChecker(["HR Manager", "AI Administrator"])), db: Session = Depends(get_db)):
    approval = db.get(Approval, approval_id)
    if not approval or approval.status != "pending": raise HTTPException(404, "Pending approval not found.")
    approval.status, approval.decision_note, approval.decided_at = ("approved" if decision.approved else "rejected"), decision.note, datetime.utcnow()
    workflow = db.get(WorkflowRun, approval.workflow_id); workflow.status, workflow.completed_at = approval.status, datetime.utcnow()
    workflow.final_output = f"Human approval {approval.status}."
    db.commit(); log_audit_action(db, user.employee_id, "approval_decided", "approval", approval_id, request.client.host if request.client else "unknown", approval.status)
    return {"approval_id": approval_id, "status": approval.status}
