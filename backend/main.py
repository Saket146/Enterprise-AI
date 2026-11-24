import os
from pathlib import Path
from typing import Optional
import logging
import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.configuration.config import settings
from app.database.connection import SessionLocal, engine, check_dependencies
from app.security.permissions import ROLE_PERMISSIONS
from app.models.models import Role, Employee
from app.authentication.security import get_password_hash
from app.observability import metrics
from app.database.connection import Base

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
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=False,
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
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    metrics.record(request.url.path, process_time * 1000, response.status_code)
    return response

# Database auto-patch and default seeds on startup
@app.on_event("startup")
def startup_db_setup():
    logger.info("Verifying database schema and patching missing fields...")
    db: Session = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        # 1. Alter Employee table to add hashed_password if missing
        db.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);"))
        db.commit()
        logger.info("Database schema verification completed (hashed_password column is present).")

        # 1b. Synchronize PostgreSQL primary key sequences with existing data.
        # This must run BEFORE anything is inserted below: data imported with explicit ids
        # (CSV / SQL seed) leaves the sequences at 1, and the next INSERT would collide
        # with an existing primary key and abort the whole startup routine.
        tables_with_pks = [
            ("departments", "department_id"),
            ("roles", "role_id"),
            ("employees", "employee_id"),
            ("clients", "client_id"),
            ("contracts", "contract_id"),
            ("projects", "project_id"),
            ("project_members", "project_member_id"),
            ("tasks", "task_id"),
            ("milestones", "milestone_id"),
            ("documents", "document_id"),
            ("meetings", "meeting_id"),
            ("emails", "email_id"),
            ("policies", "policy_id"),
            ("attendance", "attendance_id"),
            ("leave_requests", "leave_id"),
            ("payroll", "payroll_id"),
            ("performance_reviews", "review_id"),
            ("vendors", "vendor_id"),
            ("budgets", "budget_id"),
            ("expenses", "expense_id"),
            ("invoices", "invoice_id"),
            ("chat_sessions", "session_id"),
            ("workflow_runs", "workflow_id"),
            ("agent_logs", "agent_log_id"),
            ("audit_logs", "audit_id"),
            ("approvals", "approval_id"),
            ("evaluation_runs", "evaluation_id"),
        ]
        for tbl, pk in tables_with_pks:
            try:
                # Savepoint: a missing table must not poison the surrounding transaction
                with db.begin_nested():
                    db.execute(text(f"SELECT setval(pg_get_serial_sequence('{tbl}', '{pk}'), COALESCE((SELECT MAX({pk}) FROM {tbl}), 1));"))
            except Exception as seq_err:
                logger.debug(f"Sequence sync skipped for {tbl}: {seq_err}")
        db.commit()

        # 2. Seed the system (non-job) roles if missing.  Job roles such as CEO,
        # HR Director or Backend Engineer come from the company data in the roles
        # table; what each one may do is defined in app/security/permissions.py.
        required_roles = ["Admin", "AI Administrator", "Employee"]
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

        # 2b. Report job roles that have no entry in the permission matrix
        # (they still work, but only with base access).
        unmapped = [
            r.role_name for r in db.query(Role).all()
            if (r.role_name or "").strip().lower() not in ROLE_PERMISSIONS
        ]
        if unmapped:
            logger.warning(
                f"RBAC: roles without an entry in ROLE_PERMISSIONS (base access only): {unmapped}. "
                "Add them to app/security/permissions.py to grant more."
            )

        # 3. Handle passwords for imported/seeded employees
        # Check if there are employees with null passwords, and set a default 'password123'
        unsecured_employees = db.query(Employee).filter(
            (Employee.hashed_password.is_(None)) | (Employee.hashed_password == "")
        ).all()
        
        if unsecured_employees:
            logger.info(f"Found {len(unsecured_employees)} employees without passwords. Seeding default 'password123' password...")
            default_hashed = get_password_hash("password123")
            emp_role = db.query(Role).filter(Role.role_name == "Employee").first()
            emp_role_id = emp_role.role_id if emp_role else None
            for emp in unsecured_employees:
                emp.hashed_password = default_hashed
                if not emp.role_id and emp_role_id:
                    emp.role_id = emp_role_id
            db.commit()
            logger.info("Successfully updated password hashes for all employees.")

        # 5. Ensure at least one Admin user exists
        admin_role = db.query(Role).filter(Role.role_name == "Admin").first()
        admin_user = db.query(Employee).filter(
            (Employee.role_id == admin_role.role_id) | (Employee.email == "admin@enterprise.com")
        ).first() if admin_role else None
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
            logger.warning("Admin account 'admin@enterprise.com' created with the default password - change it.")

        # 6. Report which of the four data stores are reachable
        for name, info in check_dependencies().items():
            if info["status"] == "online":
                logger.info(f"Data store '{name}': online")
            elif info["required"] == "true":
                logger.error(f"Data store '{name}': OFFLINE (required) - {info.get('error')}")
            else:
                logger.warning(
                    f"Data store '{name}': offline (optional) - the API keeps working without it. {info.get('error', '')}"
                )

        # 7. Language model, and secrets put in the template file by mistake
        from app.services.llm_service import llm_service
        llm = llm_service.status()
        if llm["provider"] == "mock":
            logger.warning("Language model: none configured - answers use the built-in writer. Set LLM_PROVIDER and the API key in backend/.env.")
        else:
            logger.info(f"Language model: {llm['provider']} ({llm['model']}). Use the Operations Center 'Test connection' button to check it.")
        _warn_about_secrets_in_template()

        if settings.JWT_SECRET_KEY == "enterprise_ai_os_secret_key_very_secure_change_me_in_prod":
            logger.warning("JWT_SECRET_KEY is still the built-in default. Set a private value in backend/.env.")
            
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
from app.api.workflows import router as workflows_router
from app.api.analytics import router as analytics_router
from app.api.monitoring import router as monitoring_router
from app.api.evaluations import router as evaluations_router

