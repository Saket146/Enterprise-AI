"""
Enterprise AI Operating System

Policy Generator

Generates enterprise policies
for department knowledge base.
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

DEPARTMENT_FILE = (
    BASE_DIR
    / "csv"
    / "organization"
    / "departments.csv"
)


def load_departments():

    return pd.read_csv(
        DEPARTMENT_FILE
    )

POLICY_LIBRARY = {


"Engineering": [

    "Secure Coding Policy",

    "Code Review Standards",

    "Software Development Lifecycle Policy",

    "Version Control Guidelines",

    "Engineering Quality Standards"

],


"Artificial Intelligence": [

    "AI Model Governance Policy",

    "Responsible AI Usage Policy",

    "Machine Learning Development Standards",

    "AI Data Handling Policy"

],


"Human Resources": [

    "Employee Conduct Policy",

    "Leave Management Policy",

    "Remote Work Policy",

    "Recruitment Guidelines"

],


"Finance": [

    "Expense Management Policy",

    "Budget Approval Policy",

    "Financial Audit Policy"

],


"Sales": [

    "Customer Data Handling Policy",

    "Sales Operations Policy",

    "CRM Usage Guidelines"

],


"IT Support": [

    "Access Control Policy",

    "Infrastructure Security Policy",

    "Password Management Policy"

]

}

DEFAULT_POLICIES = [

    "Department Operational Guidelines",

    "Information Security Policy",

    "Data Management Policy",

    "Business Process Guidelines"

]

def generate_policies(departments):


    policies = []

    policy_id = 1


    for _, dept in departments.iterrows():


        dept_name = dept["department_name"]


        available = POLICY_LIBRARY.get(
            dept_name,
            DEFAULT_POLICIES
        )


        count = random.randint(
            8,
            15
        )


        for _ in range(count):


            policy_name = random.choice(
                available
            )


            policy = {


                "policy_id":
                    policy_id,


                "department_id":
                    dept["department_id"],


                "policy_name":
                    policy_name,


                "version":
                    f"v{random.randint(1,3)}.{random.randint(0,9)}",


                "effective_date":
                    fake.date_between(
                        start_date="-5y",
                        end_date="today"
                    ),


                "description":
                    fake.paragraph(
                        nb_sentences=5
                    ),


                "created_at":
                    datetime.now(),


                "updated_at":
                    datetime.now()

            }


            policies.append(
                policy
            )


            policy_id += 1


    return policies

def validate_policies(policies):


    assert len(policies) >= 100


    ids = [
        p["policy_id"]
        for p in policies
    ]


    assert len(ids) == len(set(ids))


    print(
        "Policy validation passed."
    )

def export_policies(policies):


    df = pd.DataFrame(
        policies
    )


    df.to_csv(
        CSV_DIR / "policies.csv",
        index=False
    )


    df.to_json(
        JSON_DIR / "policies.json",
        orient="records",
        indent=4,
        date_format="iso"
    )


    print(
        f"Generated {len(df)} policies."
    )

if __name__ == "__main__":


    print("="*60)
    print("Generating Enterprise Policies")
    print("="*60)


    departments = load_departments()


    policies = generate_policies(
        departments
    )


    validate_policies(
        policies
    )


    export_policies(
        policies
    )


    print(
        "Policy generation completed."
    )
    