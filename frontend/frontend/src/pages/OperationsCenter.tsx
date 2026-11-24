import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, CheckCircle2, ClipboardCheck, ClipboardList, Database, FlaskConical, RefreshCw,
  Send, ServerCog, ShieldCheck, XCircle,
} from 'lucide-react';
import { api } from '../services/api';

interface RequestType { type: string; label: string; description: string; needs_approval: boolean; needs_document?: boolean; approver_label: string | null; }
interface DocumentChoice { document_id: number; title: string; document_type: string; my_access?: string; }
interface RequestItem {
  id: number; type: string; type_label: string; title: string; details: string; status: string; status_label: string;
  requested_by: string; created_at: string; approver: string | null; decision_note: string | null; outcome: string | null;
}
interface ApprovalItem {
  approval_id: number; workflow_id: number; type_label: string; title: string; details: string;
  requested_by: string; created_at: string; own_request: boolean;
}
interface Notice { kind: 'ok' | 'error'; text: string; }

const STORES: { key: string; name: string; purpose: string }[] = [
  { key: 'postgresql', name: 'PostgreSQL', purpose: 'Company data. Required.' },
  { key: 'redis', name: 'Redis', purpose: 'Chat memory. Optional.' },
  { key: 'qdrant', name: 'Qdrant', purpose: 'Semantic document search. Optional.' },
  { key: 'neo4j', name: 'Neo4j', purpose: 'Organisation graph. Optional.' },
];

const formatDate = (iso: string | null | undefined): string => {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
};

const statusBadge = (status: string): string => {
  if (status === 'approved' || status === 'completed') return 'badge badge-success';
  if (status === 'rejected') return 'badge badge-danger';
  return 'badge badge-warning';
};

const percent = (value: number | undefined): string => (value === undefined || value === null ? '-' : `${Math.round(value * 100)}%`);

