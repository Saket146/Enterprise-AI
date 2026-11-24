"""
PostgreSQL retrieval for the RAG agents.

The company's source of truth is the relational database.  This module turns a
natural-language question into grounded facts read straight from the tables:

  * entity lookup  - employees, departments, projects and clients mentioned by
                     name, code or id ("Daksh Bakshi", "Finance", "PRJ-2026-00012")
  * keyword search - policies and documents
  * templates      - common aggregate questions translated to safe SELECTs

Every fact is filtered through the caller's job-role permissions *before* it
is returned, so the language model never sees data the user may not see.
Facts carry `pii_cleared=True` to tell the output guardrail that their content
was already authorised for this user.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.models.models import (
    AuditLog, Budget, Client, Contract, Department, Document, DocumentAccessRequest, Employee,
    Milestone, Policy, Project, ProjectMember, Role, Task,
)
from app.security.permissions import (
    KNOWLEDGE_READER_ROLES, Perm, can, can_view_employee_sensitive, document_access, policy_access,
)

logger = logging.getLogger(__name__)

Context = Dict[str, Any]

STOPWORDS = {
    "the", "and", "for", "are", "you", "who", "what", "when", "where", "which", "why", "how",
    "does", "did", "can", "could", "would", "should", "will", "has", "have", "had", "was", "were",
    "our", "their", "his", "her", "its", "your", "mine", "this", "that", "these", "those", "with",
    "from", "into", "about", "regarding", "tell", "show", "give", "list", "find", "get", "please",
    "need", "want", "know", "say", "says", "any", "all", "some", "many", "much", "more", "most",
    "details", "detail", "information", "info", "summary", "summarize", "summarise", "explain",
    "describe", "company", "enterprise", "organization", "organisation", "policy", "policies",
    "document", "documents", "file", "files", "current", "latest", "there", "is", "in", "of",
    "on", "to", "me", "my", "we", "us", "an", "at", "by", "be", "do", "it", "or", "as", "id",
    "employee", "employees", "department", "departments", "project", "projects", "client",
    "clients", "manager", "status", "budget", "team", "under", "over", "between", "per", "each",
    "not", "out", "now", "also", "than", "then", "them", "they", "been", "being", "top", "name",
}

# Role names that are also ordinary words; never treated as a job-title filter.
GENERIC_ROLE_NAMES = {"employee", "staff", "user"}

# Words too common in policy texts to identify a policy by themselves
POLICY_GENERIC_TERMS = {
    "number", "version", "polic", "policy", "document", "department", "employee", "company", "rule", "rules",
    "want", "need", "work", "team", "time", "year", "day", "days", "people", "person", "use", "used", "make",
    "review", "reviewed", "approval", "approved", "manager", "head", "write", "written", "change", "changes",
}

OPEN_TASK_EXCLUDE = {"completed", "done", "closed", "cancelled", "canceled"}


def _fmt_money(value) -> str:
    if value is None:
        return "not recorded"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _clean(text: Optional[str], max_len: int = 600) -> str:
    """Collapse whitespace so every fact stays on a single line."""
    flat = re.sub(r"\s+", " ", text or "").strip()
    return flat[:max_len] + ("..." if len(flat) > max_len else "")


def keywords(query: str) -> List[str]:
    """Meaningful lower-case search terms of a question."""
    words = re.findall(r"[a-z][a-z0-9-]{2,}", (query or "").lower())
    seen, out = set(), []
    for w in words:
        if w in STOPWORDS or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out


def _stem(word: str) -> str:
    return word[:-1] if word.endswith("s") and len(word) > 4 else word


class PostgresRetriever:
    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------
    @staticmethod
    def user_project_ids(db: Session, employee_id: Optional[int]) -> Set[int]:
        """Projects the employee manages, is a member of, or has tasks on."""
        if employee_id is None:
            return set()
        ids: Set[int] = set()
        ids.update(r[0] for r in db.query(Project.project_id).filter(Project.project_manager_id == employee_id))
        ids.update(r[0] for r in db.query(ProjectMember.project_id).filter(ProjectMember.employee_id == employee_id))
        ids.update(r[0] for r in db.query(Task.project_id).filter(Task.assigned_to == employee_id).distinct())
        return ids

    @classmethod
    def can_view_project(cls, db: Session, project: Project, user_context: Context) -> bool:
        if can(user_context, Perm.PROJECTS_READ_ALL):
            return True
        return project.project_id in cls.user_project_ids(db, user_context.get("employee_id"))

    @staticmethod
    def can_view_department_budget(department_id: int, user_context: Context) -> bool:
        if can(user_context, Perm.FINANCE_READ):
            return True
        return (
            can(user_context, Perm.FINANCE_READ_OWN_DEPT)
            and user_context.get("department_id") == department_id
        )

    @staticmethod
    def audit_denial(db: Session, user_context: Context, resource_type: str, resource_id: int, details: str):
        """Record a refused access attempt in the audit log."""
        try:
            db.add(AuditLog(
                employee_id=user_context.get("employee_id"),
                action_type="rbac_denied",
                resource_type=resource_type,
                resource_id=resource_id or 0,
                ip_address="agent",
                details=details[:500],
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record RBAC denial: {e}")

    @staticmethod
    def _denied(source: str, message: str) -> Context:
        return {
            "source": source, "text": f"Access denied: {message}", "score": 1.0, "denied": True, "pii_cleared": True,
            "kind": "denied", "label": "Access control", "body": message[:1].upper() + message[1:],
        }

    # ------------------------------------------------------------------
    # Entity resolution
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_employees(db: Session, query: str, user_context: Context, limit: int = 3) -> List[Employee]:
        q = (query or "").lower()
        ids: List[int] = []

        for m in re.finditer(r"\bemp(?:loyee)?\s*(?:id|no\.?|number)?\s*[:#]?\s*(\d{1,7})\b", q):
            ids.append(int(m.group(1)))

        if re.search(r"\bwho am i\b|\bmy (?:own )?(?:profile|details|manager|salary|role|record|information|info|email|phone|office|job|hire date|employment)\b", q):
            if user_context.get("employee_id") is not None:
                ids.append(user_context["employee_id"])

        if not ids:
            rows = db.query(Employee.employee_id, Employee.first_name, Employee.last_name).all()
            full_matches = [
                r.employee_id for r in rows
                if r.first_name and r.last_name and f"{r.first_name} {r.last_name}".lower() in q
            ]
            if full_matches:
                ids = full_matches
            else:
                tokens = set(keywords(query))
                if tokens:
                    ids = [
                        r.employee_id for r in rows
                        if (r.first_name or "").lower() in tokens or (r.last_name or "").lower() in tokens
                    ]

        if not ids:
            return []
        unique = list(dict.fromkeys(ids))[:limit]
        found = db.query(Employee).filter(Employee.employee_id.in_(unique)).all()
        order = {eid: i for i, eid in enumerate(unique)}
        return sorted(found, key=lambda e: order.get(e.employee_id, 99))

    @staticmethod
    def resolve_departments(db: Session, query: str, user_context: Context, limit: int = 3) -> List[Department]:
        q = (query or "").lower()
        ids: List[int] = []

        for m in re.finditer(r"\b(?:department|dept)\s*(?:id|no\.?|number)?\s*[:#]?\s*(\d{1,5})\b", q):
            ids.append(int(m.group(1)))

        if re.search(r"\b(?:my|our) (?:own )?(?:department|dept|team)\b", q) and user_context.get("department_id"):
            ids.append(user_context["department_id"])

        departments = db.query(Department).all()
        for d in departments:
            if d.department_name and re.search(r"\b" + re.escape(d.department_name.lower()) + r"\b", q):
                ids.append(d.department_id)
        if not ids:
            # Department codes (HR, IT, QA ...) only count when written in capitals,
            # otherwise the word "it" would select the IT department.
            for d in departments:
                if d.department_code and re.search(r"\b" + re.escape(d.department_code.upper()) + r"\b", query or ""):
                    ids.append(d.department_id)

        unique = list(dict.fromkeys(ids))[:limit]
        by_id = {d.department_id: d for d in departments}
        return [by_id[i] for i in unique if i in by_id]

    @classmethod
    def resolve_projects(cls, db: Session, query: str, user_context: Context, limit: int = 3) -> List[Project]:
        q = (query or "").lower()
        ids: List[int] = []

        for m in re.finditer(r"\bproject\s*(?:id|no\.?|number)?\s*[:#]?\s*(\d{1,7})\b", q):
            ids.append(int(m.group(1)))

        codes = [c.upper() for c in re.findall(r"\bprj-\d{4}-\d{3,6}\b", q)]
        if codes:
            ids.extend(r[0] for r in db.query(Project.project_id).filter(func.upper(Project.project_code).in_(codes)))

        if not ids:
            for pid, name in db.query(Project.project_id, Project.project_name).all():
                base = re.sub(r"\s+project$", "", (name or "").lower()).strip()
                if len(base) >= 8 and base in q:
                    ids.append(pid)

        if not ids and re.search(r"\b(?:my|our) projects?\b|\bprojects? (?:i|we) (?:am|are|manage|work)", q):
            ids.extend(sorted(cls.user_project_ids(db, user_context.get("employee_id"))))

        unique = list(dict.fromkeys(ids))[:limit]
        if not unique:
            return []
        found = db.query(Project).filter(Project.project_id.in_(unique)).all()
        order = {pid: i for i, pid in enumerate(unique)}
        return sorted(found, key=lambda p: order.get(p.project_id, 99))

    @staticmethod
    def resolve_clients(db: Session, query: str, limit: int = 3) -> List[Client]:
        q = (query or "").lower()
        ids: List[int] = []
        for m in re.finditer(r"\bclient\s*(?:id|no\.?|number)?\s*[:#]?\s*(\d{1,7})\b", q):
            ids.append(int(m.group(1)))
        if not ids:
            for cid, name in db.query(Client.client_id, Client.company_name).all():
                if name and len(name) >= 4 and name.lower() in q:
                    ids.append(cid)
        unique = list(dict.fromkeys(ids))[:limit]
        if not unique:
            return []
        return db.query(Client).filter(Client.client_id.in_(unique)).all()

    def role_facts(self, db: Session, query: str, user_context: Context) -> List[Context]:
        """
        Questions about a job title ("who is the CEO?", "who are the HR executives?").
        Small roles list their holders; large roles report a head count.
        """
        q = (query or "").lower()
        facts: List[Context] = []
        for role in db.query(Role).all():
            name = (role.role_name or "").strip()
            if len(name) < 3 or name.lower() in GENERIC_ROLE_NAMES or not re.search(r"\b" + re.escape(name.lower()) + r"s?\b", q):
                continue
            holders = db.query(Employee).filter(Employee.role_id == role.role_id).order_by(Employee.employee_id)
            total = holders.count()
            if total == 0:
                continue
            if total <= 5:
                for emp in holders.all():
                    facts.append(self.employee_fact(emp, user_context, query))
            else:
                active = holders.filter(Employee.employment_status == "Active").count()
                facts.append({
                    "source": f"PostgreSQL: employees and roles tables (role '{name}')",
                    "text": f"There are {total} employees with the job role {name} ({active} active).",
                    "score": 0.9, "pii_cleared": True,
                    "kind": "summary", "label": "Employee directory",
                    "body": f"There are **{total}** employees with the job role {name}, of whom **{active}** are active.",
                })
        return facts[:5]

    # ------------------------------------------------------------------
    # Fact builders (RBAC is applied here)
    # ------------------------------------------------------------------
    @staticmethod
    def employee_fact(emp: Employee, user_context: Context, query: str = "") -> Context:
        name = f"{emp.first_name} {emp.last_name}"
        manager = f"{emp.manager.first_name} {emp.manager.last_name}" if emp.manager else "None"
        role_name = emp.role.role_name if emp.role else "Unassigned"
        dept_name = emp.department.department_name if emp.department else "None"
        text = (
            f"Employee {name} (ID {emp.employee_id}): Role: {role_name}, "
            f"Department: {dept_name}, "
            f"Manager: {manager}, Office: {emp.office_location or 'N/A'}, "
            f"Employment status: {emp.employment_status or 'N/A'}, Work email: {emp.email}."
        )
        fields = [
            ["Role", role_name], ["Department", dept_name], ["Manager", manager],
            ["Office", emp.office_location or "N/A"], ["Employment status", emp.employment_status or "N/A"],
            ["Work email", emp.email], ["Employee ID", str(emp.employee_id)],
        ]
        note = None
        if can_view_employee_sensitive(user_context, emp.employee_id, emp.manager_id):
            text += (
                f" Phone: {emp.phone or 'N/A'}, Hire date: {emp.hire_date or 'N/A'}, "
                f"Date of birth: {emp.date_of_birth or 'N/A'}, Salary: {_fmt_money(emp.salary)}."
            )
            fields += [
                ["Phone", emp.phone or "N/A"], ["Hire date", str(emp.hire_date or "N/A")],
                ["Date of birth", str(emp.date_of_birth or "N/A")], ["Salary", _fmt_money(emp.salary)],
            ]
        elif re.search(r"salar|pay|compensation|phone|mobile|contact number|birth|dob|\bage\b", (query or "").lower()):
            note = (
                f"Salary, phone and date of birth are restricted: your role ({user_context.get('role')}) "
                f"may only see them for yourself and your direct reports."
            )
            text += " " + note
        return {
            "source": f"PostgreSQL: employees table (ID {emp.employee_id})",
            "text": text, "score": 1.0, "pii_cleared": True,
            "kind": "employee", "label": "Employee directory", "title": name, "fields": fields, "note": note,
        }

    @classmethod
    def department_fact(cls, db: Session, dept: Department, user_context: Context, include_budget: bool = True) -> Context:
        headcount = db.query(func.count(Employee.employee_id)).filter(Employee.department_id == dept.department_id).scalar() or 0
        text = (
            f"Department {dept.department_name} ({dept.department_code}, ID {dept.department_id}): "
            f"Location: {dept.location or 'N/A'}, Headcount: {headcount} employees."
        )
        fields = [
            ["Code", dept.department_code or "N/A"], ["Location", dept.location or "N/A"],
            ["Headcount", f"{headcount} employees"],
        ]
        note, table = None, None
        if include_budget:
            if cls.can_view_department_budget(dept.department_id, user_context):
                text += f" Total budget: {_fmt_money(dept.budget)}."
                fields.append(["Total budget", _fmt_money(dept.budget)])
                rows = db.query(Budget).filter(Budget.department_id == dept.department_id).order_by(Budget.fiscal_year).all()
                if rows:
                    text += " Fiscal breakdown: " + "; ".join(
                        f"Year {b.fiscal_year}: allocated {_fmt_money(b.allocated_amount)}, approved {_fmt_money(b.approved_amount)}"
                        for b in rows[:6]
                    ) + "."
                    table = {
                        "columns": ["Fiscal year", "Allocated", "Approved"],
                        "rows": [[str(b.fiscal_year), _fmt_money(b.allocated_amount), _fmt_money(b.approved_amount)] for b in rows[:6]],
                    }
            else:
                note = f"Budget figures are restricted for your role ({user_context.get('role')})."
                text += " " + note
        return {
            "source": f"PostgreSQL: departments table (ID {dept.department_id})",
            "text": text, "score": 1.0, "pii_cleared": True,
            "kind": "department", "label": "Departments", "title": f"{dept.department_name} department",
            "fields": fields, "table": table, "note": note,
        }

    @classmethod
    def project_facts(cls, db: Session, proj: Project, user_context: Context) -> List[Context]:
        if not cls.can_view_project(db, proj, user_context):
            cls.audit_denial(db, user_context, "project", proj.project_id, "Agent project lookup refused")
            return [cls._denied(
                f"PostgreSQL: projects table (ID {proj.project_id})",
                f"your role ({user_context.get('role')}) may only view projects you manage or work on, "
                f"so project ID {proj.project_id} cannot be shown."
            )]

        manager = f"{proj.manager.first_name} {proj.manager.last_name}" if proj.manager else "Unassigned"
        text = (
            f"Project {proj.project_name} ({proj.project_code}, ID {proj.project_id}) is {proj.status} "
            f"with priority {proj.priority}. Manager: {manager}. "
            f"Department: {proj.department.department_name if proj.department else 'None'}. "
            f"Client: {proj.client.company_name if proj.client else 'None'}. "
            f"Start: {proj.start_date or 'N/A'}, End: {proj.end_date or 'N/A'}. Budget: {_fmt_money(proj.budget)}. "
            f"Description: {_clean(proj.description, 200)}"
        )
        facts = [{
            "source": f"PostgreSQL: projects table (ID {proj.project_id})",
            "text": text, "score": 1.0, "pii_cleared": True,
            "kind": "project", "label": "Projects", "title": proj.project_name,
            "fields": [
                ["Code", proj.project_code or "N/A"], ["Status", proj.status or "N/A"], ["Priority", proj.priority or "N/A"],
                ["Manager", manager], ["Department", proj.department.department_name if proj.department else "None"],
                ["Client", proj.client.company_name if proj.client else "None"],
                ["Timeline", f"{proj.start_date or 'N/A'} to {proj.end_date or 'N/A'}"],
                ["Budget", _fmt_money(proj.budget)],
            ],
            "body": _clean(proj.description, 200) or None,
        }]

        status_counts = db.query(Task.status, func.count(Task.task_id)).filter(
            Task.project_id == proj.project_id
        ).group_by(Task.status).all()
        if status_counts:
            open_tasks = db.query(Task).filter(
                Task.project_id == proj.project_id,
                or_(Task.status.is_(None), func.lower(Task.status).notin_(OPEN_TASK_EXCLUDE)),
            ).order_by(Task.due_date).limit(8).all()
            summary = ", ".join(f"{s or 'Unknown'}: {n}" for s, n in status_counts)
            listing = "; ".join(
                f"{t.title} ({t.status}, priority {t.priority}, due {t.due_date or 'N/A'}, assignee "
                f"{(t.assignee.first_name + ' ' + t.assignee.last_name) if t.assignee else 'Unassigned'})"
                for t in open_tasks
            )
            facts.append({
                "source": f"PostgreSQL: tasks table (Project {proj.project_id})",
                "text": f"Tasks of {proj.project_name} by status: {summary}. Open tasks: {listing or 'None'}.",
                "score": 0.95, "pii_cleared": True,
                "kind": "tasks", "label": "Project tasks", "title": f"Tasks - {proj.project_name}",
                "body": "By status: " + summary + ".",
                "table": {
                    "columns": ["Open task", "Status", "Priority", "Due", "Assignee"],
                    "rows": [[
                        t.title or "", t.status or "", t.priority or "", str(t.due_date or "N/A"),
                        (t.assignee.first_name + " " + t.assignee.last_name) if t.assignee else "Unassigned",
                    ] for t in open_tasks],
                } if open_tasks else None,
            })

        milestones = db.query(Milestone).filter(Milestone.project_id == proj.project_id).order_by(Milestone.due_date).limit(6).all()
        if milestones:
            facts.append({
                "source": f"PostgreSQL: milestones table (Project {proj.project_id})",
                "text": f"Milestones of {proj.project_name}: " + "; ".join(
                    f"{m.milestone_name} ({m.status}, due {m.due_date or 'N/A'})" for m in milestones
                ) + ".",
                "score": 0.9, "pii_cleared": True,
                "kind": "milestones", "label": "Project milestones", "title": f"Milestones - {proj.project_name}",
                "table": {
                    "columns": ["Milestone", "Status", "Due"],
                    "rows": [[m.milestone_name or "", m.status or "", str(m.due_date or "N/A")] for m in milestones],
                },
            })
        return facts

    @classmethod
    def client_fact(cls, db: Session, client: Client, user_context: Context) -> Context:
        source = f"PostgreSQL: clients table (ID {client.client_id})"
        if not can(user_context, Perm.SALES_READ):
            cls.audit_denial(db, user_context, "client", client.client_id, "Agent client lookup refused")
            return cls._denied(source, f"your role ({user_context.get('role')}) is not permitted to view client and contract records.")
        contracts = db.query(Contract).filter(Contract.client_id == client.client_id).order_by(Contract.start_date.desc()).limit(4).all()
        text = (
            f"Client {client.company_name} (ID {client.client_id}): Industry: {client.industry or 'N/A'}, "
            f"Size: {client.client_size or 'N/A'}, Location: {client.city or 'N/A'}, {client.country or 'N/A'}, "
            f"Status: {client.status or 'N/A'}, Contact person: {client.contact_person or 'N/A'}, "
            f"Annual revenue: {_fmt_money(client.annual_revenue)}, Contract value: {_fmt_money(client.contract_value)}."
        )
        if contracts:
            text += " Contracts: " + "; ".join(
                f"{c.contract_number} '{c.contract_title}' ({c.status}, value {_fmt_money(c.contract_value)} {c.currency or ''}, "
                f"{c.start_date or 'N/A'} to {c.end_date or 'N/A'})" for c in contracts
            ) + "."
        return {
            "source": source, "text": text, "score": 1.0, "pii_cleared": True,
            "kind": "client", "label": "Clients and contracts", "title": f"{client.company_name} (client #{client.client_id})",
            "fields": [
                ["Industry", client.industry or "N/A"], ["Size", client.client_size or "N/A"],
                ["Location", f"{client.city or 'N/A'}, {client.country or 'N/A'}"], ["Status", client.status or "N/A"],
                ["Contact person", client.contact_person or "N/A"],
                ["Annual revenue", _fmt_money(client.annual_revenue)], ["Contract value", _fmt_money(client.contract_value)],
            ],
            "table": {
                "columns": ["Contract", "Title", "Status", "Value", "Period"],
                "rows": [[
                    c.contract_number or "", c.contract_title or "", c.status or "",
                    f"{_fmt_money(c.contract_value)} {c.currency or ''}".strip(),
                    f"{c.start_date or 'N/A'} to {c.end_date or 'N/A'}",
                ] for c in contracts],
            } if contracts else None,
        }

    # ------------------------------------------------------------------
    # Keyword search over text tables
    # ------------------------------------------------------------------
    @staticmethod
    def granted_document_ids(db: Session, employee_id: Optional[int]) -> Set[int]:
        """Documents this employee may read because an administrator approved their access request."""
        if employee_id is None:
            return set()
        return {
            doc_id for (doc_id,) in db.query(DocumentAccessRequest.document_id).filter(
                DocumentAccessRequest.employee_id == employee_id,
                DocumentAccessRequest.status == "approved",
            )
        }

    @classmethod
    def can_open_document(cls, db: Session, document_id: int, user_context: Context) -> bool:
        """Reader roles open every document; everyone else only documents they were granted."""
        access = document_access(user_context)
        if access == "content":
            return True
        if access == "none":
            return False
        return document_id in cls.granted_document_ids(db, user_context.get("employee_id"))

    @classmethod
    def _knowledge_denied(cls, db: Session, user_context: Context, what: str) -> List[Context]:
        """Interns may not see policies or documents at all - not even which ones exist."""
        cls.audit_denial(db, user_context, what, 0, f"Agent {what} lookup refused")
        return [cls._denied(
            f"PostgreSQL: {what} table",
            f"your role ({user_context.get('role')}) is not permitted to view company policies and documents."
        )]

    @staticmethod
    def _readable(text: Optional[str], max_len: int) -> str:
        """Keep headings and line breaks of a policy/document, cut at a paragraph boundary."""
        body = (text or "").strip()
        if len(body) <= max_len:
            return body
        cut = body[:max_len]
        if "\n\n" in cut[max_len // 2:]:
            cut = cut[:cut.rindex("\n\n")]
        return cut.rstrip() + "\n\n*The text continues. Open it in the Knowledge Explorer to read all of it.*"

    @classmethod
    def search_policies(cls, db: Session, query: str, user_context: Context, limit: int = 3) -> List[Context]:
        """
        Policies matching the question, shaped by what the role may see:
          full text for roles that can open policies, title and listing details for the others,
          and a refusal for roles with no access to the knowledge base.
        """
        terms = [_stem(k) for k in keywords(query)]
        if not terms:
            return []
        access = policy_access(user_context)
        can_read = access == "content"
        q = (query or "").lower()
        # Words that appear in nearly every policy ("version number", "department") say nothing about the topic
        topic_terms = [t for t in terms if t not in POLICY_GENERIC_TERMS]
        # One matching word in the text is enough only when the question is clearly about rules
        policy_question = bool(re.search(r"\bpolic|\brules?\b|\ballowed\b|\bguideline|\bhandbook|\bprocedure|\bcan i\b|\bmay i\b|\bam i\b", q))
        needed_text_hits = 1 if policy_question else 2
        scored: List[Tuple[float, Policy]] = []
        for p in db.query(Policy).all():
            name = (p.policy_name or "").lower()
            name_words = {_stem(w) for w in re.findall(r"[a-z0-9]+", name)}
            name_hits = sum(1 for t in terms if t in name_words)
            text_hits = 0
            if can_read:
                # Only readers may find a policy through words inside its text; whole words only,
                # so "his" does not match "this" and "number" does not match every "version number"
                text_words = {_stem(w) for w in re.findall(r"[a-z0-9]+", (p.description or "").lower())}
                text_hits = sum(1 for t in topic_terms if t in text_words)
            if name_hits == 0 and text_hits < needed_text_hits:
                continue
            score = 3.0 * name_hits + 1.0 * text_hits
            if name and re.sub(r"\s+polic(?:y|ies)$", "", name) in q:
                score += 10
            if p.department_id and p.department_id == user_context.get("department_id"):
                score += 0.5  # the user's own department's version first
            scored.append((score, p))
        if not scored:
            return []
        if access == "none":
            return cls._knowledge_denied(db, user_context, "policies")

        scored.sort(key=lambda x: (-x[0], x[1].policy_id))
        out = []
        for score, p in scored[:limit]:
            dept = p.department.department_name if p.department else "Company-wide"
            header = f"Policy '{p.policy_name}' (version {p.version or 'N/A'}, effective {p.effective_date or 'N/A'}, owner: {dept})"
            fact = {
                "source": f"PostgreSQL: policies table - '{p.policy_name}' (ID {p.policy_id})",
                "score": round(min(0.99, 0.5 + score / 30), 4),
                "pii_cleared": False,
                "kind": "policy", "label": f"Policy: {p.policy_name}", "title": p.policy_name,
                "fields": [["Version", p.version or "N/A"], ["Effective", str(p.effective_date or "N/A")], ["Owner", dept]],
            }
            if can_read:
                fact["text"] = f"{header}: {_clean(p.description, 1800)}"
                fact["body"] = cls._readable(p.description, 1800) or None
            else:
                note = "You can see that this policy exists, but your role cannot open it."
                fact["text"] = f"{header} exists. Its contents are restricted: {note}"
                fact["note"] = note
                fact["restricted"] = True
            out.append(fact)
        return out

    @classmethod
    def search_documents(cls, db: Session, query: str, user_context: Context, limit: int = 3) -> List[Context]:
        """Documents matching the question by title or type; same access rules as policies."""
        terms = keywords(query)[:6]
        if not terms:
            return []
        access = document_access(user_context)
        reads_all = access == "content"
        granted = set() if reads_all or access == "none" else cls.granted_document_ids(db, user_context.get("employee_id"))
        conditions = []
        for t in terms:
            conditions.append(Document.title.ilike(f"%{t}%"))
            conditions.append(Document.document_type.ilike(f"%{t}%"))
        rows = db.query(
            Document.document_id, Document.title, Document.document_type, Document.file_name,
            func.substr(Document.content, 1, 1600).label("snippet"),
        ).filter(or_(*conditions)).limit(300).all()

        scored = []
        for r in rows:
            title = (r.title or "").lower()
            dtype = (r.document_type or "").lower()
            score = 2.0 * sum(1 for t in terms if t in title) + 1.0 * sum(1 for t in terms if t in dtype)
            if score > 0:
                scored.append((score, r))
        if not scored:
            return []
        if access == "none":
            return cls._knowledge_denied(db, user_context, "documents")

        scored.sort(key=lambda x: (-x[0], x[1].document_id))
        out = []
        for score, r in scored[:limit]:
            fact = {
                "source": f"PostgreSQL: documents table - '{r.title}' (ID {r.document_id})",
                "score": round(min(0.95, 0.45 + score / 20), 4),
                "pii_cleared": False,
                "kind": "document", "label": f"Document: {r.title}", "title": r.title,
                "fields": [["Type", r.document_type or "N/A"], ["File", r.file_name or "N/A"]],
            }
            if reads_all or r.document_id in granted:
                fact["text"] = f"Document '{r.title}' ({r.document_type}, file {r.file_name}): {_clean(r.snippet, 1200)}"
                fact["body"] = cls._readable(r.snippet, 1100) or None
            else:
                note = (
                    "You can see that this document exists, but you need approved access to read it. "
                    "Request access to it in the Knowledge Explorer or the Operations Center; a system administrator decides."
                )
                fact["text"] = f"Document '{r.title}' ({r.document_type}, file {r.file_name}) exists. Its contents are restricted: {note}"
                fact["note"] = note
                fact["restricted"] = True
            out.append(fact)
        return out

    # ------------------------------------------------------------------
    # Overviews used when no specific entity was named
    # ------------------------------------------------------------------
    @classmethod
    def budget_overview(cls, db: Session, user_context: Context) -> List[Context]:
        source = "PostgreSQL: departments table (budgets)"
        if can(user_context, Perm.FINANCE_READ):
            depts = db.query(Department).order_by(Department.budget.desc()).all()
            total = sum(float(d.budget or 0) for d in depts)
            return [{
                "source": source,
                "text": "Department budgets: " + "; ".join(
                    f"{d.department_name}: {_fmt_money(d.budget)}" for d in depts
                ) + f". Total across all departments: {_fmt_money(total)}.",
                "score": 0.9, "pii_cleared": True,
                "kind": "summary", "label": "Department budgets", "title": "Department budgets",
                "body": f"The total budget across all departments is **{total:,.0f}**.",
                "table": {"columns": ["Department", "Budget"], "rows": [[d.department_name, _fmt_money(d.budget)] for d in depts]},
            }]
        if can(user_context, Perm.FINANCE_READ_OWN_DEPT) and user_context.get("department_id"):
            dept = db.query(Department).filter(Department.department_id == user_context["department_id"]).first()
            return [cls.department_fact(db, dept, user_context)] if dept else []
        cls.audit_denial(db, user_context, "budget", 0, "Agent budget overview refused")
        return [cls._denied(source, f"your role ({user_context.get('role')}) is not permitted to view budget and finance data.")]

    @classmethod
    def project_overview(cls, db: Session, user_context: Context) -> List[Context]:
        if can(user_context, Perm.PROJECTS_READ_ALL):
            counts = db.query(Project.status, func.count(Project.project_id)).group_by(Project.status).all()
            total = sum(n for _, n in counts)
            return [{
                "source": "PostgreSQL: projects table (portfolio)",
                "text": f"Project portfolio: {total} projects. By status: " + ", ".join(f"{s or 'Unknown'}: {n}" for s, n in counts) + ".",
                "score": 0.85, "pii_cleared": True,
                "kind": "summary", "label": "Projects", "title": "Project portfolio",
                "body": f"There are **{total}** projects in the portfolio.",
                "table": {"columns": ["Status", "Projects"], "rows": [[s or "Unknown", str(n)] for s, n in sorted(counts, key=lambda c: -c[1])]},
            }]
        ids = sorted(cls.user_project_ids(db, user_context.get("employee_id")))
        if not ids:
            return [{
                "source": "PostgreSQL: projects table",
                "text": f"You are not assigned to any project, and your role ({user_context.get('role')}) can only view projects you manage or work on.",
                "score": 0.8, "pii_cleared": True,
                "kind": "summary", "label": "Projects",
                "body": f"You are not assigned to any project, and your role ({user_context.get('role')}) can only view projects you manage or work on.",
            }]
        projects = db.query(Project).filter(Project.project_id.in_(ids[:10])).all()
        return [{
            "source": "PostgreSQL: projects table (your projects)",
            "text": "Your projects: " + "; ".join(
                f"{p.project_name} ({p.project_code}, ID {p.project_id}, {p.status}, priority {p.priority})" for p in projects
            ) + ".",
            "score": 0.85, "pii_cleared": True,
            "kind": "summary", "label": "Projects", "title": "Your projects",
            "table": {
                "columns": ["Project", "Code", "Status", "Priority"],
                "rows": [[p.project_name or "", p.project_code or "", p.status or "", p.priority or ""] for p in projects],
            },
        }]

    @staticmethod
    def my_tasks(db: Session, user_context: Context) -> List[Context]:
        emp_id = user_context.get("employee_id")
        tasks = db.query(Task).filter(
            Task.assigned_to == emp_id,
            or_(Task.status.is_(None), func.lower(Task.status).notin_(OPEN_TASK_EXCLUDE)),
        ).order_by(Task.due_date).limit(10).all()
        listing = "; ".join(
            f"{t.title} (project ID {t.project_id}, {t.status}, priority {t.priority}, due {t.due_date or 'N/A'})" for t in tasks
        )
        return [{
            "source": f"PostgreSQL: tasks table (assigned to employee {emp_id})",
            "text": f"Your open tasks: {listing or 'None'}.",
            "score": 0.9, "pii_cleared": True,
            "kind": "tasks", "label": "Project tasks", "title": "Your open tasks",
            "body": None if tasks else "You have no open tasks.",
            "table": {
                "columns": ["Task", "Project ID", "Status", "Priority", "Due"],
                "rows": [[t.title or "", str(t.project_id), t.status or "", t.priority or "", str(t.due_date or "N/A")] for t in tasks],
            } if tasks else None,
        }]

    @classmethod
    def sales_overview(cls, db: Session, user_context: Context) -> List[Context]:
        source = "PostgreSQL: clients and contracts tables"
        if not can(user_context, Perm.SALES_READ):
            cls.audit_denial(db, user_context, "client", 0, "Agent sales overview refused")
            return [cls._denied(source, f"your role ({user_context.get('role')}) is not permitted to view client and contract records.")]
        total = db.query(func.count(Client.client_id)).scalar() or 0
        by_industry = db.query(Client.industry, func.count(Client.client_id)).group_by(Client.industry).order_by(func.count(Client.client_id).desc()).limit(6).all()
        by_status = db.query(Contract.status, func.count(Contract.contract_id), func.sum(Contract.contract_value)).group_by(Contract.status).all()
        return [{
            "source": source,
            "text": (
                f"Client base: {total} clients. Top industries: " + ", ".join(f"{i or 'Unknown'}: {n}" for i, n in by_industry)
                + ". Contracts by status: " + ", ".join(f"{s or 'Unknown'}: {n} (value {_fmt_money(v)})" for s, n, v in by_status) + "."
            ),
            "score": 0.85, "pii_cleared": True,
            "kind": "summary", "label": "Clients and contracts", "title": "Client portfolio",
            "body": f"There are **{total}** clients. Top industries: " + ", ".join(f"{i or 'Unknown'} ({n})" for i, n in by_industry) + ".",
            "table": {
                "columns": ["Contract status", "Contracts", "Total value"],
                "rows": [[s or "Unknown", str(n), _fmt_money(v)] for s, n, v in by_status],
            } if by_status else None,
        }]

    # ------------------------------------------------------------------
    # One-call search used by the agents
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        user_context: Context,
        domains: Sequence[str] = ("employees", "departments", "projects", "clients", "policies", "documents"),
        limit: int = 6,
    ) -> List[Context]:
        """Collect permission-filtered facts for a question from the PostgreSQL tables."""
        facts: List[Context] = []
        db: Session = SessionLocal()
        try:
            if "employees" in domains:
                for emp in self.resolve_employees(db, query, user_context):
                    facts.append(self.employee_fact(emp, user_context, query))
                known = {f["source"] for f in facts}
                facts.extend(f for f in self.role_facts(db, query, user_context) if f["source"] not in known)
            if "departments" in domains:
                for dept in self.resolve_departments(db, query, user_context):
                    facts.append(self.department_fact(db, dept, user_context))
            if "projects" in domains:
                for proj in self.resolve_projects(db, query, user_context):
                    facts.extend(self.project_facts(db, proj, user_context))
            if "clients" in domains:
                for client in self.resolve_clients(db, query):
                    facts.append(self.client_fact(db, client, user_context))
            if "policies" in domains:
                facts.extend(self.search_policies(db, query, user_context))
            if "documents" in domains:
                facts.extend(self.search_documents(db, query, user_context))
        except Exception as e:
            db.rollback()
            logger.error(f"PostgreSQL retrieval failed: {e}", exc_info=True)
        finally:
            db.close()
        facts.sort(key=lambda c: c.get("score", 0), reverse=True)
        return facts[:limit]

    def run(self, fn_name: str, user_context: Context) -> List[Context]:
        """Run one of the overview helpers with its own session."""
        db: Session = SessionLocal()
        try:
            return getattr(self, fn_name)(db, user_context)
        except Exception as e:
            db.rollback()
            logger.error(f"PostgreSQL retrieval '{fn_name}' failed: {e}", exc_info=True)
            return []
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Natural language -> SQL templates (used when no LLM is configured,
    # or when the LLM does not return a usable SELECT)
    # ------------------------------------------------------------------
    def describe_filters(self, question: str) -> str:
        """Plain-language description of the filters a template query applied, e.g. 'department: Finance'."""
        q = (question or "").lower()
        parts: List[str] = []
        db: Session = SessionLocal()
        try:
            dept = next(iter(self.resolve_departments(db, question, {}, limit=1)), None)
            if dept:
                parts.append(f"department: {dept.department_name}")
            for _, rname in db.query(Role.role_id, Role.role_name).all():
                if rname and len(rname) >= 3 and rname.lower() not in GENERIC_ROLE_NAMES and re.search(r"\b" + re.escape(rname.lower()) + r"s?\b", q):
                    parts.append(f"job role: {rname}")
                    break
        except Exception:
            pass
        finally:
            db.close()
        for needle in ("on leave", "resigned", "active", "delayed", "completed", "on hold", "planning", "blocked", "pending", "in progress"):
            if re.search(r"\b" + needle + r"\b", q):
                parts.append(f"status: {needle.title()}")
                break
        return ", ".join(parts)

    def template_sql(self, question: str) -> Optional[str]:
        q = (question or "").lower()
        db: Session = SessionLocal()
        role_id = None
        try:
            dept = next(iter(self.resolve_departments(db, question, {}, limit=1)), None)
            # A job title in the question ("backend engineers", "interns") filters by role
            for rid, rname in db.query(Role.role_id, Role.role_name).all():
                if rname and len(rname) >= 3 and rname.lower() not in GENERIC_ROLE_NAMES and re.search(r"\b" + re.escape(rname.lower()) + r"s?\b", q):
                    role_id = int(rid)
                    break
        except Exception:
            dept = None
        finally:
            db.close()
        dept_id = int(dept.department_id) if dept else None

        by_dept = bool(re.search(r"\b(?:per|by|each|every|across|in each)\s+(?:the\s+)?departments?\b|department[- ]wise", q))
        by_status = bool(re.search(r"\b(?:per|by|each)\s+status\b|status[- ]wise", q))
        by_role = bool(re.search(r"\b(?:per|by|each)\s+(?:job\s+)?(?:role|designation|title)s?\b", q))
        by_priority = bool(re.search(r"\b(?:per|by|each)\s+priority\b", q))
        by_industry = bool(re.search(r"\b(?:per|by|each)\s+industr", q))
        by_country = bool(re.search(r"\b(?:per|by|each)\s+countr", q))
        by_location = bool(re.search(r"\b(?:per|by|each)\s+(?:location|office|city)\b", q))

        def status_in(options: Dict[str, str]) -> Optional[str]:
            for needle, value in options.items():
                if re.search(r"\b" + needle + r"\b", q):
                    return value
            return None

        # ---- salaries ------------------------------------------------
        if re.search(r"\bsalar(?:y|ies)\b|\bpayroll cost\b", q):
            agg, label = "AVG", "average_salary"
            if re.search(r"\b(?:total|sum)\b", q):
                agg, label = "SUM", "total_salary"
            elif re.search(r"\b(?:highest|max|maximum|top)\b", q):
                agg, label = "MAX", "highest_salary"
            elif re.search(r"\b(?:lowest|min|minimum)\b", q):
                agg, label = "MIN", "lowest_salary"
            if by_dept:
                return (
                    f"SELECT d.department_name, ROUND({agg}(e.salary), 2) AS {label} FROM employees e "
                    f"JOIN departments d ON d.department_id = e.department_id GROUP BY d.department_name ORDER BY 2 DESC"
                )
            if by_role:
                return (
                    f"SELECT r.role_name, ROUND({agg}(e.salary), 2) AS {label} FROM employees e "
                    f"JOIN roles r ON r.role_id = e.role_id GROUP BY r.role_name ORDER BY 2 DESC"
                )
            conds = []
            if dept_id:
                conds.append(f"department_id = {dept_id}")
            if role_id:
                conds.append(f"role_id = {role_id}")
            where = (" WHERE " + " AND ".join(conds)) if conds else ""
            return f"SELECT ROUND({agg}(salary), 2) AS {label} FROM employees{where}"

        # ---- department budgets --------------------------------------
        if "budget" in q and not re.search(r"\bprojects?\b", q):
            if dept_id:
                return f"SELECT department_name, budget FROM departments WHERE department_id = {dept_id}"
            if re.search(r"\b(?:total|sum|overall|combined)\b", q) and not by_dept:
                return "SELECT SUM(budget) AS total_budget FROM departments"
            return "SELECT department_name, budget FROM departments ORDER BY budget DESC"

        # ---- employees -----------------------------------------------
        if role_id or re.search(r"\b(?:employees?|staff|people|headcount|workforce)\b", q):
            emp_status = status_in({"active": "Active", "resigned": "Resigned", "on leave": "On Leave"})
            filters = []
            if dept_id:
                filters.append(f"e.department_id = {dept_id}")
            if role_id:
                filters.append(f"e.role_id = {role_id}")
            if emp_status:
                filters.append(f"e.employment_status = '{emp_status}'")
            where = (" WHERE " + " AND ".join(filters)) if filters else ""
            if by_dept:
                return (
                    "SELECT d.department_name, COUNT(*) AS employee_count FROM employees e "
                    f"JOIN departments d ON d.department_id = e.department_id{where} GROUP BY d.department_name ORDER BY 2 DESC"
                )
            if by_role:
                return (
                    "SELECT r.role_name, COUNT(*) AS employee_count FROM employees e "
                    f"JOIN roles r ON r.role_id = e.role_id{where} GROUP BY r.role_name ORDER BY 2 DESC"
                )
            if by_status:
                return f"SELECT e.employment_status, COUNT(*) AS employee_count FROM employees e{where} GROUP BY e.employment_status ORDER BY 2 DESC"
            if by_location:
                return f"SELECT e.office_location, COUNT(*) AS employee_count FROM employees e{where} GROUP BY e.office_location ORDER BY 2 DESC"
            return f"SELECT COUNT(*) AS employee_count FROM employees e{where}"

        # ---- tasks ---------------------------------------------------
        if re.search(r"\btasks?\b", q):
            if by_priority:
                return "SELECT priority, COUNT(*) AS task_count FROM tasks GROUP BY priority ORDER BY 2 DESC"
            task_status = status_in({"blocked": "Blocked", "pending": "Pending", "completed": "Completed", "in progress": "In Progress"})
            if task_status and not by_status:
                return f"SELECT COUNT(*) AS task_count FROM tasks WHERE status = '{task_status}'"
            return "SELECT status, COUNT(*) AS task_count FROM tasks GROUP BY status ORDER BY 2 DESC"

        # ---- projects ------------------------------------------------
        if re.search(r"\bprojects?\b", q):
            if "budget" in q:
                where = f" WHERE department_id = {dept_id}" if dept_id else ""
                return f"SELECT COUNT(*) AS project_count, SUM(budget) AS total_project_budget, ROUND(AVG(budget), 2) AS average_project_budget FROM projects{where}"
            proj_status = status_in({
                "active": "Active", "completed": "Completed", "delayed": "Delayed",
                "on hold": "On Hold", "planning": "Planning", "planned": "Planning",
            })
            filters = []
            if dept_id:
                filters.append(f"p.department_id = {dept_id}")
            if proj_status:
                filters.append(f"p.status = '{proj_status}'")
            where = (" WHERE " + " AND ".join(filters)) if filters else ""
            if by_dept:
                return (
                    "SELECT d.department_name, COUNT(*) AS project_count FROM projects p "
                    f"JOIN departments d ON d.department_id = p.department_id{where} GROUP BY d.department_name ORDER BY 2 DESC"
                )
            if by_priority:
                return f"SELECT p.priority, COUNT(*) AS project_count FROM projects p{where} GROUP BY p.priority ORDER BY 2 DESC"
            if by_status or not filters:
                return f"SELECT p.status, COUNT(*) AS project_count FROM projects p{where} GROUP BY p.status ORDER BY 2 DESC"
            return f"SELECT COUNT(*) AS project_count FROM projects p{where}"

        # ---- contracts / clients -------------------------------------
        if re.search(r"\bcontracts?\b", q):
            if re.search(r"\b(?:value|worth|total|sum)\b", q):
                return "SELECT status, COUNT(*) AS contract_count, SUM(contract_value) AS total_value FROM contracts GROUP BY status ORDER BY 3 DESC"
            return "SELECT status, COUNT(*) AS contract_count FROM contracts GROUP BY status ORDER BY 2 DESC"
        if re.search(r"\b(?:clients?|customers?)\b", q):
            if by_industry:
                return "SELECT industry, COUNT(*) AS client_count FROM clients GROUP BY industry ORDER BY 2 DESC"
            if by_country:
                return "SELECT country, COUNT(*) AS client_count FROM clients GROUP BY country ORDER BY 2 DESC"
            if by_status:
                return "SELECT status, COUNT(*) AS client_count FROM clients GROUP BY status ORDER BY 2 DESC"
            return "SELECT COUNT(*) AS client_count FROM clients"

        # ---- small reference tables ----------------------------------
        if re.search(r"\bdepartments?\b", q):
            return "SELECT department_name, department_code, location FROM departments ORDER BY department_name"
        if re.search(r"\broles?\b", q):
            return "SELECT role_name, role_level FROM roles ORDER BY role_id"
        if re.search(r"\bpolic(?:y|ies)\b", q):
            where = f" WHERE department_id = {dept_id}" if dept_id else ""
            return f"SELECT COUNT(*) AS policy_count FROM policies{where}"
        if re.search(r"\bdocuments?\b", q):
            return "SELECT document_type, COUNT(*) AS document_count FROM documents GROUP BY document_type ORDER BY 2 DESC"
        return None


postgres_retriever = PostgresRetriever()
