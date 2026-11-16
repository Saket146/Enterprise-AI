"""
Requests and approvals (the "Operations Center" workflows).

An employee submits a request; the text is screened by the guardrails, personal
data is masked, and - depending on the request type - it is routed to a human
approver.  Every step is written to the audit log.

  hr_request       HR request (leave, letters, changes)      -> approved by HR
  document_intake  Ask to add a document to the knowledge base -> approved by AI governance
  project_risk     Report a project risk                      -> recorded, no approval needed
  document_access  Ask to read one document                   -> approved by a system administrator;
                                                                 approval lets the requester open it
"""
import json
from datetime import datetime
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.middleware.rbac import get_current_user, log_audit_action, require
from app.models.models import (
    WorkflowRun, AgentLog, Approval, AuditLog, ChatSession, Document, DocumentAccessRequest, Employee,
    WorkflowRequest as RequestRecord,
)
from app.security.permissions import Perm, build_user_context, document_access, role_has
from app.services.sql_retriever import postgres_retriever
from app.observability import metrics
from app.security.defense import inspect_prompt, mask_sensitive_data

router = APIRouter(prefix="/api/workflows", tags=["workflow automation"])
WorkflowType = Literal["hr_request", "project_risk", "document_intake", "document_access"]

REQUEST_TYPES = {
    "document_access": {
        "label": "Access to a document",
        "description": "Ask to read a document from the Knowledge Explorer. A system administrator decides; once approved you can open it.",
        "approver_role": "Admin",
        "approver_label": "a system administrator",
    },
    "hr_request": {
        "label": "HR request",
        "description": "Leave, employment letters, or changes to your record. Needs approval from HR.",
        "approver_role": "HR Director",
        "approver_label": "HR (HR Director or HR Executive)",
    },
    "document_intake": {
        "label": "Add a document to the knowledge base",
        "description": "Ask for a document to be added so the assistant can use it. Needs approval from AI governance.",
        "approver_role": "AI Administrator",
        "approver_label": "AI governance (CEO, CTO or AI Administrator)",
    },
    "project_risk": {
        "label": "Report a project risk",
        "description": "Flag a delay, blocker or risk on a project. It is recorded for managers; no approval is needed.",
        "approver_role": None,
        "approver_label": None,
    },
}

STATUS_LABELS = {
    "awaiting_approval": "Waiting for approval",
    "approved": "Approved",
    "rejected": "Rejected",
    "completed": "Recorded",
    "running": "In progress",
}

# Which permission is needed to decide an approval addressed to a given approver role.
# ("HR Manager" is kept so approvals created before the job-role matrix still resolve.)
APPROVAL_PERMISSIONS = {
    "HR Director": Perm.APPROVE_HR,
    "HR Manager": Perm.APPROVE_HR,
    "AI Administrator": Perm.APPROVE_AI,
    "Admin": Perm.APPROVE_DOCUMENT_ACCESS,
}

# Anyone holding one of these can open the approvals list
APPROVER_PERMISSIONS = (Perm.APPROVE_HR, Perm.APPROVE_AI, Perm.APPROVE_DOCUMENT_ACCESS)


def _role_name(user) -> str:
    return user.role.role_name if user.role else ""


def _can_decide(user, approval: Approval) -> bool:
    needed = APPROVAL_PERMISSIONS.get(approval.approver_role)
    return bool(needed) and role_has(_role_name(user), needed)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _employee_name(db: Session, employee_id: Optional[int]) -> str:
    if employee_id is None:
        return "Unknown"
    emp = db.get(Employee, employee_id)
    return f"{emp.first_name} {emp.last_name}" if emp else "Unknown"


class WorkflowRequest(BaseModel):
    workflow_type: WorkflowType
    title: str = Field(default="", max_length=200)   # not needed for document_access (the document's title is used)
    payload: str = Field(min_length=3, max_length=10000)
    document_id: Optional[int] = None                # required for document_access
    requires_approval: bool = True   # kept for older clients; approval is decided by the request type

