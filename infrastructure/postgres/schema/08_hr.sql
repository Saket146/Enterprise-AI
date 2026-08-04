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