export const OperationsCenter: React.FC = () => {
  const user = useMemo(() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch { return {}; }
  }, []);

  const [permissions, setPermissions] = useState<string[] | null>(null);
  const [role, setRole] = useState<string>(user.role || '');
  const can = useCallback((p: string) => (permissions || []).includes(p), [permissions]);

  // System status
  const [stores, setStores] = useState<Record<string, { status: string }> | null>(null);
  const [llm, setLlm] = useState<{ provider: string; model: string | null; state: string; last_error?: string | null; avg_call_seconds?: number | null } | null>(null);
  const [llmTesting, setLlmTesting] = useState(false);
  const [llmNotice, setLlmNotice] = useState<Notice | null>(null);
  const [storesError, setStoresError] = useState('');

  // Requests
  const [types, setTypes] = useState<RequestType[]>([]);
  const [requestType, setRequestType] = useState('hr_request');
  const [title, setTitle] = useState('');
  const [details, setDetails] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitNotice, setSubmitNotice] = useState<Notice | null>(null);
  // Document picker for "Access to a document" requests
  const [docSearch, setDocSearch] = useState('');
  const [docResults, setDocResults] = useState<DocumentChoice[]>([]);
  const [chosenDoc, setChosenDoc] = useState<DocumentChoice | null>(null);
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [requestScope, setRequestScope] = useState<'mine' | 'all'>('mine');
  const [requestsError, setRequestsError] = useState('');

  // Approvals
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [decidingId, setDecidingId] = useState<number | null>(null);
  const [approvalNotice, setApprovalNotice] = useState<Notice | null>(null);

  // Monitoring, quality check, data sync
  const [monitoring, setMonitoring] = useState<any>(null);
  const [monitoringError, setMonitoringError] = useState('');
  const [evaluation, setEvaluation] = useState<any>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [evaluationError, setEvaluationError] = useState('');
  const [lastRuns, setLastRuns] = useState<any[]>([]);
  const [syncing, setSyncing] = useState<'' | 'qdrant' | 'neo4j'>('');
  const [syncNotice, setSyncNotice] = useState<Notice | null>(null);
  const [confirmGraph, setConfirmGraph] = useState(false);

  const canApprove = can('approvals:hr') || can('approvals:ai') || can('approvals:document_access');
  const canSeeAll = can('system:monitor') || can('projects:read_all');
  const canMonitor = can('system:monitor');
  const canEvaluate = can('system:evaluate');
  const canIngest = can('system:ingest');

  const loadStores = useCallback(async () => {
    try {
      const res = await api.system.dependencies();
      setStores(res.dependencies || {});
      setLlm(res.language_model || null);
      setStoresError('');
    } catch (err: any) {
      setStoresError(err?.message || 'Could not check the data stores.');
    }
  }, []);

  const loadRequests = useCallback(async (scope: 'mine' | 'all') => {
    try {
      setRequests(await api.workflows.requests(scope));
      setRequestsError('');
    } catch (err: any) {
      setRequestsError(err?.message || 'Could not load requests.');
    }
  }, []);

  const loadApprovals = useCallback(async () => {
    try { setApprovals(await api.workflows.approvals()); } catch { setApprovals([]); }
  }, []);

  const loadMonitoring = useCallback(async () => {
    try {
      setMonitoring(await api.monitoring.dashboard());
      setMonitoringError('');
    } catch (err: any) {
      setMonitoringError(err?.message || 'Could not load AI activity.');
    }
  }, []);

  // 1. Who am I allowed to be here? Everything else depends on the answer.
  useEffect(() => {
    api.auth.getPermissions()
      .then((res) => { setPermissions(res.permissions || []); setRole(res.role || ''); })
      .catch(() => setPermissions([]));
    api.workflows.types().then((res) => setTypes(res || [])).catch(() => setTypes([]));
    loadStores();
  }, [loadStores]);

  // 2. Load each section the role can use. A section that fails never blocks the others.
  useEffect(() => {
    if (permissions === null) return;
    loadRequests(requestScope);
    if (canApprove) loadApprovals();
    if (canMonitor) loadMonitoring();
    if (canEvaluate) api.evaluations.history().then((res) => setLastRuns(res || [])).catch(() => setLastRuns([]));
  }, [permissions, requestScope, canApprove, canMonitor, canEvaluate, loadRequests, loadApprovals, loadMonitoring]);

  const selectedType = types.find((t) => t.type === requestType);
  const needsDocument = Boolean(selectedType?.needs_document);

  // Select the first available request type once the list has loaded
  useEffect(() => {
    if (types.length > 0 && !types.some((t) => t.type === requestType)) setRequestType(types[0].type);
  }, [types, requestType]);

  // Find documents by title while the user types
  useEffect(() => {
    if (!needsDocument || chosenDoc || docSearch.trim().length < 2) { setDocResults([]); return; }
    let cancelled = false;
    const timer = setTimeout(() => {
      api.knowledge.listDocuments({ search: docSearch.trim(), limit: 8 })
        .then((res) => { if (!cancelled) setDocResults(res || []); })
        .catch(() => { if (!cancelled) setDocResults([]); });
    }, 250);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [needsDocument, chosenDoc, docSearch]);

  const submitRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (needsDocument) {
      if (!chosenDoc) { setSubmitNotice({ kind: 'error', text: 'Search for the document and choose it from the list first.' }); return; }
      if (details.trim().length < 3) { setSubmitNotice({ kind: 'error', text: 'Please say briefly why you need this document.' }); return; }
    } else if (title.trim().length < 3 || details.trim().length < 3) {
      setSubmitNotice({ kind: 'error', text: 'Please give the request a title and a short description (at least 3 characters each).' });
      return;
    }
    setSubmitting(true);
    setSubmitNotice(null);
    try {
      const res = await api.workflows.run(needsDocument && chosenDoc
        ? { workflow_type: requestType, title: '', payload: details.trim(), document_id: chosenDoc.document_id }
        : { workflow_type: requestType, title: title.trim(), payload: details.trim() });
      setSubmitNotice({ kind: 'ok', text: `Request #${res.workflow_id} submitted. ${res.message}` });
      setTitle('');
      setDetails('');
      setChosenDoc(null);
      setDocSearch('');
      loadRequests(requestScope);
      if (canApprove) loadApprovals();
    } catch (err: any) {
      setSubmitNotice({ kind: 'error', text: err?.message || 'The request could not be submitted.' });
    } finally {
      setSubmitting(false);
    }
  };

  const decide = async (item: ApprovalItem, approved: boolean) => {
    setDecidingId(item.approval_id);
    setApprovalNotice(null);
    try {
      await api.workflows.decide(item.approval_id, approved, (notes[item.approval_id] || '').trim());
      setApprovalNotice({ kind: 'ok', text: `"${item.title}" was ${approved ? 'approved' : 'rejected'}.` });
      loadApprovals();
      loadRequests(requestScope);
    } catch (err: any) {
      setApprovalNotice({ kind: 'error', text: err?.message || 'The decision could not be saved.' });
    } finally {
      setDecidingId(null);
    }
  };

  const runEvaluation = async () => {
    setEvaluating(true);
    setEvaluationError('');
    try {
      setEvaluation(await api.evaluations.run());
      api.evaluations.history().then((res) => setLastRuns(res || [])).catch(() => undefined);
    } catch (err: any) {
      setEvaluationError(err?.message || 'The quality check could not be run.');
    } finally {
      setEvaluating(false);
    }
  };

  const sync = async (target: 'qdrant' | 'neo4j') => {
    setConfirmGraph(false);
    setSyncing(target);
    setSyncNotice(null);
    try {
      const res = target === 'qdrant' ? await api.ingestion.syncQdrant() : await api.ingestion.syncNeo4j();
      const counts = res?.details ? Object.entries(res.details).map(([k, v]) => `${v} ${k}`).join(', ') : '';
      setSyncNotice({ kind: 'ok', text: `${target === 'qdrant' ? 'Document search index' : 'Organisation graph'} rebuilt${counts ? `: ${counts}` : ''}.` });
      loadStores();
    } catch (err: any) {
      setSyncNotice({ kind: 'error', text: err?.message || 'The rebuild failed.' });
    } finally {
      setSyncing('');
    }
  };

  const storeOnline = (key: string) => stores?.[key]?.status === 'online';

  const testLanguageModel = async () => {
    setLlmTesting(true);
    setLlmNotice(null);
    try {
      const res = await api.monitoring.testLlm();
      setLlm({ provider: res.provider, model: res.model, state: res.state, last_error: res.last_error, avg_call_seconds: res.avg_call_seconds });
      setLlmNotice({ kind: res.ok ? 'ok' : 'error', text: res.ok ? `${res.model} answered. The assistant is using it.` : res.message });
    } catch (err: any) {
      setLlmNotice({ kind: 'error', text: err?.message || 'The test could not be run.' });
    } finally {
      setLlmTesting(false);
    }
  };

  const LLM_STATES: Record<string, { label: string; cls: string }> = {
    working: { label: 'Working', cls: 'ok' },
    failing: { label: 'Failing', cls: 'bad' },
    untested: { label: 'Not used yet', cls: '' },
    not_configured: { label: 'Not configured', cls: 'bad' },
  };

  return (
    <div className="animated-fade-in oc">
      <p className="oc-intro">
        Submit requests, decide approvals and check the health of the AI system.
        You see the sections your role{role ? ` (${role})` : ''} can use.
      </p>

      {/* ---------------- System status ---------------- */}
      <section className="glass-card oc-section">
        <div className="oc-section-head">
          <h3><ServerCog size={18} /> System status</h3>
          <button className="btn btn-secondary oc-small-btn" onClick={loadStores}><RefreshCw size={14} /> Refresh</button>
        </div>
        <p className="oc-help">The four data stores and the language model behind the application. Only PostgreSQL is required; the assistant keeps answering from the database when the others are offline.</p>
        {storesError && <div className="oc-notice error">{storesError}</div>}
        <div className="oc-stores">
          {STORES.map((store) => {
            const known = stores !== null;
            const online = storeOnline(store.key);
            return (
              <div key={store.key} className={`oc-store ${known ? (online ? 'online' : 'offline') : ''}`}>
                <div className="oc-store-top">
                  <span className="oc-store-name"><Database size={14} /> {store.name}</span>
                  <span className={`oc-pill ${known ? (online ? 'ok' : 'bad') : ''}`}>{known ? (online ? 'Online' : 'Offline') : 'Checking...'}</span>
                </div>
                <div className="oc-store-purpose">{store.purpose}</div>
              </div>
            );
          })}
          {llm && (
            <div className={`oc-store ${llm.state === 'working' ? 'online' : llm.state === 'untested' ? '' : 'offline'}`}>
              <div className="oc-store-top">
                <span className="oc-store-name"><ServerCog size={14} /> Language model</span>
                <span className={`oc-pill ${LLM_STATES[llm.state]?.cls || ''}`}>{LLM_STATES[llm.state]?.label || llm.state}</span>
              </div>
              <div className="oc-store-purpose">
                {llm.provider === 'mock'
                  ? 'None configured: answers use the built-in writer.'
                  : `${llm.provider === 'gemini' ? 'Gemini' : 'OpenAI'} · ${llm.model === 'auto' ? 'newest stable Flash' : llm.model}${llm.avg_call_seconds ? ` · about ${llm.avg_call_seconds} s per call` : ''}`}
              </div>
              {canMonitor && llm.provider !== 'mock' && (
                <button className="oc-link" style={{ marginTop: 6, padding: 0 }} onClick={testLanguageModel} disabled={llmTesting}>
                  {llmTesting ? 'Testing...' : 'Test connection'}
                </button>
              )}
            </div>
          )}
        </div>
        {llmNotice && <div className={`oc-notice ${llmNotice.kind}`}>{llmNotice.text}</div>}
      </section>

      {/* ---------------- Approvals ---------------- */}
      {canApprove && (
        <section className="glass-card oc-section">
          <div className="oc-section-head">
            <h3><ClipboardCheck size={18} /> Waiting for your decision <span className="oc-count">{approvals.length}</span></h3>
          </div>
          <p className="oc-help">Requests from employees that your role is responsible for approving. You cannot decide a request you submitted yourself.</p>
          {approvalNotice && <div className={`oc-notice ${approvalNotice.kind}`}>{approvalNotice.text}</div>}
          {approvals.length === 0 ? (
            <p className="oc-empty">Nothing is waiting for you.</p>
          ) : (
            <div className="oc-approvals">
              {approvals.map((item) => (
                <div key={item.approval_id} className="oc-approval">
                  <div className="oc-approval-head">
                    <strong>{item.title}</strong>
                    <span className="badge badge-warning">{item.type_label}</span>
                  </div>
                  <div className="oc-meta">From {item.requested_by} · {formatDate(item.created_at)}</div>
                  {item.details && <p className="oc-approval-details">{item.details}</p>}
                  {item.own_request ? (
                    <p className="oc-empty">This is your own request, so someone else has to decide it.</p>
                  ) : (
                    <div className="oc-approval-actions">
                      <input
                        className="input-field"
                        type="text"
                        placeholder="Note for the requester (optional)"
                        maxLength={500}
                        value={notes[item.approval_id] || ''}
                        onChange={(e) => setNotes((prev) => ({ ...prev, [item.approval_id]: e.target.value }))}
                      />
                      <button className="btn btn-primary" disabled={decidingId === item.approval_id} onClick={() => decide(item, true)}>
                        <CheckCircle2 size={15} /> Approve
                      </button>
                      <button className="btn oc-btn-danger" disabled={decidingId === item.approval_id} onClick={() => decide(item, false)}>
                        <XCircle size={15} /> Reject
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ---------------- Requests ---------------- */}
      <div className="oc-two">
        <section className="glass-card oc-section">
          <div className="oc-section-head"><h3><Send size={18} /> Submit a request</h3></div>
          <p className="oc-help">Your text is screened by the safety filter, personal data such as phone numbers is masked, and every step is recorded in the audit log.</p>
          <form onSubmit={submitRequest} className="oc-form">
            <div className="oc-types">
              {types.map((t) => (
                <label key={t.type} className={`oc-type ${requestType === t.type ? 'selected' : ''}`}>
                  <input type="radio" name="request-type" value={t.type} checked={requestType === t.type} onChange={() => setRequestType(t.type)} />
                  <span>
                    <strong>{t.label}</strong>
                    <small>{t.description}</small>
                  </span>
                </label>
              ))}
            </div>
            {needsDocument ? (
              <>
                <label className="form-label" htmlFor="oc-doc">Document</label>
                {chosenDoc ? (
                  <div className="oc-doc-chosen">
                    <span><strong>{chosenDoc.title}</strong> <span className="oc-meta">· {chosenDoc.document_type}</span></span>
                    <button type="button" className="oc-link" onClick={() => { setChosenDoc(null); setDocSearch(''); }}>Change</button>
                  </div>
                ) : (
                  <>
                    <input id="oc-doc" className="input-field" type="text" placeholder="Type part of the document title" value={docSearch} onChange={(e) => setDocSearch(e.target.value)} />
                    {docResults.length > 0 && (
                      <div className="oc-doc-results">
                        {docResults.map((doc) => (
                          <button
                            type="button"
                            key={doc.document_id}
                            disabled={doc.my_access !== 'request'}
                            onClick={() => setChosenDoc(doc)}
                          >
                            {doc.title}
                            <small>
                              {doc.document_type}
                              {doc.my_access === 'open' ? ' · you can already open this' : doc.my_access === 'pending' ? ' · access already requested' : ''}
                            </small>
                          </button>
                        ))}
                      </div>
                    )}
                    {docSearch.trim().length >= 2 && docResults.length === 0 && <div className="oc-meta" style={{ marginTop: 6 }}>No document title matches yet.</div>}
                  </>
                )}
              </>
            ) : (
              <>
                <label className="form-label" htmlFor="oc-title">Title</label>
                <input id="oc-title" className="input-field" type="text" maxLength={200} placeholder="e.g. Three days of leave next week" value={title} onChange={(e) => setTitle(e.target.value)} />
              </>
            )}
            <label className="form-label" htmlFor="oc-details" style={{ marginTop: 12 }}>{needsDocument ? 'Why do you need it?' : 'Details'}</label>
            <textarea id="oc-details" className="input-field oc-textarea" maxLength={4000} placeholder={needsDocument ? 'e.g. I am joining this project and need the deployment steps.' : 'Describe what you need and why.'} value={details} onChange={(e) => setDetails(e.target.value)} />
            {submitNotice && <div className={`oc-notice ${submitNotice.kind}`}>{submitNotice.text}</div>}
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              <Send size={15} /> {submitting ? 'Submitting...' : selectedType?.needs_approval ? 'Submit for approval' : 'Submit'}
            </button>
          </form>
        </section>

        <section className="glass-card oc-section">
          <div className="oc-section-head">
            <h3><ClipboardList size={18} /> {requestScope === 'mine' ? 'My requests' : 'All requests'}</h3>
            {canSeeAll && (
              <div className="oc-toggle">
                <button className={requestScope === 'mine' ? 'on' : ''} onClick={() => setRequestScope('mine')}>Mine</button>
                <button className={requestScope === 'all' ? 'on' : ''} onClick={() => setRequestScope('all')}>Everyone's</button>
              </div>
            )}
          </div>
          <p className="oc-help">What you submitted and what happened to it.</p>
          {requestsError && <div className="oc-notice error">{requestsError}</div>}
          {requests.length === 0 ? (
            <p className="oc-empty">No requests yet.</p>
          ) : (
            <div className="oc-requests">
              {requests.map((r) => (
                <div key={r.id} className="oc-request">
                  <div className="oc-request-head">
                    <strong>{r.title}</strong>
                    <span className={statusBadge(r.status)}>{r.status_label}</span>
                  </div>
                  <div className="oc-meta">
                    #{r.id} · {r.type_label} · {formatDate(r.created_at)}{requestScope === 'all' ? ` · ${r.requested_by}` : ''}
                  </div>
                  {r.outcome && <div className="oc-outcome">{r.outcome}{r.decision_note ? ` Note: ${r.decision_note}` : ''}</div>}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* ---------------- AI activity ---------------- */}
      {canMonitor && (
        <section className="glass-card oc-section">
          <div className="oc-section-head">
            <h3><Activity size={18} /> AI activity</h3>
            <button className="btn btn-secondary oc-small-btn" onClick={loadMonitoring}><RefreshCw size={14} /> Refresh</button>
          </div>
          <p className="oc-help">How the assistant is being used and what the guardrails stopped. Response time and request counts are measured since the backend was last started.</p>
          {monitoringError && <div className="oc-notice error">{monitoringError}</div>}
          {monitoring && (
            <>
              <div className="oc-tiles">
                <div className="oc-tile"><span>Questions answered</span><strong>{monitoring.questions_answered ?? 0}</strong></div>
                <div className="oc-tile"><span>Unsafe prompts blocked</span><strong>{monitoring.blocked_prompts ?? 0}</strong></div>
                <div className="oc-tile"><span>Access denied by role</span><strong>{monitoring.access_denials ?? 0}</strong></div>
                <div className="oc-tile"><span>Average response time</span><strong>{monitoring.avg_latency_ms ?? 0} ms</strong></div>
                <div className="oc-tile"><span>API requests / failed</span><strong>{monitoring.requests ?? 0} / {monitoring.failures ?? 0}</strong></div>
              </div>
              <div className="oc-two inner">
                <div>
                  <h4>Work done by each agent</h4>
                  {(monitoring.agent_traces || []).length === 0 ? <p className="oc-empty">No agent runs recorded yet.</p> : (
                    <table className="oc-table">
                      <thead><tr><th>Agent</th><th>Runs</th><th>Avg. time</th></tr></thead>
                      <tbody>
                        {(monitoring.agent_traces || []).slice(0, 12).map((t: any) => (
                          <tr key={t.agent}><td>{t.agent}</td><td>{t.executions}</td><td>{t.avg_ms} ms</td></tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
                <div>
                  <h4>Latest guardrail events</h4>
                  {(monitoring.recent_security_events || []).length === 0 ? <p className="oc-empty">No guardrail events recorded.</p> : (
                    <div className="oc-events">
                      {(monitoring.recent_security_events || []).map((ev: any, idx: number) => (
                        <div key={idx} className="oc-event">
                          <div><ShieldCheck size={13} /> <strong>{ev.event}</strong> <span className="oc-meta">· employee #{ev.employee_id} · {formatDate(ev.when)}</span></div>
                          {ev.details && <div className="oc-meta">{ev.details}</div>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </section>
      )}

      {/* ---------------- Quality check ---------------- */}
      {canEvaluate && (
        <section className="glass-card oc-section">
          <div className="oc-section-head">
            <h3><FlaskConical size={18} /> Assistant quality check</h3>
            <button className="btn btn-primary oc-small-btn" onClick={runEvaluation} disabled={evaluating}>
              <CheckCircle2 size={14} /> {evaluating ? 'Running...' : 'Run quality check'}
            </button>
          </div>
          <p className="oc-help">
            Sends a fixed set of test questions through the real assistant, using your own access rights, and checks that normal questions are answered correctly and unsafe prompts are blocked.
            {lastRuns.length > 0 && ` Last run: ${percent(lastRuns[0].score)} passed on ${formatDate(lastRuns[0].created_at)}.`}
          </p>
          {evaluationError && <div className="oc-notice error">{evaluationError}</div>}
          {evaluation && (
            <>
              <div className="oc-tiles">
                <div className="oc-tile"><span>Tests passed</span><strong>{evaluation.passed} of {evaluation.dataset_cases}</strong></div>
                <div className="oc-tile"><span>Questions answered correctly</span><strong>{percent(evaluation.metrics?.answer_accuracy)}</strong></div>
                <div className="oc-tile"><span>Unsafe prompts blocked</span><strong>{percent(evaluation.metrics?.guardrail_block_rate)}</strong></div>
                <div className="oc-tile"><span>Answers backed by data</span><strong>{percent(evaluation.metrics?.grounding_score)}</strong></div>
                <div className="oc-tile"><span>Average response time</span><strong>{evaluation.metrics?.avg_latency_ms} ms</strong></div>
              </div>
              <table className="oc-table">
                <thead><tr><th>Test question</th><th>Expected</th><th>Result</th><th>Time</th></tr></thead>
                <tbody>
                  {(evaluation.cases || []).map((c: any) => (
                    <tr key={c.id}>
                      <td><div>{c.query}</div><div className="oc-meta">{c.category}</div></td>
                      <td>{c.expected === 'blocked' ? 'Blocked' : 'Answered'}</td>
                      <td>
                        <span className={c.passed ? 'badge badge-success' : 'badge badge-danger'}>{c.passed ? 'Passed' : 'Failed'}</span>
                        <div className="oc-meta">{c.detail}</div>
                      </td>
                      <td>{c.latency_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </section>
      )}

      {/* ---------------- Data sync ---------------- */}
      {canIngest && (
        <section className="glass-card oc-section">
          <div className="oc-section-head"><h3><Database size={18} /> Search index and graph</h3></div>
          <p className="oc-help">Qdrant and Neo4j hold copies of the PostgreSQL data. Rebuild them after the company data changes. Each rebuild can take a few minutes.</p>
          {syncNotice && <div className={`oc-notice ${syncNotice.kind}`}>{syncNotice.text}</div>}
          <div className="oc-sync">
            <div>
              <strong>Document search index (Qdrant)</strong>
              <div className="oc-meta">{storeOnline('qdrant') ? 'Re-indexes documents, policies, emails, meetings and chats.' : 'Qdrant is offline. Start it to enable this.'}</div>
            </div>
            <button className="btn btn-secondary" disabled={syncing !== '' || !storeOnline('qdrant')} onClick={() => sync('qdrant')}>
              <RefreshCw size={14} /> {syncing === 'qdrant' ? 'Rebuilding...' : 'Rebuild index'}
            </button>
          </div>
          <div className="oc-sync">
            <div>
              <strong>Organisation graph (Neo4j)</strong>
              <div className="oc-meta">{storeOnline('neo4j') ? 'Deletes everything in the Neo4j database, then loads employees, departments, projects and clients again.' : 'Neo4j is offline. Start it to enable this.'}</div>
            </div>
            {confirmGraph ? (
              <div className="oc-confirm">
                <span>Delete and rebuild the graph?</span>
                <button className="btn oc-btn-danger" onClick={() => sync('neo4j')}>Yes, rebuild</button>
                <button className="btn btn-secondary" onClick={() => setConfirmGraph(false)}>Cancel</button>
              </div>
            ) : (
              <button className="btn btn-secondary" disabled={syncing !== '' || !storeOnline('neo4j')} onClick={() => setConfirmGraph(true)}>
                <RefreshCw size={14} /> {syncing === 'neo4j' ? 'Rebuilding...' : 'Rebuild graph'}
              </button>
            )}
          </div>
        </section>
      )}
    </div>
  );
};
export default OperationsCenter;
