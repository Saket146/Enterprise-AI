import logging
from typing import List, Optional, Tuple
from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.models import Employee, Role, AuditLog
from app.authentication.security import decode_access_token
from app.security.permissions import (
    Perm, build_user_context, current_viewer, role_has, role_has_any,
)

logger = logging.getLogger(__name__)

# Configures OAuth2 token scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Employees with these statuses can no longer use the system.
BLOCKED_EMPLOYMENT_STATUSES = {"resigned", "terminated", "inactive"}


def _authenticate(token: Optional[str], db: Session) -> Tuple[Employee, dict]:
    """Validate the JWT and load the employee together with their security context."""
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

    # The role is always read from the database, never trusted from the token,
    # so a role change or a departure takes effect immediately.
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if employee is None or employee.email != email:
        raise credentials_exception

    if (employee.employment_status or "").strip().lower() in BLOCKED_EMPLOYMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is no longer active."
        )

    return employee, build_user_context(employee)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Employee:
    """Dependency that extracts the current logged-in employee from the JWT token."""
    employee, viewer = await run_in_threadpool(_authenticate, token, db)
    # Remember who is asking so response schemas can mask sensitive fields.
    current_viewer.set(viewer)
    return employee


def _role_name(user: Employee) -> Optional[str]:
    return user.role.role_name if user.role else None


class PermissionChecker:
    """
    Dependency that allows the request only if the user's job role holds one of
    the given permissions (see app.security.permissions.ROLE_PERMISSIONS).
    """
    def __init__(self, *permissions: str):
        self.permissions = permissions

    def __call__(self, current_user: Employee = Depends(get_current_user)) -> Employee:
        role_name = _role_name(current_user)
        if not role_has_any(role_name, self.permissions):
            logger.warning(
                f"Access denied to employee {current_user.employee_id} ({role_name}). "
                f"Required permission: {self.permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Your role ({role_name or 'none'}) does not have permission for this action."
            )
        return current_user


def require(*permissions: str) -> PermissionChecker:
    """Shorthand: Depends(require(Perm.FINANCE_READ))."""
    return PermissionChecker(*permissions)


class RoleChecker:
    """
    Dependency checker that validates if the user role matches any allowed role names.
    Kept for backwards compatibility - prefer `require(Perm.X)`.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.lower() for r in allowed_roles]

    def __call__(self, current_user: Employee = Depends(get_current_user)) -> Employee:
        if not current_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no assigned security role."
            )

        role_name = current_user.role.role_name

        # System administrators pass every check
        if role_has(role_name, Perm.ALL):
            return current_user

        if role_name.lower() not in self.allowed_roles:
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
