"""
Enterprise AI Operating System

Meeting Generator

Generates enterprise meeting records
for AI knowledge simulation.
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

PROJECT_FILE = (
    BASE_DIR /
    "csv" /
    "business" /
    "projects.csv"
)


EMPLOYEE_FILE = (
    BASE_DIR /
    "csv" /
    "organization" /
    "employees.csv"
)


DEPARTMENT_FILE = (
    BASE_DIR /
    "csv" /
    "organization" /
    "departments.csv"
)


def load_data():

    projects = pd.read_csv(
        PROJECT_FILE
    )


    employees = pd.read_csv(
        EMPLOYEE_FILE
    )


    departments = pd.read_csv(
        DEPARTMENT_FILE
    )


    return projects, employees, departments

MEETING_TYPES = [

    "Sprint Planning",

    "Client Review",

    "Technical Discussion",

    "Project Status Review",

    "Management Review",

    "Risk Assessment",

    "Architecture Review",

    "Deployment Planning"

]


MEETING_TITLES = [

    "{} Weekly Sync",

    "{} Progress Review",

    "{} Planning Meeting",

    "{} Technical Discussion",

    "{} Stakeholder Review"

]

def generate_meetings(
        projects,
        employees,
        departments
):


    meetings = []

    meeting_id = 1


    for _ in range(1500):


        project = projects.sample(
            1
        ).iloc[0]


        organizer = employees.sample(
            1
        ).iloc[0]


        department = departments[
            departments["department_id"]
            ==
            project["department_id"]
        ].iloc[0]


        project_name = project[
            "project_name"
        ]


        title = random.choice(
            MEETING_TITLES
        ).format(
            project_name
        )


        agenda = f"""

Agenda:

{fake.paragraph(
    nb_sentences=4
)}

Discussion topics include
project progress,
technical updates,
resource planning,
and upcoming milestones.

"""


        minutes = f"""

Meeting Minutes:

{fake.paragraphs(
    nb=random.randint(3,5)
)}

The team discussed current
progress and identified
next action items.

"""


        decision = f"""

Decision Summary:

{fake.paragraph(
    nb_sentences=3
)}

"""


        meeting = {


            "meeting_id":
                meeting_id,


            "project_id":
                project["project_id"],


            "department_id":
                department["department_id"],


            "organizer_id":
                organizer["employee_id"],


            "meeting_title":
                title,


            "meeting_type":
                random.choice(
                    MEETING_TYPES
                ),


            "meeting_date":
                fake.date_time_between(
                    start_date="-2y",
                    end_date="now"
                ),


            "duration_minutes":
                random.choice(
                    [30,45,60,90,120]
                ),


            "meeting_room":
                random.choice(
                    [
                        "Conference Room A",
                        "Conference Room B",
                        "Virtual Meeting",
                        "Board Room"
                    ]
                ),


            "agenda":
                agenda,


            "minutes":
                minutes,


            "decision_summary":
                decision,


            "created_at":
                datetime.now()

        }


        meetings.append(
            meeting
        )


        meeting_id += 1


    return meetings

def validate_meetings(meetings):


    assert len(meetings) == 1500


    ids = [
        m["meeting_id"]
        for m in meetings
    ]


    assert len(ids) == len(set(ids))


    print(
        "Meeting validation passed."
    )

def export_meetings(meetings):


    df = pd.DataFrame(
        meetings
    )


    df.to_csv(
        CSV_DIR / "meetings.csv",
        index=False
    )


    df.to_json(
        JSON_DIR / "meetings.json",
        orient="records",
        indent=4,
        date_format="iso"
    )


    print(
        f"Generated {len(df)} meetings."
    )

if __name__ == "__main__":


    print("="*60)
    print("Generating Enterprise Meetings")
    print("="*60)


    projects, employees, departments = load_data()


    meetings = generate_meetings(
        projects,
        employees,
        departments
    )


    validate_meetings(
        meetings
    )


    export_meetings(
        meetings
    )


    print(
        "Meeting generation completed."
    )