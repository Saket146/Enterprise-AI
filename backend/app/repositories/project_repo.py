from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.repositories.base import BaseRepository
from app.models.models import Project, Task, Milestone

class ProjectRepository(BaseRepository[Project]):
    def __init__(self):
        super().__init__(Project)

    def search_projects(
        self,
        db: Session,
        *,
        search_query: Optional[str] = None,
        department_id: Optional[int] = None,
        manager_id: Optional[int] = None,
        client_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Project], int]:
        """Search projects with custom filters and search patterns. Returns list and total count."""
        query = db.query(Project)
        
        # Apply filters
        if department_id:
            query = query.filter(Project.department_id == department_id)
        if manager_id:
            query = query.filter(Project.project_manager_id == manager_id)
        if client_id:
            query = query.filter(Project.client_id == client_id)
        if status:
            query = query.filter(Project.status == status)
            
        # Apply search string matching project name, code, or description
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                or_(
                    Project.project_name.ilike(search_pattern),
                    Project.project_code.ilike(search_pattern),
                    Project.description.ilike(search_pattern)
                )
            )
            
        total = query.count()
        results = query.offset(skip).limit(limit).all()
        return results, total

    def get_project_tasks(
        self,
        db: Session,
        project_id: int,
        status: Optional[str] = None,
        assigned_to: Optional[int] = None
    ) -> List[Task]:
        """Retrieve tasks belonging to a project with filters."""
        query = db.query(Task).filter(Task.project_id == project_id)
        if status:
            query = query.filter(Task.status == status)
        if assigned_to:
            query = query.filter(Task.assigned_to == assigned_to)
        return query.all()

    def get_project_milestones(
        self,
        db: Session,
        project_id: int,
        status: Optional[str] = None
    ) -> List[Milestone]:
        """Retrieve milestones belonging to a project."""
        query = db.query(Milestone).filter(Milestone.project_id == project_id)
        if status:
            query = query.filter(Milestone.status == status)
        return query.order_index_by(Milestone.due_date) if hasattr(query, 'order_index_by') else query.order_by(Milestone.due_date).all()

project_repo = ProjectRepository()
