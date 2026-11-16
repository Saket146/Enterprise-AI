from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.middleware.rbac import require
from app.security.permissions import Perm
from app.models.models import Project, Task, Employee, Client, Contract, WorkflowRun, AgentLog

router = APIRouter(prefix="/api/analytics", tags=["enterprise analytics"])

@router.get("/overview")
def overview(user=Depends(require(Perm.ANALYTICS_OVERVIEW)), db: Session = Depends(get_db)):
    project_status = db.query(Project.status, func.count(Project.project_id)).group_by(Project.status).all()
    workload = db.query(Employee.first_name, Employee.last_name, func.count(Task.task_id).label("tasks")).outerjoin(Task, Task.assigned_to == Employee.employee_id).group_by(Employee.employee_id).order_by(func.count(Task.task_id).desc()).limit(8).all()
    contracts = db.query(Contract.status, func.count(Contract.contract_id)).group_by(Contract.status).all()
    workflows = db.query(WorkflowRun.status, func.count(WorkflowRun.workflow_id)).group_by(WorkflowRun.status).all()
    total_runs = sum(v for _, v in workflows) or 1
    successful = sum(v for s, v in workflows if s in ("completed", "approved"))
    at_risk = db.query(func.count(Project.project_id)).filter(Project.status.in_(["On Hold", "At Risk", "Delayed"])).scalar() or 0
    return {"projects": {"health": [{"name": s or "Unknown", "value": n} for s,n in project_status], "risks": at_risk, "delays": at_risk},
            "employees": {"workload": [{"name": f"{f} {l}", "value": n} for f,l,n in workload]},
            "clients": {"contracts": [{"name": s or "Unknown", "value": n} for s,n in contracts], "engagement": db.query(func.count(Client.client_id)).filter(Client.status == "Active").scalar() or 0},
            "ai": {"queries": total_runs, "agent_usage": db.query(func.count(AgentLog.agent_log_id)).scalar() or 0, "success_rate": round(successful / total_runs * 100, 1)}}
