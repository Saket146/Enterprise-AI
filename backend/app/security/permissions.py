"""
Job-role based access control (RBAC).

Every employee has exactly one row in the `roles` table (their job role: CEO,
HR Director, Backend Engineer, ...).  This module is the single place that
says what each job role is allowed to do.  API routes, agent tools, the SQL
analytics guard and the vector search all ask this module instead of
comparing role names themselves.

To change who can do what, edit ROLE_PERMISSIONS below - nothing else.
"""
import logging
from contextvars import ContextVar
from typing import Any, Dict, FrozenSet, Iterable, Optional

logger = logging.getLogger(__name__)


class Perm:
    """Permission names. A role holds a set of these."""
    # Everyone who can log in
    DIRECTORY_READ = "directory:read"            # names, job role, department, manager, office, work email
    # Company policies and documents (Knowledge Explorer)
    KNOWLEDGE_LIST = "knowledge:list_titles"     # see that a policy/document exists: title, type, version, owner
    POLICY_CONTENT = "policies:read_content"     # open any policy and read its text
    DOCUMENT_CONTENT = "documents:read_content"  # open any document and read its text (others request access per document)

    # HR
    EMPLOYEE_SENSITIVE = "employees:read_sensitive"   # salary, date of birth, phone, payroll, reviews, leave
    EMPLOYEE_MANAGE = "employees:manage"              # create / update employee records
    EMPLOYEE_DELETE = "employees:delete"

    # Projects
    PROJECTS_READ_ALL = "projects:read_all"      # every project, task, milestone, meeting (others see only their own)

    # Finance
    FINANCE_READ = "finance:read"                # all budgets, expenses, invoices, vendors
    FINANCE_READ_OWN_DEPT = "finance:read_own_department"  # budget of the user's own department only

    # Sales
    SALES_READ = "sales:read"                    # clients and contracts

    # Analytics / AI operations
    ANALYTICS_OVERVIEW = "analytics:overview"    # management dashboard
    APPROVE_HR = "approvals:hr"                  # decide HR workflow approvals
    APPROVE_AI = "approvals:ai"                  # decide document-intake / AI approvals
    APPROVE_DOCUMENT_ACCESS = "approvals:document_access"  # decide requests to read a document (system administrators)
    SYSTEM_INGEST = "system:ingest"              # rebuild Qdrant / Neo4j from PostgreSQL
    SYSTEM_MONITOR = "system:monitor"            # monitoring dashboard, agent logs, audit logs
    SYSTEM_EVALUATE = "system:evaluate"          # run evaluation suites
    PRIVATE_COMMS_ALL = "communications:read_all"  # other people's emails and chat sessions

    ALL = "*"                                    # system administrator


# Granted to every authenticated employee, whatever their job role.
BASE_PERMISSIONS: FrozenSet[str] = frozenset({
    Perm.DIRECTORY_READ, Perm.KNOWLEDGE_LIST, Perm.POLICY_CONTENT,
})

# Everyone except Interns reads all policies and sees document titles.  To read a document they
# ask for access to it in the Operations Center, and a system administrator decides.

# Interns: the employee directory only. They cannot see policies or documents at all, not even titles.
INTERN_PERMISSIONS: FrozenSet[str] = frozenset({Perm.DIRECTORY_READ})

# Roles allowed to open every document without asking (system administrators always can).
KNOWLEDGE_READER_ROLES = "the CEO, CTO, CFO or a system administrator"


def _role(*perms: str) -> FrozenSet[str]:
    return BASE_PERMISSIONS | frozenset(perms)


