"""
Enterprise AI Operating System

Chat Session Generator

Generates AI assistant interaction history.
"""


import random

from datetime import datetime
from pathlib import Path

import pandas as pd
from faker import Faker


fake = Faker("en_IN")

random.seed(42)
Faker.seed(42)


BASE_DIR = Path(__file__).resolve().parents[2]


CSV_DIR = BASE_DIR / "csv" / "knowledge"
JSON_DIR = BASE_DIR / "json" / "knowledge"


CSV_DIR.mkdir(
    parents=True,
    exist_ok=True
)

JSON_DIR.mkdir(
    parents=True,
    exist_ok=True
)

EMPLOYEE_FILE = (
    BASE_DIR /
    "csv" /
    "organization" /
    "employees.csv"
)


PROJECT_FILE = (
    BASE_DIR /
    "csv" /
    "business" /
    "projects.csv"
)


def load_data():

    employees = pd.read_csv(
        EMPLOYEE_FILE
    )


    projects = pd.read_csv(
        PROJECT_FILE
    )


    return employees, projects

SESSION_TYPES = [

    "AI Assistant Query",

    "Project Analysis",

    "Report Generation",

    "Technical Support",

    "HR Assistance",

    "Data Analysis",

    "Document Search"

]


SESSION_TITLES = [

    "Project status analysis",

    "Generate project report",

    "Analyze pending tasks",

    "Find enterprise documents",

    "Employee information query",

    "Performance analysis",

    "Business insights request"

]


STATUSES = [

    "Completed",

    "Active",

    "Archived"

]

def generate_chat_sessions(
        employees,
        projects
):


    sessions = []

    session_id = 1


    for _ in range(3000):


        employee = employees.sample(
            1
        ).iloc[0]


        project = projects.sample(
            1
        ).iloc[0]


        started = fake.date_time_between(
            start_date="-2y",
            end_date="now"
        )


        ended = started


        session = {


            "session_id":
                session_id,


            "employee_id":
                employee["employee_id"],


            "project_id":
                project["project_id"],


            "session_title":
                random.choice(
                    SESSION_TITLES
                ),


            "session_type":
                random.choice(
                    SESSION_TYPES
                ),


            "started_at":
                started,


            "ended_at":
                ended,


            "status":
                random.choice(
                    STATUSES
                ),


            "message_count":
                random.randint(
                    3,
                    25
                ),


            "conversation_summary":

                f"""
Employee requested AI assistance
regarding {project['project_name']}.

The assistant provided analysis,
recommendations and relevant
enterprise information.

{fake.paragraph()}
""",


            "created_at":
                datetime.now()

        }


        sessions.append(
            session
        )


        session_id += 1


    return sessions

def validate_sessions(sessions):


    assert len(sessions) == 3000


    ids = [
        s["session_id"]
        for s in sessions
    ]


    assert len(ids) == len(set(ids))


    print(
        "Chat session validation passed."
    )

def export_sessions(sessions):


    df = pd.DataFrame(
        sessions
    )


    df.to_csv(
        CSV_DIR / "chat_sessions.csv",
        index=False
    )


    df.to_json(
        JSON_DIR / "chat_sessions.json",
        orient="records",
        indent=4,
        date_format="iso"
    )


    print(
        f"Generated {len(df)} chat sessions."
    )

if __name__ == "__main__":


    print("="*60)
    print("Generating Enterprise Chat Sessions")
    print("="*60)


    employees, projects = load_data()


    sessions = generate_chat_sessions(
        employees,
        projects
    )


    validate_sessions(
        sessions
    )


    export_sessions(
        sessions
    )


    print(
        "Chat session generation completed."
    )

