import logging
import re
from typing import Dict, Any, List, Optional
from sqlalchemy import text, func, or_
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.models import Employee, Project, Task, Policy, Department, Budget, ProjectMember
from app.agents.guardrails import AIGuardrails
from app.services.rag_service import rag_service
from app.services.sql_retriever import postgres_retriever, OPEN_TASK_EXCLUDE
from app.security.permissions import Perm, can, can_view_employee_sensitive
from app.security.sql_guard import MAX_ROWS, mask_result_columns, referenced_tables, validate_sql

logger = logging.getLogger(__name__)


class ControlledTools:
    """
    Controlled tool definitions with built-in job-role verification, logging, and audit tracks.
    Every permission decision goes through app.security.permissions.
    """

    @staticmethod
    def get_employee_details(employee_id: int, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        HR Tool: Fetch profile card of an employee.
        Directory fields are visible to every employee; phone, salary, hire date and date of
        birth only to the employee, their direct manager, and HR / executive roles.
        """
        logger.info(f"Tool execution: get_employee_details on ID {employee_id}")

        db: Session = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
            if not emp:
                return {"success": False, "error": f"Employee with ID {employee_id} not found."}

            result = {
                "success": True,
                "employee_id": emp.employee_id,
                "name": f"{emp.first_name} {emp.last_name}",
                "email": emp.email,
                "office_location": emp.office_location,
                "employment_status": emp.employment_status,
                "role": emp.role.role_name if emp.role else "Employee",
                "department": emp.department.department_name if emp.department else "None",
                "manager": f"{emp.manager.first_name} {emp.manager.last_name}" if emp.manager else "None",
                "sensitive_fields_visible": False,
            }
            if can_view_employee_sensitive(user_context, emp.employee_id, emp.manager_id):
                result.update({
                    "sensitive_fields_visible": True,
                    "phone": emp.phone,
                    "hire_date": str(emp.hire_date) if emp.hire_date else None,
                    "date_of_birth": str(emp.date_of_birth) if emp.date_of_birth else None,
                    "salary": str(emp.salary) if emp.salary is not None else None,
                })
            return result
        finally:
            db.close()

    @staticmethod
    def search_hr_policy(query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """HR Tool: Search company policies in Qdrant (semantic) and PostgreSQL (keyword)."""
        logger.info(f"Tool execution: search_hr_policy on query: '{query}'")

        # Access (full text / titles only / nothing) is decided by the user's role inside both retrievers
        hits = rag_service.search_collection(query, collection_name="policies", limit=3, user_context=user_context)
        hits += postgres_retriever.search(query, user_context, domains=("policies",), limit=3)
        return {
            "success": True,
            "results": hits
        }

    @staticmethod
    def _project_access(db: Session, proj: Project, user_context: Dict[str, Any]) -> bool:
        return postgres_retriever.can_view_project(db, proj, user_context)

    @staticmethod
    def get_project_status(project_id: int, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Project Tool: Fetch summary status of a project. Restricted to project-oversight roles, the PM, or assigned members."""
        logger.info(f"Tool execution: get_project_status on ID {project_id}")

        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.project_id == project_id).first()
            if not proj:
                return {"success": False, "error": f"Project with ID {project_id} not found."}

            if not ControlledTools._project_access(db, proj, user_context):
                postgres_retriever.audit_denial(db, user_context, "project", project_id, "get_project_status refused")
                return {"success": False, "error": "Unauthorized: You do not have permission to view this project board."}

            return {
                "success": True,
                "project_id": proj.project_id,
                "name": proj.project_name,
                "code": proj.project_code,
                "status": proj.status,
                "priority": proj.priority,
                "budget": str(proj.budget) if proj.budget else "0.00",
                "manager": f"{proj.manager.first_name} {proj.manager.last_name}" if proj.manager else "Unassigned",
                "department": proj.department.department_name if proj.department else "None"
            }
        finally:
            db.close()

    @staticmethod
    def get_pending_tasks(project_id: int, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Project Tool: Fetch list of incomplete tasks. Restricted to project-oversight roles, the PM, or assigned members."""
        logger.info(f"Tool execution: get_pending_tasks on ID {project_id}")

        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.project_id == project_id).first()
            if not proj:
                return {"success": False, "error": f"Project with ID {project_id} not found."}

            if not ControlledTools._project_access(db, proj, user_context):
                postgres_retriever.audit_denial(db, user_context, "project", project_id, "get_pending_tasks refused")
                return {"success": False, "error": "Unauthorized: You do not have permission to view tasks for this project."}

            # Everything that is not finished counts as pending (Pending, In Progress, Blocked, ...)
            tasks = db.query(Task).filter(
                Task.project_id == project_id,
                or_(Task.status.is_(None), func.lower(Task.status).notin_(OPEN_TASK_EXCLUDE)),
            ).order_by(Task.due_date).limit(50).all()

            return {
                "success": True,
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "title": t.title,
                        "status": t.status,
                        "priority": t.priority,
                        "assignee": f"{t.assignee.first_name} {t.assignee.last_name}" if t.assignee else "Unassigned"
                    }
                    for t in tasks
                ]
            }
        finally:
            db.close()

    @staticmethod
    def get_budget_information(department_id: int, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finance Tool: Get budget summaries.
        Finance / executive roles see every department; managers only their own department.
        """
        logger.info(f"Tool execution: get_budget_information on department {department_id}")

        db: Session = SessionLocal()
        try:
            if not postgres_retriever.can_view_department_budget(department_id, user_context):
                postgres_retriever.audit_denial(db, user_context, "budget", department_id, "get_budget_information refused")
                return {"success": False, "error": "Unauthorized: You do not have permissions to access this department's budget sheets."}

            dept = db.query(Department).filter(Department.department_id == department_id).first()
            if not dept:
                return {"success": False, "error": f"Department ID {department_id} not found."}

            budgets = db.query(Budget).filter(Budget.department_id == department_id).all()
            return {
                "success": True,
                "department_name": dept.department_name,
                "total_budget": str(dept.budget) if dept.budget else "0.00",
                "fiscal_runs": [
                    {
                        "fiscal_year": b.fiscal_year,
                        "allocated": str(b.allocated_amount),
                        "approved": str(b.approved_amount)
                    }
                    for b in budgets
                ]
            }
        finally:
            db.close()

    @staticmethod
    def execute_authorized_sql(sql_query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analytics Tool: Execute a read-only SQL analytics query.

        Guardrails (app.security.sql_guard):
          * a single SELECT statement only - no comments, no mutating keywords, no system catalogs
          * every table referenced must be readable by the user's job role
          * sensitive columns (salary, phone, hashed_password ...) are refused and masked
          * executed inside a READ ONLY transaction with a statement timeout
        """
        logger.info(f"Tool execution: execute_authorized_sql on query: '{sql_query}'")

        allowed, error, clean_sql = validate_sql(sql_query, user_context)
        if not allowed:
            logger.warning(f"SQL guardrail blocked query from employee {user_context.get('employee_id')}: {error}")
            db: Session = SessionLocal()
            try:
                postgres_retriever.audit_denial(db, user_context, "sql", 0, f"{error} | {sql_query[:300]}")
            finally:
                db.close()
            return {"success": False, "error": error}

        db = SessionLocal()
        try:
            # The database itself refuses writes, whatever slipped past the text checks.
            db.execute(text("SET TRANSACTION READ ONLY"))
            db.execute(text("SET LOCAL statement_timeout = 8000"))

            # Escape ':' so literals such as '12:30' or casts are not parsed as bind parameters.
            stmt = text(clean_sql.replace(":", r"\:"))
            res = db.execute(stmt)

            # Limit rows
            rows = res.fetchmany(MAX_ROWS)
            columns = list(res.keys())

            serialized_rows = []
            for r in rows:
                row_dict = {}
                for idx, col in enumerate(columns):
                    val = r[idx]
                    # Format decimals/dates for JSON
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    elif hasattr(val, "as_tuple") or type(val).__name__ == "Decimal":
                        val = float(val)
                    row_dict[col] = val
                serialized_rows.append(row_dict)

            serialized_rows = mask_result_columns(columns, serialized_rows, user_context, referenced_tables(clean_sql))
            visible_columns = list(serialized_rows[0].keys()) if serialized_rows else [c for c in columns if c.lower() != "hashed_password"]

            return {
                "success": True,
                "columns": visible_columns,
                "rows": serialized_rows,
                "row_count": len(serialized_rows)
            }
        except Exception as e:
            return {"success": False, "error": f"SQL Database execution failed: {str(e).splitlines()[0]}"}
        finally:
            db.rollback()
            db.close()
