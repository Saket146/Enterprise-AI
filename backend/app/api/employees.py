from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.connection import get_db
from app.repositories.employee_repo import employee_repo
from app.schemas.schemas import EmployeeResponse, EmployeeListResponse, EmployeeUpdate
from app.middleware.rbac import get_current_user, RoleChecker
from app.models.models import Employee

router = APIRouter(prefix="/api/employees", tags=["Employee Management"])

# Setup RBAC guards
admin_only = RoleChecker(allowed_roles=["Admin"])
hr_or_admin = RoleChecker(allowed_roles=["Admin", "HR Manager"])

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
    current_user: Employee = Depends(hr_or_admin)
):
    """Update employee details. Restrict to Admin or HR Managers."""
    emp = employee_repo.get_by_id(db, employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found."
        )
    
    updated_emp = employee_repo.update(db, db_obj=emp, obj_in=update_data.dict(exclude_unset=True))
    return updated_emp

@router.delete("/{employee_id}", response_model=EmployeeResponse)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(admin_only)
):
    """Delete employee details. Restrict to Admins only."""
    emp = employee_repo.get_by_id(db, employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found."
        )
    
    deleted_emp = employee_repo.delete(db, id=employee_id)
    return deleted_emp
