import json
import pandas as pd
from pathlib import Path

# ==========================================================
# Enterprise AI Operating System
# Role Generator
# ==========================================================

roles = [
    {"role_id": 1, "role_name": "CEO", "level": "Executive"},
    {"role_id": 2, "role_name": "CTO", "level": "Executive"},
    {"role_id": 3, "role_name": "CFO", "level": "Executive"},
    {"role_id": 4, "role_name": "HR Director", "level": "Director"},
    {"role_id": 5, "role_name": "Engineering Manager", "level": "Manager"},
    {"role_id": 6, "role_name": "Project Manager", "level": "Manager"},
    {"role_id": 7, "role_name": "Backend Engineer", "level": "Senior"},
    {"role_id": 8, "role_name": "Frontend Engineer", "level": "Senior"},
    {"role_id": 9, "role_name": "AI Engineer", "level": "Senior"},
    {"role_id": 10, "role_name": "QA Engineer", "level": "Mid"},
    {"role_id": 11, "role_name": "Data Scientist", "level": "Senior"},
    {"role_id": 12, "role_name": "Finance Analyst", "level": "Mid"},
    {"role_id": 13, "role_name": "Sales Executive", "level": "Mid"},
    {"role_id": 14, "role_name": "HR Executive", "level": "Mid"},
    {"role_id": 15, "role_name": "Intern", "level": "Entry"}
]

# ==========================================================
# Output Directories
# ==========================================================

base_path = Path(__file__).resolve().parents[2]

csv_path = base_path / "csv" / "organization"
json_path = base_path / "json" / "organization"

csv_path.mkdir(parents=True, exist_ok=True)
json_path.mkdir(parents=True, exist_ok=True)

# Save CSV
df = pd.DataFrame(roles)
df.to_csv(csv_path / "roles.csv", index=False)

# Save JSON
with open(json_path / "roles.json", "w", encoding="utf-8") as f:
    json.dump(roles, f, indent=4)

print("✅ Roles generated successfully!")
print(f"CSV  : {csv_path / 'roles.csv'}")
print(f"JSON : {json_path / 'roles.json'}")