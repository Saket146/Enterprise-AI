"""
Enterprise AI Operating System

Client Generator

Generates enterprise clients for
ApexNova Technologies.

Exports:

CSV
JSON
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

CSV_DIR = BASE_DIR / "csv" / "business"
JSON_DIR = BASE_DIR / "json" / "business"

CSV_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)

CLIENT_INDUSTRIES = [
    "Banking",
    "Healthcare",
    "Retail",
    "Telecommunications",
    "Manufacturing",
    "Education",
    "Insurance",
    "Energy",
    "Logistics",
    "E-Commerce",
    "Automotive",
    "Pharmaceuticals"
]

CLIENT_STATUS = [
    "Active",
    "Onboarding",
    "Inactive"
]

CLIENT_SIZE = [
    "Startup",
    "SME",
    "Enterprise"
]

COMPANY_PREFIX = [
    "Global",
    "NextGen",
    "Prime",
    "Nova",
    "Future",
    "Vertex",
    "Blue",
    "Quantum",
    "Smart",
    "Elite",
    "United",
    "Vision"
]

COMPANY_SUFFIX = [
    "Technologies",
    "Solutions",
    "Systems",
    "Industries",
    "Healthcare",
    "Logistics",
    "Retail",
    "Finance",
    "Consulting",
    "Networks",
    "Digital",
    "Corporation"
]

def generate_clients():

    clients = []

    for client_id in range(1, 251):

        company_name = (
            f"{random.choice(COMPANY_PREFIX)} "
            f"{random.choice(COMPANY_SUFFIX)}"
        )

        industry = random.choice(CLIENT_INDUSTRIES)

        country = random.choice([
            "India",
            "USA",
            "UK",
            "Germany",
            "Singapore",
            "Australia"
        ])

        city = fake.city()

        client = {

            "client_id": client_id,

            "company_name": company_name,

            "industry": industry,

            "client_size": random.choice(CLIENT_SIZE),

            "annual_revenue": random.randint(
                50_000_000,
                5_000_000_000
            ),

            "contact_person": fake.name(),

            "email": fake.company_email(),

            "phone": fake.phone_number(),

            "country": country,

            "city": fake.city(),

            "contract_value": random.randint(
                2_000_000,
                200_000_000
            ),

            "account_manager": random.randint(1, 1000),

            "status": random.choice(CLIENT_STATUS),

            "created_at": datetime.now(),

            "updated_at": datetime.now()

        }

        clients.append(client)

    return clients

def export_clients(clients):

    df = pd.DataFrame(clients)

    df.to_csv(
        CSV_DIR / "clients.csv",
        index=False
    )

    df.to_json(
        JSON_DIR / "clients.json",
        orient="records",
        indent=4,
        date_format="iso"
    )

    print(f"Generated {len(df)} clients.")

def validate_clients(clients):

    assert len(clients) == 250, \
        "Client count mismatch."

    client_ids = [c["client_id"] for c in clients]

    assert len(client_ids) == len(set(client_ids)), \
        "Duplicate client IDs found."

    company_names = [c["company_name"] for c in clients]

    print(f"Unique company names : {len(set(company_names))}")

    print("Client validation passed.")

if __name__ == "__main__":

    print("=" * 60)
    print("Generating Enterprise Clients")
    print("=" * 60)

    clients = generate_clients()

    validate_clients(clients)

    export_clients(clients)

    print("Client generation completed.")