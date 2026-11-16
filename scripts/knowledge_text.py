"""
English text for the company's policies and project documents.

The original seed data filled `policies.description` and `documents.content`
with "lorem ipsum" placeholder words.  This module writes real English text:

  * one full policy per policy name (purpose, scope, rules, responsibilities)
  * one project document per row, built from the real project record
    (client, manager, status, dates) plus sections that fit the document

Used by scripts/apply_english_text.py.  The text is deterministic: running the
script again produces exactly the same content.
"""
import hashlib
from typing import Any, Dict, List, Optional

# ----------------------------------------------------------------------
# Policies
# ----------------------------------------------------------------------
# {dept} is replaced by the owning department's name.
POLICIES: Dict[str, Dict[str, Any]] = {
    "AI Model Governance Policy": {
        "purpose": "This policy sets out how artificial intelligence and machine learning models are approved, released and monitored so that they stay accurate, fair and safe throughout their life.",
        "scope": "It applies to every model that is built, bought or fine-tuned by the company and used in a product, an internal tool or a business decision.",
        "rules": [
            "Every model must have a named owner and an entry in the model register before it is used in production.",
            "A model may only be released after a documented review of its training data, evaluation results, known limitations and intended use.",
            "Models that influence decisions about people, money or security are classed as high risk and need sign-off from the AI governance board.",
            "Production models are monitored for accuracy, drift and bias, and are re-evaluated at least every six months.",
            "A model that fails its agreed thresholds must be rolled back or switched off until the cause is understood and fixed.",
        ],
        "responsibilities": "Model owners keep the documentation and monitoring up to date. The AI governance board reviews high-risk models and keeps the register.",
    },
    "Access Control Policy": {
        "purpose": "This policy makes sure that people and systems can reach only the information and tools they need for their work, and nothing more.",
        "scope": "It covers all company applications, databases, cloud accounts, networks and physical offices, for employees, contractors and service accounts.",
        "rules": [
            "Access is granted by job role on the principle of least privilege and must be approved by the employee's manager and the system owner.",
            "Every person uses their own named account. Shared and generic accounts are not allowed.",
            "Multi-factor authentication is required for remote access, administrator access and all systems that hold confidential data.",
            "Managers review the access of their team every quarter and remove anything that is no longer needed.",
            "Access is removed on the last working day of anyone who leaves, and adjusted within three working days when someone changes role.",
        ],
        "responsibilities": "System owners approve and review access. IT Support carries out the changes and keeps the records. Managers report role changes and departures promptly.",
    },
    "Budget Approval Policy": {
        "purpose": "This policy explains how departmental and project budgets are requested, approved and changed, so that spending stays planned and accountable.",
        "scope": "It applies to all operating and project budgets in every department.",
        "rules": [
            "Each department submits its annual budget request to Finance before the start of the fiscal year, with a short justification for every major line.",
            "Budgets are approved first by the department head, then by the Chief Financial Officer; budgets above the board threshold also need approval from the Chief Executive Officer.",
            "Spending may not start on an activity that has no approved budget.",
            "A change of more than ten percent to an approved budget line needs a written revision approved by the same people who approved the original.",
            "Finance compares actual spending with the budget every month and reports significant differences to the department head.",
        ],
        "responsibilities": "Department heads own their budgets. Finance maintains the approved figures, the revision history and the monthly comparison.",
    },
    "Business Process Guidelines": {
        "purpose": "These guidelines describe how the {dept} department documents, runs and improves its regular business processes, so that work is done the same reliable way whoever does it.",
        "scope": "They apply to all recurring processes owned by the {dept} department and to everyone who takes part in them.",
        "rules": [
            "Every recurring process has a named owner and a written description of its steps, inputs, outputs and expected turnaround time.",
            "Requests enter a process through the agreed channel, so that they can be tracked from start to finish.",
            "Hand-overs between people or teams are recorded, including what is still open and who is now responsible.",
            "Problems and delays are raised with the process owner as soon as they are noticed, not at the deadline.",
            "Each process is reviewed at least once a year and after any serious failure, and the description is updated to match how the work is really done.",
        ],
        "responsibilities": "Process owners keep the descriptions current and measure how the process performs. Team members follow the documented steps and suggest improvements.",
    },
    "CRM Usage Guidelines": {
        "purpose": "These guidelines keep customer information in the CRM system complete, accurate and useful for everyone who works with clients.",
        "scope": "They apply to all employees who create or change accounts, contacts, opportunities or activities in the CRM system.",
        "rules": [
            "Every client interaction that matters, such as a meeting, a call or a proposal, is logged in the CRM within one working day.",
            "Opportunities carry a realistic value, stage and expected close date, and are updated whenever one of these changes.",
            "Before creating an account or contact, search for an existing record to avoid duplicates.",
            "Customer data is not exported from the CRM to personal files or devices without approval from the sales manager.",
            "Each account has one named owner, who is responsible for the quality of its records.",
        ],
        "responsibilities": "Account owners keep their records current. Sales management reviews pipeline data weekly and arranges clean-up of incomplete or duplicate records.",
    },
    "Code Review Standards": {
        "purpose": "These standards make sure that every change to the company's source code is checked by a second person before it reaches the main branch.",
        "scope": "They apply to all repositories that hold production code, infrastructure definitions or shared libraries.",
        "rules": [
            "Every change is submitted as a pull request and approved by at least one reviewer who did not write it.",
            "Reviewers check correctness, readability, test coverage, security and the effect on performance, not only coding style.",
            "Automated builds, tests and static analysis must pass before a pull request can be merged.",
            "Pull requests should be small enough to review properly; large changes are split into logical parts.",
            "Review comments are answered or resolved before merging, and urgent fixes merged without review are reviewed afterwards within one working day.",
        ],
        "responsibilities": "Authors explain what a change does and how it was tested. Reviewers respond within one working day. Team leads make sure the standards are followed.",
    },
    "Customer Data Handling Policy": {
        "purpose": "This policy protects the personal and business information that customers entrust to the company.",
        "scope": "It applies to all customer data in any form, and to every employee, contractor and supplier who can see or process it.",
        "rules": [
            "Customer data is used only for the purpose for which it was provided and is not shared outside the company without a contract or the customer's consent.",
            "Customer data is stored only in approved systems, encrypted in storage and in transit.",
            "Real customer data is not copied into test or development environments unless it has been anonymised.",
            "Data is kept only as long as the contract or the law requires, and is then deleted or anonymised.",
            "Any suspected loss or unauthorised disclosure of customer data is reported to the security team immediately.",
        ],
        "responsibilities": "Account and project managers know what customer data their teams hold. The security team investigates incidents and advises on safe handling.",
    },
    "Data Management Policy": {
        "purpose": "This policy sets out how the {dept} department classifies, stores, shares and retires the data it creates and uses.",
        "scope": "It applies to all data owned or processed by the {dept} department, whether in databases, documents, spreadsheets or reports.",
        "rules": [
            "Every data set has an owner and a classification: public, internal, confidential or restricted.",
            "Data is stored in the approved systems for its classification, never only on a personal device.",
            "Confidential and restricted data is shared on a need-to-know basis and with the owner's approval.",
            "Important data is backed up, and the backups are tested by restoring them at least once a year.",
            "Data that is no longer needed is deleted according to the retention schedule, and the deletion is recorded.",
        ],
        "responsibilities": "Data owners decide on classification, access and retention. Everyone who handles data follows the classification rules and reports errors in the data they find.",
    },
    "Department Operational Guidelines": {
        "purpose": "These guidelines describe the day-to-day working arrangements of the {dept} department, so that responsibilities, working hours and escalation routes are clear to everyone.",
        "scope": "They apply to all members of the {dept} department, including contractors who work as part of the team.",
        "rules": [
            "Core working hours are 10:00 to 16:00 on working days; outside those hours people arrange their time with their manager.",
            "The team meets weekly to review priorities, progress and blockers, and decisions are noted and shared afterwards.",
            "Requests to the department are made through its ticket queue or shared mailbox, so that nothing depends on one person's inbox.",
            "Planned absence is entered in the team calendar in advance, and a colleague is named to cover urgent matters.",
            "Issues that cannot be resolved within the team within two working days are escalated to the department head.",
        ],
        "responsibilities": "The department head sets priorities and resolves escalations. Team members keep their work visible and raise problems early.",
    },
    "Employee Conduct Policy": {
        "purpose": "This policy describes the standard of behaviour the company expects from everyone who works for it.",
        "scope": "It applies to all employees, interns and contractors, in the office, when working remotely, at client sites and at company events.",
        "rules": [
            "Treat colleagues, clients and suppliers with respect. Harassment, bullying and discrimination of any kind are not tolerated.",
            "Act honestly and in the company's interest, and declare any conflict of interest to your manager.",
            "Protect confidential information and company property, and use them only for work.",
            "Do not offer or accept gifts or hospitality that could influence a business decision; anything beyond a token value must be declared.",
            "Raise concerns about misconduct with your manager or Human Resources. Reports made in good faith are protected from retaliation.",
        ],
        "responsibilities": "Managers set the example and act on concerns. Human Resources investigates complaints fairly and confidentially. Breaches may lead to disciplinary action.",
    },
    "Engineering Quality Standards": {
        "purpose": "These standards define the minimum level of quality that software must reach before it is delivered to a client or released to production.",
        "scope": "They apply to all engineering teams and to all software the company builds or maintains.",
        "rules": [
            "New code is covered by automated tests, and the build must pass before a change is merged.",
            "Every release has acceptance criteria agreed with the product owner and is tested against them.",
            "Defects are logged, given a severity and fixed within the time agreed for that severity; critical defects block a release.",
            "Performance, security and accessibility are tested for every major release, not only functional behaviour.",
            "After a production incident the team holds a blameless review and records the actions that will prevent a repeat.",
        ],
        "responsibilities": "Engineering managers are accountable for quality in their teams. Quality Assurance verifies releases independently and reports on quality trends.",
    },
    "Expense Management Policy": {
        "purpose": "This policy explains which business expenses the company pays for and how employees claim them.",
        "scope": "It applies to all employees who spend money on behalf of the company, including travel, accommodation, meals, training and small purchases.",
        "rules": [
            "Expenses must be necessary for work, reasonable in cost and approved by the employee's manager; travel is approved before it is booked.",
            "Claims are submitted within thirty days of the expense, each with an itemised receipt.",
            "Travel is booked in economy class and at standard business hotels unless the department head approves an exception in writing.",
            "Personal expenses, fines and penalties are not reimbursed.",
            "Approved claims are paid with the next monthly payroll run.",
        ],
        "responsibilities": "Employees claim honestly and keep receipts. Managers check that claims are justified. Finance audits a sample of claims every month.",
    },
    "Financial Audit Policy": {
        "purpose": "This policy sets out how the company's financial records are checked, internally and by external auditors, so that they can be trusted.",
        "scope": "It applies to all financial transactions, accounts and reports, and to every department that creates or approves them.",
        "rules": [
            "The internal audit team reviews each major financial process at least once a year, following an audit plan approved by the Chief Financial Officer.",
            "The annual financial statements are audited by an independent external auditor.",
            "Every transaction is supported by documents that show what was bought or sold, who approved it and when.",
            "No one may both create and approve the same transaction.",
            "Audit findings are given an owner and a due date, and are followed up until they are closed.",
        ],
        "responsibilities": "Finance keeps records ready for audit. Department heads give auditors the information they ask for and correct the findings assigned to them.",
    },
    "Information Security Policy": {
        "purpose": "This policy protects the confidentiality, integrity and availability of the information that the {dept} department works with.",
        "scope": "It applies to everyone in the {dept} department and to all devices, systems and information they use for work.",
        "rules": [
            "Information is handled according to its classification, and confidential information is not discussed or displayed where others can see or hear it.",
            "Company devices are encrypted, locked when unattended and kept up to date with security patches.",
            "Only approved software and cloud services are used for company information.",
            "Be alert to phishing: do not open unexpected attachments or links, and report suspicious messages to the security team.",
            "Every security incident or near miss is reported at once, even if it seems minor.",
        ],
        "responsibilities": "Everyone completes the annual security awareness training. Managers make sure the rules are followed in their teams. The security team monitors, advises and responds to incidents.",
    },
    "Infrastructure Security Policy": {
        "purpose": "This policy sets the security requirements for the servers, networks and cloud services that run the company's systems.",
        "scope": "It applies to all production and non-production infrastructure, whether hosted in the company's own data centres or in the cloud.",
        "rules": [
            "Infrastructure is built from approved, hardened templates and managed as code, so that every change is reviewed and traceable.",
            "Networks are segmented, and production systems are reachable only through controlled, logged entry points.",
            "Security patches rated critical are applied within seven days, and all others within thirty days.",
            "Administrator access uses individual accounts with multi-factor authentication, and all administrator actions are logged.",
            "Logs from all systems are collected centrally, kept for at least one year and monitored for signs of attack.",
        ],
        "responsibilities": "The infrastructure team builds and maintains systems to these requirements. The security team runs regular vulnerability scans and an annual penetration test.",
    },
    "Leave Management Policy": {
        "purpose": "This policy explains the types of leave employees are entitled to and how leave is requested and approved.",
        "scope": "It applies to all permanent employees. Interns and contractors follow the leave terms in their own agreements.",
        "rules": [
            "Each employee is entitled to 24 days of paid annual leave per calendar year, in addition to public holidays.",
            "Annual leave is requested in the HR system at least two weeks in advance and needs the manager's approval.",
            "Up to 10 unused days of annual leave may be carried over into the next year; the rest lapse.",
            "Employees are entitled to 12 days of paid sick leave per year. A medical certificate is needed for sickness lasting more than two consecutive working days.",
            "Parental, bereavement and other special leave are granted according to the law and the employee handbook.",
        ],
        "responsibilities": "Employees plan leave early and hand over their work. Managers approve fairly and make sure the team stays covered. Human Resources keeps the leave records.",
    },
    "Machine Learning Development Standards": {
        "purpose": "These standards describe how machine learning models are developed so that results can be reproduced, compared and trusted.",
        "scope": "They apply to all teams that train, evaluate or deploy machine learning models.",
        "rules": [
            "Code, data versions, parameters and results of every experiment are tracked, so that any result can be reproduced.",
            "Training, validation and test data are kept separate, and test data is never used to tune a model.",
            "A model is compared against a simple baseline and evaluated on the agreed metrics before it is proposed for release.",
            "Data sets are checked for quality, bias and licence restrictions before they are used for training.",
            "Models are packaged with a model card that states the intended use, the training data, the evaluation results and the known limitations.",
        ],
        "responsibilities": "Data scientists and machine learning engineers follow these standards in their daily work. Team leads review experiments and model cards before release.",
    },
    "Password Management Policy": {
        "purpose": "This policy sets the rules for creating, using and protecting passwords and other login credentials.",
        "scope": "It applies to every account used for company work, including service accounts and accounts on third-party services.",
        "rules": [
            "Passwords are at least 12 characters long and are not reused between systems.",
            "Passwords are stored only in the company's approved password manager, never in documents, chats or on paper.",
            "Passwords are never shared, and no one from the company will ever ask an employee for a password.",
            "A password is changed immediately if it may have been disclosed. Passwords for administrator accounts are changed at least every 90 days.",
            "Multi-factor authentication is switched on wherever a system supports it.",
        ],
        "responsibilities": "Every account holder is responsible for their own credentials. IT Support enforces the technical rules and helps with the password manager.",
    },
    "Recruitment Guidelines": {
        "purpose": "These guidelines make sure that hiring is fair, consistent and based on the needs of the role.",
        "scope": "They apply to the recruitment of all permanent employees, interns and fixed-term staff.",
        "rules": [
            "A vacancy is opened only after the hiring manager and Human Resources have agreed the job description and the budget.",
            "Vacancies are advertised internally and externally for at least five working days.",
            "Candidates are assessed against the same written criteria by an interview panel of at least two people.",
            "Hiring decisions are based on skills and experience. Discrimination on any personal characteristic is prohibited.",
            "Offers are made in writing by Human Resources after reference and background checks are complete.",
        ],
        "responsibilities": "Hiring managers lead the selection. Human Resources runs the process, keeps the records and gives every interviewed candidate an answer.",
    },
    "Remote Work Policy": {
        "purpose": "This policy sets out when and how employees may work away from the office.",
        "scope": "It applies to all employees whose work can be done remotely, as agreed with their manager.",
        "rules": [
            "Employees may work remotely up to three days a week, by agreement with their manager and depending on the needs of the team.",
            "During working hours remote workers are reachable by chat, phone and video, and attend team meetings as usual.",
            "Work is done only on company-issued devices and over the company VPN.",
            "Confidential information is not handled in public places or on public Wi-Fi without the VPN.",
            "The employee provides a safe, quiet place to work and a reliable internet connection.",
        ],
        "responsibilities": "Managers agree remote arrangements and judge work by its results. Employees keep to the security rules wherever they work.",
    },
    "Responsible AI Usage Policy": {
        "purpose": "This policy explains how employees may use artificial intelligence tools, including the company's own assistant, safely and responsibly.",
        "scope": "It applies to all employees and contractors who use AI tools for company work.",
        "rules": [
            "Confidential, personal or customer data is entered only into AI tools that the company has approved for that kind of data.",
            "AI output is checked by a person before it is used in a decision, sent to a client or added to a product.",
            "AI is not used to make decisions about hiring, pay or discipline without human review.",
            "Content produced with AI is not presented as solely one's own work where a client or the law requires disclosure.",
            "Errors, biased results or misuse of an AI tool are reported to the AI governance board.",
        ],
        "responsibilities": "Each user remains responsible for the work they deliver with the help of AI. The AI governance board approves tools and reviews reported problems.",
    },
    "Sales Operations Policy": {
        "purpose": "This policy sets out how sales opportunities are qualified, priced and closed, so that the company makes commitments it can keep.",
        "scope": "It applies to everyone involved in selling the company's services, from the first contact to the signed contract.",
        "rules": [
            "Opportunities are qualified against the agreed criteria before a proposal is written.",
            "Prices follow the approved rate card. Discounts of more than ten percent need the approval of the sales director.",
            "Delivery teams review the scope, timeline and staffing of a proposal before it is sent to the client.",
            "Only authorised signatories may sign contracts, and only after legal review.",
            "The sales forecast is updated in the CRM every week and reviewed with sales management.",
        ],
        "responsibilities": "Sales executives own their opportunities and forecasts. Sales management approves pricing and reviews the pipeline.",
    },
    "Secure Coding Policy": {
        "purpose": "This policy sets out the practices developers follow so that the software the company builds resists common attacks.",
        "scope": "It applies to all developers and to all code written for the company or its clients.",
        "rules": [
            "All input from users and other systems is validated, and database queries use parameters rather than text built from input.",
            "Passwords, keys and other secrets are never written into source code; they are kept in the approved secrets store.",
            "Third-party libraries come from trusted sources, are scanned for known vulnerabilities and are kept up to date.",
            "Authentication, authorisation and encryption use the company's standard libraries, not home-made implementations.",
            "Security-relevant code is reviewed by a second developer, and automated security scans run on every build.",
        ],
        "responsibilities": "Developers complete secure coding training every year. Team leads make sure findings from scans and reviews are fixed before release.",
    },
    "Version Control Guidelines": {
        "purpose": "These guidelines describe how source code is stored, branched and released, so that the history of every change is clear.",
        "scope": "They apply to all source code, configuration and infrastructure definitions maintained by the company.",
        "rules": [
            "All code is kept in the company's version control system; nothing is developed only on a personal machine.",
            "Work is done on short-lived branches that are merged into the main branch through reviewed pull requests.",
            "Commit messages say what was changed and why, and refer to the related task.",
            "The main branch is always in a state that can be released, and every release is tagged with a version number.",
            "Large binary files, generated files and secrets are not committed to a repository.",
        ],
        "responsibilities": "Developers follow the branching rules. Repository owners protect the main branch and keep access to the repository up to date.",
    },
}

