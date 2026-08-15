import logging
import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.configuration.config import settings
from app.database.connection import SessionLocal, engine
from app.models.models import Role, Employee
from app.authentication.security import get_password_hash

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Enterprise AI Operating System: A Guardrailed Multi-Agent Intelligence Platform for Enterprise Automation"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Exception handlers
@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception caught on request {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred."}
    )

# Request duration middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Database auto-patch and default seeds on startup
@app.on_event("startup")
def startup_db_setup():
    logger.info("Verifying database schema and patching missing fields...")
    db: Session = SessionLocal()
    try:
        # 1. Alter Employee table to add hashed_password if missing
        db.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);"))
        db.commit()
        logger.info("Database schema verification completed (hashed_password column is present).")

        # 2. Seed Default Roles if missing
        required_roles = ["Admin", "HR Manager", "Project Manager", "Employee", "AI Administrator"]
        for r_name in required_roles:
            exists = db.query(Role).filter(Role.role_name == r_name).first()
            if not exists:
                logger.info(f"Seeding default role: {r_name}")
                new_role = Role(
                    role_name=r_name,
                    role_level="standard" if r_name == "Employee" else "managerial",
                    description=f"{r_name} security role."
                )
                db.add(new_role)
        db.commit()

        # 3. Handle passwords for imported/seeded employees
        # Check if there are employees with null passwords, and set a default 'password123'
        unsecured_employees = db.query(Employee).filter(
            (Employee.hashed_password.is_(None)) | (Employee.hashed_password == "")
        ).all()
        
        if unsecured_employees:
            logger.info(f"Found {len(unsecured_employees)} employees without passwords. Seeding default 'password123' password...")
            default_hashed = get_password_hash("password123")
            for emp in unsecured_employees:
                emp.hashed_password = default_hashed
                
                # Make sure employees have a default role if role_id is null
                if not emp.role_id:
                    # Assign standard 'Employee' role
                    emp_role = db.query(Role).filter(Role.role_name == "Employee").first()
                    if emp_role:
                        emp.role_id = emp_role.role_id
                        
            db.commit()
            logger.info("Successfully updated password hashes for all employees.")

        # 4. Ensure at least one Admin user exists
        admin_role = db.query(Role).filter(Role.role_name == "Admin").first()
        admin_user = db.query(Employee).filter(Employee.role_id == admin_role.role_id).first() if admin_role else None
        if not admin_user and admin_role:
            logger.info("Creating default system admin account...")
            default_admin = Employee(
                first_name="System",
                last_name="Administrator",
                email="admin@enterprise.com",
                phone="000-000-0000",
                hashed_password=get_password_hash("adminpass"),
                role_id=admin_role.role_id,
                employment_status="Active"
            )
            db.add(default_admin)
            db.commit()
            logger.info("Admin account 'admin@enterprise.com' created (Password: 'adminpass').")
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error during startup database configuration: {e}", exc_info=True)
    finally:
        db.close()

# Import and mount API routers
from app.api.auth import router as auth_router
from app.api.employees import router as employee_router
from app.api.projects import router as project_router
from app.api.knowledge import router as knowledge_router
from app.api.communications import router as comms_router
from app.api.ingestion import router as ingestion_router

app.include_router(auth_router)
app.include_router(employee_router)
app.include_router(project_router)
app.include_router(knowledge_router)
app.include_router(comms_router)
app.include_router(ingestion_router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "api_version": settings.PROJECT_VERSION,
        "docs_url": "/docs"
    }
