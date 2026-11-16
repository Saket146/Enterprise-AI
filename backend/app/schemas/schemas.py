from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional, List, Union
from datetime import date, datetime, time
from decimal import Decimal

# ----------------------------------------------------
# Authentication Schemas
# ----------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    employee_id: int
    email: str
    role: str
    first_name: str
    last_name: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    employee_id: Optional[int] = None

# ----------------------------------------------------
# Department and Role Schemas
# ----------------------------------------------------
class DepartmentBase(BaseModel):
    department_name: str
    department_code: str
    description: Optional[str] = None
    location: Optional[str] = None
    budget: Optional[Decimal] = None

class DepartmentResponse(DepartmentBase):
    department_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def _mask_budget(self):
        """
        RBAC field-level masking. A department's budget is only returned to finance and
        executive roles, or to managers for their own department. Departments are nested
        inside employee, project, policy and document responses, so this runs for all of them.
        """
        from app.security.permissions import Perm, can, current_viewer
        viewer = current_viewer.get()
        allowed = can(viewer, Perm.FINANCE_READ) or (
            can(viewer, Perm.FINANCE_READ_OWN_DEPT) and viewer.get("department_id") == self.department_id
        )
        if not allowed:
            self.budget = None
        return self

class RoleBase(BaseModel):
    role_name: str
    role_level: Optional[str] = None
    description: Optional[str] = None

class RoleResponse(RoleBase):
    role_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------------------------
# Employee Schemas
# ----------------------------------------------------
class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    hire_date: Optional[date] = None
    department_id: Optional[int] = None
    role_id: Optional[int] = None
    manager_id: Optional[int] = None
    employment_status: Optional[str] = None
    salary: Optional[Decimal] = None
    office_location: Optional[str] = None

class EmployeeCreate(EmployeeBase):
    password: str

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    role_id: Optional[int] = None
    manager_id: Optional[int] = None
    employment_status: Optional[str] = None
    office_location: Optional[str] = None

class EmployeeResponse(EmployeeBase):
    employee_id: int
    created_at: datetime
    updated_at: datetime
    role: Optional[RoleResponse] = None
    department: Optional[DepartmentResponse] = None
    # Avoid infinite manager recursion, just save details
    manager_name: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def _mask_sensitive_fields(self):
        """
        RBAC field-level masking.  Salary, date of birth and phone are only
        returned to the employee, their direct manager, or HR/executive roles.
        This runs wherever an employee is serialised (also when nested inside
        projects, tasks, documents, emails and meetings).
        """
        from app.security.permissions import can_view_employee_sensitive, current_viewer
        if not can_view_employee_sensitive(current_viewer.get(), self.employee_id, self.manager_id):
            self.salary = None
            self.date_of_birth = None
            self.phone = None
        return self

class EmployeeListResponse(BaseModel):
    total: int
    items: List[EmployeeResponse]

# ----------------------------------------------------
# Project, Task, and Milestone Schemas
# ----------------------------------------------------
class ClientResponse(BaseModel):
    client_id: int
    company_name: Optional[str] = None
    client_name: Optional[str] = None
    industry: Optional[str] = None
    client_size: Optional[str] = None
    annual_revenue: Optional[Decimal] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    contract_value: Optional[Decimal] = None
    account_manager: Optional[Union[int, str]] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True

class ProjectBase(BaseModel):
    project_name: str
    project_code: str
    client_id: Optional[int] = None
    department_id: Optional[int] = None
    project_manager_id: Optional[int] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = None
    priority: Optional[str] = None
    description: Optional[str] = None

class ProjectResponse(ProjectBase):
    project_id: int
    created_at: datetime
    updated_at: datetime
    client: Optional[ClientResponse] = None
    department: Optional[DepartmentResponse] = None
    manager: Optional[EmployeeResponse] = None

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    project_id: int
    assigned_to: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None

class TaskResponse(TaskBase):
    task_id: int
    created_at: datetime
    assignee: Optional[EmployeeResponse] = None

    class Config:
        from_attributes = True

class MilestoneResponse(BaseModel):
    milestone_id: int
    project_id: int
    milestone_name: str
    due_date: Optional[date] = None
    completion_date: Optional[date] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True

# ----------------------------------------------------
# Document and Policy Schemas
# ----------------------------------------------------
class DocumentResponse(BaseModel):
    document_id: int
    project_id: Optional[int] = None
    department_id: Optional[int] = None
    title: Optional[str] = None
    document_type: Optional[str] = None
    file_name: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    creator: Optional[EmployeeResponse] = None
    department: Optional[DepartmentResponse] = None
    # For the caller: "open" (may read it), "pending" (access requested) or "request" (may ask for access)
    my_access: Optional[str] = None

    class Config:
        from_attributes = True

class PolicyResponse(BaseModel):
    policy_id: int
    department_id: Optional[int] = None
    policy_name: Optional[str] = None
    version: Optional[str] = None
    effective_date: Optional[date] = None
    description: Optional[str] = None
    created_at: datetime
    department: Optional[DepartmentResponse] = None

    class Config:
        from_attributes = True

# ----------------------------------------------------
# Communications Schemas
# ----------------------------------------------------
class EmailResponse(BaseModel):
    email_id: int
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    sent_at: Optional[datetime] = None
    sender: Optional[EmployeeResponse] = None
    receiver: Optional[EmployeeResponse] = None

    class Config:
        from_attributes = True

class MeetingResponse(BaseModel):
    meeting_id: int
    project_id: Optional[int] = None
    organizer_id: Optional[int] = None
    meeting_title: Optional[str] = None
    meeting_date: Optional[datetime] = None
    meeting_room: Optional[str] = None
    minutes: Optional[str] = None
    organizer: Optional[EmployeeResponse] = None

    class Config:
        from_attributes = True

# ----------------------------------------------------
# Chat & Agent Schemas
# ----------------------------------------------------
class AgentLogResponse(BaseModel):
    agent_log_id: int
    workflow_id: Optional[int] = None
    agent_name: Optional[str] = None
    task_description: Optional[str] = None
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    execution_time_ms: Optional[int] = None
    confidence_score: Optional[Decimal] = None
    created_at: datetime

    class Config:
        from_attributes = True

class WorkflowRunResponse(BaseModel):
    workflow_id: int
    session_id: Optional[int] = None
    workflow_name: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: Optional[str] = None
    final_output: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    agent_logs: List[AgentLogResponse] = []

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    session_id: int
    employee_id: Optional[int] = None
    session_title: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: Optional[str] = None
    workflows: List[WorkflowRunResponse] = []

    class Config:
        from_attributes = True

# ----------------------------------------------------
# Pipeline/Ingestion Schemas
# ----------------------------------------------------
class SyncResponse(BaseModel):
    success: bool
    message: str
    details: Optional[dict] = None
