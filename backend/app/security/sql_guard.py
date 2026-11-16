"""
Guardrail for SQL produced by the Analytics Agent (or typed by a user).

A query is only executed when it is a single read-only SELECT over tables the
user's job role may read.  Sensitive columns are refused in the query text and
masked again in the result rows, so `SELECT *` cannot leak them either.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

from app.security.permissions import Perm, can, can_any

# Table -> permission needed to query it (None = every authenticated employee).
# A table that is not listed here cannot be queried at all.
TABLE_ACCESS: Dict[str, Optional[str]] = {
    "departments": None,
    "roles": None,
    "employees": None,
    "policies": Perm.KNOWLEDGE_LIST,
    "documents": Perm.KNOWLEDGE_LIST,
    "projects": Perm.PROJECTS_READ_ALL,
    "project_members": Perm.PROJECTS_READ_ALL,
    "tasks": Perm.PROJECTS_READ_ALL,
    "milestones": Perm.PROJECTS_READ_ALL,
    "meetings": Perm.PROJECTS_READ_ALL,
    "clients": Perm.SALES_READ,
    "contracts": Perm.SALES_READ,
    "budgets": Perm.FINANCE_READ,
    "expenses": Perm.FINANCE_READ,
    "invoices": Perm.FINANCE_READ,
    "vendors": Perm.FINANCE_READ,
    "payroll": Perm.EMPLOYEE_SENSITIVE,
    "performance_reviews": Perm.EMPLOYEE_SENSITIVE,
    "leave_requests": Perm.EMPLOYEE_SENSITIVE,
    "attendance": Perm.EMPLOYEE_SENSITIVE,
    "emails": Perm.PRIVATE_COMMS_ALL,
    "chat_sessions": Perm.PRIVATE_COMMS_ALL,
    "chat_messages": Perm.PRIVATE_COMMS_ALL,
    "workflow_requests": Perm.SYSTEM_MONITOR,
    "document_access_requests": Perm.SYSTEM_MONITOR,
    "workflow_runs": Perm.SYSTEM_MONITOR,
    "agent_logs": Perm.SYSTEM_MONITOR,
    "audit_logs": Perm.SYSTEM_MONITOR,
    "approvals": Perm.SYSTEM_MONITOR,
    "evaluation_runs": Perm.SYSTEM_MONITOR,
}

# Columns nobody may read through SQL analytics.
FORBIDDEN_COLUMNS = {"hashed_password"}

# Column -> permissions (any one is enough) needed to read it.
RESTRICTED_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "salary": (Perm.EMPLOYEE_SENSITIVE,),
    "date_of_birth": (Perm.EMPLOYEE_SENSITIVE,),
    "basic_salary": (Perm.EMPLOYEE_SENSITIVE,),
    "net_salary": (Perm.EMPLOYEE_SENSITIVE,),
    "bonus": (Perm.EMPLOYEE_SENSITIVE,),
    "budget": (Perm.FINANCE_READ, Perm.PROJECTS_READ_ALL),
}
# Columns that are restricted only when a particular table is part of the query.
TABLE_RESTRICTED_COLUMNS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    # `phone` is personal data only when it comes from the employees table
    "employees": {"phone": (Perm.EMPLOYEE_SENSITIVE,)},
    # The text of policies and documents may only be read by roles that can open them
    "policies": {"description": (Perm.POLICY_CONTENT,)},
    "documents": {"content": (Perm.DOCUMENT_CONTENT,)},
}


# Wording used when a query is refused
TABLE_LABELS = {"policies": "company policies and documents", "documents": "company policies and documents"}
COLUMN_LABELS = {"description": "the text of policies", "content": "the text of documents without an approved access request"}


def referenced_tables(sql: str) -> set:
    """Known enterprise tables named anywhere in the query."""
    identifiers = set(re.findall(r"[a-z_][a-z0-9_]*", _strip_literals((sql or "").lower())))
    return identifiers & set(TABLE_ACCESS.keys())


def _restricted_columns(tables) -> Dict[str, Tuple[str, ...]]:
    restricted = dict(RESTRICTED_COLUMNS)
    for table in tables or ():
        restricted.update(TABLE_RESTRICTED_COLUMNS.get(table, {}))
    return restricted

FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "truncate", "create", "grant", "revoke",
    "into", "copy", "call", "do", "execute", "merge", "vacuum", "analyze", "set", "reset",
    "lock", "listen", "notify", "prepare", "deallocate", "refresh", "reindex", "cluster",
    "begin", "commit", "rollback", "savepoint", "show", "explain",
]
FORBIDDEN_FUNCTIONS = [
    "dblink", "lo_import", "lo_export", "current_setting", "set_config", "query_to_xml",
    "current_user", "session_user", "inet_server_addr", "current_database",
]

MAX_ROWS = 50
MASK = "[RESTRICTED]"


def _strip_literals(sql: str) -> str:
    """Remove quoted string literals so their content is not mistaken for identifiers."""
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def validate_sql(sql_query: str, user_context: Dict[str, Any]) -> Tuple[bool, str, str]:
    """
    Returns (is_allowed, error_message, cleaned_sql).
    """
    if not sql_query or not sql_query.strip():
        return False, "Query Violation: Empty SQL statement.", ""

    sql = sql_query.strip().rstrip(";").strip()
    lowered = sql.lower()

    if len(sql) > 4000:
        return False, "Query Violation: SQL statement is too long.", sql

    # 1. One read-only statement only
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False, "Query Violation: Only read-only SELECT queries are authorized.", sql
    if "--" in sql or "/*" in sql or "*/" in sql:
        return False, "Query Violation: SQL comments are not allowed.", sql

    bare = _strip_literals(lowered)
    if ";" in bare:
        return False, "Query Violation: Only a single SQL statement is allowed.", sql
    if '"' in bare:
        return False, "Query Violation: Quoted identifiers are not allowed.", sql

    # 2. Block mutating / session-changing keywords
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", bare):
            return False, f"Query Violation: Keyword '{kw.upper()}' is forbidden.", sql

    identifiers = set(re.findall(r"[a-z_][a-z0-9_]*", bare))

    # 3. Block system catalogs and dangerous functions
    for ident in identifiers:
        if ident.startswith("pg_") or ident == "information_schema":
            return False, "Query Violation: Access to system catalogs is forbidden.", sql
    for fn in FORBIDDEN_FUNCTIONS:
        if fn in identifiers:
            return False, f"Query Violation: Function '{fn}' is forbidden.", sql

    # 4. Table-level RBAC
    cte_names = set(re.findall(r"([a-z_][a-z0-9_]*)\s+as\s*\(", bare))
    named_sources = set(re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_.]*)", bare))
    for source in named_sources:
        table = source.split(".")[-1]
        if table not in TABLE_ACCESS and table not in cte_names:
            return False, f"Query Violation: Table '{table}' is not available for analytics.", sql

    tables_in_query = identifiers & set(TABLE_ACCESS.keys())
    if not tables_in_query:
        return False, "Query Violation: The query does not read any enterprise table.", sql
    role = user_context.get("role", "Employee")
    for table in sorted(tables_in_query):
        needed = TABLE_ACCESS[table]
        if needed and not can(user_context, needed):
            return False, (
                f"Unauthorized: your role ({role}) is not permitted to view {TABLE_LABELS.get(table, table.replace('_', ' ') + ' records')}."
            ), sql

    # 5. Column-level RBAC
    for col in FORBIDDEN_COLUMNS:
        if col in identifiers:
            return False, f"Query Violation: Column '{col}' can never be queried.", sql
    restricted = _restricted_columns(tables_in_query)
    for col, perms in restricted.items():
        if col in identifiers and not can_any(user_context, perms):
            return False, (
                f"Unauthorized: your role ({role}) is not permitted to view {COLUMN_LABELS.get(col, col.replace('_', ' ') + ' data')}."
            ), sql

    return True, "", sql


def mask_result_columns(
    columns: List[str],
    rows: List[Dict[str, Any]],
    user_context: Dict[str, Any],
    tables=None,
) -> List[Dict[str, Any]]:
    """Second line of defence for `SELECT *`: mask restricted columns in the result set."""
    restricted = _restricted_columns(tables if tables is not None else TABLE_RESTRICTED_COLUMNS.keys())

    masked_rows = []
    for row in rows:
        clean = {}
        for col in columns:
            name = col.lower()
            if name in FORBIDDEN_COLUMNS:
                continue
            if name in restricted and not can_any(user_context, restricted[name]):
                clean[col] = MASK
            else:
                clean[col] = row.get(col)
        masked_rows.append(clean)
    return masked_rows