app.include_router(auth_router)
app.include_router(employee_router)
app.include_router(project_router)
app.include_router(knowledge_router)
app.include_router(comms_router)
app.include_router(ingestion_router)
app.include_router(workflows_router)
app.include_router(analytics_router)
app.include_router(monitoring_router)
app.include_router(evaluations_router)

@app.get("/health")
def health():
    return {"status": "healthy", "version": settings.PROJECT_VERSION}

def _warn_about_secrets_in_template():
    """backend/.env.example is committed to git and is NOT read by the backend; real secrets belong in backend/.env."""
    template = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.example")
    if not os.path.exists(template):
        return
    try:
        with open(template, encoding="utf-8-sig") as handle:
            lines = handle.read().splitlines()
    except Exception:
        return
    placeholders = ("", "replace-with-a-64-character-random-secret", "your-key", "your_api_key", "changeme")
    for line in lines:
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key in ("GEMINI_API_KEY", "OPENAI_API_KEY", "JWT_SECRET_KEY") and value.lower() not in placeholders:
            logger.warning(
                f"backend/.env.example contains a value for {key}. That file is a template that is committed to git, "
                f"and the backend does not read it. Move the value to backend/.env and empty it in .env.example."
            )


@app.get("/health/dependencies")
def health_dependencies():
    """Connectivity of PostgreSQL (required) and Redis, Qdrant, Neo4j (optional)."""
    report = check_dependencies()
    required_ok = all(v["status"] == "online" for v in report.values() if v["required"] == "true")
    all_ok = all(v["status"] == "online" for v in report.values())
    from app.services.llm_service import llm_service
    llm = llm_service.status()
    return {
        "status": "healthy" if all_ok else ("degraded" if required_ok else "unhealthy"),
        "dependencies": {name: {k: v for k, v in info.items() if k != "error"} for name, info in report.items()},
        # Last known state only (no call is made here): working | failing | untested | not_configured
        "language_model": {"provider": llm["provider"], "model": llm["model"], "state": llm["state"],
                           "avg_call_seconds": llm["avg_call_seconds"]},
    }

def _frontend_dist() -> Optional[Path]:
    """Folder with the built website (npm run build), or None when it has not been built."""
    candidates = [Path(settings.FRONTEND_DIST)] if settings.FRONTEND_DIST else []
    root = Path(__file__).resolve().parent.parent
    candidates += [root / "frontend" / "frontend" / "dist", root / "frontend" / "dist"]
    for folder in candidates:
        if (folder / "index.html").is_file():
            return folder.resolve()
    return None


FRONTEND_DIST = _frontend_dist()
API_PATHS = ("api/", "health", "docs", "redoc", "openapi.json")

if FRONTEND_DIST:
    # Production: the backend also serves the website, so the whole app runs on one address
    logger.warning(f"Serving the website from {FRONTEND_DIST}")

    @app.get("/", include_in_schema=False)
    def read_root():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def website(path: str):
        if path.startswith(API_PATHS):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        file = (FRONTEND_DIST / path).resolve()
        if file.is_file() and file.is_relative_to(FRONTEND_DIST):
            return FileResponse(file)
        # Page addresses such as /login belong to the single-page app
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/")
    def read_root():
        return {
            "status": "online",
            "service": settings.PROJECT_NAME,
            "api_version": settings.PROJECT_VERSION,
            "docs_url": "/docs",
            "website": "not built here: run the Vite dev server, or `npm run build` to let the backend serve it",
        }
