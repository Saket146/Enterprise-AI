-- Phase 3 workflow approvals and durable evaluation history
CREATE TABLE IF NOT EXISTS approvals (
  approval_id SERIAL PRIMARY KEY,
  workflow_id INTEGER NOT NULL REFERENCES workflow_runs(workflow_id),
  requested_by INTEGER REFERENCES employees(employee_id),
  approver_role VARCHAR(100) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  decision_note TEXT,
  decided_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS evaluation_runs (
  evaluation_id SERIAL PRIMARY KEY,
  suite_name VARCHAR(100) NOT NULL,
  metric_name VARCHAR(100) NOT NULL,
  score DECIMAL(6,3) NOT NULL,
  sample_count INTEGER NOT NULL,
  details TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON agent_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