GENERIC_POLICY = {
    "purpose": "This document sets out the rules the {dept} department follows for the subject named in its title.",
    "scope": "It applies to everyone in the {dept} department.",
    "rules": [
        "Work in this area follows the documented procedure and is recorded so that it can be checked later.",
        "Exceptions need written approval from the department head.",
        "Problems are reported to the department head as soon as they are noticed.",
    ],
    "responsibilities": "The department head owns this document and reviews it every year.",
}


def policy_text(policy_name: str, department: Optional[str], version: Optional[str], effective_date: Any) -> str:
    """Full text of one policy."""
    spec = POLICIES.get(policy_name, GENERIC_POLICY)
    dept = department or "company"
    owner = f"the {department} department" if department else "the company"

    def fill(text: str) -> str:
        return text.replace("{dept}", dept)

    parts = [
        f"This is version {version or '1.0'} of the {policy_name}, effective from {effective_date or 'the date of approval'} and maintained by {owner}.",
        "## Purpose",
        fill(spec["purpose"]),
        "## Scope",
        fill(spec["scope"]),
        "## Rules",
        "\n".join(f"- {fill(rule)}" for rule in spec["rules"]),
        "## Responsibilities",
        fill(spec["responsibilities"]),
        "## Exceptions and review",
        (
            f"Exceptions need written approval from the head of {owner}. "
            "This document is reviewed at least once a year, and the version number changes whenever the content does."
        ),
    ]
    return "\n\n".join(parts)


