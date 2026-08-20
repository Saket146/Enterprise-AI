from sqlalchemy import Column, Integer, String, Text, DECIMAL, Date, DateTime, Time, ForeignKey, Table, func
from sqlalchemy.orm import relationship
from app.database.connection import Base

# Model Definitions

class Department(Base):
    __tablename__ = "departments"

    department_id = Column(Integer, primary_key=True, index=True)
    department_name = Column(String(100), nullable=False, unique=True)
    department_code = Column(String(10), nullable=False, unique=True)
    description = Column(Text)
    location = Column(String(100))
    budget = Column(DECIMAL(15, 2))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    employees = relationship("Employee", back_populates="department")
    projects = relationship("Project", back_populates="department")
    documents = relationship("Document", back_populates="department")
    policies = relationship("Policy", back_populates="department")
    budgets = relationship("Budget", back_populates="department")


class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(100), nullable=False, unique=True)
    role_level = Column(String(50))
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    employees = relationship("Employee", back_populates="role")


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    phone = Column(String(20))
    gender = Column(String(20))
    date_of_birth = Column(Date)
    hire_date = Column(Date)
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    role_id = Column(Integer, ForeignKey("roles.role_id"))
    manager_id = Column(Integer, ForeignKey("employees.employee_id"))
    employment_status = Column(String(30))
    salary = Column(DECIMAL(12, 2))
    office_location = Column(String(100))
    hashed_password = Column(String(255), nullable=True) # Custom, added dynamically if missing
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    department = relationship("Department", back_populates="employees")
    role = relationship("Role", back_populates="employees")
    
    # Self-referential hierarchy
    manager = relationship("Employee", remote_side=[employee_id], back_populates="subordinates")
    subordinates = relationship("Employee", back_populates="manager")

    project_memberships = relationship("ProjectMember", back_populates="employee")
    projects_managed = relationship("Project", back_populates="manager")
    tasks_assigned = relationship("Task", back_populates="assignee")
    documents_created = relationship("Document", back_populates="creator")
    meetings_organized = relationship("Meeting", back_populates="organizer")
    
    chat_sessions = relationship("ChatSession", back_populates="employee")
    audit_logs = relationship("AuditLog", back_populates="employee")


class Client(Base):
    __tablename__ = "clients"

    client_id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(200), nullable=False)
    industry = Column(String(100))
    contact_person = Column(String(150))
    email = Column(String(150))
    phone = Column(String(20))
    country = Column(String(100))
    status = Column(String(30))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    projects = relationship("Project", back_populates="client")
    contracts = relationship("Contract", back_populates="client")


class Contract(Base):
    __tablename__ = "contracts"

    contract_id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.client_id"), nullable=False)
    contract_number = Column(String(50), unique=True)
    contract_title = Column(String(200))
    start_date = Column(Date)
    end_date = Column(Date)
    contract_value = Column(DECIMAL(15, 2))
    status = Column(String(30))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    client = relationship("Client", back_populates="contracts")


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(200), nullable=False)
    project_code = Column(String(30), nullable=False, unique=True)
    client_id = Column(Integer, ForeignKey("clients.client_id"))
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    project_manager_id = Column(Integer, ForeignKey("employees.employee_id"))
    status = Column(String(30))
    start_date = Column(Date)
    end_date = Column(Date)
    budget = Column(DECIMAL(15, 2))
    priority = Column(String(20))
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("Client", back_populates="projects")
    department = relationship("Department", back_populates="projects")
    manager = relationship("Employee", back_populates="projects_managed")
    
    members = relationship("ProjectMember", back_populates="project")
    tasks = relationship("Task", back_populates="project")
    milestones = relationship("Milestone", back_populates="project")
    documents = relationship("Document", back_populates="project")
    meetings = relationship("Meeting", back_populates="project")
    budgets = relationship("Budget", back_populates="project")
    expenses = relationship("Expense", back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_members"

    project_member_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    assigned_role = Column(String(100))
    allocation_percentage = Column(Integer)
    assigned_date = Column(Date)

    # Relationships
    project = relationship("Project", back_populates="members")
    employee = relationship("Employee", back_populates="project_memberships")


class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("employees.employee_id"))
    title = Column(String(250))
    description = Column(Text)
    status = Column(String(30))
    priority = Column(String(30))
    start_date = Column(Date)
    due_date = Column(Date)
    completed_date = Column(Date)
    estimated_hours = Column(Integer)
    actual_hours = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("Employee", back_populates="tasks_assigned")


class Milestone(Base):
    __tablename__ = "milestones"

    milestone_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    milestone_name = Column(String(200))
    due_date = Column(Date)
    completion_date = Column(Date)
    status = Column(String(30))

    # Relationships
    project = relationship("Project", back_populates="milestones")


class Document(Base):
    __tablename__ = "documents"

    document_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    title = Column(String(250))
    document_type = Column(String(100))
    file_name = Column(String(255))
    created_by = Column(Integer, ForeignKey("employees.employee_id"))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="documents")
    department = relationship("Department", back_populates="documents")
    creator = relationship("Employee", back_populates="documents_created")


