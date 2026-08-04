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