# ----------------------------------------------------------------------
# Project documents
# ----------------------------------------------------------------------
def _pick(options: List[str], *key: Any) -> str:
    """Stable choice: the same document always gets the same sentence."""
    digest = hashlib.md5("|".join(str(k) for k in key).encode("utf-8")).hexdigest()
    return options[int(digest, 16) % len(options)]


# What each kind of document is for (documents.document_type)
TYPE_PURPOSE = {
    "API Documentation": "It is written for developers who integrate with the system and need to know how its interfaces behave.",
    "Architecture Document": "It records the structure of the solution and the reasons behind the main design decisions.",
    "Business Requirement Document": "It records what the business needs from the project, in terms the client and the delivery team have both agreed.",
    "Deployment Guide": "It is written for the engineers who release and operate the system.",
    "Performance Report": "It reports how the system behaves under load and whether it meets the agreed service levels.",
    "Project Requirement Document": "It lists the requirements the project must meet and how each will be accepted.",
    "Project Status Report": "It gives stakeholders a short, factual picture of progress, risks and next steps.",
    "Security Assessment": "It records the security review of the solution and the actions that follow from it.",
    "Technical Design Document": "It describes how the solution is built, in enough detail for engineers to implement and maintain it.",
    "Testing Report": "It reports what was tested, what was found and whether the release is ready.",
}

