"""
Enterprise AI Operating System
Organization Blueprint

This file defines how the company is structured.
Every future generator (employees, projects, payroll, etc.)
will use these business rules.
"""

DEPARTMENT_STRUCTURE = {

    "Engineering": {
        "department_id": 1,
        "headcount": 300,
        "manager_role": "Engineering Manager",
        "roles": {
            "Engineering Manager": 10,
            "Backend Engineer": 130,
            "Frontend Engineer": 120,
            "Intern": 39
        }
    },

    "Artificial Intelligence": {
        "department_id": 2,
        "headcount": 150,
        "manager_role": "Engineering Manager",
        "roles": {
            "Engineering Manager": 5,
            "AI Engineer": 90,
            "Data Scientist": 40,
            "Intern": 15
        }
    },

    "Quality Assurance": {
        "department_id": 3,
        "headcount": 100,
        "manager_role": "Engineering Manager",
        "roles": {
            "Engineering Manager": 4,
            "QA Engineer": 76,
            "Intern": 20
        }
    },

    "Human Resources": {
        "department_id": 4,
        "headcount": 40,
        "manager_role": "HR Director",
        "roles": {
            "HR Director": 1,
            "HR Executive": 34,
            "Intern": 5
        }
    },

    "Finance": {
        "department_id": 5,
        "headcount": 50,
        "manager_role": "CFO",
        "roles": {
            "CFO": 1,
            "Finance Analyst": 44,
            "Intern": 5
        }
    },

    "Sales": {
        "department_id": 6,
        "headcount": 120,
        "manager_role": "Project Manager",
        "roles": {
            "Project Manager": 8,
            "Sales Executive": 92,
            "Intern": 19
        }
    },

    "Marketing": {
        "department_id": 7,
        "headcount": 40,
        "manager_role": "Project Manager",
        "roles": {
            "Project Manager": 2,
            "Sales Executive": 30,
            "Intern": 8
        }
    },

    "Operations": {
        "department_id": 8,
        "headcount": 50,
        "manager_role": "Project Manager",
        "roles": {
            "Project Manager": 3,
            "Backend Engineer": 20,
            "Frontend Engineer": 17,
            "Intern": 10
        }
    },

    "Legal": {
        "department_id": 9,
        "headcount": 10,
        "manager_role": "Project Manager",
        "roles": {
            "Project Manager": 1,
            "Sales Executive": 7,
            "Intern": 2
        }
    },

    "IT Support": {
        "department_id": 10,
        "headcount": 40,
        "manager_role": "Engineering Manager",
        "roles": {
            "Engineering Manager": 2,
            "Backend Engineer": 28,
            "Intern": 10
        }
    },

    "Data Science": {
        "department_id": 11,
        "headcount": 60,
        "manager_role": "Engineering Manager",
        "roles": {
            "Engineering Manager": 2,
            "Data Scientist": 48,
            "Intern": 10
        }
    },

    "Customer Success": {
        "department_id": 12,
        "headcount": 40,
        "manager_role": "Project Manager",
        "roles": {
            "Project Manager": 2,
            "Sales Executive": 28,
            "Intern": 10
        }
    },
    "Executive Office": {
        "department_id": 13,
        "headcount": 2,
        "manager_role": "CEO",
        "roles": {
            "CEO": 1,
            "CTO": 1
        }
    }

}

total = 0

for dept in DEPARTMENT_STRUCTURE.values():
    total += sum(dept["roles"].values())

print(total)