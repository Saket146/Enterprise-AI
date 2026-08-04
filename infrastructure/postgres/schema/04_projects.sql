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