# Sections by the focus named at the end of the title ("... Project Security Review")
FOCUS_SECTIONS: Dict[str, List[Dict[str, Any]]] = {
    "Implementation Guide": [
        {"heading": "Implementation approach", "options": [
            "The work is delivered in two-week iterations. Each iteration ends with a demonstration to the client and a short review of what to improve.",
            "Implementation follows the phases agreed in the project plan: foundation, core features, integration and hardening. A phase is closed only when its acceptance criteria are met.",
            "The team builds the solution feature by feature behind feature switches, so that unfinished work can be merged early without affecting users.",
        ]},
        {"heading": "Environment and tools", "options": [
            "Development, test and production environments are created from the same infrastructure definitions, which keeps them consistent. Access to production is limited to the release engineers.",
            "Each developer works in a local environment that mirrors the test environment. Shared test data is refreshed every week and contains no real customer information.",
            "Source code, build pipelines and infrastructure definitions live in the project repository. Every change reaches the main branch through a reviewed pull request.",
        ]},
        {"heading": "Steps for the team", "bullets": [
            ["Set up the development environment from the repository instructions.", "Request access to the project repository, the test environment and the task board."],
            ["Pick up tasks from the board in priority order and keep their status current.", "Break each feature into tasks that can be finished within two days."],
            ["Write automated tests together with the code and run them before opening a pull request.", "Document configuration changes in the same pull request as the code that needs them."],
            ["Demonstrate finished work to the product owner before it is marked as done.", "Raise blockers in the daily meeting so they can be removed quickly."],
        ]},
    ],
    "Security Review": [
        {"heading": "Scope of the review", "options": [
            "The review covered the application, its interfaces, the data it stores and the infrastructure it runs on. Third-party services were reviewed through their published security documentation.",
            "The review looked at authentication, authorisation, data protection, logging and the security of the build and release process.",
            "The review was carried out against the company's Secure Coding Policy and Infrastructure Security Policy, using design documents, code inspection and automated scans.",
        ]},
        {"heading": "Findings", "bullets": [
            ["Access to the application is role-based, and administrator functions need multi-factor authentication.", "User sessions expire after a period of inactivity, and tokens are signed and time-limited."],
            ["Data is encrypted in transit and at rest. Encryption keys are held in the approved secrets store.", "No secrets were found in the source code repository."],
            ["Two medium-severity dependencies with known vulnerabilities were found and scheduled for upgrade.", "Logging of failed sign-in attempts was incomplete and has been added to the backlog as a high-priority task."],
            ["No critical findings remain open at the time of writing.", "Input validation is applied consistently at the service boundary."],
        ]},
        {"heading": "Recommendations", "options": [
            "Upgrade the affected dependencies before the next release, repeat the automated scan, and schedule a penetration test before go-live.",
            "Close the open findings within the current iteration and add security test cases to the regression suite so that they cannot return unnoticed.",
            "Review access rights for the project environments every quarter and repeat this review after any major change to the architecture.",
        ]},
    ],
    "Architecture Overview": [
        {"heading": "Solution overview", "options": [
            "The solution is built as a set of services behind an API gateway. Each service owns its data and communicates with the others through well-defined interfaces.",
            "The solution has three layers: a web front end, an application layer that holds the business rules, and a data layer. The layers are deployed independently.",
            "The solution combines a transactional core with a separate reporting store, so that heavy analysis does not slow down day-to-day operations.",
        ]},
        {"heading": "Main components", "bullets": [
            ["A web application used by the client's staff.", "An API gateway that authenticates requests and routes them to the services."],
            ["Application services that implement the business rules.", "A message queue that decouples long-running work from user requests."],
            ["A relational database for transactional data.", "A document search index for full-text and semantic search."],
            ["Monitoring and central logging for all components.", "Automated pipelines that build, test and deploy each component."],
        ]},
        {"heading": "Design decisions", "options": [
            "Managed cloud services were preferred over self-hosted components to reduce operational effort. The trade-off is a dependency on the provider, which was accepted by the client.",
            "The team chose a relational database because the data is strongly structured and consistency matters more than extreme scale.",
            "Services are stateless so that they can be scaled out under load and replaced without downtime.",
        ]},
    ],
    "Development Specification": [
        {"heading": "Functional scope", "options": [
            "This specification covers the features planned for the current release. Each feature is described by its user stories and acceptance criteria on the task board.",
            "The specification describes the behaviour of the system from the user's point of view, the business rules behind it and the data each feature reads and writes.",
            "Features are grouped into modules. A module can be developed and tested on its own, which lets several developers work in parallel.",
        ]},
        {"heading": "Technical requirements", "bullets": [
            ["Pages respond within two seconds for ninety-five percent of requests under normal load.", "The system supports the number of concurrent users agreed with the client, with room for growth."],
            ["All interfaces are versioned, and changes that break compatibility need a new version.", "Every service exposes health and metrics endpoints for monitoring."],
            ["Code follows the company's Code Review Standards and Secure Coding Policy.", "New code is covered by automated unit and integration tests."],
            ["User-facing text can be translated without code changes.", "The application meets recognised accessibility guidelines."],
        ]},
        {"heading": "Definition of done", "options": [
            "A feature is done when it meets its acceptance criteria, has passed code review and automated tests, is documented, and has been demonstrated to the product owner.",
            "Work is complete when the code is merged, the tests pass in the build pipeline, the feature works in the test environment and the product owner has accepted it.",
            "A task is closed only after review, testing and deployment to the test environment. Known limitations are recorded on the task.",
        ]},
    ],
    "Technical Report": [
        {"heading": "Work completed", "options": [
            "Since the last report the team has completed the planned features for the iteration and reduced the open defect count. Integration with the client's systems is working in the test environment.",
            "The core functions are implemented and tested. Work in the reporting period focused on integration, performance tuning and fixing defects found in testing.",
            "The team finished the technical foundation, including the build pipeline, the environments and monitoring, and has started delivering business features.",
        ]},
        {"heading": "Technical observations", "bullets": [
            ["Response times are within the agreed limits in the test environment.", "The build pipeline runs in under fifteen minutes, which keeps feedback fast."],
            ["Test coverage of the core modules is above the team's target.", "Some older modules lack automated tests and are being covered as they are changed."],
            ["One external interface was less stable than expected, so retries and clearer error handling were added.", "Database queries on the largest tables were tuned after load testing."],
        ]},
        {"heading": "Risks and next steps", "options": [
            "The main risk is the dependency on a client system that is still being changed. The next steps are to agree the final interface, complete end-to-end testing and prepare the release.",
            "Remaining work is on schedule. The next steps are user acceptance testing, a performance test at production scale and the go-live checklist.",
            "Staffing is tight during the holiday period, which may delay lower-priority tasks. The next steps are to finish the open high-priority tasks and plan the following release.",
        ]},
    ],
    "Deployment Documentation": [
        {"heading": "Before you deploy", "bullets": [
            ["Confirm that the build passed all automated tests.", "Confirm that the release has been approved by the product owner."],
            ["Check that database migrations were tested against a copy of production data.", "Take a backup of the production database."],
            ["Announce the deployment window to the client and the support team.", "Make sure a second engineer is available during the deployment."],
        ]},
        {"heading": "Deployment steps", "bullets": [
            ["Start the release pipeline for the approved version.", "Tag the release in the repository and trigger the production pipeline."],
            ["The pipeline applies the database migrations, then deploys the new version alongside the old one.", "The pipeline rolls the new version out gradually, one instance at a time."],
            ["Run the smoke tests against the new version.", "Check the dashboards for errors and response times for fifteen minutes."],
            ["Switch all traffic to the new version and remove the old one.", "Record the deployment in the release log."],
        ]},
        {"heading": "Rollback", "options": [
            "If the smoke tests fail or errors rise, switch traffic back to the previous version, which stays available for one hour after every deployment. Database migrations are written so that the previous version keeps working.",
            "To roll back, redeploy the previous tagged version through the same pipeline. Restore the database backup only if a migration has damaged data, and only with approval from the project manager.",
            "Rollback takes less than ten minutes: the pipeline keeps the previous version ready. After a rollback, open an incident so that the cause is investigated before the next attempt.",
        ]},
    ],
    "Testing Strategy": [
        {"heading": "Test levels", "bullets": [
            ["Unit tests, written by developers, run on every change.", "Integration tests check that services and the database work together."],
            ["End-to-end tests cover the most important user journeys.", "Regression tests run automatically every night."],
            ["Performance tests are run before every major release.", "Security tests include automated scans and a penetration test before go-live."],
            ["User acceptance testing is carried out by the client before each release.", "Exploratory testing is planned for every new feature."],
        ]},
        {"heading": "Entry and exit criteria", "options": [
            "Testing of a feature starts when it is deployed to the test environment with its acceptance criteria. A release may go ahead when all planned tests have run and no critical or high-severity defect is open.",
            "A build enters system testing only after it passes the automated checks. It leaves testing when the agreed test cases have passed and the remaining defects have been accepted by the product owner.",
            "The exit criteria for a release are: all critical journeys pass, test coverage meets the target, and performance is within the agreed limits.",
        ]},
        {"heading": "Defect handling", "options": [
            "Defects are recorded on the task board with steps to reproduce, a severity and a screenshot or log. Critical defects are fixed first and retested by someone other than the developer who fixed them.",
            "Every defect has a severity and an owner. The team reviews open defects twice a week, and defect trends are reported to the project manager.",
            "A fixed defect is closed only after it has been retested and a regression test has been added where one was missing.",
        ]},
    ],
}

