from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.connection import get_db
from app.repositories.employee_repo import employee_repo
from app.schemas.schemas import EmployeeResponse, EmployeeListResponse, EmployeeUpdate
from app.middleware.rbac import get_current_user, require
from app.models.models import Employee, Role
from app.security.permissions import Perm, SYSTEM_ROLES, role_has

router = APIRouter(prefix="/api/employees", tags=["Employee Management"])

# Setup RBAC guards
# Reading the directory is open to every employee; salary, phone and date of birth are
# masked in EmployeeResponse unless the viewer is the employee, their manager, or HR.
can_delete_employees = require(Perm.EMPLOYEE_DELETE)
can_manage_employees = require(Perm.EMPLOYEE_MANAGE)

@router.get("", response_model=EmployeeListResponse)
def get_employees(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Search by name, email or location"),
    department_id: Optional[int] = Query(None),
    role_id: Optional[int] = Query(None),
    manager_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Retrieve lists of employees with criteria filters and offset pagination."""
    items, total = employee_repo.search_employees(
        db,
        search_query=search,
        department_id=department_id,
        role_id=role_id,
        manager_id=manager_id,
        status=status,
        skip=skip,
        limit=limit
    )
    return {"total": total, "items": items}

@router.get("/hierarchy")
def get_organizational_chart(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Retrieve full corporate hierarchy reporting relationships for graphing."""
    return employee_repo.get_hierarchy_tree(db)

@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee_by_id(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Fetch employee node details by database key."""
    emp = employee_repo.get_by_id(db, employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found."
        )
    return emp

@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    update_data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(can_manage_employees)
):
    """Update employee details. Restricted to HR roles (employees:manage)."""
    emp = employee_repo.get_by_id(db, employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found."
        )
    
    changes = update_data.dict(exclude_unset=True)

    # Changing a job role changes what that person can access - guard against privilege escalation.
    new_role_id = changes.get("role_id")
    if new_role_id is not None and new_role_id != emp.role_id:
        actor_role = current_user.role.role_name if current_user.role else None
        is_admin = role_has(actor_role, Perm.ALL)
        new_role = db.query(Role).filter(Role.role_id == new_role_id).first()
        if not new_role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role_id.")
        if employee_id == current_user.employee_id and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot change your own role.")
        if new_role.role_name.lower() in SYSTEM_ROLES and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a system administrator can assign administrator roles."
            )

    updated_emp = employee_repo.update(db, db_obj=emp, obj_in=changes)
    return updated_emp

@router.delete("/{employee_id}", response_model=EmployeeResponse)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(can_delete_employees)
):
    """Delete employee details. Restricted to roles holding employees:delete."""
    emp = employee_repo.get_by_id(db, employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found."
        )
    
    deleted_emp = employee_repo.delete(db, id=employee_id)
    return deleted_emp
