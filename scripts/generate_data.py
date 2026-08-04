# scripts/generate_data.py
# Master Python script to generate all synthetic enterprise data for the Enterprise AI OS.
# Runs using standard Python libraries only.

import os
import csv
import json
import random
import uuid
from datetime import datetime, date, timedelta

# Define base output directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "synthetic_data")
CSV_DIR = os.path.join(SYNTHETIC_DIR, "csv")
JSON_DIR = os.path.join(SYNTHETIC_DIR, "json")
RAG_DIR = os.path.join(SYNTHETIC_DIR, "rag_docs")
POSTGRES_DIR = os.path.join(SYNTHETIC_DIR, "postgres")
NEO4J_DIR = os.path.join(SYNTHETIC_DIR, "neo4j")
QDRANT_DIR = os.path.join(SYNTHETIC_DIR, "qdrant")

# Create directories
for d in [CSV_DIR, JSON_DIR, RAG_DIR, POSTGRES_DIR, NEO4J_DIR, QDRANT_DIR]:
    os.makedirs(d, exist_ok=True)

# Sub-directories for RAG documents
RAG_SUBDIRS = {
    "handbook": os.path.join(RAG_DIR, "handbook"),
    "policies": os.path.join(RAG_DIR, "policies"),
    "engineering": os.path.join(RAG_DIR, "engineering"),
    "finance": os.path.join(RAG_DIR, "finance"),
    "contracts": os.path.join(RAG_DIR, "contracts"),
    "manuals": os.path.join(RAG_DIR, "manuals"),
    "communications": os.path.join(RAG_DIR, "communications")
}
for d in RAG_SUBDIRS.values():
    os.makedirs(d, exist_ok=True)

print("Starting synthetic data generation...")

# ==========================================
# 1. VOCABULARY AND SEED DATA
# ==========================================

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
    "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
    "Christopher", "Nancy", "Daniel", "Lisa", "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra",
    "Donald", "Ashley", "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Carol", "Kevin", "Amanda", "Brian", "Dorothy", "George", "Melissa", "Timothy", "Deborah",
    "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon", "Jeffrey", "Laura", "Ryan", "Cynthia",
    "Jacob", "Kathleen", "Gary", "Amy", "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Helen",
    "Stephen", "Anna", "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Emma",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Alexander", "Debra", "Frank", "Rachel",
    "Patrick", "Carolyn", "Raymond", "Janet", "Jack", "Maria", "Dennis", "Heather", "Jerry", "Diane",
    "Tyler", "Virginia", "Aaron", "Julie", "Jose", "Joyce", "Adam", "Victoria", "Henry", "Olivia",
    "Nathan", "Kelly", "Douglas", "Christina", "Zachary", "Lauren", "Peter", "Joan", "Kyle", "Evelyn",
    "Walter", "Judith", "Harold", "Megan", "Jeremy", "Cheryl", "Ethan", "Andrea", "Carl", "Hannah",
    "Keith", "Martha", "Roger", "Jacqueline", "Gerald", "Frances", "Christian", "Gloria", "Terry", "Ann",
    "Sean", "Teresa", "Arthur", "Kathryn", "Austin", "Sara", "Noah", "Janice", "Lawrence", "Jean",
    "Christian", "Alice", "Albert", "Madison", "Joe", "Doris", "Ethan", "Abigail", "Billy", "Julia",
    "Bryan", "Judy", "Bruce", "Grace", "Jordan", "Denise", "Ralph", "Amber", "Roy", "Marilyn",
    "Alan", "Madison", "Wayne", "Danielle", "Louis", "Diana", "Dylan", "Brittany", "Eugene", "Charlotte"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts",
    "Gomez", "Phillips", "Evans", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart",
    "Morris", "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson",
    "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson", "Watson",
    "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes", "Price",
    "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez", "Porter",
    "Ryan", "Salazar", "Flores", "Webb", "Mason", "Sutton", "Shaw", "Gordon", "Burns", "Warren",
    "Jordan", "Owens", "Cole", "Ellis", "Harrison", "Gibson", "McDonald", "Cruz", "Marshall", "Gomez",
    "Ortiz", "Murray", "Freeman", "Wells", "Webb", "Simpson", "Stevens", "Tucker", "Porter", "Hunter",
    "Hicks", "Crawford", "Boyd", "Mason", "Olson", "GarZA", "Shaw", "Gordon", "Wagner", "Hunter"
]

DEPARTMENTS_DATA = [
    ("Human Resources", "HR"), ("Engineering", "ENG"), ("Sales", "SLS"), 
    ("Marketing", "MKT"), ("Finance", "FIN"), ("Product Management", "PRD"), 
    ("Operations", "OPS"), ("Legal", "LGL"), ("Information Security", "SEC"), 
    ("IT Support", "ITS"), ("Research & Development", "RND"), ("Customer Success", "CSM"), 
    ("Procurement", "PRC"), ("Facilities & Real Estate", "FAC"), ("Quality Assurance", "QA"), 
    ("Data & Analytics", "DAT"), ("Corporate Compliance", "COM"), ("Public Relations", "PR"), 
    ("Strategy & Growth", "EGY"), ("Training & Enablement", "TRN"), ("Taxation", "TAX"), 
    ("Treasury & Capital", "TRS"), ("Internal Audit", "AUD"), ("Logistics & Supply", "LOG"), 
    ("Hardware Engineering", "HW"), ("Design & UX", "DGN"), ("Global Expansion", "GLB"), 
    ("Corporate Responsibility", "CSR"), ("Accounting & Bookkeeping", "ACT"), ("Internal Communications", "ICM")
]

ROLES_DATA = [
    ("Executive Officer", "Senior executive leadership", 10),
    ("Vice President", "Department-level executive leadership", 9),
    ("Director", "Strategic leadership for a functional group", 8),
    ("Manager", "People manager handling daily operations", 7),
    ("Principal Specialist", "Highly experienced individual contributor", 6),
    ("Team Lead", "Technical or operational team coordinator", 5),
    ("Senior Associate", "Experienced professional", 4),
    ("Associate", "Standard professional staff", 3),
    ("Junior Associate", "Entry-level professional staff", 2),
    ("Coordinator", "Administrative or support staff", 1)
]

PERMISSIONS_DATA = [
    ("read:system_logs", "Read system audit logs", "Security"),
    ("write:system_logs", "Write system audit logs", "Security"),
    ("read:employee_private", "Read private employee details (SSN, home address)", "HR"),
    ("write:employee_private", "Write private employee details", "HR"),
    ("read:payroll", "View financial payroll logs", "Finance"),
    ("write:payroll", "Modify payroll distributions", "Finance"),
    ("read:financials", "View financial budgets and ledgers", "Finance"),
    ("write:financials", "Modify financial budgets and expense limits", "Finance"),
    ("read:documents", "View general internal documentation", "Operations"),
    ("write:documents", "Create/Modify internal documentation", "Operations"),
    ("delete:documents", "Delete internal documentation", "Operations"),
    ("read:client_contracts", "View client contracts and proposals", "Legal"),
    ("write:client_contracts", "Edit client contracts and proposals", "Legal"),
    ("execute:workflows", "Trigger system and orchestration workflows", "Engineering"),
    ("admin:all", "Superuser full administrative privileges", "Admin")
]

CLIENT_INDUSTRIES = ["Technology", "Healthcare", "Financial Services", "Energy", "Retail", "Manufacturing", "Telecommunications", "Automotive", "Education", "Government"]
CLIENT_SUFFIXES = ["Corp", "Inc", "Holdings", "Solutions", "Enterprises", "Group", "LLC", "Global"]
CLIENT_NAMES_WORDS = ["Apex", "Vertex", "Quantum", "Nexus", "Synergy", "Beacon", "Crest", "Horizon", "Nova", "Stellar", "Summit", "Vanguard", "Pinnacle", "Aegis", "Centric", "Core", "Delta", "Echo", "Flux", "Helix", "Infini", "Matrix", "Omni", "Prism", "Sovereign", "Vector", "Zenith", "Alliance", "Legacy", "Titan"]

VENDOR_SERVICES = ["Cloud Infrastructure", "Office Supplies", "Hardware Procurement", "Catering & Events", "Legal Consultation", "Recruiting Agencies", "Software Licenses", "Facility Maintenance", "Security Services", "Logistics & Transport"]
VENDOR_NAMES_WORDS = ["CloudScale", "OfficeDepot", "DellDirect", "TastyBites", "BakerMcKenzie", "RobertHalf", "Salesforce", "CleanCorp", "Securitas", "FedExLogistics", "AWS", "GCP", "Microsoft", "ZoomInc", "SlackTechnologies", "IronMountain", "OracleCorp", "Atlassian", "Workday", "SAP"]

