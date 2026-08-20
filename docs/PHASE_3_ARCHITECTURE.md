# Enterprise AI Operating System — Phase 3 Architecture

The platform uses a React operations console and FastAPI control plane. PostgreSQL is the system of record; Qdrant provides retrieval; Neo4j represents enterprise relationships; Redis is reserved for cache/session workloads.

## Control flow

`User → JWT/RBAC → prompt safety → workflow orchestrator → agent steps → approval gate → audit and agent logs → analytics/monitoring`

Workflow types are HR request, project risk, and document intake. Every run is persisted in `workflow_runs`; each agent step is persisted in `agent_logs`; human decisions are persisted in `approvals` and `audit_logs`.

## Security design

- Role checks guard operational endpoints; Admin retains an explicit break-glass path.
- JWT access tokens protect interactive APIs; an environment API-key slot supports service integrations.
- Input is checked for common prompt-injection patterns before agents execute.
- Agent log inputs mask email, telephone, and national-ID-looking values.
- Security response headers and request latency metrics are emitted on every API response.

Production hardening still requires TLS at the ingress, secret-manager injection, restrictive CORS origins, database backups, and centralized immutable log shipping.
