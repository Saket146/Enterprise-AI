import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle2, Play, ShieldCheck, Workflow } from 'lucide-react';
import { api } from '../services/api';

export const OperationsCenter: React.FC = () => {
  const [analytics, setAnalytics] = useState<any>(); const [monitoring, setMonitoring] = useState<any>();
  const [runs, setRuns] = useState<any[]>([]); const [message, setMessage] = useState('');
  const refresh = async () => { try { const [a, m, r] = await Promise.all([api.analytics.overview(), api.monitoring.dashboard(), api.workflows.runs()]); setAnalytics(a); setMonitoring(m); setRuns(r); } catch (e: any) { setMessage(e.message || 'Unable to load operations data.'); } };
  useEffect(() => { refresh(); }, []);
  const launch = async (workflow_type: string) => { try { const result = await api.workflows.run({ workflow_type, title: `${workflow_type.replace('_', ' ')} request`, payload: 'Enterprise request submitted for policy-aware processing.', requires_approval: workflow_type !== 'project_risk' }); setMessage(`Workflow #${result.workflow_id}: ${result.status}`); refresh(); } catch (e: any) { setMessage(e.message); } };
  const evaluate = async () => { try { const r = await api.evaluations.run(); setMessage(`Evaluation suite ran across ${r.dataset_cases} enterprise cases.`); } catch (e: any) { setMessage(e.message); } };
  const cards = [['Project risks', analytics?.projects?.risks ?? '—'], ['AI success rate', `${analytics?.ai?.success_rate ?? '—'}%`], ['API p95 latency', `${monitoring?.p95_latency_ms ?? '—'} ms`], ['Retrieval failures', monitoring?.retrieval_failures ?? '—']];
  return <div className="animated-fade-in operations" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
    <div className="dashboard-grid">{cards.map(([name, value]) => <div className="glass-card metric-card" key={name}><div className="metric-info"><h3>{name}</h3><div className="metric-value">{value}</div></div><div className="metric-icon"><Activity size={22}/></div></div>)}</div>
    <div className="ops-grid"><section className="glass-card"><h3><Workflow size={18}/> Workflow automation</h3><p>Guardrailed, auditable agent workflows with human approval gates.</p><div className="ops-actions"><button className="btn btn-primary" onClick={() => launch('hr_request')}><Play size={15}/> HR request</button><button className="btn btn-secondary" onClick={() => launch('project_risk')}>Project risk</button><button className="btn btn-secondary" onClick={() => launch('document_intake')}>Document intake</button></div><div className="ops-list">{runs.slice(0, 5).map(r => <div key={r.id}><span>{r.name}</span><span className="badge badge-success">{r.status}</span></div>)}</div></section>
    <section className="glass-card"><h3><ShieldCheck size={18}/> Observability & evaluation</h3><p>{monitoring?.requests ?? 0} observed requests · {monitoring?.failures ?? 0} failures · {monitoring?.agent_traces?.length ?? 0} agent trace types</p><button className="btn btn-primary" onClick={evaluate}><CheckCircle2 size={15}/> Run evaluation suite</button><div className="ops-list">{monitoring?.agent_traces?.slice(0,5).map((t: any) => <div key={t.agent}><span>{t.agent}</span><span>{t.executions} runs · {t.avg_ms} ms</span></div>)}</div></section></div>
    {message && <div className="ops-message">{message}</div>}</div>;
};
