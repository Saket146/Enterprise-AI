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