from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.middleware.rbac import RoleChecker
from app.models.models import AgentLog, AuditLog
from app.observability import metrics

router = APIRouter(prefix="/api/monitoring", tags=["observability"])
@router.get("/dashboard")
def dashboard(user=Depends(RoleChecker(["AI Administrator", "Admin"])), db: Session = Depends(get_db)):
    data = metrics.snapshot()
    data["agent_traces"] = [{"agent": n or "Unknown", "executions": c, "avg_ms": round(float(avg or 0), 1)} for n,c,avg in db.query(AgentLog.agent_name, func.count(AgentLog.agent_log_id), func.avg(AgentLog.execution_time_ms)).group_by(AgentLog.agent_name).all()]
    data["audit_events"] = db.query(func.count(AuditLog.audit_id)).scalar() or 0
    return data
