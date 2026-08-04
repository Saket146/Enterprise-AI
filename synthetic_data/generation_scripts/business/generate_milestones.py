"""
Enterprise AI Operating System

Milestone Generator
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

MILESTONE_NAMES = [

    "Requirement Analysis",

    "System Design",

    "Architecture Approval",

    "Development Phase",

    "Integration Testing",

    "User Acceptance Testing",

    "Production Deployment",

    "Project Review"

]


STATUS = [

    "Completed",

    "In Progress",

    "Pending",

    "Delayed"

]

def generate_milestones():

    milestones = []

    milestone_id = 1


    for project_id in range(1,401):


        milestone_count = random.randint(3,6)


        project_start = fake.date_between(
            start_date="-3y",
            end_date="-6m"
        )


        for _ in range(milestone_count):


            due_date = project_start + timedelta(
                days=random.randint(30,900)
            )


            status = random.choice(
                STATUS
            )


            completion_date = None


            if status == "Completed":

                completion_date = (
                    due_date -
                    timedelta(
                        days=random.randint(1,30)
                    )
                )


            milestone = {


                "milestone_id":
                    milestone_id,


                "project_id":
                    project_id,


                "milestone_name":
                    random.choice(
                        MILESTONE_NAMES
                    ),


                "due_date":
                    due_date,


                "completion_date":
                    completion_date,


                "status":
                    status,


                "created_at":
                    datetime.now(),


                "updated_at":
                    datetime.now()

            }


            milestones.append(
                milestone
            )


            milestone_id += 1


    return milestones

def validate_milestones(milestones):

    assert len(milestones) > 1000


    ids = [
        m["milestone_id"]
        for m in milestones
    ]


    assert len(ids) == len(set(ids))


    print(
        "Milestone validation passed."
    )

def export_milestones(milestones):

    df = pd.DataFrame(milestones)


    df.to_csv(
        CSV_DIR / "milestones.csv",
        index=False
    )


    df.to_json(
        JSON_DIR / "milestones.json",
        orient="records",
        indent=4,
        date_format="iso"
    )


    print(
        f"Generated {len(df)} milestones."
    )

if __name__ == "__main__":


    print("="*60)
    print("Generating Enterprise Milestones")
    print("="*60)


    milestones = generate_milestones()


    validate_milestones(
        milestones
    )


    export_milestones(
        milestones
    )


    print(
        "Milestone generation completed."
    )
    