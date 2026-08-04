"""
==========================================================
Enterprise AI Operating System
Enterprise Data Factory
==========================================================

Generates the complete synthetic enterprise:

✔ Organization
✔ Employees
✔ Projects
✔ Clients
✔ HR
✔ Finance
✔ Knowledge
✔ AI Operations

Author: Saket
"""

import random
import json
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

from company_config import COMPANY
from organization_blueprint import DEPARTMENT_STRUCTURE

# ==========================================================
# Configuration
# ==========================================================

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)

BASE_DIR = Path(__file__).resolve().parents[2]

CSV_DIR = BASE_DIR / "csv"
JSON_DIR = BASE_DIR / "json"

CSV_DIR.mkdir(exist_ok=True)
JSON_DIR.mkdir(exist_ok=True)

print("=" * 60)
print(f"Generating Synthetic Enterprise Data")
print(f"Company : {COMPANY['name']}")
print("=" * 60)

# ==========================================================
# Helper Functions
# ==========================================================

def save_dataset(data, folder, filename):
    """
    Saves both CSV and JSON versions of a dataset.
    """

    csv_folder = CSV_DIR / folder
    json_folder = JSON_DIR / folder

    csv_folder.mkdir(parents=True, exist_ok=True)
    json_folder.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(data)


# Fix integer columns containing NULL values

    integer_columns = [
        "employee_id",
        "department_id",
        "role_id",
        "manager_id"
    ]


    for column in integer_columns:

        if column in df.columns:

            df[column] = (
                df[column]
                .astype("Int64")
            )

    df.to_csv(csv_folder / f"{filename}.csv", index=False)

    with open(json_folder / f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, default=str)

    print(f"✔ {filename} generated ({len(df)} rows)")

# ==========================================================
# Main
# ==========================================================

ROLE_MAPPING = {
    "CEO": {"role_id": 1, "salary": (6000000, 8000000)},
    "CTO": {"role_id": 2, "salary": (5000000, 7000000)},
    "CFO": {"role_id": 3, "salary": (4500000, 6500000)},
    "HR Director": {"role_id": 4, "salary": (2500000, 3500000)},
    "Engineering Manager": {"role_id": 5, "salary": (2200000, 3500000)},
    "Project Manager": {"role_id": 6, "salary": (1800000, 2800000)},
    "Backend Engineer": {"role_id": 7, "salary": (900000, 1800000)},
    "Frontend Engineer": {"role_id": 8, "salary": (900000, 1700000)},
    "AI Engineer": {"role_id": 9, "salary": (1200000, 2200000)},
    "QA Engineer": {"role_id": 10, "salary": (700000, 1400000)},
    "Data Scientist": {"role_id": 11, "salary": (1300000, 2400000)},
    "Finance Analyst": {"role_id": 12, "salary": (800000, 1500000)},
    "Sales Executive": {"role_id": 13, "salary": (600000, 1400000)},
    "HR Executive": {"role_id": 14, "salary": (600000, 1200000)},
    "Intern": {"role_id": 15, "salary": (250000, 400000)}
}

def random_salary(role):
    low, high = ROLE_MAPPING[role]["salary"]
    return random.randint(low, high)

# ==========================================================
# Manager Hierarchy Assignment
# ==========================================================

def assign_managers(employees):

    """
    Creates reporting hierarchy between employees.

    Rules:
    - Executives have no managers
    - Managers report to executives
    - Employees report to managers
    """

    # Store employees by role

    role_groups = {}

    for employee in employees:

        role_id = employee["role_id"]

        if role_id not in role_groups:
            role_groups[role_id] = []

        role_groups[role_id].append(employee)


    # Role IDs from our schema

    CEO = 1
    CTO = 2
    CFO = 3
    HR_DIRECTOR = 4

    ENGINEERING_MANAGER = 5
    PROJECT_MANAGER = 6


    # --------------------------------------------------
    # Find top executives
    # --------------------------------------------------

    executives = {}

    for role_id in [CEO, CTO, CFO, HR_DIRECTOR]:

        if role_id in role_groups:

            executives[role_id] = role_groups[role_id][0]["employee_id"]


    # --------------------------------------------------
    # Assign managers
    # --------------------------------------------------

    managers = []

    if ENGINEERING_MANAGER in role_groups:
        managers.extend(
            role_groups[ENGINEERING_MANAGER]
        )


    if PROJECT_MANAGER in role_groups:
        managers.extend(
            role_groups[PROJECT_MANAGER]
        )


    # --------------------------------------------------
    # Assign manager_id
    # --------------------------------------------------

    for employee in employees:


        role_id = employee["role_id"]


        # Executives
        if role_id in [
            CEO,
            CTO,
            CFO,
            HR_DIRECTOR
        ]:
            employee["manager_id"] = None


        # Managers
        elif role_id in [
            ENGINEERING_MANAGER,
            PROJECT_MANAGER
        ]:

            employee["manager_id"] = random.choice(
                list(executives.values())
            )


        # Other employees

        else:

            possible_managers = [
                m["employee_id"]
                for m in managers
            ]

            employee["manager_id"] = random.choice(
                possible_managers
            )


    return employees

