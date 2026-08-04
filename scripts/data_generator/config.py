# scripts/data_generator/config.py
import os
from datetime import date

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "synthetic_data")
CSV_DIR = os.path.join(SYNTHETIC_DIR, "csv")
JSON_DIR = os.path.join(SYNTHETIC_DIR, "json")
RAG_DIR = os.path.join(SYNTHETIC_DIR, "rag_docs")
POSTGRES_DIR = os.path.join(SYNTHETIC_DIR, "postgres")
NEO4J_DIR = os.path.join(SYNTHETIC_DIR, "neo4j")
QDRANT_DIR = os.path.join(SYNTHETIC_DIR, "qdrant")

RAG_SUBDIRS = {
    "handbook": os.path.join(RAG_DIR, "handbook"),
    "policies": os.path.join(RAG_DIR, "policies"),
    "security": os.path.join(RAG_DIR, "security"),
    "engineering": os.path.join(RAG_DIR, "engineering"),
    "finance": os.path.join(RAG_DIR, "finance"),
    "sales": os.path.join(RAG_DIR, "sales"),
    "specs": os.path.join(RAG_DIR, "specs"),
    "contracts": os.path.join(RAG_DIR, "contracts"),
    "manuals": os.path.join(RAG_DIR, "manuals"),
    "communications": os.path.join(RAG_DIR, "communications")
}

# Date ranges
START_DATE = date(2022, 1, 1)
END_DATE = date(2026, 7, 31)

# Name pools
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
    "Alice", "Albert", "Madison", "Joe", "Doris", "Abigail", "Billy", "Julia",
    "Bryan", "Judy", "Bruce", "Grace", "Jordan", "Denise", "Ralph", "Amber", "Roy", "Marilyn",
    "Alan", "Wayne", "Danielle", "Louis", "Diana", "Dylan", "Brittany", "Eugene", "Charlotte"
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
    "Ryan", "Salazar", "Webb", "Mason", "Sutton", "Shaw", "Gordon", "Burns", "Warren",
    "Jordan", "Owens", "Cole", "Ellis", "Harrison", "Gibson", "McDonald", "Marshall", "Murray", 
    "Freeman", "Wells", "Simpson", "Stevens", "Tucker", "Hunter", "Hicks", "Crawford", "Boyd", "Olson", 
    "Garza", "Wagner"
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

# (Skill Name, Department Code associated with it)
SKILLS = [
    ("Python", "ENG"), ("SQL", "DAT"), ("PostgreSQL", "DAT"),
    ("Project Management", "OPS"), ("Financial Modeling", "FIN"), ("Legal Writing", "LGL"),
    ("Machine Learning", "RND"), ("Kubernetes", "ENG"), ("Cloud Architecture", "ENG"),
    ("Docker", "ENG"), ("React", "ENG"), ("TypeScript", "ENG"),
    ("Node.js", "ENG"), ("Neo4j", "DAT"), ("Qdrant", "DAT"),
    ("Redis", "ITS"), ("Git", "ENG"), ("CI/CD Orchestration", "ENG"),
    ("Enterprise Risk Management", "COM"), ("Talent Acquisition", "HR"),
    ("Strategic Planning", "EGY"), ("Copywriting", "MKT"), ("SEO", "MKT"),
    ("Public Speaking", "PR"), ("Contract Negotiation", "LGL"), ("Budgeting", "FIN"),
    ("Employee Relations", "HR"), ("Product Strategy", "PRD"),
    ("Customer Relationship Management", "CSM"), ("Agile Methodologies", "PRD")
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

SECURITY_POLICY_TOPICS = [
    ("Identity and Access Management Policy", "Defines standard methods for identity verification, password complexity, and multi-factor authentication requirements."),
    ("Incident Response and Containment Standard", "Specifies steps and roles required to contain, investigate, and report security breaches."),
    ("Data Encryption and Protection Policy", "Outlines parameters for data encryption in transit (TLS 1.3) and at rest (AES-256)."),
    ("Vulnerability Management and Patching Policy", "Defines response cycles for patching CVSS critical, high, and medium vulnerabilities."),
    ("Security Logging and Audit Standards", "Ensures that all key backend processes record audit-compliant access logs to Postgres."),
    ("Physical and Clean-Desk Security Policy", "Details rules for secure badge access, hardware locking, and visitor logging inside company offices."),
    ("Mobile Device and Endpoint Security Rules", "Establishes device management software requirements and local storage locks on employee endpoints."),
    ("Third-Party Vendor Risk Assessment Policy", "Specifies security review steps required before engaging cloud services or contractors."),
    ("Business Continuity and Disaster Recovery Standard", "Outlines RTO and RPO metrics for backup recovery and site replication operations."),
    ("Data Retention and Disposal Guidelines", "Establishes retention schedules and cryptographic shredding for consumer personal data.")
]
