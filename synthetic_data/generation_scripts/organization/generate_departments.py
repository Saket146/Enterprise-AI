import json
import pandas as pd
from pathlib import Path

# ==========================================================
# Enterprise AI Operating System
# Department Generator
# ==========================================================

from organization_blueprint import DEPARTMENT_STRUCTURE

DEPARTMENT_CODES = {
    "Engineering": "ENG",
    "Artificial Intelligence": "AI",
    "Quality Assurance": "QA",
    "Human Resources": "HR",
    "Finance": "FIN",
    "Sales": "SALES",
    "Marketing": "MKT",
    "Operations": "OPS",
    "Legal": "LEGAL",
    "IT Support": "IT",
    "Data Science": "DS",
    "Customer Success": "CS",
    "Executive Office": "EXEC"
}

DEPARTMENT_BUDGETS = {
    "Engineering": 50000000,
    "Artificial Intelligence": 65000000,
    "Quality Assurance": 22000000,
    "Human Resources": 15000000,
    "Finance": 28000000,
    "Sales": 40000000,
    "Marketing": 18000000,
    "Operations": 25000000,
    "Legal": 12000000,
    "IT Support": 20000000,
    "Data Science": 32000000,
    "Customer Success": 17000000,
    "Executive Office": 100000000
}

DEPARTMENT_LOCATIONS = {
    "Engineering": "Hyderabad",
    "Artificial Intelligence": "Bengaluru",
    "Quality Assurance": "Hyderabad",
    "Human Resources": "Hyderabad",
    "Finance": "Mumbai",
    "Sales": "Mumbai",
    "Marketing": "Mumbai",
    "Operations": "Pune",
    "Legal": "Mumbai",
    "IT Support": "Chennai",
    "Data Science": "Bengaluru",
    "Customer Success": "Pune",
    "Executive Office": "Hyderabad"
}

departments = []

for department_name, department in DEPARTMENT_STRUCTURE.items():

    departments.append({
        "department_id": department["department_id"],
        "department_code": DEPARTMENT_CODES[department_name],
        "department_name": department_name,
        "location": DEPARTMENT_LOCATIONS[department_name],
        "budget": DEPARTMENT_BUDGETS[department_name],
        "headcount": sum(department["roles"].values())
    })

# ==========================================================
# Output Directories
# ==========================================================

base_path = Path(__file__).resolve().parents[2]

csv_path = base_path / "csv" / "organization"
json_path = base_path / "json" / "organization"

csv_path.mkdir(parents=True, exist_ok=True)
json_path.mkdir(parents=True, exist_ok=True)

# ==========================================================
# Save CSV
# ==========================================================

df = pd.DataFrame(departments)
df.to_csv(csv_path / "departments.csv", index=False)

# ==========================================================
# Save JSON
# ==========================================================

with open(json_path / "departments.json", "w", encoding="utf-8") as f:
    json.dump(departments, f, indent=4)

print("✅ Departments generated successfully!")
print(f"CSV  : {csv_path / 'departments.csv'}")
print(f"JSON : {json_path / 'departments.json'}")