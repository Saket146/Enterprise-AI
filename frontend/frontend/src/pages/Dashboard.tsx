import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import {
  Users, Briefcase, FileText, Database, RefreshCw, Play, Activity, ShieldAlert
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';

export const Dashboard: React.FC = () => {
  const [employeeCount, setEmployeeCount] = useState<number>(0);
  const [projectCount, setProjectCount] = useState<number>(0);
  const [documentCount, setDocumentCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncStatus, setSyncStatus] = useState<{ type: string; status: string; msg?: string } | null>(null);

  // Mock charts and log data for demonstration
  const projectStatusData = [
    { name: 'Active', value: 5, color: '#6366f1' },
    { name: 'Completed', value: 3, color: '#10b981' },
    { name: 'In Planning', value: 2, color: '#f59e0b' },
    { name: 'On Hold', value: 1, color: '#ef4444' },
  ];

  const agentActivityData = [
    { name: 'Mon', queries: 40, errors: 2 },
    { name: 'Tue', queries: 55, errors: 4 },
    { name: 'Wed', queries: 78, errors: 1 },
    { name: 'Thu', queries: 62, errors: 3 },
    { name: 'Fri', queries: 95, errors: 0 },
    { name: 'Sat', queries: 25, errors: 1 },
    { name: 'Sun', queries: 32, errors: 2 },
  ];

  const recentLogs = [
    { time: '10:42:15', agent: 'OrchestratorAgent', event: 'Decomposed search query', status: 'success' },
    { time: '10:42:16', agent: 'RetrieverAgent', event: 'Vector similarity scan (Qdrant)', status: 'success' },
    { time: '10:42:17', agent: 'GuardrailAgent', event: 'Executed compliance PII checks', status: 'success' },
    { time: '10:15:02', agent: 'System', event: 'Manual database sync triggered', status: 'warning' },
  ];

  useEffect(() => {
    const fetchCounts = async () => {
      try {
        const emps = await api.employees.list({ limit: 1 });
        setEmployeeCount(emps.total || 0);

        const projs = await api.projects.list({ limit: 100 });
        setProjectCount(projs.length || 0);

        const docs = await api.knowledge.listDocuments({ limit: 1 });
        // Since listDocuments returns a direct array, we check length
        setDocumentCount(docs.length || 0);
      } catch (err) {
        console.error('Failed to load counts from DB:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchCounts();
  }, []);

  const handleSync = async (type: 'qdrant' | 'neo4j') => {
    setSyncStatus({ type, status: 'running' });
    try {
      if (type === 'qdrant') {
        const res = await api.ingestion.syncQdrant();
        setSyncStatus({
          type,
          status: 'success',
          msg: `Ingested: ${res.details?.documents || 0} Docs, ${res.details?.policies || 0} Policies.`
        });
      } else {
        const res = await api.ingestion.syncNeo4j();
        setSyncStatus({
          type,
          status: 'success',
          msg: `Created: ${res.details?.nodes || 0} Nodes, ${res.details?.relationships || 0} Edges.`
        });
      }
    } catch (err: any) {
      setSyncStatus({
        type,
        status: 'error',
        msg: err.message || 'Sync failed.'
      });
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-secondary)' }}>Loading enterprise configurations...</p>
      </div>
    );
  }

  return (
    <div className="animated-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* 1. Metric Indicators Row */}
      <div className="dashboard-grid">
        <div className="glass-card metric-card">
          <div className="metric-info">
            <h3>Enterprise Workforce</h3>
            <div className="metric-value">{employeeCount}</div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Active Employees</p>
          </div>
          <div className="metric-icon">
            <Users size={24} />
          </div>
        </div>

        <div className="glass-card metric-card">
          <div className="metric-info">
            <h3>Active Projects</h3>
            <div className="metric-value">{projectCount}</div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Across 8 Departments</p>
          </div>
          <div className="metric-icon">
            <Briefcase size={24} />
          </div>
        </div>

        <div className="glass-card metric-card">
          <div className="metric-info">
            <h3>Knowledge Assets</h3>
            <div className="metric-value">{documentCount}</div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>RAG Ingested Docs</p>
          </div>
          <div className="metric-icon">
            <FileText size={24} />
          </div>
        </div>

        <div className="glass-card metric-card">
          <div className="metric-info">
            <h3>Graph Sync Status</h3>
            <div className="metric-value">Active</div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>Neo4j Graph Database</p>
          </div>
          <div className="metric-icon">
            <Database size={24} />
          </div>
        </div>
      </div>

      {/* 2. Visual Graphs Section */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
        <div className="glass-card">
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={18} className="text-primary" /> Multi-Agent Execution Metrics
          </h3>
          <div style={{ width: '100%', height: '300px' }}>
            <ResponsiveContainer>
              <BarChart data={agentActivityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="name" stroke="var(--text-secondary)" fontSize={12} />
                <YAxis stroke="var(--text-secondary)" fontSize={12} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }} />
                <Bar dataKey="queries" fill="url(#accentGrad)" name="Successful Tasks" radius={[4, 4, 0, 0]} />
                <Bar dataKey="errors" fill="#ef4444" name="Security Intercepts" radius={[4, 4, 0, 0]} />
                <defs>
                  <linearGradient id="accentGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" />
                    <stop offset="100%" stopColor="#a855f7" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginBottom: '20px' }}>Project Portfolio</h3>
          <div style={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={projectStatusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {projectStatusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.8rem' }}>
            {projectStatusData.map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: item.color }} />
                <span>{item.name}: {item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 3. Ingestion Sync Controls & Audit Logs */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Sync Controls */}
        <div className="glass-card">
          <h3 style={{ marginBottom: '16px' }}>AI Operating System Sync Center</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '24px' }}>
            Synchronize PostgreSQL data to the Vector Search (Qdrant) and Knowledge Graph (Neo4j) database layers.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', border: '1px solid var(--border-color)', borderRadius: '12px', backgroundColor: 'rgba(255,255,255,0.01)' }}>
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Qdrant Vector Database</h4>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Generate 384d all-MiniLM-L6-v2 embeddings</p>
              </div>
              <button
                className="btn btn-secondary"
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                onClick={() => handleSync('qdrant')}
                disabled={syncStatus?.type === 'qdrant' && syncStatus?.status === 'running'}
              >
                <RefreshCw size={14} className={syncStatus?.type === 'qdrant' && syncStatus?.status === 'running' ? 'spin' : ''} /> Sync
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', border: '1px solid var(--border-color)', borderRadius: '12px', backgroundColor: 'rgba(255,255,255,0.01)' }}>
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Neo4j Knowledge Graph</h4>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Update employee structures and assign relationships</p>
              </div>
              <button
                className="btn btn-secondary"
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                onClick={() => handleSync('neo4j')}
                disabled={syncStatus?.type === 'neo4j' && syncStatus?.status === 'running'}
              >
                <Play size={14} /> Sync Graph
              </button>
            </div>

            {syncStatus && (
              <div style={{
                padding: '12px',
                borderRadius: '8px',
                fontSize: '0.85rem',
                border: '1px solid var(--border-color)',
                backgroundColor: syncStatus.status === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                color: syncStatus.status === 'error' ? '#ef4444' : '#10b981'
              }}>
                <strong>{syncStatus.type.toUpperCase()}:</strong> {syncStatus.status === 'running' ? 'Running ingestion pipeline...' : syncStatus.msg}
              </div>
            )}
          </div>
        </div>

        {/* Recent Audit / Execution Logs */}
        <div className="glass-card">
          <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldAlert size={18} className="text-warning" /> Security & Ingestion Monitor
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {recentLogs.map((log, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border-color)' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>[{log.time}]</span>
                    <strong style={{ fontSize: '0.85rem', color: 'var(--color-primary)' }}>{log.agent}</strong>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>{log.event}</p>
                </div>
                <span className={`badge ${log.status === 'success' ? 'badge-success' : 'badge-warning'}`}>
                  {log.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
export default Dashboard;
