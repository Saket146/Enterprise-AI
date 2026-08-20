# API documentation

Interactive OpenAPI documentation is served at `/docs` when the backend is running.

| Area | Endpoint | Purpose |
|---|---|---|
| Workflow | `POST /api/workflows/run` | Start `hr_request`, `project_risk`, or `document_intake` workflow |
| Workflow | `GET /api/workflows/runs` | Recent workflow state |
| Approval | `GET/POST /api/workflows/approvals` | Review and decide human approval gates |
| Analytics | `GET /api/analytics/overview` | Project, employee, client, and AI measures |
| Monitoring | `GET /api/monitoring/dashboard` | Latency, failure, token, trace, and audit metrics |
| Evaluation | `POST /api/evaluations/run` | Execute enterprise evaluation dataset |
| Evaluation | `GET /api/evaluations/history` | Evaluation history |

All endpoints except `/`, `/health`, and authentication require `Authorization: Bearer <JWT>`. Operational endpoints require an appropriate role, typically AI Administrator, Project Manager, HR Manager, or Admin.
