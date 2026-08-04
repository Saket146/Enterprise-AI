# Enterprise AI OS - PostgreSQL Database Schema

## Naming Convention

### Tables

- Use lowercase
- Use snake_case
- Use plural names

Example:

employees
departments
projects

---

### Primary Keys

Always:

<entity>_id

Examples:

employee_id
department_id
project_id

---

### Foreign Keys

Reference the parent table primary key.

Examples:

department_id
manager_id
client_id

---

### Timestamps

Every table should contain:

created_at
updated_at

---

### Status Fields

Use VARCHAR instead of ENUM to keep the schema easier to evolve.

Examples:

ACTIVE
INACTIVE
PENDING
COMPLETED

---

### UUID

Use INTEGER primary keys for simplicity in this academic project.

UUIDs can be introduced later if needed.

# Organization

1. departments
2. roles
3. employees
4. employee_roles

---

# Projects

5. projects
6. project_members
7. tasks
8. milestones

---

# HR

9. attendance
10. leave_requests
11. payroll
12. performance_reviews

---

# Finance

13. budgets
14. expenses
15. invoices
16. vendors

---

# Sales

17. clients
18. contracts

---

# Knowledge Management

19. documents
20. meetings
21. emails
22. policies

---

# AI Operations

23. chat_sessions
24. workflow_runs
25. agent_logs
26. audit_logs

# High-Level Relationships

Department
│
├── Employees
│     ├── Payroll
│     ├── Attendance
│     ├── Leave Requests
│     ├── Performance Reviews
│     └── Employee Roles
│
├── Projects
│     ├── Tasks
│     ├── Milestones
│     └── Project Members
│
├── Documents
│
├── Meetings
│
└── Policies

Clients
│
├── Projects
└── Contracts

Projects
│
├── Budgets
├── Expenses
├── Documents
├── Meetings
└── Tasks

Chat Sessions
│
└── Workflow Runs
      │
      ├── Agent Logs
      └── Audit Logs

# Estimated Data Volume

Departments          : 12
Roles                : 15
Employees            : 1000
Employee Roles       : 1200

Projects             : 500
Tasks                : 5000
Milestones           : 1500
Project Members      : 6000

Attendance           : 100000
Leave Requests       : 3500
Payroll              : 12000
Performance Reviews  : 2000

Clients              : 300
Contracts            : 400

Budgets              : 500
Expenses             : 4000
Invoices             : 2500
Vendors              : 100

Documents            : 5000
Meetings             : 2500
Emails               : 10000
Policies             : 500

Chat Sessions        : 5000
Workflow Runs        : 15000
Agent Logs           : 75000
Audit Logs           : 50000