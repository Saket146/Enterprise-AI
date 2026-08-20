# Database documentation

PostgreSQL remains the transactional system of record. Phase 3 adds:

- `approvals`: durable human approval queue linked to `workflow_runs`.
- `evaluation_runs`: historical retrieval, generation, agent, and system evaluation scores.

Existing operational tables used by the new services are `workflow_runs`, `agent_logs`, and `audit_logs`. Indexes on agent-log creation time and audit timestamps support operations dashboards and investigations. Qdrant holds retrieval vectors, Neo4j holds relationship graph data, and Redis supports cache/session use cases; none replaces PostgreSQL audit history.