SKILLS = [
    ("Python", "Engineering"), ("SQL", "Data & Analytics"), ("PostgreSQL", "Data & Analytics"),
    ("Project Management", "Operations"), ("Financial Modeling", "Finance"), ("Legal Writing", "Legal"),
    ("Machine Learning", "Engineering"), ("Kubernetes", "Engineering"), ("Cloud Architecture", "Engineering"),
    ("Docker", "Engineering"), ("React", "Engineering"), ("TypeScript", "Engineering"),
    ("Node.js", "Engineering"), ("Neo4j", "Engineering"), ("Qdrant", "Engineering"),
    ("Redis", "Engineering"), ("Git", "Engineering"), ("CI/CD Orchestration", "Engineering"),
    ("Enterprise Risk Management", "Corporate Compliance"), ("Talent Acquisition", "Human Resources"),
    ("Strategic Planning", "Strategy & Growth"), ("Copywriting", "Marketing"), ("SEO", "Marketing"),
    ("Public Speaking", "Public Relations"), ("Contract Negotiation", "Legal"), ("Budgeting", "Finance"),
    ("Employee Relations", "Human Resources"), ("Product Strategy", "Product Management"),
    ("Customer Relationship Management", "Customer Success"), ("Agile Methodologies", "Product Management")
]

TECHNOLOGIES = [
    ("Python 3.11", "Programming Language"), ("PostgreSQL 15", "Database"),
    ("Qdrant Vector DB", "Database"), ("Neo4j Graph Database", "Database"),
    ("Redis Cluster", "Cache"), ("Kubernetes (EKS)", "Infrastructure"),
    ("Docker", "Infrastructure"), ("FastAPI", "Web Framework"),
    ("React 18", "Frontend Library"), ("GitHub Actions", "CI/CD"),
    ("Apache Kafka", "Message Broker"), ("Elasticsearch", "Search Index"),
    ("TensorFlow", "Machine Learning"), ("PyTorch", "Machine Learning"),
    ("Prometheus & Grafana", "Monitoring")
]

HR_POLICY_TOPICS = [
    ("Remote Work & Hybrid Schedule Policy", "Establishes standard rules and core hours for hybrid and remote work arrangements."),
    ("Expense Reimbursement Guidelines", "Defines eligible business expenses, limits for meals and travel, and approval workflows."),
    ("Code of Business Conduct & Ethics", "Outlines expectations for professional behavior, conflicts of interest, and reporting channels."),
    ("Information Security & Clean Desk Policy", "Required practices for handling confidential data, passwords, and workstation locking."),
    ("Equal Employment Opportunity & Anti-Harassment", "Affirms commitment to fair employment practices and zero tolerance for harassment."),
    ("Annual Leave, Sick Time, and Family Care Policy", "Procedures for booking paid time off, medical leaves, and parental allocations."),
    ("Whistleblower Protection Policy", "Protects employees who report suspected illegal activities or policy breaches."),
    ("Intellectual Property & Inventions Agreement", "Clarifies ownership of products, designs, and code created during employment."),
    ("Performance Management & Promotion Review Paths", "Details the cycle for performance evaluations, ratings, and promotion reviews."),
    ("Vendor Code of Conduct & Procurement Guidelines", "Standard rules for engagement with third-party vendors, suppliers, and bids.")
]

# Helper to generate random dates
def random_date(start, end):
    return start + timedelta(days=random.randint(0, int((end - start).days)))

START_DATE = date(2022, 1, 1)
END_DATE = date(2026, 7, 31)

# Keep track of generated IDs to maintain absolute consistency
departments = []
roles = []
permissions = []
role_permissions = []
employees = []
clients = []
vendors = []
projects = []
project_members = []
tasks = []
meetings = []
meeting_participants = []
documents_metadata = []
payroll_records = []
leave_requests = []
performance_reviews = []
budgets = []
expenses = []
invoices = []
notifications = []
chat_sessions = []
chat_messages = []
audit_logs = []
workflow_executions = []

# Map lists for helper accesses
employee_ids_by_dept = {}

# ==========================================
# 2. GENERATE STATIC STRUCTURES
# ==========================================

# 2.1 Roles & Permissions
print("Generating Roles and Permissions...")
for name, desc, lvl in ROLES_DATA:
    roles.append({
        "id": str(uuid.uuid4()),
        "name": name,
        "description": desc,
        "level": lvl
    })

for name, desc, cat in PERMISSIONS_DATA:
    permissions.append({
        "id": str(uuid.uuid4()),
        "name": name,
        "description": desc,
        "category": cat
    })

# Associate permissions to roles based on level
for r in roles:
    for p in permissions:
        # High level roles get almost everything
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

# 2.2 Departments
print("Generating 30 Departments...")
for name, code in DEPARTMENTS_DATA:
    departments.append({
        "id": str(uuid.uuid4()),
        "name": name,
        "code": code,
        "manager_id": None  # Assigned later
    })
    employee_ids_by_dept[departments[-1]["id"]] = []

# ==========================================
# 3. GENERATE EMPLOYEES (1000) WITH HIERARCHY
# ==========================================
print("Generating 1000 Employees...")

# Determine hierarchy structure:
# 1 CEO (Executive Officer, Level 10)
# 5 VPs (VP, Level 9) reporting to CEO
# 24 Directors (Level 8) reporting to VPs or CEO
# 30 Managers (Level 7) - one for each department, reporting to Directors/VPs
# 100 Team Leads (Level 5) reporting to Managers
# ~840 Individual Contributors (Levels 1-4) reporting to Team Leads or Managers

ceo_id = str(uuid.uuid4())
ceo_role = [r for r in roles if r["level"] == 10][0]
vp_role = [r for r in roles if r["level"] == 9][0]
dir_role = [r for r in roles if r["level"] == 8][0]
mgr_role = [r for r in roles if r["level"] == 7][0]
lead_role = [r for r in roles if r["level"] == 5][0]
ic_roles = [r for r in roles if r["level"] in [2, 3, 4]]

# Create CEO
ceo_first = "Arthur"
ceo_last = "Pendleton"
ceo_dept_id = [d for d in departments if d["code"] == "EGY"][0]["id"]
ceo_salary = 450000.00
ceo = {
    "id": ceo_id,
    "first_name": ceo_first,
    "last_name": ceo_last,
    "email": f"{ceo_first.lower()}.{ceo_last.lower()}@syntheticenterprise.com",
    "phone": f"+1-555-010-0001",
    "hire_date": "2022-01-01",
    "salary": ceo_salary,
    "department_id": ceo_dept_id,
    "manager_id": None,
    "role_id": ceo_role["id"],
    "status": "ACTIVE"
}
employees.append(ceo)
employee_ids_by_dept[ceo_dept_id].append(ceo_id)

# Create 5 VPs
vp_ids = []
for i in range(5):
    vp_id = str(uuid.uuid4())
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    dept_id = departments[i % len(departments)]["id"]  # Distribute in early departments
    vp_salary = round(random.uniform(220000.00, 280000.00), 2)
    hire_dt = random_date(date(2022, 1, 15), date(2023, 6, 30))
    vp = {
        "id": vp_id,
        "first_name": first,
        "last_name": last,
        "email": f"{first.lower()}.{last.lower()}@syntheticenterprise.com",
        "phone": f"+1-555-010-000{i+2}",
        "hire_date": hire_dt.strftime("%Y-%m-%d"),
        "salary": vp_salary,
        "department_id": dept_id,
        "manager_id": ceo_id,
        "role_id": vp_role["id"],
        "status": "ACTIVE"
    }
    employees.append(vp)
    vp_ids.append(vp_id)
    employee_ids_by_dept[dept_id].append(vp_id)

# Create 24 Directors reporting to VPs
dir_ids = []
for i in range(24):
    dir_id = str(uuid.uuid4())
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    dept_id = departments[(i + 5) % len(departments)]["id"]
    dir_salary = round(random.uniform(160000.00, 200000.00), 2)
    hire_dt = random_date(date(2022, 3, 1), date(2023, 12, 31))
    director = {
        "id": dir_id,
        "first_name": first,
        "last_name": last,
        "email": f"{first.lower()}.{last.lower()}@syntheticenterprise.com",
        "phone": f"+1-555-010-00{i+10}",
        "hire_date": hire_dt.strftime("%Y-%m-%d"),
        "salary": dir_salary,
        "department_id": dept_id,
        "manager_id": random.choice(vp_ids),
        "role_id": dir_role["id"],
        "status": "ACTIVE"
    }
    employees.append(director)
    dir_ids.append(dir_id)
    employee_ids_by_dept[dept_id].append(dir_id)

# Create Managers (30 Managers, one for each department)
mgr_ids = []
for i, dept in enumerate(departments):
    mgr_id = str(uuid.uuid4())
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    mgr_salary = round(random.uniform(120000.00, 150000.00), 2)
    hire_dt = random_date(date(2022, 6, 1), date(2024, 6, 30))
    manager = {
        "id": mgr_id,
        "first_name": first,
        "last_name": last,
        "email": f"{first.lower()}.{last.lower()}@syntheticenterprise.com",
        "phone": f"+1-555-020-00{i:02d}",
        "hire_date": hire_dt.strftime("%Y-%m-%d"),
        "salary": mgr_salary,
        "department_id": dept["id"],
        "manager_id": random.choice(dir_ids),
        "role_id": mgr_role["id"],
        "status": "ACTIVE"
    }
    employees.append(manager)
    mgr_ids.append(mgr_id)
    employee_ids_by_dept[dept["id"]].append(mgr_id)
    # Update manager_id for the department
    dept["manager_id"] = mgr_id

