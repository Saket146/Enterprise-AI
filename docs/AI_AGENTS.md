# AI agent documentation

| Agent | Workflow | Responsibility | Guardrail |
|---|---|---|---|
| HR Agent | HR request | Validates employee request context | Input safety inspection |
| Policy Agent | HR request | Applies enterprise policy controls | Policy/approval trace |
| Engineering Agent | Project risk | Assesses technical impact | Audited recommendation |
| Project Manager Agent | Project risk | Produces mitigation recommendation | Human accountable owner |
| Classification Agent | Document intake | Applies type and sensitivity label | Sensitive-data masking |
| Knowledge Indexer | Document intake | Queues approved content for RAG indexing | Approval gate |

The current orchestrator uses deterministic, auditable steps as a production-safe baseline. A model provider can be enabled behind the same controls through the existing LLM service; agent output must remain structured, policy-scoped, logged, and approval-gated for consequential actions.
