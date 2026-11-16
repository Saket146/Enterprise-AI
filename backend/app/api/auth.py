from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database.connection import get_db
from app.models.models import Employee, Role
from app.schemas.schemas import LoginRequest, Token, EmployeeCreate, EmployeeResponse
from app.authentication.security import get_password_hash, verify_password, create_access_token
from app.middleware.rbac import get_current_user, require, BLOCKED_EMPLOYMENT_STATUSES
from app.security.permissions import Perm, SYSTEM_ROLES, permissions_for, role_has

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def register_employee(
    employee_in: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require(Perm.EMPLOYEE_MANAGE))
):
    """
    Register a new employee record and set a password.
    Restricted to HR roles: an open sign-up endpoint would let anyone create an
    account and read the company directory.
    """
    # Check if email is already in use
    existing = db.query(Employee).filter(Employee.email == employee_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An employee with this email is already registered."
        )
        
    hashed_pwd = get_password_hash(employee_in.password)
    
    data = employee_in.dict()
    data.pop("password")
    requested_role_id = data.pop("role_id", None)
    data["hashed_password"] = hashed_pwd

    # The job role decides what the new account can access, so it is validated here.
    if requested_role_id is not None:
        employee_role = db.query(Role).filter(Role.role_id == requested_role_id).first()
        if not employee_role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role_id.")
        actor_role = current_user.role.role_name if current_user.role else None
        if employee_role.role_name.lower() in SYSTEM_ROLES and not role_has(actor_role, Perm.ALL):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a system administrator can assign administrator roles."
            )
    else:
        employee_role = db.query(Role).filter(Role.role_name == "Employee").first()
        if not employee_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default Employee role is not configured."
            )
    data["role_id"] = employee_role.role_id
    
    db_employee = Employee(**data)
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate employee credentials and return a bearer JWT access token."""
    employee = db.query(Employee).filter(Employee.email == login_data.email).first()
    if not employee or not verify_password(login_data.password, employee.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if (employee.employment_status or "").strip().lower() in BLOCKED_EMPLOYMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is no longer active."
        )

    role_name = employee.role.role_name if employee.role else "Employee"
    
    # Generate token payload
    token_payload = {
        "email": employee.email,
        "employee_id": employee.employee_id,
        "role": role_name
    }
    
    access_token = create_access_token(data=token_payload)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        employee_id=employee.employee_id,
        email=employee.email,
        role=role_name,
        first_name=employee.first_name,
        last_name=employee.last_name
    )

@router.get("/profile", response_model=EmployeeResponse)
def get_profile(current_user: Employee = Depends(get_current_user)):
    """Fetch profile details of the currently authenticated session employee."""
    return current_user


@router.get("/permissions")
def get_permissions(current_user: Employee = Depends(get_current_user)):
    """
    The job role of the current user and what it is allowed to do.
    The frontend uses this to show only the sections the user can actually use;
    the real enforcement always happens on the server.
    """
    role_name = current_user.role.role_name if current_user.role else "Employee"
    granted = permissions_for(role_name)
    is_admin = Perm.ALL in granted
    all_permissions = sorted(v for k, v in vars(Perm).items() if k.isupper() and v != Perm.ALL)
    return {
        "employee_id": current_user.employee_id,
        "role": role_name,
        "is_admin": is_admin,
        "permissions": all_permissions if is_admin else sorted(granted),
    }