class ApprovalDecision(BaseModel):
    approved: bool
    note: str = Field(default="", max_length=1000)


@router.get("/types")
def list_request_types(user=Depends(get_current_user)):
    """The kinds of request an employee can submit, with a plain description of what happens to each."""
    can_request_documents = document_access(build_user_context(user)) == "titles"
    return [{"type": key, **{k: v for k, v in info.items() if k != "approver_role"},
             "needs_approval": bool(info["approver_role"]), "needs_document": key == "document_access"}
            for key, info in REQUEST_TYPES.items()
            # Roles that already read every document, or may not see documents at all, cannot ask for document access
            if key != "document_access" or can_request_documents]


@router.post("/run")
def run_workflow(body: WorkflowRequest, request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Submit a request."""
    info = REQUEST_TYPES[body.workflow_type]

    # A document access request names the document; everything else needs a title
    document = None
    if body.workflow_type == "document_access":
        context = build_user_context(user)
        access = document_access(context)
        if access == "none":
            log_audit_action(db, user.employee_id, "rbac_denied", "workflow", 0, _client_ip(request), "document_access request refused")
            raise HTTPException(403, "Your role is not permitted to view or request company documents.")
        if body.document_id is None:
            raise HTTPException(400, "Choose the document you want access to.")
        document = db.get(Document, body.document_id)
        if not document:
            raise HTTPException(404, "That document does not exist.")
        if postgres_retriever.can_open_document(db, document.document_id, context):
            raise HTTPException(400, "You can already open this document.")
        already_pending = db.query(DocumentAccessRequest).filter(
            DocumentAccessRequest.employee_id == user.employee_id,
            DocumentAccessRequest.document_id == document.document_id,
            DocumentAccessRequest.status == "pending",
        ).first()
        if already_pending:
            raise HTTPException(400, "You have already requested access to this document. It is waiting for a decision.")
        body.title = f"Access to: {document.title}"[:200]
    elif len(body.title.strip()) < 3:
        raise HTTPException(400, "Please give the request a title of at least 3 characters.")

    # Guardrail 1: prompt-injection screen on everything the user typed
    safety = inspect_prompt(f"{body.title}\n{body.payload}")
    if not safety.safe:
        metrics.increment("security_intercepts")
        log_audit_action(db, user.employee_id, "blocked_prompt", "workflow", 0, _client_ip(request), ",".join(safety.reasons))
        raise HTTPException(400, "This request was blocked by the safety filter. Please describe it in plain words.")

    # Guardrail 2: personal data (emails, phone numbers, card numbers) is masked before it is stored
    title = body.title.strip() if document else mask_sensitive_data(body.title.strip())
    details = mask_sensitive_data(body.payload.strip())

    workflow = WorkflowRun(workflow_name=body.workflow_type, status="running", final_output=None, confidence_score=1)
    db.add(workflow); db.flush()
    db.add(RequestRecord(workflow_id=workflow.workflow_id, requested_by=user.employee_id,
                         request_type=body.workflow_type, title=title, details=details))
    if document:
        db.add(DocumentAccessRequest(workflow_id=workflow.workflow_id, document_id=document.document_id,
                                     employee_id=user.employee_id, status="pending"))

    steps = [
        ("Safety filter", "Screened the request text for prompt-injection patterns", "Passed"),
        ("Privacy filter", "Masked personal data before storing the request",
         "Personal data was masked" if (title, details) != (body.title.strip(), body.payload.strip()) else "Nothing to mask"),
    ]
    if info["approver_role"]:
        db.add(Approval(workflow_id=workflow.workflow_id, requested_by=user.employee_id, approver_role=info["approver_role"]))
        workflow.status = "awaiting_approval"
        workflow.final_output = f"Sent to {info['approver_label']} for approval."
        steps.append(("Approval routing", f"Routed to {info['approver_label']}", "Waiting for a decision"))
    else:
        workflow.status, workflow.completed_at = "completed", datetime.utcnow()
        workflow.final_output = "Recorded. Managers with project oversight can see it in the request log."
        steps.append(("Request log", "Recorded the request for managers with project oversight", "Recorded"))

    for name, action, result in steps:
        db.add(AgentLog(workflow_id=workflow.workflow_id, agent_name=name, task_description=action,
                        input_data=json.dumps({"title": title}), output_data=result,
                        execution_time_ms=1, confidence_score=1))
    db.commit(); db.refresh(workflow)
    log_audit_action(db, user.employee_id, "workflow_started", "workflow", workflow.workflow_id, _client_ip(request), body.workflow_type)
    metrics.increment("workflows_started")
    return {
        "workflow_id": workflow.workflow_id,
        "status": workflow.status,
        "status_label": STATUS_LABELS.get(workflow.status, workflow.status),
        "output": workflow.final_output,
        "message": workflow.final_output,
        "needs_approval": bool(info["approver_role"]),
        "steps": [s[0] for s in steps],
        "agents": [s[0] for s in steps],
    }


def _request_out(db: Session, record: RequestRecord, workflow: WorkflowRun, approval: Optional[Approval]) -> dict:
    info = REQUEST_TYPES.get(record.request_type, {})
    return {
        "id": workflow.workflow_id,
        "type": record.request_type,
        "type_label": info.get("label", record.request_type),
        "title": record.title,
        "details": record.details,
        "status": workflow.status,
        "status_label": STATUS_LABELS.get(workflow.status, workflow.status),
        "requested_by": _employee_name(db, record.requested_by),
        "created_at": record.created_at,
        "approver": info.get("approver_label"),
        "decided_at": approval.decided_at if approval else None,
        "decision_note": approval.decision_note if approval else None,
        "outcome": workflow.final_output,
    }


@router.get("/requests")
def list_requests(
    scope: str = Query("mine", description="mine = requests I submitted; all = everyone's (needs monitoring or project-oversight permission)"),
    limit: int = Query(25, ge=1, le=100),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Requests submitted through the Operations Center, newest first."""
    query = db.query(RequestRecord, WorkflowRun).join(WorkflowRun, WorkflowRun.workflow_id == RequestRecord.workflow_id)
    role = _role_name(user)
    if scope == "all":
        if role_has(role, Perm.SYSTEM_MONITOR):
            pass
        elif role_has(role, Perm.PROJECTS_READ_ALL):
            query = query.filter(or_(RequestRecord.request_type == "project_risk", RequestRecord.requested_by == user.employee_id))
        else:
            raise HTTPException(403, "Access denied. Your role can only see the requests you submitted.")
    else:
        query = query.filter(RequestRecord.requested_by == user.employee_id)

    rows = query.order_by(RequestRecord.workflow_id.desc()).limit(limit).all()
    approvals = {a.workflow_id: a for a in db.query(Approval).filter(Approval.workflow_id.in_([w.workflow_id for _, w in rows] or [0]))}
    return [_request_out(db, record, workflow, approvals.get(workflow.workflow_id)) for record, workflow in rows]


@router.get("/runs")
def list_runs(limit: int = 25, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Raw workflow runs (chat answers and requests). Kept for older clients; the UI uses /requests."""
    query = db.query(WorkflowRun)
    if not role_has(_role_name(user), Perm.SYSTEM_MONITOR):
        # Workflow outputs contain other people's questions and answers:
        # without the monitoring permission a user only sees runs they started.
        own_sessions = db.query(ChatSession.session_id).filter(ChatSession.employee_id == user.employee_id)
        own_started = db.query(AuditLog.resource_id).filter(
            AuditLog.employee_id == user.employee_id,
            AuditLog.action_type == "workflow_started",
            AuditLog.resource_type == "workflow",
        )
        own_requested = db.query(Approval.workflow_id).filter(Approval.requested_by == user.employee_id)
        query = query.filter(or_(
            WorkflowRun.session_id.in_(own_sessions),
            WorkflowRun.workflow_id.in_(own_started),
            WorkflowRun.workflow_id.in_(own_requested),
        ))
    runs = query.order_by(WorkflowRun.started_at.desc()).limit(max(1, min(limit, 100))).all()
    return [{"id": r.workflow_id, "name": r.workflow_name, "status": r.status, "started_at": r.started_at, "output": r.final_output} for r in runs]


@router.get("/approvals")
def list_approvals(user=Depends(require(*APPROVER_PERMISSIONS)), db: Session = Depends(get_db)):
    """Pending approvals that this user's role is allowed to decide."""
    pending = db.query(Approval).filter(Approval.status == "pending").order_by(Approval.approval_id.desc()).all()
    out = []
    for a in pending:
        if not _can_decide(user, a):
            continue
        record = db.get(RequestRecord, a.workflow_id)
        if record:
            info = REQUEST_TYPES.get(record.request_type, {})
        else:
            # Approval created before request details were stored: fall back to the workflow type
            legacy = db.get(WorkflowRun, a.workflow_id)
            info = REQUEST_TYPES.get(legacy.workflow_name if legacy else "", {})
        out.append({
            "approval_id": a.approval_id,
            "workflow_id": a.workflow_id,
            "approver_role": a.approver_role,
            "status": a.status,
            "created_at": a.created_at,
            "type_label": info.get("label", "Request"),
            "title": record.title if record else f"{info.get('label', 'Request')} #{a.workflow_id}",
            "details": record.details if record else "Submitted before request details were recorded.",
            "requested_by": _employee_name(db, a.requested_by),
            # Nobody decides their own request (system administrators excepted)
            "own_request": a.requested_by == user.employee_id and not role_has(_role_name(user), Perm.ALL),
        })
    return out


@router.post("/approvals/{approval_id}")
def decide_approval(approval_id: int, decision: ApprovalDecision, request: Request, user=Depends(require(*APPROVER_PERMISSIONS)), db: Session = Depends(get_db)):
    approval = db.get(Approval, approval_id)
    if not approval or approval.status != "pending": raise HTTPException(404, "Pending approval not found.")
    client_ip = _client_ip(request)
    # An HR approver must not decide AI approvals and vice versa
    if not _can_decide(user, approval):
        log_audit_action(db, user.employee_id, "rbac_denied", "approval", approval_id, client_ip, f"needs {approval.approver_role}")
        raise HTTPException(403, f"Access denied. This approval must be decided by: {approval.approver_role}.")
    # Segregation of duties: nobody approves their own request
    if approval.requested_by == user.employee_id and not role_has(_role_name(user), Perm.ALL):
        raise HTTPException(403, "You cannot decide an approval that you requested yourself.")
    if inspect_prompt(decision.note).reasons:
        raise HTTPException(400, "Decision note blocked by prompt-injection policy.")
    approval.status, approval.decision_note, approval.decided_at = ("approved" if decision.approved else "rejected"), mask_sensitive_data(decision.note), datetime.utcnow()
    workflow = db.get(WorkflowRun, approval.workflow_id); workflow.status, workflow.completed_at = approval.status, datetime.utcnow()
    decider = f"{user.first_name} {user.last_name}"
    workflow.final_output = f"{approval.status.capitalize()} by {decider}."

    # A decided document access request grants (or refuses) the right to open that one document
    access_request = db.get(DocumentAccessRequest, approval.workflow_id)
    if access_request:
        access_request.status, access_request.decided_by, access_request.decided_at = approval.status, user.employee_id, datetime.utcnow()
        if decision.approved:
            workflow.final_output += " You can now open the document in the Knowledge Explorer."
    db.add(AgentLog(workflow_id=workflow.workflow_id, agent_name="Human approval", task_description=f"Decision by {decider}",
                    input_data="", output_data=approval.status.capitalize(), execution_time_ms=1, confidence_score=1))
    db.commit(); log_audit_action(db, user.employee_id, "approval_decided", "approval", approval_id, client_ip, approval.status)
    return {"approval_id": approval_id, "status": approval.status, "status_label": STATUS_LABELS.get(approval.status, approval.status)}