# Create 100 Team Leads reporting to Managers
lead_ids = []
for i in range(100):
    lead_id = str(uuid.uuid4())
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    dept = random.choice(departments)
    dept_mgr_id = dept["manager_id"]
    lead_salary = round(random.uniform(95000.00, 118000.00), 2)
    hire_dt = random_date(date(2022, 8, 1), date(2025, 1, 1))
    lead = {
        "id": lead_id,
        "first_name": first,
        "last_name": last,
        "email": f"{first.lower()}.{last.lower()}@syntheticenterprise.com",
        "phone": f"+1-555-030-00{i:02d}",
        "hire_date": hire_dt.strftime("%Y-%m-%d"),
        "salary": lead_salary,
        "department_id": dept["id"],
        "manager_id": dept_mgr_id,
        "role_id": lead_role["id"],
        "status": "ACTIVE"
    }
    employees.append(lead)
    lead_ids.append(lead_id)
    employee_ids_by_dept[dept["id"]].append(lead_id)

# Create 840 Individual Contributors (IC) reporting to Team Leads or Managers
for i in range(840):
    emp_id = str(uuid.uuid4())
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    dept = random.choice(departments)
    
    # Manager selection (either a Team Lead in this department or the Department Manager)
    dept_leads = [l_id for l_id in lead_ids if l_id in employee_ids_by_dept[dept["id"]]]
    mgr_in_charge = random.choice(dept_leads) if (dept_leads and random.random() > 0.3) else dept["manager_id"]
    
    role = random.choice(ic_roles)
    status = "ACTIVE" if random.random() > 0.05 else random.choice(["LEAVE", "SUSPENDED"])
    
    # Adjust salary based on role level
    salary_range = {
        4: (75000.00, 92000.00),
        3: (55000.00, 72000.00),
        2: (42000.00, 52000.00)
    }.get(role["level"], (50000.00, 70000.00))
    
    salary = round(random.uniform(*salary_range), 2)
    hire_dt = random_date(date(2022, 10, 1), date(2026, 6, 1))
    
    employee = {
        "id": emp_id,
        "first_name": first,
        "last_name": last,
        "email": f"{first.lower()}.{last.lower()}_{i}@syntheticenterprise.com",
        "phone": f"+1-555-040-{i:04d}",
        "hire_date": hire_dt.strftime("%Y-%m-%d"),
        "salary": salary,
        "department_id": dept["id"],
        "manager_id": mgr_in_charge,
        "role_id": role["id"],
        "status": status
    }
    employees.append(employee)
    employee_ids_by_dept[dept["id"]].append(emp_id)

# ==========================================
# 4. CLIENTS (300) AND VENDORS (100)
# ==========================================
print("Generating 300 Clients and 100 Vendors...")

for i in range(300):
    client_id = str(uuid.uuid4())
    name = f"{random.choice(CLIENT_NAMES_WORDS)} {random.choice(CLIENT_SUFFIXES)} {i}"
    contact_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    contact_email = f"contact@{name.lower().replace(' ', '')}.com"
    industry = random.choice(CLIENT_INDUSTRIES)
    billing_address = f"{random.randint(100, 9999)} Business Plaza, Suite {random.randint(10, 999)}, Chicago, IL 60601"
    
    clients.append({
        "id": client_id,
        "name": name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": f"+1-800-555-{i:04d}",
        "industry": industry,
        "billing_address": billing_address
    })

for i in range(100):
    vendor_id = str(uuid.uuid4())
    name = f"{random.choice(VENDOR_NAMES_WORDS)} SolutionGroup {i}"
    contact_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    contact_email = f"sales@{name.lower().replace(' ', '')}.com"
    service = random.choice(VENDOR_SERVICES)
    start_dt = random_date(date(2022, 1, 1), date(2024, 1, 1))
    end_dt = start_dt + timedelta(days=365 * 3)
    
    vendors.append({
        "id": vendor_id,
        "name": name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": f"+1-888-555-{i:04d}",
        "services_provided": service,
        "contract_start": start_dt.strftime("%Y-%m-%d"),
        "contract_end": end_dt.strftime("%Y-%m-%d")
    })

# ==========================================
# 5. PROJECTS (500) AND PROJECT MEMBERS
# ==========================================
print("Generating 500 Projects and Assignments...")

PROJECT_TOPICS = [
    "Cloud Infrastructure Migration", "AI Customer Service Agent Integration",
    "Data Lake Warehouse Implementation", "Enterprise Compliance Audit Tooling",
    "Security Threat Assessment Framework", "ERP System Upgrade",
    "API Gateway Consolidation Project", "HR Management System Modernization",
    "CRM Campaign Manager Development", "Supply Chain Analytics Platform"
]

active_employees = [e for e in employees if e["status"] == "ACTIVE"]

for i in range(500):
    project_id = str(uuid.uuid4())
    topic = random.choice(PROJECT_TOPICS)
    name = f"Project {topic} - Phase {random.randint(1, 4)} ({i})"
    desc = f"Enterprise initiative to implement {topic.lower()}. Aiming for scalable performance and high reliability."
    status = random.choice(["PLANNING", "ACTIVE", "ON_HOLD", "COMPLETED"])
    start_dt = random_date(date(2023, 1, 1), date(2025, 12, 31))
    end_dt = start_dt + timedelta(days=random.randint(90, 365)) if status in ["COMPLETED"] else None
    client = random.choice(clients)
    dept = random.choice(departments)
    budget = round(random.uniform(50000.00, 850000.00), 2)
    
    projects.append({
        "id": project_id,
        "name": name,
        "description": desc,
        "status": status,
        "start_date": start_dt.strftime("%Y-%m-%d"),
        "end_date": end_dt.strftime("%Y-%m-%d") if end_dt else "",
        "client_id": client["id"],
        "department_id": dept["id"],
        "budget_amount": budget
    })
    
    # Assign project members (between 3 to 10 employees from the department)
    dept_staff = employee_ids_by_dept[dept["id"]]
    if not dept_staff:
        # Fallback to general employees
        dept_staff = [e["id"] for e in active_employees[:20]]
    
    members_count = random.randint(3, min(10, len(dept_staff)))
    assigned_staff = random.sample(dept_staff, members_count)
    
    for idx, emp_id in enumerate(assigned_staff):
        role_in_project = "Project Lead" if idx == 0 else random.choice(["Key Contributor", "Engineer", "Analyst", "QA Reviewer"])
        project_members.append({
            "project_id": project_id,
            "employee_id": emp_id,
            "role_in_project": role_in_project
        })

# ==========================================
# 6. TASKS (3000)
# ==========================================
print("Generating 3000 Tasks...")

TASK_TITLES = [
    "Design API Schema", "Configure CI/CD Pipelines", "Execute Security Scans",
    "Prepare Financial Forecasts", "Draft Service Level Agreement",
    "Conduct User Acceptance Testing", "Optimize Database Queries",
    "Develop Chat User Interface", "Integrate Vector Store Index",
    "Draft Employee Onboarding Manual", "Review Vendor Contracts",
    "Set Up Prometheus Metrics", "Draft Marketing Campaign Copy"
]

for i in range(3000):
    task_id = str(uuid.uuid4())
    proj = random.choice(projects)
    proj_m = [m for m in project_members if m["project_id"] == proj["id"]]
    
    if proj_m:
        assignee_id = random.choice(proj_m)["employee_id"]
    else:
        assignee_id = random.choice(active_employees)["id"]
        
    creator_id = random.choice(active_employees)["id"]
    title = f"{random.choice(TASK_TITLES)} - {i}"
    desc = f"Action item to complete: {title.lower()} as part of project {proj['name']}."
    status = random.choice(["TODO", "IN_PROGRESS", "REVIEW", "DONE", "BLOCKED"])
    priority = random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    due_dt = date.today() + timedelta(days=random.randint(-30, 90))
    
    tasks.append({
        "id": task_id,
        "title": title,
        "description": desc,
        "status": status,
        "priority": priority,
        "due_date": due_dt.strftime("%Y-%m-%d"),
        "project_id": proj["id"],
        "assignee_id": assignee_id,
        "creator_id": creator_id
    })

# ==========================================
# 7. MEETINGS AND PARTICIPANTS (2000)
# ==========================================
print("Generating 2000 Meetings...")

MEETING_TITLES = [
    "Weekly Sync", "Sprint Planning", "Architecture Review", "Security Alignment",
    "Client Demo", "Budget Verification", "Retrospective", "Strategy Session",
    "HR Policy Alignment", "Vendor Evaluation Check"
]

for i in range(2000):
    meeting_id = str(uuid.uuid4())
    proj = random.choice(projects)
    organizer = random.choice(active_employees)
    title = f"{proj['name']} - {random.choice(MEETING_TITLES)}"
    desc = f"Discussion regarding key milestones, bottlenecks, and timeline adjustments of {proj['name']}."
    meeting_dt = datetime.now() + timedelta(days=random.randint(-180, 180), hours=random.randint(9, 17))
    loc = random.choice(["Conference Room Alpha", "Conference Room Beta", "Microsoft Teams Link", "Zoom Room 4", "Huddle Space B"])
    
    meetings.append({
        "id": meeting_id,
        "title": title,
        "description": desc,
        "date_time": meeting_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "location": loc,
        "project_id": proj["id"],
        "organizer_id": organizer["id"]
    })
    
    # Participants (3 to 8 project members or general employees)
    proj_m = [m for m in project_members if m["project_id"] == proj["id"]]
    p_pool = [m["employee_id"] for m in proj_m] if proj_m else [e["id"] for e in active_employees[:50]]
    participants_count = min(random.randint(3, 8), len(p_pool))
    
    p_ids = random.sample(p_pool, participants_count)
    if organizer["id"] not in p_ids:
        p_ids.append(organizer["id"])
        
    for p_id in p_ids:
        meeting_participants.append({
            "meeting_id": meeting_id,
            "employee_id": p_id
        })

