import logging
from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.models import Employee, Role, AuditLog
from app.authentication.security import decode_access_token

logger = logging.getLogger(__name__)

# Configures OAuth2 token scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Employee:
    """Dependency that extracts the current logged-in employee from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
        
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    email: str = payload.get("email")
    employee_id: int = payload.get("employee_id")
    if email is None or employee_id is None:
        raise credentials_exception
        
    # Query database to get latest status and relationships
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if employee is None:
        raise credentials_exception
        
    return employee

class RoleChecker:
    """Dependency checker that validates if the user role matches any allowed roles."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Employee = Depends(get_current_user)) -> Employee:
        if not current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no assigned security role."
            )
            
        role_name = current_user.role.role_name
        
        # Admin bypasses most checks, otherwise check allowed list
        if role_name == "Admin":
            return current_user
            
        if role_name not in self.allowed_roles:
            logger.warning(f"Access denied to employee {current_user.employee_id} ({role_name}). Required roles: {self.allowed_roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
            )
            
        return current_user

def log_audit_action(
    db: Session,
    employee_id: int,
    action_type: str,
    resource_type: str,
    resource_id: int,
    ip_address: str = "0.0.0.0",
    details: str = ""
):
    """Write log entry to PostgreSQL audit logs table."""
    try:
        audit_entry = AuditLog(
            employee_id=employee_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record audit log: {e}")
