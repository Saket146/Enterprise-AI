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