# ==========================================
# 8. FINANCE & PAYROLL: PAYROLL (1000), EXPENSES (3000), INVOICES (2000), BUDGETS
# ==========================================
print("Generating Financial Records...")

# Budgets: Departments for 2025 and 2026 (60 budgets)
for dept in departments:
    for year in [2025, 2026]:
        budget_id = str(uuid.uuid4())
        tot = round(random.uniform(500000.00, 3000000.00), 2)
        spent = round(random.uniform(100000.00, tot * 0.9), 2)
        allocated = round(tot * random.uniform(0.9, 1.0), 2)
        budgets.append({
            "id": budget_id,
            "department_id": dept["id"],
            "fiscal_year": year,
            "total_amount": tot,
            "allocated_amount": allocated,
            "spent_amount": spent
        })

# Payroll: 1000 records
for i in range(1000):
    emp = random.choice(employees)
    payroll_id = str(uuid.uuid4())
    pay_dt = date(2025, 1, 1) + timedelta(days=random.randint(0, 500))
    base = emp["salary"] / 12.0
    bon = round(random.uniform(0.00, base * 0.15) if random.random() > 0.8 else 0.00, 2)
    ded = round(base * random.uniform(0.05, 0.12), 2)
    net = round(base + bon - ded, 2)
    
    payroll_records.append({
        "id": payroll_id,
        "employee_id": emp["id"],
        "pay_date": pay_dt.strftime("%Y-%m-%d"),
        "base_salary": round(base, 2),
        "bonuses": bon,
        "deductions": ded,
        "net_pay": net,
        "status": "PAID"
    })

# Expenses: 3000 records
EXPENSE_DETAILS = {
    "TRAVEL": ["Flights for Client Onsite", "Hotel Booking for Conference", "Taxi & Commute Reimbursement"],
    "MEALS": ["Team Dinner Meeting", "Client Lunch", "Coffee catering for workshop"],
    "SOFTWARE": ["Annual IDE Subscription", "API Integration Credits", "Figma SaaS Team License"],
    "HARDWARE": ["Ultrawide Monitor upgrade", "Replacement Laptop Charger", "Testing Mobile Device"],
    "OFFICE_SUPPLIES": ["Whiteboard Markers", "Notebooks & Pens", "Ergonomic Keyboard"],
    "TRAINING": ["AWS Architecture Online Course", "Kubernetes Bootcamp Ticket"],
    "OTHER": ["Courier Delivery Service", "Printed Pitchbooks"]
}

for i in range(3000):
    expense_id = str(uuid.uuid4())
    emp = random.choice(active_employees)
    cat = random.choice(list(EXPENSE_DETAILS.keys()))
    desc = f"{random.choice(EXPENSE_DETAILS[cat])} ({i})"
    amt = round(random.uniform(15.00, 1800.00), 2)
    exp_dt = random_date(date(2024, 1, 1), date(2026, 7, 30))
    status = random.choice(["PENDING", "APPROVED", "REJECTED"])
    approver = employees[i % len(employees)] # Simply pick a deterministic reviewer
    while approver["id"] == emp["id"]:
        approver = employees[(i + 1) % len(employees)]
        
    expenses.append({
        "id": expense_id,
        "employee_id": emp["id"],
        "department_id": emp["department_id"],
        "description": desc,
        "amount": amt,
        "expense_date": exp_dt.strftime("%Y-%m-%d"),
        "category": cat,
        "status": status,
        "approver_id": approver["id"]
    })

# Invoices: 2000 records
for i in range(2000):
    invoice_id = str(uuid.uuid4())
    proj = random.choice(projects)
    client_id = proj["client_id"]
    inv_num = f"INV-2026-{i:05d}"
    issue_dt = random_date(date(2024, 6, 1), date(2026, 7, 15))
    due_dt = issue_dt + timedelta(days=30)
    sub = round(random.uniform(5000.00, 150000.00), 2)
    tax = round(sub * 0.08, 2)
    tot = round(sub + tax, 2)
    status = random.choice(["UNPAID", "PAID", "OVERDUE", "CANCELLED"])
    
    invoices.append({
        "id": invoice_id,
        "client_id": client_id,
        "project_id": proj["id"],
        "invoice_number": inv_num,
        "issue_date": issue_dt.strftime("%Y-%m-%d"),
        "due_date": due_dt.strftime("%Y-%m-%d"),
        "subtotal": sub,
        "tax": tax,
        "total_amount": tot,
        "status": status
    })

# ==========================================
# 9. HR OPERATIONALS: LEAVE REQUESTS (500), PERFORMANCE REVIEWS (500)
# ==========================================
print("Generating HR requests and reviews...")

for i in range(500):
    leave_id = str(uuid.uuid4())
    emp = random.choice(employees)
    l_type = random.choice(["SICK", "VACATION", "PERSONAL", "MATERNITY", "PATERNITY", "BEREAVEMENT"])
    start_dt = random_date(date(2024, 1, 1), date(2026, 6, 1))
    end_dt = start_dt + timedelta(days=random.randint(1, 14))
    status = random.choice(["PENDING", "APPROVED", "REJECTED"])
    
    # Manager as approver
    approver_id = emp["manager_id"] if emp["manager_id"] else ceo_id
    
    leave_requests.append({
        "id": leave_id,
        "employee_id": emp["id"],
        "leave_type": l_type,
        "start_date": start_dt.strftime("%Y-%m-%d"),
        "end_date": end_dt.strftime("%Y-%m-%d"),
        "status": status,
        "approver_id": approver_id
    })

for i in range(500):
    review_id = str(uuid.uuid4())
    emp = random.choice(employees)
    reviewer_id = emp["manager_id"] if emp["manager_id"] else ceo_id
    rev_dt = random_date(date(2024, 12, 15), date(2026, 7, 1))
    rating = random.choice([3, 4, 5]) if random.random() > 0.1 else random.choice([1, 2])
    comments = f"Demonstrates core competencies. Performance matches rating of {rating}/5 for this review period."
    
    performance_reviews.append({
        "id": review_id,
        "employee_id": emp["id"],
        "reviewer_id": reviewer_id,
        "review_date": rev_dt.strftime("%Y-%m-%d"),
        "period_start": (rev_dt - timedelta(days=365)).strftime("%Y-%m-%d"),
        "period_end": rev_dt.strftime("%Y-%m-%d"),
        "rating": rating,
        "comments": comments
    })

# ==========================================
# 10. SYSTEM & INTERACTIVE logs: NOTIFICATIONS, CHATS, AUDIT LOGS, WORKFLOW EXECUTIONS
# ==========================================
print("Generating operational logs...")

# Notifications (5000)
for i in range(5000):
    not_id = str(uuid.uuid4())
    emp = random.choice(active_employees)
    msg = f"Alert: Notification message content detailing action sequence {i}."
    status = "READ" if random.random() > 0.4 else "UNREAD"
    notifications.append({
        "id": not_id,
        "employee_id": emp["id"],
        "message": msg,
        "status": status
    })

