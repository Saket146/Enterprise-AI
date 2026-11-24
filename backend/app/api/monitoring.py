from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.middleware.rbac import require
from app.security.permissions import Perm
from app.models.models import AgentLog, AuditLog, WorkflowRun
from app.observability import metrics

router = APIRouter(prefix="/api/monitoring", tags=["observability"])
@router.get("/dashboard")
def dashboard(user=Depends(require(Perm.SYSTEM_MONITOR)), db: Session = Depends(get_db)):
    """
    Activity of the AI system. Request counts and response times are measured since the
    backend was last started; everything else is read from the database and is permanent.
    """
    data = metrics.snapshot()
    data["agent_traces"] = [{"agent": n or "Unknown", "executions": c, "avg_ms": round(float(avg or 0), 1)} for n,c,avg in db.query(AgentLog.agent_name, func.count(AgentLog.agent_log_id), func.avg(AgentLog.execution_time_ms)).group_by(AgentLog.agent_name).order_by(func.count(AgentLog.agent_log_id).desc()).all()]
    data["audit_events"] = db.query(func.count(AuditLog.audit_id)).scalar() or 0

    def audit_count(action: str) -> int:
        return db.query(func.count(AuditLog.audit_id)).filter(AuditLog.action_type == action).scalar() or 0

    data["questions_answered"] = db.query(func.count(WorkflowRun.workflow_id)).filter(WorkflowRun.session_id.isnot(None)).scalar() or 0
    data["blocked_prompts"] = audit_count("blocked_prompt")
    data["access_denials"] = audit_count("rbac_denied")
    data["recent_security_events"] = [
        {
            "when": e.timestamp,
            "event": {"blocked_prompt": "Unsafe prompt blocked", "rbac_denied": "Access denied by role"}.get(e.action_type, e.action_type),
            "employee_id": e.employee_id,
            "area": e.resource_type,
            "details": (e.details or "")[:160],
        }
        for e in db.query(AuditLog).filter(AuditLog.action_type.in_(["blocked_prompt", "rbac_denied"])).order_by(AuditLog.audit_id.desc()).limit(8)
    ]
    return data



@router.get("/llm")
def language_model_status(user=Depends(require(Perm.SYSTEM_MONITOR))):
    """Which language model answers, and whether its last calls worked (the API key is never returned)."""
    from app.services.llm_service import llm_service
    return llm_service.status()


@router.post("/llm/test")
def test_language_model(user=Depends(require(Perm.SYSTEM_MONITOR))):
    """Send one tiny request to the language model to check that the key and the model work."""
    from app.services.llm_service import llm_service
    if not llm_service.has_model:
        return {**llm_service.status(), "ok": False, "reply": None,
                "message": "No language model is configured. Set LLM_PROVIDER and the API key in backend/.env, then restart the backend."}
    result = llm_service.test_connection()
    result["message"] = "The language model answered." if result["ok"] else (result.get("last_error") or "The language model did not answer.")
    return result