# Keys are role names from the `roles` table, lower-cased.
ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    # ---- Executives -------------------------------------------------
    "ceo": _role(
        Perm.DOCUMENT_CONTENT, Perm.EMPLOYEE_SENSITIVE, Perm.PROJECTS_READ_ALL, Perm.FINANCE_READ, Perm.SALES_READ,
        Perm.ANALYTICS_OVERVIEW, Perm.APPROVE_HR, Perm.APPROVE_AI, Perm.SYSTEM_MONITOR,
    ),
    "cto": _role(
        Perm.DOCUMENT_CONTENT, Perm.PROJECTS_READ_ALL, Perm.FINANCE_READ, Perm.ANALYTICS_OVERVIEW, Perm.APPROVE_AI,
        Perm.SYSTEM_INGEST, Perm.SYSTEM_MONITOR, Perm.SYSTEM_EVALUATE,
    ),
    "cfo": _role(
        Perm.DOCUMENT_CONTENT, Perm.EMPLOYEE_SENSITIVE, Perm.PROJECTS_READ_ALL, Perm.FINANCE_READ, Perm.SALES_READ,
        Perm.ANALYTICS_OVERVIEW,
    ),
    # ---- HR ---------------------------------------------------------
    "hr director": _role(
        Perm.EMPLOYEE_SENSITIVE, Perm.EMPLOYEE_MANAGE, Perm.EMPLOYEE_DELETE,
        Perm.APPROVE_HR, Perm.ANALYTICS_OVERVIEW,
    ),
    "hr executive": _role(Perm.EMPLOYEE_SENSITIVE, Perm.EMPLOYEE_MANAGE, Perm.APPROVE_HR),
    # ---- Managers ---------------------------------------------------
    "engineering manager": _role(
        Perm.PROJECTS_READ_ALL, Perm.FINANCE_READ_OWN_DEPT, Perm.ANALYTICS_OVERVIEW,
    ),
    "project manager": _role(
        Perm.PROJECTS_READ_ALL, Perm.SALES_READ, Perm.FINANCE_READ_OWN_DEPT, Perm.ANALYTICS_OVERVIEW,
    ),
    # ---- Specialists ------------------------------------------------
    "finance analyst": _role(Perm.FINANCE_READ, Perm.SALES_READ),
    "sales executive": _role(Perm.SALES_READ),
    "ai engineer": _role(Perm.SYSTEM_MONITOR, Perm.SYSTEM_EVALUATE),
    "data scientist": _role(Perm.ANALYTICS_OVERVIEW),
    # ---- Individual contributors: base access only ------------------
    "backend engineer": _role(),
    "frontend engineer": _role(),
    "qa engineer": _role(),
    "intern": INTERN_PERMISSIONS,
    # ---- System (non-job) roles created by the application ----------
    "admin": frozenset({Perm.ALL}),
    "ai administrator": _role(
        Perm.SYSTEM_INGEST, Perm.SYSTEM_MONITOR, Perm.SYSTEM_EVALUATE,
        Perm.APPROVE_AI, Perm.ANALYTICS_OVERVIEW,
    ),
    # ---- Legacy names kept so older rows keep working ---------------
    "hr manager": _role(
        Perm.EMPLOYEE_SENSITIVE, Perm.EMPLOYEE_MANAGE, Perm.APPROVE_HR, Perm.ANALYTICS_OVERVIEW,
    ),
    "employee": _role(),
}

# Roles that only a system administrator may hand out.
SYSTEM_ROLES = frozenset({"admin", "ai administrator"})


def permissions_for(role_name: Optional[str]) -> FrozenSet[str]:
    """Permissions of a job role. Unknown or missing roles get base access only."""
    key = (role_name or "").strip().lower()
    perms = ROLE_PERMISSIONS.get(key)
    if perms is None:
        if key:
            logger.warning(f"RBAC: role '{role_name}' is not in ROLE_PERMISSIONS; granting base access only.")
        return BASE_PERMISSIONS
    return perms


def role_has(role_name: Optional[str], permission: str) -> bool:
    perms = permissions_for(role_name)
    return Perm.ALL in perms or permission in perms


def role_has_any(role_name: Optional[str], permissions: Iterable[str]) -> bool:
    return any(role_has(role_name, p) for p in permissions)


def can(user_context: Optional[Dict[str, Any]], permission: str) -> bool:
    """Check a permission for an agent/user context dict ({'employee_id', 'role', 'department_id'})."""
    if not user_context:
        return False
    return role_has(user_context.get("role"), permission)


def can_any(user_context: Optional[Dict[str, Any]], permissions: Iterable[str]) -> bool:
    return any(can(user_context, p) for p in permissions)


def build_user_context(employee) -> Dict[str, Any]:
    """Security context handed to agents, tools and retrieval for one employee."""
    role_name = employee.role.role_name if getattr(employee, "role", None) else None
    return {
        "employee_id": employee.employee_id,
        "role": role_name or "Employee",
        "department_id": employee.department_id,
        "name": f"{employee.first_name} {employee.last_name}",
    }


def policy_access(user_context: Optional[Dict[str, Any]]) -> str:
    """
    What a user may see of company policies:
      "content" - open and read every policy (every role except Intern)
      "none"    - nothing, not even titles (Intern)
    """
    if can(user_context, Perm.KNOWLEDGE_LIST) and can(user_context, Perm.POLICY_CONTENT):
        return "content"
    return "titles" if can(user_context, Perm.KNOWLEDGE_LIST) else "none"


def document_access(user_context: Optional[Dict[str, Any]]) -> str:
    """
    What a user may see of company documents by role alone:
      "content" - open and read every document (CEO, CTO, CFO, system administrators)
      "titles"  - titles and listing details; a single document opens after an approved access request
      "none"    - nothing, not even titles (Intern)
    """
    if can(user_context, Perm.DOCUMENT_CONTENT):
        return "content"
    return "titles" if can(user_context, Perm.KNOWLEDGE_LIST) else "none"


def can_view_employee_sensitive(
    viewer: Optional[Dict[str, Any]],
    employee_id: Optional[int],
    manager_id: Optional[int] = None,
) -> bool:
    """
    Salary, date of birth and phone of an employee are visible to: the employee,
    their direct manager, and roles holding EMPLOYEE_SENSITIVE.
    """
    if not viewer:
        return False
    viewer_id = viewer.get("employee_id")
    if viewer_id is not None and viewer_id == employee_id:
        return True
    if viewer_id is not None and manager_id is not None and viewer_id == manager_id:
        return True
    return can(viewer, Perm.EMPLOYEE_SENSITIVE)


# The employee making the current HTTP request.  Set by
# app.middleware.rbac.get_current_user and read by the response schemas so
# sensitive employee fields are masked wherever an employee is serialised.
current_viewer: ContextVar[Optional[Dict[str, Any]]] = ContextVar("current_viewer", default=None)
