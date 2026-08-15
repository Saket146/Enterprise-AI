from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.repositories.base import BaseRepository
from app.models.models import Employee, Department, Role

class EmployeeRepository(BaseRepository[Employee]):
    def __init__(self):
        super().__init__(Employee)

    def search_employees(
        self,
        db: Session,
        *,
        search_query: Optional[str] = None,
        department_id: Optional[int] = None,
        role_id: Optional[int] = None,
        manager_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Employee], int]:
        """Search employees with filters and query strings. Returns list of matches and total count."""
        query = db.query(Employee)
        
        # Apply filters
        if department_id:
            query = query.filter(Employee.department_id == department_id)
        if role_id:
            query = query.filter(Employee.role_id == role_id)
        if manager_id:
            query = query.filter(Employee.manager_id == manager_id)
        if status:
            query = query.filter(Employee.employment_status == status)
            
        # Apply search string matching name, email or location
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                or_(
                    Employee.first_name.ilike(search_pattern),
                    Employee.last_name.ilike(search_pattern),
                    Employee.email.ilike(search_pattern),
                    Employee.office_location.ilike(search_pattern)
                )
            )
            
        total = query.count()
        results = query.offset(skip).limit(limit).all()
        return results, total

    def get_subordinates(self, db: Session, employee_id: int) -> List[Employee]:
        """Get list of employees reporting directly to this employee."""
        return db.query(Employee).filter(Employee.manager_id == employee_id).all()

    def get_hierarchy_tree(self, db: Session) -> List[dict]:
        """Retrieve executive leaders and child mappings for rendering reporting trees."""
        # Find CEOs/executives who have no managers or manage themselves
        execs = db.query(Employee).filter(
            or_(
                Employee.manager_id.is_(None),
                Employee.manager_id == Employee.employee_id
            )
        ).all()
        
        tree = []
        for ex in execs:
            tree.append(self._build_node(db, ex))
        return tree

    def _build_node(self, db: Session, employee: Employee) -> dict:
        """Helper to recursively build employee hierarchy nodes."""
        # Simple recursion limit is handled naturally by organizational hierarchy depth
        subordinates = db.query(Employee).filter(
            Employee.manager_id == employee.employee_id,
            Employee.employee_id != employee.manager_id # Avoid infinite loop
        ).all()
        
        node = {
            "employee_id": employee.employee_id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "role": employee.role.role_name if employee.role else None,
            "department": employee.department.department_name if employee.department else None,
            "subordinates": [self._build_node(db, sub) for sub in subordinates]
        }
        return node

employee_repo = EmployeeRepository()
