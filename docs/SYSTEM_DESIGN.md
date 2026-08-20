# System design

## Components

| Component | Responsibility | Scale boundary |
|---|---|---|
| React/Nginx frontend | Authenticated enterprise console | Stateless horizontal replicas |
| FastAPI backend | APIs, authorization, orchestration | Stateless horizontal replicas |
| PostgreSQL | Transactional, audit, workflow state | HA database / backups |
| Qdrant | Semantic retrieval | Persisted vector volume / cluster |
| Neo4j | Enterprise relationship graph | Persisted graph volume / cluster |
| Redis | Cache and session-adjacent acceleration | Managed Redis / replicated cache |

## Reliability model

Workflow state is written before an approval gate is exposed. Agent steps are independently recorded in `agent_logs`; user and approval actions go to `audit_logs`. Requests emit duration/error metrics, while evaluation runs create a durable quality trend. Production workers can safely be separated from the API process once queue-backed asynchronous execution is introduced; the API contracts and persisted state are designed for that change.

## Data boundaries

Sensitive values are masked before agent-log persistence. Retrieval and graph stores receive only approved/indexed content. PostgreSQL remains authoritative for access, workflow, approval, and audit records. Human approval is required for HR and sensitive document workflows.
