# scripts/data_generator/org_generator.py
import uuid
import random
from datetime import date, timedelta
from .config import FIRST_NAMES, LAST_NAMES, DEPARTMENTS_DATA, ROLES_DATA, PERMISSIONS_DATA

def random_date(start, end):
    return start + timedelta(days=random.randint(0, int((end - start).days)))

def generate_roles():
    roles = []
    for name, desc, lvl in ROLES_DATA:
        roles.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "description": desc,
            "level": lvl
        })
    return roles

def generate_permissions():
    permissions = []
    for name, desc, cat in PERMISSIONS_DATA:
        permissions.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "description": desc,
            "category": cat
        })
    return permissions

def generate_role_permissions(roles, permissions):
    role_permissions = []
    for r in roles:
        for p in permissions:
            if r["level"] >= 9:
                role_permissions.append({"role_id": r["id"], "permission_id": p["id"]})
            elif r["level"] >= 7:
                if p["category"] in ["HR", "Finance", "Operations", "Legal", "Security"]:
                    role_permissions.append({"role_id": r["id"], "permission_id": p["id"]})
            elif r["level"] >= 4:
                if p["name"] in ["read:documents", "write:documents", "execute:workflows"]:
                    role_permissions.append({"role_id": r["id"], "permission_id": p["id"]})
            else:
                if p["name"] in ["read:documents"]:
                    role_permissions.append({"role_id": r["id"], "permission_id": p["id"]})
    return role_permissions

def generate_departments():
    departments = []
    for name, code in DEPARTMENTS_DATA:
        departments.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "code": code,
            "manager_id": None
        })
    return departments