DEFAULT_FOCUS = "Technical Report"


def _focus_of(title: str) -> str:
    for focus in FOCUS_SECTIONS:
        if (title or "").strip().endswith(focus):
            return focus
    return DEFAULT_FOCUS


def document_text(doc: Dict[str, Any]) -> str:
    """
    Full text of one project document.

    `doc` holds: document_id, title, document_type, and (when known) project_name,
    project_code, project_description, project_status, project_priority, start_date,
    end_date, client, department, manager, author, created_on.
    """
    doc_id = doc.get("document_id")
    title = doc.get("title") or "Project document"
    doc_type = doc.get("document_type") or "Project document"
    project = doc.get("project_name") or "the project"
    focus = _focus_of(title)

    facts = []
    if doc.get("project_name"):
        code = f" ({doc['project_code']})" if doc.get("project_code") else ""
        facts.append(f"- **Project:** {doc['project_name']}{code}")
    if doc.get("client"):
        facts.append(f"- **Client:** {doc['client']}")
    if doc.get("department"):
        facts.append(f"- **Department:** {doc['department']}")
    if doc.get("manager"):
        facts.append(f"- **Project manager:** {doc['manager']}")
    if doc.get("project_status"):
        priority = f", priority {doc['project_priority']}" if doc.get("project_priority") else ""
        facts.append(f"- **Project status:** {doc['project_status']}{priority}")
    if doc.get("start_date") or doc.get("end_date"):
        facts.append(f"- **Timeline:** {doc.get('start_date') or 'not set'} to {doc.get('end_date') or 'not set'}")
    facts.append(f"- **Document type:** {doc_type}")
    if doc.get("author"):
        on = f" on {doc['created_on']}" if doc.get("created_on") else ""
        facts.append(f"- **Prepared by:** {doc['author']}{on}")

    description = (doc.get("project_description") or "").strip()
    about = f" {description}" if description else ""
    client_part = f" for {doc['client']}" if doc.get("client") else ""
    summary = (
        f"This {doc_type.lower()} belongs to {project}, which the company is delivering{client_part}.{about} "
        f"{TYPE_PURPOSE.get(doc_type, 'It is part of the project documentation.')} "
        f"This document focuses on the {focus.lower()}."
    )

    parts = ["## Summary", summary, "## Project details", "\n".join(facts)]
    for section in FOCUS_SECTIONS[focus]:
        parts.append(f"## {section['heading']}")
        if "bullets" in section:
            lines = [f"- {_pick(pair, doc_id, section['heading'], idx)}" for idx, pair in enumerate(section["bullets"])]
            parts.append("\n".join(lines))
        else:
            parts.append(_pick(section["options"], doc_id, section["heading"]))

    parts.append("## Document control")
    parts.append(
        "This is an internal document. It is kept in the project repository, and changes are approved by the project manager. "
        "Questions about its content go to the author."
    )
    return "\n\n".join(parts)
