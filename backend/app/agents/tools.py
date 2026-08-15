import logging
import time
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.models import Employee, Project, Task, Policy, Department, Budget, ProjectMember
from app.agents.guardrails import AIGuardrails
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

class ControlledTools:
    """
    Controlled tool definitions with built-in role verification, logging, and audit tracks.
    """
    
    @staticmethod
    def get_employee_details(employee_id: int, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """HR Tool: Fetch profile card of an employee. Restrict to self, managers, or HR Managers."""
        logger.info(f"Tool execution: get_employee_details on ID {employee_id}")
        
        user_id = user_context.get("employee_id")
        user_role = user_context.get("role", "Employee")
        
        # Check permissions
        is_authorized = False
        if user_role in ["Admin", "HR Manager"]:
            is_authorized = True
        elif user_id == employee_id:
            is_authorized = True
        
        db: Session = SessionLocal()
        try:
            # If not self or admin, check if user is manager of the employee
            if not is_authorized:
                emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
                if emp and emp.manager_id == user_id:
                    is_authorized = True
            
            if not is_authorized:
                return {"success": False, "error": "Unauthorized: You do not have permission to view this employee's details."}
                
            emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
            if not emp:
                return {"success": False, "error": f"Employee with ID {employee_id} not found."}
                
            return {
                "success": True,
                "employee_id": emp.employee_id,
                "name": f"{emp.first_name} {emp.last_name}",
                "email": emp.email,
                "phone": emp.phone,
                "office_location": emp.office_location,
                "employment_status": emp.employment_status,
                "role": emp.role.role_name if emp.role else "Employee",
                "department": emp.department.department_name if emp.department else "None",
                "manager": f"{emp.manager.first_name} {emp.manager.last_name}" if emp.manager else "None"
            }
        finally:
            db.close()

    @staticmethod
    def search_hr_policy(query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """HR Tool: Search vector database (Qdrant) for matching company policies."""
        logger.info(f"Tool execution: search_hr_policy on query: '{query}'")
        
        # Policies are public to all logged-in employees, no strict RBAC filter needed
        hits = rag_service.search_collection(query, collection_name="policies", limit=3)
        return {
            "success": True,
            "results": hits
        }

    @staticmethod
    def get_project_status(project_id: int, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Project Tool: Fetch summary status of a project. Restrict to Admin, PMs, or assigned members."""
        logger.info(f"Tool execution: get_project_status on ID {project_id}")
        
        user_id = user_context.get("employee_id")
        user_role = user_context.get("role", "Employee")
        
        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.project_id == project_id).first()
            if not proj:
                return {"success": False, "error": f"Project with ID {project_id} not found."}
                
            # Check permissions
            is_member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.employee_id == user_id
            ).first() is not None
            
            is_authorized = (
                user_role in ["Admin", "Project Manager"] or
                proj.project_manager_id == user_id or
                is_member
            )
            
            if not is_authorized:
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
        """Project Tool: Fetch list of incomplete tasks. Restrict to Admin, PMs, or assigned members."""
        logger.info(f"Tool execution: get_pending_tasks on ID {project_id}")
        
        user_id = user_context.get("employee_id")
        user_role = user_context.get("role", "Employee")
        
        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.project_id == project_id).first()
            if not proj:
                return {"success": False, "error": f"Project with ID {project_id} not found."}
                
            is_member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.employee_id == user_id
            ).first() is not None
            
            if not (user_role in ["Admin", "Project Manager"] or proj.project_manager_id == user_id or is_member):
                return {"success": False, "error": "Unauthorized: You do not have permission to view tasks for this project."}
                
            tasks = db.query(Task).filter(
                Task.project_id == project_id,
                Task.status.in_(["To-Do", "In-Progress", "todo", "in_progress"])
            ).all()
            
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
        """Finance Tool: Get budget summaries. Restrict to Admin, HR Manager, or PMs."""
        logger.info(f"Tool execution: get_budget_information on department {department_id}")
        
        user_role = user_context.get("role", "Employee")
        if user_role not in ["Admin", "HR Manager", "Project Manager"]:
            return {"success": False, "error": "Unauthorized: You do not have permissions to access corporate budget sheets."}
            
        db: Session = SessionLocal()
        try:
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
        Analytics Tool: Execute custom SQL analytics queries.
        Restricted to Admin or AI Administrator. Strictly blocks modifications and sensitive columns.
        """
        logger.info(f"Tool execution: execute_authorized_sql on query: '{sql_query}'")
        
        user_role = user_context.get("role", "Employee")
        if user_role not in ["Admin", "AI Administrator"]:
            return {"success": False, "error": "Unauthorized: SQL analytics engine is restricted to Admin or AI Administrators."}
            
        # 1. SQL Guardrails: Allow only SELECT
        clean_query = sql_query.strip().lower()
        if not clean_query.startswith("select"):
            return {"success": False, "error": "Query Violation: Only read-only SELECT queries are authorized."}
            
        # 2. Block mutating actions
        mutating_keywords = ["insert", "update", "delete", "drop", "alter", "truncate", "create", "grant", "revoke"]
        for kw in mutating_keywords:
            if re.search(r"\b" + kw + r"\b", clean_query):
                return {"success": False, "error": f"Query Violation: Mutating keyword '{kw.upper()}' is forbidden."}
                
        # 3. Prevent non-admin role checking payroll
        if "payroll" in clean_query and user_role != "Admin":
            return {"success": False, "error": "Query Violation: Access to payroll ledger table is restricted to senior Administrators."}
            
        db: Session = SessionLocal()
        try:
            # Bind text wrapper
            stmt = text(sql_query)
            res = db.execute(stmt)
            
            # Limit rows
            rows = res.fetchmany(50)
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
                
            return {
                "success": True,
                "columns": columns,
                "rows": serialized_rows,
                "row_count": len(serialized_rows)
            }
        except Exception as e:
            return {"success": False, "error": f"SQL Database execution failed: {str(e)}"}
        finally:
            db.close()
