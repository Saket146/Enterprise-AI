"""
Enterprise AI Operating System

Contract Generator

Generates enterprise client contracts.

Exports:
- CSV
- JSON
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

CONTRACT_TYPES = [
    "Software Development",
    "AI Consulting",
    "Cloud Migration",
    "Managed Services",
    "Annual Support",
    "Data Analytics"
]

PAYMENT_TERMS = [
    "Net 30",
    "Net 60",
    "Quarterly",
    "Annual"
]

STATUS = [
    "Active",
    "Expired",
    "Pending Renewal",
    "Terminated"
]

CURRENCIES = [
    "INR",
    "USD"
]

def generate_contracts():

    contracts = []

    for contract_id in range(1, 301):

        start = fake.date_between(
            start_date="-5y",
            end_date="-1y"
        )

        end = start + timedelta(
            days=random.randint(365, 1095)
        )

        contract = {

            "contract_id": contract_id,

            "client_id": random.randint(1, 250),

            "contract_number": f"CN-{2026}-{contract_id:05d}",

            "contract_title": (
                random.choice(CONTRACT_TYPES)
                + " Agreement"
            ),

            "contract_type": random.choice(CONTRACT_TYPES),

            "start_date": start,

            "end_date": end,

            "renewal_date": end,

            "contract_value": random.randint(
                2_000_000,
                200_000_000
            ),

            "payment_terms": random.choice(
                PAYMENT_TERMS
            ),

            "currency": random.choice(
                CURRENCIES
            ),

            "status": random.choice(
                STATUS
            ),

            "created_at": datetime.now(),

            "updated_at": datetime.now()

        }

        contracts.append(contract)

    return contracts

def validate_contracts(contracts):

    assert len(contracts) == 300

    ids = [c["contract_id"] for c in contracts]

    assert len(ids) == len(set(ids))

    print("Contract validation passed.")

def export_contracts(contracts):

    df = pd.DataFrame(contracts)

    df.to_csv(
        CSV_DIR / "contracts.csv",
        index=False
    )

    df.to_json(
        JSON_DIR / "contracts.json",
        orient="records",
        indent=4,
        date_format="iso"
    )

    print(f"Generated {len(df)} contracts.")

if __name__ == "__main__":

    print("=" * 60)
    print("Generating Enterprise Contracts")
    print("=" * 60)

    contracts = generate_contracts()

    validate_contracts(contracts)

    export_contracts(contracts)

    print("Contract generation completed.")