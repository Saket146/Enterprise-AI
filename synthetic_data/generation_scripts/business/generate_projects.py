"""
Enterprise AI Operating System

Project Generator

Generates enterprise projects linked with:
- Clients
- Contracts
- Departments
- Employees
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker


fake = Faker("en_IN")

random.seed(42)
Faker.seed(42)


BASE_DIR = Path(__file__).resolve().parents[2]


CSV_DIR = BASE_DIR / "csv" / "business"
JSON_DIR = BASE_DIR / "json" / "business"


CSV_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_TYPES = [
    "AI Platform Development",
    "Cloud Migration",
    "Enterprise Software Development",
    "Data Analytics Platform",
    "Automation System",
    "Cyber Security Implementation",
    "Mobile Application Development",
    "ERP Integration"
]


PROJECT_STATUS = [
    "Planning",
    "Active",
    "Completed",
    "Delayed",
    "On Hold"
]


PROJECT_PRIORITY = [
    "Low",
    "Medium",
    "High",
    "Critical"
]

def generate_projects():

    projects = []


    for project_id in range(1, 401):


        start_date = fake.date_between(
            start_date="-3y",
            end_date="-6m"
        )


        end_date = start_date + timedelta(
            days=random.randint(180, 900)
        )


        project = {


            "project_id": project_id,


            "project_name":
                fake.catch_phrase()
                + " Project",


            "project_code":
                f"PRJ-2026-{project_id:05d}",


            "contract_id":
                random.randint(1,300),


            "client_id":
                random.randint(1,250),


            "department_id":
                random.randint(1,12),


            "project_manager_id":
                random.randint(1,1000),


            "status":
                random.choice(PROJECT_STATUS),


            "start_date":
                start_date,


            "end_date":
                end_date,


            "budget":
                random.randint(
                    5_000_000,
                    500_000_000
                ),


            "priority":
                random.choice(PROJECT_PRIORITY),


            "description":
                random.choice(PROJECT_TYPES)
                + " initiative focused on enterprise transformation.",


            "created_at":
                datetime.now(),


            "updated_at":
                datetime.now()

        }


        projects.append(project)


    return projects

def validate_projects(projects):


    assert len(projects) == 400


    project_ids = [
        p["project_id"]
        for p in projects
    ]


    assert len(project_ids) == len(set(project_ids))


    print("Project validation passed.")

def export_projects(projects):


    df = pd.DataFrame(projects)


    df.to_csv(
        CSV_DIR / "projects.csv",
        index=False
    )


    df.to_json(
        JSON_DIR / "projects.json",
        orient="records",
        indent=4,
        date_format="iso"
    )


    print(
        f"Generated {len(df)} projects."
    )

if __name__ == "__main__":


    print("=" * 60)
    print("Generating Enterprise Projects")
    print("=" * 60)


    projects = generate_projects()


    validate_projects(projects)


    export_projects(projects)


    print(
        "Project generation completed."
    )