class Meeting(Base):
    __tablename__ = "meetings"

    meeting_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    organizer_id = Column(Integer, ForeignKey("employees.employee_id"))
    meeting_title = Column(String(250))
    meeting_date = Column(DateTime)
    meeting_room = Column(String(100))
    minutes = Column(Text)

    # Relationships
    project = relationship("Project", back_populates="meetings")
    organizer = relationship("Employee", back_populates="meetings_organized")


class Email(Base):
    __tablename__ = "emails"

    email_id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("employees.employee_id"))
    receiver_id = Column(Integer, ForeignKey("employees.employee_id"))
    subject = Column(String(250))
    body = Column(Text)
    sent_at = Column(DateTime)

    # Relationships
    sender = relationship("Employee", foreign_keys=[sender_id])
    receiver = relationship("Employee", foreign_keys=[receiver_id])


class Policy(Base):
    __tablename__ = "policies"

    policy_id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    policy_name = Column(String(200))
    version = Column(String(20))
    effective_date = Column(Date)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    department = relationship("Department", back_populates="policies")


class Attendance(Base):
    __tablename__ = "attendance"

    attendance_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    check_in = Column(Time)
    check_out = Column(Time)
    work_mode = Column(String(20))
    status = Column(String(20))

    # Relationships
    employee = relationship("Employee")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    leave_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    leave_type = Column(String(30))
    start_date = Column(Date)
    end_date = Column(Date)
    reason = Column(Text)
    approval_status = Column(String(20))
    approved_by = Column(Integer, ForeignKey("employees.employee_id"))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id])
    approver = relationship("Employee", foreign_keys=[approved_by])


class Payroll(Base):
    __tablename__ = "payroll"

    payroll_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    pay_month = Column(Integer)
    pay_year = Column(Integer)
    basic_salary = Column(DECIMAL(12, 2))
    bonus = Column(DECIMAL(12, 2))
    deductions = Column(DECIMAL(12, 2))
    net_salary = Column(DECIMAL(12, 2))
    payment_date = Column(Date)

    # Relationships
    employee = relationship("Employee")


class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    review_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("employees.employee_id"))
    review_period = Column(String(30))
    rating = Column(DECIMAL(3, 2))
    comments = Column(Text)
    review_date = Column(Date)

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id])
    reviewer = relationship("Employee", foreign_keys=[reviewer_id])


class Vendor(Base):
    __tablename__ = "vendors"

    vendor_id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String(200), nullable=False)
    contact_person = Column(String(150))
    email = Column(String(150))
    phone = Column(String(20))
    address = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    expenses = relationship("Expense", back_populates="vendor")
    invoices = relationship("Invoice", back_populates="vendor")


class Budget(Base):
    __tablename__ = "budgets"

    budget_id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    fiscal_year = Column(Integer)
    allocated_amount = Column(DECIMAL(15, 2))
    approved_amount = Column(DECIMAL(15, 2))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    department = relationship("Department", back_populates="budgets")
    project = relationship("Project", back_populates="budgets")


class Expense(Base):
    __tablename__ = "expenses"

    expense_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    vendor_id = Column(Integer, ForeignKey("vendors.vendor_id"))
    expense_category = Column(String(100))
    amount = Column(DECIMAL(15, 2))
    expense_date = Column(Date)
    description = Column(Text)

    # Relationships
    project = relationship("Project", back_populates="expenses")
    vendor = relationship("Vendor", back_populates="expenses")


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True)
    vendor_id = Column(Integer, ForeignKey("vendors.vendor_id"))
    invoice_date = Column(Date)
    due_date = Column(Date)
    amount = Column(DECIMAL(15, 2))
    payment_status = Column(String(30))

    # Relationships
    vendor = relationship("Vendor", back_populates="invoices")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"))
    session_title = Column(String(250))
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime)
    status = Column(String(30))

    # Relationships
    employee = relationship("Employee", back_populates="chat_sessions")
    workflows = relationship("WorkflowRun", back_populates="session")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    workflow_id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.session_id"))
    workflow_name = Column(String(200))
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    status = Column(String(30))
    final_output = Column(Text)
    confidence_score = Column(DECIMAL(5, 2))

    # Relationships
    session = relationship("ChatSession", back_populates="workflows")
    agent_logs = relationship("AgentLog", back_populates="workflow")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    agent_log_id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflow_runs.workflow_id"))
    agent_name = Column(String(100))
    task_description = Column(Text)
    input_data = Column(Text)
    output_data = Column(Text)
    execution_time_ms = Column(Integer)
    confidence_score = Column(DECIMAL(5, 2))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    workflow = relationship("WorkflowRun", back_populates="agent_logs")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"))
    action_type = Column(String(100))
    resource_type = Column(String(100))
    resource_id = Column(Integer)
    ip_address = Column(String(50))
    timestamp = Column(DateTime, server_default=func.now())
    details = Column(Text)

    # Relationships
    employee = relationship("Employee", back_populates="audit_logs")


class Approval(Base):
    __tablename__ = "approvals"
    approval_id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflow_runs.workflow_id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("employees.employee_id"))
    approver_role = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    decision_note = Column(Text)
    decided_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    evaluation_id = Column(Integer, primary_key=True)
    suite_name = Column(String(100), nullable=False)
    metric_name = Column(String(100), nullable=False)
    score = Column(DECIMAL(6, 3), nullable=False)
    sample_count = Column(Integer, nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
