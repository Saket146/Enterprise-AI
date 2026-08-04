"""
Enterprise AI Operating System

Email Generator

Generates internal enterprise communication
for AI knowledge simulation.
"""

import random

from datetime import datetime, timedelta
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


DEPARTMENT_FILE = (
    BASE_DIR /
    "csv" /
    "organization" /
    "departments.csv"
)


def load_data():

    employees = pd.read_csv(
        EMPLOYEE_FILE
    )


    projects = pd.read_csv(
        PROJECT_FILE
    )


    departments = pd.read_csv(
        DEPARTMENT_FILE
    )


    return employees, projects, departments

EMAIL_TYPES = [

    "Project Update",

    "Technical Discussion",

    "Meeting Follow-up",

    "Client Communication",

    "Approval Request",

    "Escalation",

    "Status Report",

    "Internal Announcement"

]


PRIORITIES = [

    "Low",

    "Medium",

    "High",

    "Critical"

]


SUBJECT_TEMPLATES = [

    "Project {} update",

    "Action required for {}",

    "{} progress discussion",

    "Follow-up regarding {}",

    "Important update: {}",

    "{} status report"

]

def generate_emails(
        employees,
        projects,
        departments
):


    emails = []

    email_id = 1


    for _ in range(5000):


        sender = employees.sample(
            1
        ).iloc[0]


        receiver = employees.sample(
            1
        ).iloc[0]


        project = projects.sample(
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


        subject = random.choice(
            SUBJECT_TEMPLATES
        ).format(
            project_name
        )


        body = f"""

Hello,

This email is regarding
{project_name}.

{fake.paragraphs(
    nb=random.randint(2,5)
)}


Please review and provide
necessary updates.


Regards,
Enterprise Team

"""


        email = {


            "email_id":
                email_id,


            "sender_id":
                sender["employee_id"],


            "receiver_id":
                receiver["employee_id"],


            "project_id":
                project["project_id"],


            "department_id":
                department["department_id"],


            "subject":
                subject,


            "body":
                body,


            "email_type":
                random.choice(
                    EMAIL_TYPES
                ),


            "priority":
                random.choice(
                    PRIORITIES
                ),


            "sent_at":
                fake.date_time_between(
                    start_date="-2y",
                    end_date="now"
                ),


            "created_at":
                datetime.now()

        }


        emails.append(
            email
        )


        email_id += 1


    return emails

def validate_emails(emails):


    assert len(emails) == 5000


    ids = [
        e["email_id"]
        for e in emails
    ]


    assert len(ids) == len(set(ids))


    print(
        "Email validation passed."
    )

def export_emails(emails):


    df = pd.DataFrame(
        emails
    )


    df.to_csv(
        CSV_DIR / "emails.csv",
        index=False
    )


    df.to_json(
        JSON_DIR / "emails.json",
        orient="records",
        indent=4,
        date_format="iso"
    )


    print(
        f"Generated {len(df)} emails."
    )

if __name__ == "__main__":


    print("="*60)
    print("Generating Enterprise Emails")
    print("="*60)


    employees, projects, departments = load_data()


    emails = generate_emails(
        employees,
        projects,
        departments
    )


    validate_emails(
        emails
    )


    export_emails(
        emails
    )


    print(
        "Email generation completed."
    )