"""
Enterprise AI Operating System

Document Generator

Generates enterprise knowledge documents
for RAG simulation.
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


CSV_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)

DOCUMENT_TYPES = [

    "Technical Design Document",

    "Project Requirement Document",

    "API Documentation",

    "Architecture Document",

    "Testing Report",

    "Deployment Guide",

    "Business Requirement Document",

    "Security Assessment",

    "Performance Report",

    "Project Status Report"

]


TITLE_TEMPLATES = [

    "{} Architecture Overview",

    "{} Development Specification",

    "{} Implementation Guide",

    "{} Testing Strategy",

    "{} Deployment Documentation",

    "{} Security Review",

    "{} Technical Report"

]

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


def load_data():

    projects = pd.read_csv(
        PROJECT_FILE
    )


    employees = pd.read_csv(
        EMPLOYEE_FILE
    )


    return projects, employees

def generate_documents(
        projects,
        employees
):

    documents = []

    document_id = 1


    for _ in range(2000):


        project = projects.sample(
            1
        ).iloc[0]


        employee = employees.sample(
            1
        ).iloc[0]


        project_name = (
            project["project_name"]
        )


        title = random.choice(
            TITLE_TEMPLATES
        ).format(
            project_name
        )


        content = f"""

Document Title:
{title}


Project:
{project_name}


Summary:

{fake.paragraphs(
    nb=random.randint(3,6)
)}


This document contains enterprise
information related to project execution,
technical decisions, implementation details
and operational guidelines.


Generated for internal enterprise usage.

"""


        document = {


            "document_id":
                document_id,


            "project_id":
                project["project_id"],


            "department_id":
                project["department_id"],


            "title":
                title,


            "document_type":
                random.choice(
                    DOCUMENT_TYPES
                ),


            "file_name":
                f"document_{document_id}.pdf",


            "content":
                content,


            "created_by":
                employee["employee_id"],


            "created_at":
                datetime.now(),


            "updated_at":
                datetime.now()

        }


        documents.append(
            document
        )


        document_id += 1


    return documents

def validate_documents(documents):

    assert len(documents) == 2000


    ids = [
        d["document_id"]
        for d in documents
    ]


    assert len(ids) == len(set(ids))


    print(
        "Document validation passed."
    )

def export_documents(documents):

    df = pd.DataFrame(
        documents
    )


    df.to_csv(
        CSV_DIR / "documents.csv",
        index=False
    )


    df.to_json(
        JSON_DIR / "documents.json",
        orient="records",
        indent=4,
        date_format="iso"
    )


    print(
        f"Generated {len(df)} documents."
    )

if __name__ == "__main__":


    print("="*60)
    print("Generating Enterprise Documents")
    print("="*60)


    projects, employees = load_data()


    documents = generate_documents(
        projects,
        employees
    )


    validate_documents(
        documents
    )


    export_documents(
        documents
    )


    print(
        "Document generation completed."
    )