def generate_employees(roles, departments):
    employees = []
    employee_ids_by_dept = {d["id"]: [] for d in departments}
    
    # Identify roles by level
    ceo_role = [r for r in roles if r["level"] == 10][0]
    vp_role = [r for r in roles if r["level"] == 9][0]
    dir_role = [r for r in roles if r["level"] == 8][0]
    mgr_role = [r for r in roles if r["level"] == 7][0]
    lead_role = [r for r in roles if r["level"] == 5][0]
    ic_roles = [r for r in roles if r["level"] in [2, 3, 4]]
    
    # 1. Create CEO
    ceo_id = str(uuid.uuid4())
    ceo_dept = [d for d in departments if d["code"] == "EGY"][0]
    ceo = {
        "id": ceo_id,
        "first_name": "Arthur",
        "last_name": "Pendleton",
        "email": "arthur.pendleton@syntheticenterprise.com",
        "phone": "+1-555-010-0001",
        "hire_date": "2022-01-01",
        "salary": 450000.00,
        "department_id": ceo_dept["id"],
        "manager_id": None,
        "role_id": ceo_role["id"],
        "status": "ACTIVE"
    }
    employees.append(ceo)
    employee_ids_by_dept[ceo_dept["id"]].append(ceo_id)
    
    # 2. Create 5 VPs reporting to CEO
    vp_ids = []
    for i in range(5):
        vp_id = str(uuid.uuid4())
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        dept_id = departments[i % len(departments)]["id"]
        vp = {
            "id": vp_id,
            "first_name": first,
            "last_name": last,
            "email": f"{first.lower()}.{last.lower()}@syntheticenterprise.com",
            "phone": f"+1-555-010-000{i+2}",
            "hire_date": random_date(date(2022, 1, 15), date(2023, 6, 30)).strftime("%Y-%m-%d"),
            "salary": round(random.uniform(220000.00, 280000.00), 2),
            "department_id": dept_id,
            "manager_id": ceo_id,
            "role_id": vp_role["id"],
            "status": "ACTIVE"
        }
        employees.append(vp)
        vp_ids.append(vp_id)
        employee_ids_by_dept[dept_id].append(vp_id)
        
    # 3. Create 24 Directors reporting to VPs
    dir_ids = []
    for i in range(24):
        dir_id = str(uuid.uuid4())
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        dept_id = departments[(i + 5) % len(departments)]["id"]
        director = {
            "id": dir_id,
            "first_name": first,
            "last_name": last,
            "email": f"{first.lower()}.{last.lower()}@syntheticenterprise.com",
            "phone": f"+1-555-010-00{i+10}",
            "hire_date": random_date(date(2022, 3, 1), date(2023, 12, 31)).strftime("%Y-%m-%d"),
            "salary": round(random.uniform(160000.00, 200000.00), 2),
            "department_id": dept_id,
            "manager_id": random.choice(vp_ids),
            "role_id": dir_role["id"],
            "status": "ACTIVE"
        }
        employees.append(director)
        dir_ids.append(dir_id)
        employee_ids_by_dept[dept_id].append(dir_id)
        
    # 4. Create Managers (30 Managers, one for each department)
    mgr_ids = []
    for i, dept in enumerate(departments):
        mgr_id = str(uuid.uuid4())
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        manager = {
            "id": mgr_id,
            "first_name": first,
            "last_name": last,
            "email": f"{first.lower()}.{last.lower()}@syntheticenterprise.com",
            "phone": f"+1-555-020-00{i:02d}",
            "hire_date": random_date(date(2022, 6, 1), date(2024, 6, 30)).strftime("%Y-%m-%d"),
            "salary": round(random.uniform(120000.00, 150000.00), 2),
            "department_id": dept["id"],
            "manager_id": random.choice(dir_ids),
            "role_id": mgr_role["id"],
            "status": "ACTIVE"
        }
        employees.append(manager)
        mgr_ids.append(mgr_id)
        employee_ids_by_dept[dept["id"]].append(mgr_id)
        # Link department manager
        dept["manager_id"] = mgr_id
        
    # 5. Create 100 Team Leads reporting to Managers
    lead_ids = []
    for i in range(100):
        lead_id = str(uuid.uuid4())
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        dept = random.choice(departments)
        lead = {
            "id": lead_id,
            "first_name": first,
            "last_name": last,
            "email": f"{first.lower()}.{last.lower()}@syntheticenterprise.com",
            "phone": f"+1-555-030-00{i:02d}",
            "hire_date": random_date(date(2022, 8, 1), date(2025, 1, 1)).strftime("%Y-%m-%d"),
            "salary": round(random.uniform(95000.00, 118000.00), 2),
            "department_id": dept["id"],
            "manager_id": dept["manager_id"],
            "role_id": lead_role["id"],
            "status": "ACTIVE"
        }
        employees.append(lead)
        lead_ids.append(lead_id)
        employee_ids_by_dept[dept["id"]].append(lead_id)
        
    # 6. Create 840 Individual Contributors (ICs) reporting to Team Leads or Managers
    for i in range(840):
        emp_id = str(uuid.uuid4())
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        dept = random.choice(departments)
        
        # Select manager (Leads in department or Department Manager)
        dept_leads = [l_id for l_id in lead_ids if l_id in employee_ids_by_dept[dept["id"]]]
        mgr_in_charge = random.choice(dept_leads) if (dept_leads and random.random() > 0.3) else dept["manager_id"]
        
        role = random.choice(ic_roles)
        status = "ACTIVE" if random.random() > 0.05 else random.choice(["LEAVE", "SUSPENDED"])
        
        salary_range = {
            4: (75000.00, 92000.00),
            3: (55000.00, 72000.00),
            2: (42000.00, 52000.00)
        }.get(role["level"], (50000.00, 70000.00))
        
        employee = {
            "id": emp_id,
            "first_name": first,
            "last_name": last,
            "email": f"{first.lower()}.{last.lower()}_{i}@syntheticenterprise.com",
            "phone": f"+1-555-040-{i:04d}",
            "hire_date": random_date(date(2022, 10, 1), date(2026, 6, 1)).strftime("%Y-%m-%d"),
            "salary": round(random.uniform(*salary_range), 2),
            "department_id": dept["id"],
            "manager_id": mgr_in_charge,
            "role_id": role["id"],
            "status": status
        }
        employees.append(employee)
        employee_ids_by_dept[dept["id"]].append(emp_id)
        
    return employees