# ==========================================================
# Employee Data Validation
# ==========================================================

def validate_employees(employees):

    print("\nRunning employee validation...\n")


    # 1. Employee count

    assert len(employees) == 1000, \
        "Employee count mismatch"

    print("✔ Employee count verified")


    # 2. Required fields

    required_fields = [
        "first_name",
        "last_name",
        "email",
        "department_id",
        "role_id",
        "salary"
    ]


    for employee in employees:

        for field in required_fields:

            assert employee[field] is not None, \
                f"Missing {field}"


    print("✔ Required fields verified")


    # 3. Manager validation

    employee_ids = {
        emp["employee_id"]
        for emp in employees
    }


    for employee in employees:

        if employee["manager_id"]:

            assert employee["manager_id"] in employee_ids, \
                "Invalid manager reference"


    print("✔ Manager hierarchy verified")


    # 4. Salary validation

    for employee in employees:

        assert employee["salary"] > 0


    print("✔ Salary validation verified")


    print("\nEmployee dataset validation successful ✅\n")

# ==========================================================
# Employee Generation
# ==========================================================

def generate_employees():

    executive_roles = [
    "CEO",
    "CTO",
    "CFO",
    "HR Director"
]

    employees = []

    employee_id = 1

    office_locations = {
        1: "Hyderabad",
        2: "Bengaluru",
        3: "Hyderabad",
        4: "Hyderabad",
        5: "Mumbai",
        6: "Mumbai",
        7: "Mumbai",
        8: "Pune",
        9: "Mumbai",
        10: "Chennai",
        11: "Bengaluru",
        12: "Pune",
        13: "Hyderabad"
    }

    for department_name, dept in DEPARTMENT_STRUCTURE.items():

        department_id = dept["department_id"]

        for role_name, count in dept["roles"].items():

            role_id = ROLE_MAPPING[role_name]["role_id"]

            for _ in range(count):

                gender = random.choice(["Male", "Female"])

                if gender == "Male":
                    first_name = fake.first_name_male()
                else:
                    first_name = fake.first_name_female()

                last_name = fake.last_name()

                email = (
                    f"{first_name.lower()}."
                    f"{last_name.lower()}."
                    f"{employee_id}@apexnova.ai"
                )

                phone = fake.phone_number()

                dob = fake.date_between(
                    start_date="-45y",
                    end_date="-21y"
                )

                hire_date = fake.date_between(
                    start_date="-7y",
                    end_date="today"
                )

                employee = {

                    "employee_id": employee_id,

                    "first_name": first_name,

                    "last_name": last_name,

                    "email": email,

                    "phone": phone,

                    "gender": gender,

                    "date_of_birth": dob,

                    "hire_date": hire_date,

                    "department_id": department_id,

                    "role_id": role_id,

                    "manager_id": None,

                    "employment_status": random.choices(
                        ["Active", "On Leave", "Resigned"],
                        weights=[90, 5, 5]
                    )[0],

                    "salary": random_salary(role_name),

                    "office_location": office_locations[department_id],

                    "created_at": datetime.now(),

                    "updated_at": datetime.now()

                }

                employees.append(employee)

                employee_id += 1

    return employees

if __name__ == "__main__":

    print("\nEnterprise Data Factory Started...\n")

    employees = generate_employees()

    print(f"Generated {len(employees)} employees.")

    employees = assign_managers(employees)

    print("Manager hierarchy assigned.")

    validate_employees(employees)

    save_dataset(
        employees,
        "organization",
        "employees"
    )

    print("\nEnterprise Data Factory Completed Successfully!")