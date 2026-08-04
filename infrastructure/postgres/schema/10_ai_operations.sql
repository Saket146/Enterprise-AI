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