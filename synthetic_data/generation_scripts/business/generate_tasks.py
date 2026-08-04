"""
Enterprise AI Operating System

Task Generator

Generates project tasks assigned
to suitable employees based on roles.
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

EMPLOYEE_FILE = (
    BASE_DIR
    / "csv"
    / "organization"
    / "employees.csv"
)


def load_employees():

    df = pd.read_csv(
        EMPLOYEE_FILE
    )

    return df

def create_employee_pools(df):

    pools = {

        "Backend Engineer": [],

        "Frontend Engineer": [],

        "AI Engineer": [],

        "Data Scientist": [],

        "QA Engineer": [],

        "Project Manager": [],

        "Engineering Manager": [],

        "Intern": []

    }


    for _, row in df.iterrows():

        role = row["role_id"]


        if role == 7:
            pools["Backend Engineer"].append(
                row["employee_id"]
            )


        elif role == 8:
            pools["Frontend Engineer"].append(
                row["employee_id"]
            )


        elif role == 9:
            pools["AI Engineer"].append(
                row["employee_id"]
            )


        elif role == 11:
            pools["Data Scientist"].append(
                row["employee_id"]
            )


        elif role == 10:
            pools["QA Engineer"].append(
                row["employee_id"]
            )


        elif role == 6:
            pools["Project Manager"].append(
                row["employee_id"]
            )


        elif role == 5:
            pools["Engineering Manager"].append(
                row["employee_id"]
            )


        elif role == 15:
            pools["Intern"].append(
                row["employee_id"]
            )


    return pools

TASK_LIBRARY = [

    (
        "Backend Engineer",
        [
            "Develop API endpoints",
            "Optimize database queries",
            "Implement backend services",
            "Create authentication module"
        ]
    ),


    (
        "Frontend Engineer",
        [
            "Build UI components",
            "Improve application interface",
            "Implement frontend validation"
        ]
    ),


    (
        "AI Engineer",
        [
            "Develop machine learning pipeline",
            "Build AI model integration",
            "Optimize inference workflow"
        ]
    ),


    (
        "Data Scientist",
        [
            "Perform data analysis",
            "Create predictive model",
            "Prepare analytical reports"
        ]
    ),


    (
        "QA Engineer",
        [
            "Execute test cases",
            "Perform regression testing",
            "Validate application quality"
        ]
    ),


    (
        "Intern",
        [
            "Prepare documentation",
            "Assist development team",
            "Research technical solutions"
        ]
    )

]

def generate_tasks(employee_pools):

    tasks = []

    task_id = 1


    for project_id in range(1,401):


        number_of_tasks = random.randint(5,10)


        for _ in range(number_of_tasks):


            role, titles = random.choice(
                TASK_LIBRARY
            )


            employees = employee_pools[role]


            if not employees:
                continue


            start_date = fake.date_between(
                start_date="-2y",
                end_date="today"
            )


            due_date = start_date + timedelta(
                days=random.randint(15,180)
            )


            status = random.choice(
                [
                    "Pending",
                    "In Progress",
                    "Completed",
                    "Blocked"
                ]
            )


            completed_date = None


            if status == "Completed":

                completed_date = (
                    due_date -
                    timedelta(
                        days=random.randint(1,20)
                    )
                )


            task = {


                "task_id": task_id,


                "project_id": project_id,


                "assigned_to":
                    random.choice(employees),


                "title":
                    random.choice(titles),


                "description":
                    fake.sentence(),


                "status":
                    status,


                "priority":
                    random.choice(
                        [
                            "Low",
                            "Medium",
                            "High",
                            "Critical"
                        ]
                    ),


                "start_date":
                    start_date,


                "due_date":
                    due_date,


                "completed_date":
                    completed_date,


                "estimated_hours":
                    random.randint(
                        8,
                        120
                    ),


                "actual_hours":
                    random.randint(
                        5,
                        150
                    ),


                "created_at":
                    datetime.now(),


                "updated_at":
                    datetime.now()

            }


            tasks.append(task)


            task_id += 1


    return tasks

def validate_tasks(tasks):

    assert len(tasks) > 2000


    ids = [
        t["task_id"]
        for t in tasks
    ]


    assert len(ids) == len(set(ids))


    print(
        "Task validation passed."
    )

def export_tasks(tasks):

    df = pd.DataFrame(tasks)


    df.to_csv(
        CSV_DIR / "tasks.csv",
        index=False
    )


    df.to_json(
        JSON_DIR / "tasks.json",
        orient="records",
        indent=4,
        date_format="iso"
    )


    print(
        f"Generated {len(df)} tasks."
    )

if __name__ == "__main__":


    print("="*60)
    print("Generating Enterprise Tasks")
    print("="*60)


    employees = load_employees()


    employee_pools = create_employee_pools(
        employees
    )


    tasks = generate_tasks(
        employee_pools
    )


    validate_tasks(
        tasks
    )


    export_tasks(
        tasks
    )


    print(
        "Task generation completed."
    )
