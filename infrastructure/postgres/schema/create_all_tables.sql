CREATE TABLE departments (
    department_id SERIAL PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    department_code VARCHAR(10) NOT NULL UNIQUE,
    description TEXT,
    location VARCHAR(100),
    budget DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(100) NOT NULL UNIQUE,
    role_level VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,

    first_name VARCHAR(100) NOT NULL,

    last_name VARCHAR(100) NOT NULL,

    email VARCHAR(150) UNIQUE NOT NULL,

    phone VARCHAR(20),

    gender VARCHAR(20),

    date_of_birth DATE,

    hire_date DATE,

    department_id INTEGER,

    role_id INTEGER,

    manager_id INTEGER,

    employment_status VARCHAR(30),

    salary DECIMAL(12,2),

    office_location VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_department
        FOREIGN KEY (department_id)
        REFERENCES departments(department_id),

    CONSTRAINT fk_role
        FOREIGN KEY (role_id)
        REFERENCES roles(role_id),

    CONSTRAINT fk_manager
        FOREIGN KEY (manager_id)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- PROJECTS TABLE
-- ==========================================

CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,

    project_name VARCHAR(200) NOT NULL,

    project_code VARCHAR(30) UNIQUE NOT NULL,

    client_id INTEGER,

    department_id INTEGER,

    project_manager_id INTEGER,

    status VARCHAR(30),

    start_date DATE,

    end_date DATE,

    budget DECIMAL(15,2),

    priority VARCHAR(20),

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_project_department
        FOREIGN KEY (department_id)
        REFERENCES departments(department_id),

    CONSTRAINT fk_project_manager
        FOREIGN KEY (project_manager_id)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- PROJECT MEMBERS
-- ==========================================

CREATE TABLE project_members (

    project_member_id SERIAL PRIMARY KEY,

    project_id INTEGER NOT NULL,

    employee_id INTEGER NOT NULL,

    assigned_role VARCHAR(100),

    allocation_percentage INTEGER,

    assigned_date DATE,

    CONSTRAINT fk_pm_project
        FOREIGN KEY(project_id)
        REFERENCES projects(project_id),

    CONSTRAINT fk_pm_employee
        FOREIGN KEY(employee_id)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- TASKS
-- ==========================================

CREATE TABLE tasks (

    task_id SERIAL PRIMARY KEY,

    project_id INTEGER NOT NULL,

    assigned_to INTEGER,

    title VARCHAR(250),

    description TEXT,

    status VARCHAR(30),

    priority VARCHAR(30),

    start_date DATE,

    due_date DATE,

    completed_date DATE,

    estimated_hours INTEGER,

    actual_hours INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_task_project
        FOREIGN KEY(project_id)
        REFERENCES projects(project_id),

    CONSTRAINT fk_task_employee
        FOREIGN KEY(assigned_to)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- MILESTONES
-- ==========================================

CREATE TABLE milestones (

    milestone_id SERIAL PRIMARY KEY,

    project_id INTEGER NOT NULL,

    milestone_name VARCHAR(200),

    due_date DATE,

    completion_date DATE,

    status VARCHAR(30),

    CONSTRAINT fk_milestone_project
        FOREIGN KEY(project_id)
        REFERENCES projects(project_id)
);

-- ==========================================
-- CLIENTS
-- ==========================================

CREATE TABLE clients (

    client_id SERIAL PRIMARY KEY,

    client_name VARCHAR(200) NOT NULL,

    industry VARCHAR(100),

    contact_person VARCHAR(150),

    email VARCHAR(150),

    phone VARCHAR(20),

    country VARCHAR(100),

    status VARCHAR(30),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- CONTRACTS
-- ==========================================

CREATE TABLE contracts (

    contract_id SERIAL PRIMARY KEY,

    client_id INTEGER NOT NULL,

    contract_number VARCHAR(50) UNIQUE,

    contract_title VARCHAR(200),

    start_date DATE,

    end_date DATE,

    contract_value DECIMAL(15,2),

    status VARCHAR(30),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_contract_client
        FOREIGN KEY(client_id)
        REFERENCES clients(client_id)
);

-- ==========================================
-- ADD PROJECT -> CLIENT RELATION
-- ==========================================

ALTER TABLE projects
ADD CONSTRAINT fk_project_client
FOREIGN KEY (client_id)
REFERENCES clients(client_id);

-- ==========================================
-- DOCUMENTS
-- ==========================================

CREATE TABLE documents (

    document_id SERIAL PRIMARY KEY,

    project_id INTEGER,

    department_id INTEGER,

    title VARCHAR(250),

    document_type VARCHAR(100),

    file_name VARCHAR(255),

    created_by INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_document_project
        FOREIGN KEY(project_id)
        REFERENCES projects(project_id),

    CONSTRAINT fk_document_department
        FOREIGN KEY(department_id)
        REFERENCES departments(department_id),

    CONSTRAINT fk_document_employee
        FOREIGN KEY(created_by)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- MEETINGS
-- ==========================================

CREATE TABLE meetings (

    meeting_id SERIAL PRIMARY KEY,

    project_id INTEGER,

    organizer_id INTEGER,

    meeting_title VARCHAR(250),

    meeting_date TIMESTAMP,

    meeting_room VARCHAR(100),

    minutes TEXT,

    CONSTRAINT fk_meeting_project
        FOREIGN KEY(project_id)
        REFERENCES projects(project_id),

    CONSTRAINT fk_meeting_employee
        FOREIGN KEY(organizer_id)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- EMAILS
-- ==========================================

CREATE TABLE emails (

    email_id SERIAL PRIMARY KEY,

    sender_id INTEGER,

    receiver_id INTEGER,

    subject VARCHAR(250),

    body TEXT,

    sent_at TIMESTAMP,

    CONSTRAINT fk_email_sender
        FOREIGN KEY(sender_id)
        REFERENCES employees(employee_id),

    CONSTRAINT fk_email_receiver
        FOREIGN KEY(receiver_id)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- POLICIES
-- ==========================================

CREATE TABLE policies (

    policy_id SERIAL PRIMARY KEY,

    department_id INTEGER,

    policy_name VARCHAR(200),

    version VARCHAR(20),

    effective_date DATE,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_policy_department
        FOREIGN KEY(department_id)
        REFERENCES departments(department_id)
);

-- ==========================================
-- ATTENDANCE
-- ==========================================

CREATE TABLE attendance (

    attendance_id SERIAL PRIMARY KEY,

    employee_id INTEGER NOT NULL,

    attendance_date DATE NOT NULL,

    check_in TIME,

    check_out TIME,

    work_mode VARCHAR(20),

    status VARCHAR(20),

    CONSTRAINT fk_attendance_employee
        FOREIGN KEY(employee_id)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- LEAVE REQUESTS
-- ==========================================

CREATE TABLE leave_requests (

    leave_id SERIAL PRIMARY KEY,

    employee_id INTEGER NOT NULL,

    leave_type VARCHAR(30),

    start_date DATE,

    end_date DATE,

    reason TEXT,

    approval_status VARCHAR(20),

    approved_by INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_leave_employee
        FOREIGN KEY(employee_id)
        REFERENCES employees(employee_id),

    CONSTRAINT fk_leave_manager
        FOREIGN KEY(approved_by)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- PAYROLL
-- ==========================================

CREATE TABLE payroll (

    payroll_id SERIAL PRIMARY KEY,

    employee_id INTEGER NOT NULL,

    pay_month INTEGER,

    pay_year INTEGER,

    basic_salary DECIMAL(12,2),

    bonus DECIMAL(12,2),

    deductions DECIMAL(12,2),

    net_salary DECIMAL(12,2),

    payment_date DATE,

    CONSTRAINT fk_payroll_employee
        FOREIGN KEY(employee_id)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- PERFORMANCE REVIEWS
-- ==========================================

CREATE TABLE performance_reviews (

    review_id SERIAL PRIMARY KEY,

    employee_id INTEGER NOT NULL,

    reviewer_id INTEGER,

    review_period VARCHAR(30),

    rating DECIMAL(3,2),

    comments TEXT,

    review_date DATE,

    CONSTRAINT fk_review_employee
        FOREIGN KEY(employee_id)
        REFERENCES employees(employee_id),

    CONSTRAINT fk_reviewer
        FOREIGN KEY(reviewer_id)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- VENDORS
-- ==========================================

CREATE TABLE vendors (

    vendor_id SERIAL PRIMARY KEY,

    vendor_name VARCHAR(200) NOT NULL,

    contact_person VARCHAR(150),

    email VARCHAR(150),

    phone VARCHAR(20),

    address TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- BUDGETS
-- ==========================================

CREATE TABLE budgets (

    budget_id SERIAL PRIMARY KEY,

    department_id INTEGER,

    project_id INTEGER,

    fiscal_year INTEGER,

    allocated_amount DECIMAL(15,2),

    approved_amount DECIMAL(15,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_budget_department
        FOREIGN KEY(department_id)
        REFERENCES departments(department_id),

    CONSTRAINT fk_budget_project
        FOREIGN KEY(project_id)
        REFERENCES projects(project_id)
);

-- ==========================================
-- EXPENSES
-- ==========================================

CREATE TABLE expenses (

    expense_id SERIAL PRIMARY KEY,

    project_id INTEGER,

    vendor_id INTEGER,

    expense_category VARCHAR(100),

    amount DECIMAL(15,2),

    expense_date DATE,

    description TEXT,

    CONSTRAINT fk_expense_project
        FOREIGN KEY(project_id)
        REFERENCES projects(project_id),

    CONSTRAINT fk_expense_vendor
        FOREIGN KEY(vendor_id)
        REFERENCES vendors(vendor_id)
);

-- ==========================================
-- INVOICES
-- ==========================================

CREATE TABLE invoices (

    invoice_id SERIAL PRIMARY KEY,

    invoice_number VARCHAR(50) UNIQUE,

    vendor_id INTEGER,

    invoice_date DATE,

    due_date DATE,

    amount DECIMAL(15,2),

    payment_status VARCHAR(30),

    CONSTRAINT fk_invoice_vendor
        FOREIGN KEY(vendor_id)
        REFERENCES vendors(vendor_id)
);

-- ==========================================
-- CHAT SESSIONS
-- Stores user conversations with AI system
-- ==========================================

CREATE TABLE chat_sessions (

    session_id SERIAL PRIMARY KEY,

    employee_id INTEGER,

    session_title VARCHAR(250),

    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    ended_at TIMESTAMP,

    status VARCHAR(30),

    CONSTRAINT fk_session_employee
        FOREIGN KEY(employee_id)
        REFERENCES employees(employee_id)
);


-- ==========================================
-- WORKFLOW RUNS
-- Stores LangGraph workflow executions
-- ==========================================

CREATE TABLE workflow_runs (

    workflow_id SERIAL PRIMARY KEY,

    session_id INTEGER,

    workflow_name VARCHAR(200),

    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    completed_at TIMESTAMP,

    status VARCHAR(30),

    final_output TEXT,

    confidence_score DECIMAL(5,2),

    CONSTRAINT fk_workflow_session
        FOREIGN KEY(session_id)
        REFERENCES chat_sessions(session_id)
);


-- ==========================================
-- AGENT LOGS
-- Stores individual AI agent activities
-- ==========================================

CREATE TABLE agent_logs (

    agent_log_id SERIAL PRIMARY KEY,

    workflow_id INTEGER,

    agent_name VARCHAR(100),

    task_description TEXT,

    input_data TEXT,

    output_data TEXT,

    execution_time_ms INTEGER,

    confidence_score DECIMAL(5,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    CONSTRAINT fk_agent_workflow
        FOREIGN KEY(workflow_id)
        REFERENCES workflow_runs(workflow_id)
);


-- ==========================================
-- AUDIT LOGS
-- Enterprise security tracking
-- ==========================================

CREATE TABLE audit_logs (

    audit_id SERIAL PRIMARY KEY,

    employee_id INTEGER,

    action_type VARCHAR(100),

    resource_type VARCHAR(100),

    resource_id INTEGER,

    ip_address VARCHAR(50),

    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    details TEXT,


    CONSTRAINT fk_audit_employee
        FOREIGN KEY(employee_id)
        REFERENCES employees(employee_id)
);

-- ==========================================
-- EMPLOYEE INDEXES
-- ==========================================

CREATE INDEX idx_employee_department
ON employees(department_id);

CREATE INDEX idx_employee_role
ON employees(role_id);

CREATE INDEX idx_employee_manager
ON employees(manager_id);


-- ==========================================
-- PROJECT INDEXES
-- ==========================================

CREATE INDEX idx_project_department
ON projects(department_id);

CREATE INDEX idx_project_manager
ON projects(project_manager_id);

CREATE INDEX idx_task_project
ON tasks(project_id);

CREATE INDEX idx_task_employee
ON tasks(assigned_to);


-- ==========================================
-- HR INDEXES
-- ==========================================

CREATE INDEX idx_attendance_employee
ON attendance(employee_id);

CREATE INDEX idx_leave_employee
ON leave_requests(employee_id);

CREATE INDEX idx_payroll_employee
ON payroll(employee_id);


-- ==========================================
-- FINANCE INDEXES
-- ==========================================

CREATE INDEX idx_expense_project
ON expenses(project_id);

CREATE INDEX idx_invoice_vendor
ON invoices(vendor_id);


-- ==========================================
-- KNOWLEDGE INDEXES
-- ==========================================

CREATE INDEX idx_documents_project
ON documents(project_id);

CREATE INDEX idx_documents_department
ON documents(department_id);


-- ==========================================
-- AI SYSTEM INDEXES
-- ==========================================

CREATE INDEX idx_chat_employee
ON chat_sessions(employee_id);

CREATE INDEX idx_workflow_session
ON workflow_runs(session_id);

CREATE INDEX idx_agent_workflow
ON agent_logs(workflow_id);

CREATE INDEX idx_audit_employee
ON audit_logs(employee_id);