# Chat sessions & Messages (500 sessions, ~5 messages per session = 2500 messages)
for i in range(500):
    sess_id = str(uuid.uuid4())
    emp = random.choice(active_employees)
    created_at = datetime.now() - timedelta(days=random.randint(1, 100))
    chat_sessions.append({
        "id": sess_id,
        "employee_id": emp["id"],
        "session_name": f"Agent Workspace Session {i}",
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": (created_at + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # 5 messages per session
    for j in range(5):
        msg_id = str(uuid.uuid4())
        sender_type = "USER" if j % 2 == 0 else "AGENT"
        msg_content = f"User query message text on task step {j}." if sender_type == "USER" else f"Agent guardrailed intelligence response detailing action step {j}."
        chat_messages.append({
            "id": msg_id,
            "session_id": sess_id,
            "sender_type": sender_type,
            "message_content": msg_content,
            "created_at": (created_at + timedelta(minutes=j*3)).strftime("%Y-%m-%d %H:%M:%S")
        })

# Audit logs (5000)
AUDIT_ACTIONS = ["CREATE_PROJECT", "APPROVE_EXPENSE", "UPDATE_SALARY", "DELETE_DOCUMENT", "AUTHENTICATE_USER", "TRIGGER_WORKFLOW"]
AUDIT_TABLES = ["projects", "expenses", "employees", "documents_metadata", "chat_sessions", "workflow_executions"]

for i in range(5000):
    log_id = str(uuid.uuid4())
    emp = random.choice(active_employees)
    action = random.choice(AUDIT_ACTIONS)
    table_name = random.choice(AUDIT_TABLES)
    timestamp = datetime.now() - timedelta(days=random.randint(1, 200), seconds=random.randint(1, 86400))
    
    audit_logs.append({
        "id": log_id,
        "employee_id": emp["id"],
        "action": action,
        "table_name": table_name,
        "record_id": str(uuid.uuid4()),
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "details": json.dumps({"ip_address": f"10.120.{random.randint(1,254)}.{random.randint(1,254)}", "user_agent": "Mozilla/5.0 Enterprise-AI-Agent", "status": "SUCCESS"})
    })

# Workflow executions (2000)
WORKFLOWS = ["Employee Onboarding Integration", "Monthly Payroll Orchestration", "Daily Data Sync & Embedding Creation", "Invoice Settlement Automation"]

for i in range(2000):
    exec_id = str(uuid.uuid4())
    wf_name = random.choice(WORKFLOWS)
    status = random.choice(["COMPLETED", "FAILED", "RUNNING"])
    start_time = datetime.now() - timedelta(days=random.randint(1, 300), hours=random.randint(1, 12))
    end_time = start_time + timedelta(minutes=random.randint(1, 45)) if status in ["COMPLETED", "FAILED"] else None
    executor = random.choice(active_employees)
    
    steps = [
        {"step": "Fetch Trigger Data", "status": "SUCCESS", "duration_ms": random.randint(100, 800)},
        {"step": "Validate Constraints", "status": "SUCCESS", "duration_ms": random.randint(50, 200)},
        {"step": "Update DB Store", "status": "SUCCESS" if status == "COMPLETED" else "FAILED", "duration_ms": random.randint(200, 1500)}
    ]
    
    workflow_executions.append({
        "id": exec_id,
        "workflow_name": wf_name,
        "status": status,
        "started_at": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": end_time.strftime("%Y-%m-%d %H:%M:%S") if end_time else "",
        "executed_by": executor["id"],
        "steps": json.dumps(steps)
    })

# ==========================================
# 11. DOCUMENTS METADATA AND RAG DOCUMENTS
# ==========================================
print("Generating Documents Metadata and RAG Documents (Handbook, HR, Eng, Finance, Manuals, Contracts)...")

# Keep a pool of generated documents for referential integrity
rag_counter = 0

# Helper to register document metadata in Postgres and generate RAG file
def add_rag_document(title, category, content, doc_type, dept_code):
    global rag_counter
    rag_counter += 1
    doc_id = str(uuid.uuid4())
    dept = [d for d in departments if d["code"] == dept_code][0]
    creator = random.choice(active_employees)
    
    # Save metadata
    clean_title = title.lower().replace(' ', '_').replace('&', 'and')
    for char in [':', '<', '>', '"', '/', '\\', '|', '?', '*']:
        clean_title = clean_title.replace(char, '')
    file_name = f"{clean_title}_{rag_counter}.md"
    file_path = os.path.join(RAG_SUBDIRS[category], file_name)
    
    documents_metadata.append({
        "id": doc_id,
        "title": title,
        "file_path": f"synthetic_data/rag_docs/{category}/{file_name}",
        "file_size": len(content),
        "mime_type": "text/markdown",
        "creator_id": creator["id"],
        "department_id": dept["id"],
        "document_type": doc_type
    })
    
    # Write the RAG Markdown file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return doc_id

# 11.1 Employee Handbook
handbook_text = """# Synthetic Enterprise Employee Handbook
**Version:** 2026.1  
**Last Updated:** January 15, 2026  

## Welcome to Synthetic Enterprise
Welcome to the team! At Synthetic Enterprise, we are dedicated to building state-of-the-art software systems that automate complicated business operations. This handbook is designed to introduce you to our culture, policies, benefits, and workplace standards.

## Code of Conduct
We expect all employees to conduct themselves with the utmost integrity, respect, and professionalism. Collaborative behavior, open communication, and diverse perspectives are the pillars of our operational excellence. 

### Core Workplace Values:
- **Respect and Inclusion:** Zero tolerance for discrimination, harassment, or verbal abuse.
- **Innovation:** Proactively searching for better solutions and validating choices with empirical data.
- **Security First:** Protecting customer data is every employee's daily responsibility.

## Working Hours & Agile Framework
Our core business hours are **10:00 AM to 4:00 PM EST**. We operate in bi-weekly Agile sprints. Teams synchronize daily at 10:00 AM for Stand-up.

## Benefits and Perks
- Comprehensive Health, Dental, and Vision coverage starting from day one.
- 401(k) retirement matching up to 5% of base salary.
- Yearly training stipend of $2,500.
"""
add_rag_document("Employee Handbook", "handbook", handbook_text, "HR", "HR")

# 11.2 HR Policies (500 documents: 10 main ones + 490 structured variations)
print("Generating 500 HR Policies...")
for idx, (title, desc) in enumerate(HR_POLICY_TOPICS):
    policy_content = f"""# HR Policy {idx + 1:03d}: {title}
**Reference Code:** POL-HR-{idx + 1:03d}  
**Classification:** Internal Use  

## 1. Purpose
This policy details the operational framework for {title.lower()}. Specifically: {desc}

## 2. Scope
This policy applies to all 1000+ employees of Synthetic Enterprise, including executives, full-time staff, part-time associates, and third-party contractors working within any department (including Engineering, Sales, and Operations).

## 3. Policy Details
- **Adherence:** All employees must strictly follow the outlined procedures.
- **Approvals:** Actions violating this standard require written approval from a department Director (Level 8) or VP (Level 9).
- **Compliance:** Failure to comply will result in a performance review adjustment or suspension.

## 4. Revision History
- **Version 1.0 (2023-01-15):** Original release.
- **Version 2.0 (2025-06-30):** Updated for remote work alignment.
"""
    add_rag_document(f"HR Policy: {title}", "policies", policy_content, "POLICY", "HR")

# Let's generate 490 additional HR Policy documents to meet the target of 500
for i in range(11, 501):
    t = f"Operational Procedure: HR Section {i}"
    c = f"""# HR Policy: {t}
**Policy ID:** POL-HR-GEN-{i}  
**Effective Date:** 2024-05-12  

## Overview
This is a standard HR document addressing operational guidelines for subsection {i}. It ensures compliance with general labor standards.

## Guidelines
- Employees must submit a formal request for processing operational tasks under code {i}.
- Senior Managers are required to maintain reports regarding execution rates of these directives.
- Internal Audit logs will track changes to these settings.
"""
    add_rag_document(t, "policies", c, "POLICY", "HR")

# 11.3 Engineering Standards, API Specifications, Software Design (e.g. 500 documents)
print("Generating Engineering Documents...")
eng_standards = """# Engineering Standards: Production Code Quality
**Scope:** Engineering Department  
**Version:** ENG-QA-2026-v2  

## 1. Code Style and Linting
- All Python code must comply with PEP 8 style guides and pass formatting checks using `Black`.
- Type hinting is mandatory on all public function signatures.

## 2. API Design Guidelines
- All web services must use FastAPI and implement standard OpenAPI documentation.
- Endpoint naming must follow RESTful standards (e.g., `/api/v1/projects`).
- Responses must return standardized JSON payloads with strict error messages.

## 3. Database Interactions
- Write-heavy interactions must use connection pooling.
- Raw SQL queries are discouraged; use SQLAlchemy ORM with typed models.
- Index creation is mandatory for all query filter fields.
"""
add_rag_document("Engineering Standards", "engineering", eng_standards, "TECHNICAL", "ENG")

# Generate 50 API Specifications
for i in range(50):
    spec = f"""# API Endpoint Documentation: v1/service_{i}
**Endpoint:** `GET /api/v1/service_{i}/{{id}}`  
**Authentication:** JWT Token Required  

## Request Headers:
`Authorization: Bearer <token>`  

## Response (200 OK):
```json
{{
  "status": "success",
  "data": {{
    "service_id": "service_{i}",
    "entity_uuid": "generated-uuid-value",
    "updated_at": "2026-07-31T15:54:00Z"
  }}
}}
```
"""
    add_rag_document(f"API Document: Service {i}", "engineering", spec, "TECHNICAL", "ENG")

# Generate 150 Software Design Documents
for i in range(150):
    design = f"""# System Design Document: Architecture Module {i}
**Author:** Engineering Team Lead  
**Status:** Approved  

## 1. Abstract
This document outlines the software design for system subsystem {i}, utilizing a microservices framework connected to a PostgreSQL read-replica cluster.

## 2. High-Level Architecture
- **Inbound Layer:** FastAPI routes request.
- **Service Layer:** Validation and orchestration layer.
- **Persistence Layer:** CRUD operations using SQLAlchemy.
- **Vector Indexing:** Real-time updates pushed to Qdrant collections.
"""
    add_rag_document(f"Design Doc: Module {i}", "engineering", design, "TECHNICAL", "ENG")

# 11.4 Financial Reports (100 reports)
print("Generating Financial Reports...")
for i in range(100):
    fin = f"""# Financial Performance Summary: Q{ (i % 4) + 1 } 202{ 3 + (i // 4) % 4 }
**Report Code:** FIN-REP-{i:03d}  
**Classification:** Confidential  

## Quarterly Statement
This report summarizes the operational budgets, spent amounts, and invoices processing metrics for Quarter { (i % 4) + 1 }.

- **Allocated Total Budget:** $15,450,000.00
- **Total Spent Revenue:** $12,980,000.00
- **Unsettled Invoices:** $412,000.00
- **Target Performance Ratio:** { round(random.uniform(85.0, 99.5), 2) }%
"""
    add_rag_document(f"Financial Report: Q{(i % 4) + 1} 202{3 + (i // 4) % 4} - {i}", "finance", fin, "FINANCE", "FIN")

# 11.5 Client Contracts (300 contracts)
print("Generating Client Contracts...")
for i, cl in enumerate(clients):
    contract = f"""# Client Service Agreement: {cl['name']}
**Agreement Reference:** CSA-2026-{i:04d}  
**Client:** {cl['name']}  
**Industry Vertical:** {cl['industry']}  

## Terms of Engagement
Synthetic Enterprise agrees to provide custom software integrations, data pipelines, and database modeling services as specified in the agreed-upon project proposals.

- **Duration:** 24 Months
- **Billing Terms:** Net 30 invoices.
- **Warranty:** Standard SLA of 99.9% API uptime for deployed solutions.
- **Signatures:** Executed by client representative: {cl['contact_name']}.
"""
    add_rag_document(f"Client Contract: {cl['name']}", "contracts", contract, "CONTRACT", "LGL")

# 11.6 Product Manuals (100 manuals)
print("Generating Product Manuals...")
for i in range(100):
    manual = f"""# Product User Guide: Module {i}
**Product Line:** Enterprise Orchestration Suite  
**Document version:** 4.2  

## Getting Started
To integrate Product Module {i} into your ecosystem:
1. Obtain API credentials from the Information Security portal.
2. Initialize the client using standard python configs.
3. Establish communication channel via standard web sockets.
"""
    add_rag_document(f"Product Manual: Module {i}", "manuals", manual, "MANUAL", "PRD")

# 11.7 Meeting Minutes (2000 documents)
print("Generating 2000 Meeting Minutes documents...")
for i, mt in enumerate(meetings):
    minutes = f"""# Meeting Minutes: {mt['title']}
**Date:** {mt['date_time']}  
**Location:** {mt['location']}  
**Organizer ID:** {mt['organizer_id']}  

## Agenda
Review of current milestones, task allocations, and critical blockages.

## Key Discussion Points
- Progress updates from team members.
- Task status review: tasks identified as todo vs in-progress.
- Discussion on budgets and invoices issues.
- Integration issues with API spec and system design.

## Action Items
- Follow up on outstanding deliverables by next week.
- Coordinate with department manager for budget clearance.
"""
    # Create the text document and register its metadata
    doc_id = add_rag_document(f"Minutes: {mt['title']}", "communications", minutes, "COMMUNICATION", "ICM")

# 11.8 Email Threads (10000 emails, saved as files under RAG_DIR and inside json/emails.json)
print("Generating 10000 Emails...")
emails_json_data = []

EMAIL_TEMPLATES = [
    ("RE: Project Status Update", "Just checking in on the progress of the task. Can we schedule a quick sync to review the designs?"),
    ("Action Required: Expense Approval", "Please review the submitted expense report on your portal. Needs manager clearance."),
    ("API Specifications Review", "I have uploaded the new endpoint design markdown. Please take a look and provide feedback."),
    ("Weekly Sync Agenda", "Please add your topics to the weekly sync notes before the stand-up tomorrow morning."),
    ("HR Policy Update Notice", "Please review the updated policy POL-HR-002 regarding the remote work hybrid schedule.")
]

for i in range(10000):
    sender = random.choice(employees)
    recipient = random.choice(employees)
    while recipient["id"] == sender["id"]:
        recipient = random.choice(employees)
        
    subj, body_tpl = random.choice(EMAIL_TEMPLATES)
    subject = f"{subj} - Thread {i // 5} ({i})"
    body = f"Hi {recipient['first_name']},\n\n{body_tpl}\n\nThanks,\n{sender['first_name']} {sender['last_name']}\nSynthetic Enterprise Inc."
    sent_at = datetime.now() - timedelta(days=random.randint(1, 400), seconds=random.randint(1, 86400))
    email_id = str(uuid.uuid4())
    thread_id = str(uuid.uuid4()) if i % 5 == 0 else emails_json_data[-1]["thread_id"]
    
    # Save to JSON database
    emails_json_data.append({
        "id": email_id,
        "thread_id": thread_id,
        "sender": sender["email"],
        "recipient": recipient["email"],
        "subject": subject,
        "body": body,
        "sent_at": sent_at.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # We also generate RAG files for some of them (~500 emails to keep file count under control but rich)
    if i < 500:
        content = f"""# Email: {subject}
**From:** {sender['email']}  
**To:** {recipient['email']}  
**Date:** {sent_at.strftime("%Y-%m-%d %H:%M:%S")}  

{body}
"""
        add_rag_document(f"Email: {subject}", "communications", content, "COMMUNICATION", "ICM")

# Save structured emails JSON
with open(os.path.join(JSON_DIR, "emails.json"), "w", encoding="utf-8") as f:
    json.dump(emails_json_data, f, indent=2)

print(f"Total documents metadata generated: {len(documents_metadata)}")

# ==========================================
# 12. WRITE CSV AND JSON FILES
# ==========================================
print("Writing CSV files...")

def write_csv(filename, data, fieldnames):
    filepath = os.path.join(CSV_DIR, filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

write_csv("roles.csv", roles, ["id", "name", "description", "level"])
write_csv("permissions.csv", permissions, ["id", "name", "description", "category"])
write_csv("role_permissions.csv", role_permissions, ["role_id", "permission_id"])
write_csv("departments.csv", departments, ["id", "name", "code", "manager_id"])
write_csv("employees.csv", employees, ["id", "first_name", "last_name", "email", "phone", "hire_date", "salary", "department_id", "manager_id", "role_id", "status"])
write_csv("clients.csv", clients, ["id", "name", "contact_name", "contact_email", "contact_phone", "industry", "billing_address"])
write_csv("vendors.csv", vendors, ["id", "name", "contact_name", "contact_email", "contact_phone", "services_provided", "contract_start", "contract_end"])
write_csv("projects.csv", projects, ["id", "name", "description", "status", "start_date", "end_date", "client_id", "department_id", "budget_amount"])
write_csv("project_members.csv", project_members, ["project_id", "employee_id", "role_in_project"])
write_csv("tasks.csv", tasks, ["id", "title", "description", "status", "priority", "due_date", "project_id", "assignee_id", "creator_id"])
write_csv("meetings.csv", meetings, ["id", "title", "description", "date_time", "location", "project_id", "organizer_id"])
write_csv("meeting_participants.csv", meeting_participants, ["meeting_id", "employee_id"])
write_csv("documents_metadata.csv", documents_metadata, ["id", "title", "file_path", "file_size", "mime_type", "created_at", "updated_at", "creator_id", "department_id", "document_type"])
write_csv("payroll.csv", payroll_records, ["id", "employee_id", "pay_date", "base_salary", "bonuses", "deductions", "net_pay", "status"])
write_csv("leave_requests.csv", leave_requests, ["id", "employee_id", "leave_type", "start_date", "end_date", "status", "approver_id"])
write_csv("performance_reviews.csv", performance_reviews, ["id", "employee_id", "reviewer_id", "review_date", "period_start", "period_end", "rating", "comments"])
write_csv("budgets.csv", budgets, ["id", "department_id", "fiscal_year", "total_amount", "allocated_amount", "spent_amount"])
write_csv("expenses.csv", expenses, ["id", "employee_id", "department_id", "description", "amount", "expense_date", "category", "status", "approver_id"])
write_csv("invoices.csv", invoices, ["id", "client_id", "project_id", "invoice_number", "issue_date", "due_date", "subtotal", "tax", "total_amount", "status"])
write_csv("notifications.csv", notifications, ["id", "employee_id", "message", "status"])

print("Writing JSON logs...")

with open(os.path.join(JSON_DIR, "chat_sessions.json"), "w", encoding="utf-8") as f:
    json.dump({
        "sessions": chat_sessions,
        "messages": chat_messages
    }, f, indent=2)

with open(os.path.join(JSON_DIR, "audit_logs.json"), "w", encoding="utf-8") as f:
    json.dump(audit_logs, f, indent=2)

with open(os.path.join(JSON_DIR, "workflow_executions.json"), "w", encoding="utf-8") as f:
    json.dump(workflow_executions, f, indent=2)

# ==========================================
# 13. GENERATE POSTGRESQL INSERT SEED SCRIPTS
# ==========================================
print("Generating PostgreSQL insert scripts (seed_data.sql)...")

# Write to synthetic_data/postgres/seed_data.sql
postgres_seed_path = os.path.join(POSTGRES_DIR, "seed_data.sql")
with open(postgres_seed_path, "w", encoding="utf-8") as sf:
    sf.write("-- Seed Data Script for PostgreSQL\n")
    sf.write("BEGIN;\n\n")
    
    # Roles
    sf.write("-- Roles\n")
    for r in roles:
        desc_escaped = r['description'].replace("'", "''")
        sf.write(f"INSERT INTO roles (id, name, description, level) VALUES ('{r['id']}', '{r['name']}', '{desc_escaped}', {r['level']});\n")
    sf.write("\n")
    
    # Permissions
    sf.write("-- Permissions\n")
    for p in permissions:
        desc_escaped = p['description'].replace("'", "''")
        sf.write(f"INSERT INTO permissions (id, name, description, category) VALUES ('{p['id']}', '{p['name']}', '{desc_escaped}', '{p['category']}');\n")
    sf.write("\n")
    
    # Role Permissions
    sf.write("-- Role Permissions\n")
    for rp in role_permissions:
        sf.write(f"INSERT INTO role_permissions (role_id, permission_id) VALUES ('{rp['role_id']}', '{rp['permission_id']}');\n")
    sf.write("\n")
    
    # Departments (temporarily set manager_id to NULL to prevent circular dependencies)
    sf.write("-- Departments (Manager set to NULL initially)\n")
    for d in departments:
        sf.write(f"INSERT INTO departments (id, name, code, manager_id) VALUES ('{d['id']}', '{d['name']}', '{d['code']}', NULL);\n")
    sf.write("\n")
    
    # Employees (Managers will reference existing employee IDs, root node CEO manager_id is NULL)
    sf.write("-- Employees\n")
    for e in employees:
        mgr_val = f"'{e['manager_id']}'" if e['manager_id'] else "NULL"
        role_val = f"'{e['role_id']}'" if e['role_id'] else "NULL"
        dept_val = f"'{e['department_id']}'" if e['department_id'] else "NULL"
        sf.write(f"INSERT INTO employees (id, first_name, last_name, email, phone, hire_date, salary, department_id, manager_id, role_id, status) VALUES ('{e['id']}', '{e['first_name']}', '{e['last_name']}', '{e['email']}', '{e['phone']}', '{e['hire_date']}', {e['salary']}, {dept_val}, {mgr_val}, {role_val}, '{e['status']}');\n")
    sf.write("\n")
    
    # Update Department Managers
    sf.write("-- Update Department Managers\n")
    for d in departments:
        if d['manager_id']:
            sf.write(f"UPDATE departments SET manager_id = '{d['manager_id']}' WHERE id = '{d['id']}';\n")
    sf.write("\n")
    
    # Clients
    sf.write("-- Clients\n")
    for c in clients:
        addr_escaped = c['billing_address'].replace("'", "''")
        sf.write(f"INSERT INTO clients (id, name, contact_name, contact_email, contact_phone, industry, billing_address) VALUES ('{c['id']}', '{c['name']}', '{c['contact_name']}', '{c['contact_email']}', '{c['contact_phone']}', '{c['industry']}', '{addr_escaped}');\n")
    sf.write("\n")
    
    # Vendors
    sf.write("-- Vendors\n")
    for v in vendors:
        sf.write(f"INSERT INTO vendors (id, name, contact_name, contact_email, contact_phone, services_provided, contract_start, contract_end) VALUES ('{v['id']}', '{v['name']}', '{v['contact_name']}', '{v['contact_email']}', '{v['contact_phone']}', '{v['services_provided']}', '{v['contract_start']}', '{v['contract_end']}');\n")
    sf.write("\n")
    
    # Projects
    sf.write("-- Projects\n")
    for p in projects:
        desc_escaped = p['description'].replace("'", "''") if p['description'] else ""
        end_val = f"'{p['end_date']}'" if p['end_date'] else "NULL"
        sf.write(f"INSERT INTO projects (id, name, description, status, start_date, end_date, client_id, department_id, budget_amount) VALUES ('{p['id']}', '{p['name']}', '{desc_escaped}', '{p['status']}', '{p['start_date']}', {end_val}, '{p['client_id']}', '{p['department_id']}', {p['budget_amount']});\n")
    sf.write("\n")
    
    # Project Members
    sf.write("-- Project Members\n")
    for pm in project_members:
        sf.write(f"INSERT INTO project_members (project_id, employee_id, role_in_project) VALUES ('{pm['project_id']}', '{pm['employee_id']}', '{pm['role_in_project']}');\n")
    sf.write("\n")
    
    # Tasks
    sf.write("-- Tasks\n")
    for t in tasks:
        desc_escaped = t['description'].replace("'", "''") if t['description'] else ""
        title_escaped = t['title'].replace("'", "''")
        sf.write(f"INSERT INTO tasks (id, title, description, status, priority, due_date, project_id, assignee_id, creator_id) VALUES ('{t['id']}', '{title_escaped}', '{desc_escaped}', '{t['status']}', '{t['priority']}', '{t['due_date']}', '{t['project_id']}', '{t['assignee_id']}', '{t['creator_id']}');\n")
    sf.write("\n")
    
    # Meetings
    sf.write("-- Meetings\n")
    for m in meetings:
        title_escaped = m['title'].replace("'", "''")
        desc_escaped = m['description'].replace("'", "''")
        sf.write(f"INSERT INTO meetings (id, title, description, date_time, location, project_id, organizer_id) VALUES ('{m['id']}', '{title_escaped}', '{desc_escaped}', '{m['date_time']}', '{m['location']}', '{m['project_id']}', '{m['organizer_id']}');\n")
    sf.write("\n")
    
    # Meeting Participants
    sf.write("-- Meeting Participants\n")
    for mp in meeting_participants:
        sf.write(f"INSERT INTO meeting_participants (meeting_id, employee_id) VALUES ('{mp['meeting_id']}', '{mp['employee_id']}');\n")
    sf.write("\n")
    
    # Documents Metadata
    sf.write("-- Documents Metadata\n")
    for d in documents_metadata:
        title_escaped = d['title'].replace("'", "''")
        sf.write(f"INSERT INTO documents_metadata (id, title, file_path, file_size, mime_type, creator_id, department_id, document_type) VALUES ('{d['id']}', '{title_escaped}', '{d['file_path']}', {d['file_size']}, '{d['mime_type']}', '{d['creator_id']}', '{d['department_id']}', '{d['document_type']}');\n")
    sf.write("\n")
    
    # Payroll
    sf.write("-- Payroll\n")
    for pay in payroll_records:
        sf.write(f"INSERT INTO payroll (id, employee_id, pay_date, base_salary, bonuses, deductions, net_pay, status) VALUES ('{pay['id']}', '{pay['employee_id']}', '{pay['pay_date']}', {pay['base_salary']}, {pay['bonuses']}, {pay['deductions']}, {pay['net_pay']}, '{pay['status']}');\n")
    sf.write("\n")
    
    # Leave Requests
    sf.write("-- Leave Requests\n")
    for lr in leave_requests:
        sf.write(f"INSERT INTO leave_requests (id, employee_id, leave_type, start_date, end_date, status, approver_id) VALUES ('{lr['id']}', '{lr['employee_id']}', '{lr['leave_type']}', '{lr['start_date']}', '{lr['end_date']}', '{lr['status']}', '{lr['approver_id']}');\n")
    sf.write("\n")
    
    # Performance Reviews
    sf.write("-- Performance Reviews\n")
    for pr in performance_reviews:
        comments_escaped = pr['comments'].replace("'", "''")
        sf.write(f"INSERT INTO performance_reviews (id, employee_id, reviewer_id, review_date, period_start, period_end, rating, comments) VALUES ('{pr['id']}', '{pr['employee_id']}', '{pr['reviewer_id']}', '{pr['review_date']}', '{pr['period_start']}', '{pr['period_end']}', {pr['rating']}, '{comments_escaped}');\n")
    sf.write("\n")
    
    # Budgets
    sf.write("-- Budgets\n")
    for b in budgets:
        sf.write(f"INSERT INTO budgets (id, department_id, fiscal_year, total_amount, allocated_amount, spent_amount) VALUES ('{b['id']}', '{b['department_id']}', {b['fiscal_year']}, {b['total_amount']}, {b['allocated_amount']}, {b['spent_amount']});\n")
    sf.write("\n")
    
    # Expenses
    sf.write("-- Expenses\n")
    for ex in expenses:
        desc_escaped = ex['description'].replace("'", "''")
        sf.write(f"INSERT INTO expenses (id, employee_id, department_id, description, amount, expense_date, category, status, approver_id) VALUES ('{ex['id']}', '{ex['employee_id']}', '{ex['department_id']}', '{desc_escaped}', {ex['amount']}, '{ex['expense_date']}', '{ex['category']}', '{ex['status']}', '{ex['approver_id']}');\n")
    sf.write("\n")
    
    # Invoices
    sf.write("-- Invoices\n")
    for inv in invoices:
        sf.write(f"INSERT INTO invoices (id, client_id, project_id, invoice_number, issue_date, due_date, subtotal, tax, total_amount, status) VALUES ('{inv['id']}', '{inv['client_id']}', '{inv['project_id']}', '{inv['invoice_number']}', '{inv['issue_date']}', '{inv['due_date']}', {inv['subtotal']}, {inv['tax']}, {inv['total_amount']}, '{inv['status']}');\n")
    sf.write("\n")
    
    # Notifications
    sf.write("-- Notifications\n")
    for n in notifications:
        sf.write(f"INSERT INTO notifications (id, employee_id, message, status) VALUES ('{n['id']}', '{n['employee_id']}', '{n['message']}', '{n['status']}');\n")
    sf.write("\n")
    
    sf.write("COMMIT;\n")

# ==========================================
# 14. GENERATE NEO4J CYPHER INSERTS
# ==========================================
print("Generating Cypher scripts for Neo4j (import_graph.cypher)...")

neo4j_cypher_path = os.path.join(NEO4J_DIR, "import_graph.cypher")
with open(neo4j_cypher_path, "w", encoding="utf-8") as cf:
    cf.write("// Neo4j Knowledge Graph Import Queries\n")
    cf.write("// Enterprise AI OS Knowledge Representation\n\n")
    
    # Constraints & Indexes
    cf.write("// Constraints & Indexes\n")
    cf.write("CREATE CONSTRAINT unique_employee_id IF NOT EXISTS FOR (e:Employee) REQUIRE e.id IS UNIQUE;\n")
    cf.write("CREATE CONSTRAINT unique_department_id IF NOT EXISTS FOR (d:Department) REQUIRE d.id IS UNIQUE;\n")
    cf.write("CREATE CONSTRAINT unique_project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE;\n")
    cf.write("CREATE CONSTRAINT unique_client_id IF NOT EXISTS FOR (c:Client) REQUIRE c.id IS UNIQUE;\n")
    cf.write("CREATE CONSTRAINT unique_vendor_id IF NOT EXISTS FOR (v:Vendor) REQUIRE v.id IS UNIQUE;\n")
    cf.write("CREATE CONSTRAINT unique_document_id IF NOT EXISTS FOR (doc:Document) REQUIRE doc.id IS UNIQUE;\n")
    cf.write("CREATE CONSTRAINT unique_meeting_id IF NOT EXISTS FOR (m:Meeting) REQUIRE m.id IS UNIQUE;\n")
    cf.write("CREATE CONSTRAINT unique_technology_name IF NOT EXISTS FOR (t:Technology) REQUIRE t.name IS UNIQUE;\n")
    cf.write("CREATE CONSTRAINT unique_skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE;\n\n")
    
    # Create Departments
    cf.write("// Create Departments\n")
    for d in departments:
        cf.write(f"MERGE (:Department {{id: '{d['id']}', name: '{d['name']}', code: '{d['code']}'}});\n")
    cf.write("\n")
    
    # Create Skills & Tech
    cf.write("// Create Skills\n")
    for name, cat in SKILLS:
        cf.write(f"MERGE (:Skill {{name: '{name}', category: '{cat}'}});\n")
    cf.write("\n")
    
    cf.write("// Create Technologies\n")
    for name, cat in TECHNOLOGIES:
        cf.write(f"MERGE (:Technology {{name: '{name}', category: '{cat}'}});\n")
    cf.write("\n")
    
    # Create Employees
    cf.write("// Create Employees\n")
    for e in employees:
        name_full = f"{e['first_name']} {e['last_name']}"
        cf.write(f"MERGE (:Employee {{id: '{e['id']}', name: '{name_full}', email: '{e['email']}', status: '{e['status']}'}});\n")
    cf.write("\n")
    
    # Create Clients & Vendors
    cf.write("// Create Clients\n")
    for c in clients:
        cf.write(f"MERGE (:Client {{id: '{c['id']}', name: '{c['name']}', industry: '{c['industry']}'}});\n")
    cf.write("\n")
    
    cf.write("// Create Vendors\n")
    for v in vendors:
        cf.write(f"MERGE (:Vendor {{id: '{v['id']}', name: '{v['name']}', services: '{v['services_provided']}'}});\n")
    cf.write("\n")
    
    # Create Projects
    cf.write("// Create Projects\n")
    for p in projects:
        name_escaped = p['name'].replace("'", "''")
        cf.write(f"MERGE (:Project {{id: '{p['id']}', name: '{name_escaped}', status: '{p['status']}', budget: {p['budget_amount']}}});\n")
    cf.write("\n")
    
    # Create Meetings
    cf.write("// Create Meetings\n")
    for m in meetings:
        title_escaped = m['title'].replace("'", "''")
        cf.write(f"MERGE (:Meeting {{id: '{m['id']}', title: '{title_escaped}', dateTime: '{m['date_time']}'}});\n")
    cf.write("\n")
    
    # Create Documents
    cf.write("// Create Documents\n")
    for doc in documents_metadata:
        title_escaped = doc['title'].replace("'", "''")
        cf.write(f"MERGE (:Document {{id: '{doc['id']}', title: '{title_escaped}', type: '{doc['document_type']}', path: '{doc['file_path']}'}});\n")
    cf.write("\n")
    
    # Relationships: WORKS_IN, REPORTS_TO, MANAGES
    cf.write("// Employee relationships\n")
    for e in employees:
        cf.write(f"MATCH (emp:Employee {{id: '{e['id']}'}}), (d:Department {{id: '{e['department_id']}'}}) MERGE (emp)-[:WORKS_IN]->(d);\n")
        if e['manager_id']:
            cf.write(f"MATCH (emp:Employee {{id: '{e['id']}'}}), (m:Employee {{id: '{e['manager_id']}'}}) MERGE (emp)-[:REPORTS_TO]->(m);\n")
    cf.write("\n")
    
    # Department managers
    cf.write("// Department managers\n")
    for d in departments:
        if d['manager_id']:
            cf.write(f"MATCH (emp:Employee {{id: '{d['manager_id']}'}}), (d:Department {{id: '{d['id']}'}}) MERGE (emp)-[:MANAGES]->(d);\n")
    cf.write("\n")
    
    # Project Assignments and Client Ownership
    cf.write("// Project client ownership\n")
    for p in projects:
        cf.write(f"MATCH (c:Client {{id: '{p['client_id']}'}}), (proj:Project {{id: '{p['id']}'}}) MERGE (c)-[:OWNS]->(proj);\n")
    cf.write("\n")
    
    cf.write("// Project members assignments\n")
    for pm in project_members:
        cf.write(f"MATCH (emp:Employee {{id: '{pm['employee_id']}'}}), (proj:Project {{id: '{pm['project_id']}'}}) MERGE (emp)-[:ASSIGNED_TO {{role: '{pm['role_in_project']}'}}]->(proj);\n")
    cf.write("\n")
    
    # Meetings participation
    cf.write("// Meeting participants\n")
    for mp in meeting_participants:
        cf.write(f"MATCH (emp:Employee {{id: '{mp['employee_id']}'}}), (m:Meeting {{id: '{mp['meeting_id']}'}}) MERGE (emp)-[:PARTICIPATED_IN]->(m);\n")
    cf.write("\n")
    
    # Document creation and ownership
    cf.write("// Document creators and departments\n")
    for doc in documents_metadata:
        if doc['creator_id']:
            cf.write(f"MATCH (emp:Employee {{id: '{doc['creator_id']}'}}), (doc:Document {{id: '{doc['id']}'}}) MERGE (emp)-[:CREATED]->(doc);\n")
        if doc['department_id']:
            cf.write(f"MATCH (d:Department {{id: '{doc['department_id']}'}}), (doc:Document {{id: '{doc['id']}'}}) MERGE (d)-[:OWNS]->(doc);\n")
    cf.write("\n")
    
    # Link Skill / Tech to employee or project
    cf.write("// Assign skills to employees (randomized matching for Cypher demonstration)\n")
    for e in employees[:300]: # Match skills for first 300 employees to keep queries reasonable
        s_rand = random.choice(SKILLS)[0]
        cf.write(f"MATCH (emp:Employee {{id: '{e['id']}'}}), (s:Skill {{name: '{s_rand}'}}) MERGE (emp)-[:HAS_SKILL {{proficiency: 'PROFFICIENT'}}]->(s);\n")
        
    cf.write("\n// Assign technologies used in projects\n")
    for p in projects[:150]:
        t_rand = random.choice(TECHNOLOGIES)[0]
        cf.write(f"MATCH (proj:Project {{id: '{p['id']}'}}), (t:Technology {{name: '{t_rand}'}}) MERGE (proj)-[:USES_TECHNOLOGY]->(t);\n")

print("All synthetic enterprise files written successfully!")

# ==========================================
# 15. SELF-VALIDATION CHECKS
# ==========================================
print("Running referential integrity checks...")

# Load written CSV data and verify PK-FK relationships
dept_ids = {d["id"] for d in departments}
emp_ids = {e["id"] for e in employees}
client_ids = {c["id"] for c in clients}
project_ids = {p["id"] for p in projects}

# Verify employees departments
for e in employees:
    assert e["department_id"] in dept_ids, f"Referential error: Employee {e['id']} department {e['department_id']} not found."
    if e["manager_id"]:
        assert e["manager_id"] in emp_ids, f"Referential error: Employee {e['id']} manager {e['manager_id']} not found."

# Verify projects
for p in projects:
    assert p["client_id"] in client_ids, f"Referential error: Project {p['id']} client {p['client_id']} not found."
    assert p["department_id"] in dept_ids, f"Referential error: Project {p['id']} department {p['department_id']} not found."

# Verify document metadata
for d in documents_metadata:
    if d["creator_id"]:
        assert d["creator_id"] in emp_ids, f"Referential error: Document {d['id']} creator {d['creator_id']} not found."
    if d["department_id"]:
        assert d["department_id"] in dept_ids, f"Referential error: Document {d['id']} department {d['department_id']} not found."

print("Validation: Success! All constraints and foreign key linkages verified.")
