from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database.connection import get_db
from app.models.models import Employee, Role
from app.schemas.schemas import LoginRequest, Token, EmployeeCreate, EmployeeResponse
from app.authentication.security import get_password_hash, verify_password, create_access_token
from app.middleware.rbac import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def register_employee(employee_in: EmployeeCreate, db: Session = Depends(get_db)):
    """Register a new employee record and set a password."""
    # Check if email is already in use
    existing = db.query(Employee).filter(Employee.email == employee_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An employee with this email is already registered."
        )
        
    hashed_pwd = get_password_hash(employee_in.password)
    
    # Exclude password field from the create schemas
    data = employee_in.dict()
    data.pop("password")
    data["hashed_password"] = hashed_pwd
    
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
