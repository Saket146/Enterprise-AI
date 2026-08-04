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