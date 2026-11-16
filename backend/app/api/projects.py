from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.connection import get_db
from app.repositories.project_repo import project_repo
from app.schemas.schemas import ProjectResponse, TaskResponse, MilestoneResponse
from app.middleware.rbac import get_current_user
from app.models.models import Employee
from app.security.permissions import Perm, build_user_context, role_has
from app.services.sql_retriever import postgres_retriever

router = APIRouter(prefix="/api/projects", tags=["Project Management"])

# RBAC helpers
def _sees_all_projects(user: Employee) -> bool:
    return role_has(user.role.role_name if user.role else None, Perm.PROJECTS_READ_ALL)


def _get_visible_project(db: Session, project_id: int, user: Employee):
    """
    Load a project and enforce access: roles with projects:read_all see every project,
    everyone else only projects they manage, are a member of, or have tasks on.
    """
    proj = project_repo.get_by_id(db, project_id)
    if not proj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found."
        )
    if not postgres_retriever.can_view_project(db, proj, build_user_context(user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view projects you manage or work on."
        )
    return proj

@router.get("", response_model=List[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Search project name, code, description"),
    department_id: Optional[int] = Query(None),
    manager_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """List projects matching filter parameters with offset pagination (only projects the user may see)."""
    visible_ids = None
    if not _sees_all_projects(current_user):
        visible_ids = sorted(postgres_retriever.user_project_ids(db, current_user.employee_id))

    projects, _ = project_repo.search_projects(
        db,
        search_query=search,
        department_id=department_id,
        manager_id=manager_id,
        client_id=client_id,
        status=status,
        visible_project_ids=visible_ids,
        skip=skip,
        limit=limit
    )
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_by_id(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Fetch project details by database ID."""
    proj = _get_visible_project(db, project_id, current_user)
    return proj

@router.get("/{project_id}/tasks", response_model=List[TaskResponse])
def get_project_tasks(
    project_id: int,
    status: Optional[str] = Query(None),
    assigned_to: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Retrieve tasks belonging to a project with optional filters."""
    proj = _get_visible_project(db, project_id, current_user)
    return project_repo.get_project_tasks(db, project_id, status=status, assigned_to=assigned_to)

@router.get("/{project_id}/milestones", response_model=List[MilestoneResponse])
def get_project_milestones(
    project_id: int,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Retrieve milestones belonging to a project."""
    proj = _get_visible_project(db, project_id, current_user)
    return project_repo.get_project_milestones(db, project_id, status=status)
