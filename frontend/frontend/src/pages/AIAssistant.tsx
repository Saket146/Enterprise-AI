import React, { useEffect, useState, useRef } from 'react';
import { api } from '../services/api';
import { 
  Send, Plus, BrainCircuit, Terminal, Percent, Clock, CheckCircle, 
  Activity, ArrowRight, ShieldAlert, Sparkles, FileText, Database, GitMerge
} from 'lucide-react';

interface AgentLog {
  agent_log_id: number;
  agent_name: string;
  task_description: string;
  input_data: string;
  output_data: string;
  execution_time_ms: number;
  confidence_score: number;
}

interface WorkflowRun {
  workflow_id: number;
  workflow_name: string;
  status: string;
  final_output: string;
  confidence_score: number;
  agent_logs: AgentLog[];
}

interface ChatSession {
  session_id: number;
  session_title: string;
  status: string;
  workflows: WorkflowRun[];
}

interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  agentLogs?: AgentLog[];
  isStreaming?: boolean;
}

export const AIAssistant: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [sessionDetails, setSessionDetails] = useState<ChatSession | null>(null);
  const [newTitle, setNewTitle] = useState<string>('');
  const [inputText, setInputText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [sessionsLoading, setSessionsLoading] = useState<boolean>(true);
  
  // Custom states for premium streaming and timeline
  const [displayMessages, setDisplayMessages] = useState<DisplayMessage[]>([]);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [simulatedLogs, setSimulatedLogs] = useState<AgentLog[]>([]);
  const [showTimeline, setShowTimeline] = useState<boolean>(true);
  const [selectedSourceDetail, setSelectedSourceDetail] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const loadSessions = async (selectFirst = false) => {
    setSessionsLoading(true);
    try {
      const res = await api.communications.getChats();
      setSessions(res || []);
      if (selectFirst && res && res.length > 0) {
        setSelectedSessionId(res[0].session_id);
      }
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  // Load chat sessions on mount
  useEffect(() => {
    loadSessions(true);
  }, []);

  // Build display messages list when session details change
  useEffect(() => {
    if (!sessionDetails) {
      setDisplayMessages([]);
      return;
    }

    const msgs: DisplayMessage[] = [];
    sessionDetails.workflows?.forEach((wf) => {
      // Extract user prompt from workflow name
      const userPrompt = wf.workflow_name
        .replace("Enterprise QA: ", "")
        .replace("...", "");
      
      msgs.push({
        id: `user-${wf.workflow_id}`,
        role: 'user',
        content: userPrompt
      });

      // Parse sources from final output
      const parsed = parseSources(wf.final_output);

      msgs.push({
        id: `assistant-${wf.workflow_id}`,
        role: 'assistant',
        content: parsed.cleanText,
        sources: parsed.sources,
        agentLogs: wf.agent_logs
      });
    });

    setDisplayMessages(msgs);
    setSimulatedLogs([]);
    setActiveStepIndex(-1);
  }, [sessionDetails]);

  // Scroll to bottom on updates
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [displayMessages, simulatedLogs, loading]);

  // Load active chat details when session changes
  useEffect(() => {
    if (selectedSessionId === null) return;
    
    const loadChatDetails = async () => {
      try {
        const details = await api.communications.getChat(selectedSessionId);
        setSessionDetails(details);
      } catch (err) {
        console.error('Failed to load session details:', err);
      }
    };
    loadChatDetails();
  }, [selectedSessionId]);

  // Helper to extract source references from markdown
  const parseSources = (text: string) => {
    if (!text) return { cleanText: "", sources: [] };
    
    // Find all occurrences of [Qdrant: ...] or [Neo4j: ...] or Source: ...
    const sourceRegex = /\[(Qdrant|Neo4j|SQL|Postgres|Reference).*?\]/g;
    const matches = text.match(sourceRegex) || [];
    
    // Clean text by removing brackets patterns
    let cleanText = text;
    matches.forEach(m => {
      cleanText = cleanText.replace(m, "");
    });
    
    // Also cleanup residual headers or double sources blocks
    if (cleanText.includes("### Verified Sources")) {
      cleanText = cleanText.split("### Verified Sources")[0];
    }
    if (cleanText.includes("### Sources")) {
      cleanText = cleanText.split("### Sources")[0];
    }

    return {
      cleanText: cleanText.trim(),
      sources: matches.map(m => m.replace(/[\[\]]/g, ""))
    };
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      const newSession = await api.communications.createChat(newTitle);
      setNewTitle('');
      await loadSessions();
      setSelectedSessionId(newSession.session_id);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  // Premium Streaming & timeline simulation
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || selectedSessionId === null) return;

    setLoading(true);
    const userMsg = inputText;
    setInputText('');

    // Optimistically add user query to thread list
    setDisplayMessages(prev => [
      ...prev,
      { id: `temp-user-${Date.now()}`, role: 'user', content: userMsg }
    ]);

    try {
      // 1. Fetch response from LangGraph backend
      const runRes = await api.communications.sendMessage(selectedSessionId, userMsg);
      const logs = runRes.agent_logs || [];
      
      // 2. Animate Agent Timeline steps sequentially
      setSimulatedLogs([]);
      for (let i = 0; i < logs.length; i++) {
        setActiveStepIndex(i);
        setSimulatedLogs(prev => [...prev, logs[i]]);
        // Delay to show reasoning step
        await new Promise(resolve => setTimeout(resolve, 800));
      }
      setActiveStepIndex(-1);

      // 3. Simulates word-by-word streaming of final response
      const { cleanText, sources } = parseSources(runRes.final_output);
      const words = cleanText.split(" ");
      let currentText = "";
      
      const streamId = `stream-assistant-${runRes.workflow_id}`;
      // Add empty assistant bubble
      setDisplayMessages(prev => [
        ...prev,
        { id: streamId, role: 'assistant', content: "", isStreaming: true, agentLogs: logs }
      ]);

      for (let w = 0; w < words.length; w++) {
        currentText += (w === 0 ? "" : " ") + words[w];
        setDisplayMessages(prev => 
          prev.map(m => m.id === streamId ? { ...m, content: currentText } : m)
        );
        // Custom delay per word
        await new Promise(resolve => setTimeout(resolve, 35));
      }

      // Mark streaming as complete, attach sources
      setDisplayMessages(prev => 
        prev.map(m => m.id === streamId ? { ...m, isStreaming: false, sources } : m)
      );

      // Refresh final chat state from DB
      const details = await api.communications.getChat(selectedSessionId);
      setSessionDetails(details);

    } catch (err) {
      console.error('Failed to transmit message:', err);
      setDisplayMessages(prev => [
        ...prev,
        { id: `err-${Date.now()}`, role: 'assistant', content: "🚨 Failed to receive agent completion. Please check backend server log connections." }
      ]);
    } finally {
      setLoading(false);
      setSimulatedLogs([]);
    }
  };

  const getSourceIcon = (src: string) => {
    if (src.toLowerCase().includes('qdrant')) return <FileText size={12} className="source-icon qdrant" />;
    if (src.toLowerCase().includes('neo4j') || src.toLowerCase().includes('graph')) return <GitMerge size={12} className="source-icon neo4j" />;
    return <Database size={12} className="source-icon sql" />;
  };

  return (
    <div className="animated-fade-in chat-container">
      {/* 1. Sidebar conversation list */}
      <div className="glass-card chat-sidebar" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'between', marginBottom: '8px' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BrainCircuit size={18} style={{ color: 'var(--color-primary)' }} /> Session Registry
          </h3>
        </div>
        
        <form onSubmit={handleCreateSession} style={{ display: 'flex', gap: '8px' }}>
          <input
            className="input-field"
            type="text"
            placeholder="New session title..."
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            required
            style={{ padding: '8px 12px', fontSize: '0.85rem' }}
          />
          <button className="btn btn-primary" type="submit" style={{ padding: '8px 12px' }}>
            <Plus size={16} />
          </button>
        </form>

        <div className="chat-history-list" style={{ flexGrow: 1, marginTop: '12px' }}>
          {sessionsLoading ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading threads...</p>
          ) : sessions.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No sessions found.</p>
          ) : (
            sessions.map(s => (
              <div
                key={s.session_id}
                onClick={() => setSelectedSessionId(s.session_id)}
                className={`chat-session-item ${selectedSessionId === s.session_id ? 'active' : ''}`}
                style={{ padding: '12px', borderRadius: '10px', marginBottom: '8px' }}
              >
                <div style={{ fontWeight: 600, fontSize: '0.88rem', marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {s.session_title}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span>ID: #{s.session_id}</span>
                  <span style={{ textTransform: 'capitalize' }}>● {s.status}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 2. Main Active Playground */}
      <div className="glass-card chat-main" style={{ display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
        {selectedSessionId !== null && sessionDetails ? (
          <>
            {/* Thread Header */}
            <div style={{ paddingBottom: '16px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>{sessionDetails.session_title}</h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Activity size={12} style={{ color: 'var(--color-success)' }} /> LangGraph Multi-Agent Fabric Layer
                </p>
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button 
                  onClick={() => setShowTimeline(!showTimeline)} 
                  className="btn btn-secondary" 
                  style={{ padding: '6px 12px', fontSize: '0.75rem', borderRadius: '20px' }}
                >
                  {showTimeline ? "Hide Execution Traces" : "Show Execution Traces"}
                </button>
                <span className="badge badge-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', height: '28px' }}>
                  <CheckCircle size={12} /> Guardrails Enabled
                </span>
              </div>
            </div>

            {/* Conversation list viewport */}
            <div className="chat-messages" style={{ flexGrow: 1, padding: '20px 8px', overflowY: 'auto' }}>
              
              {/* Core greeting */}
              <div className="chat-message agent">
                <div className="sidebar-avatar" style={{ background: 'var(--accent-gradient)', color: 'white' }}>Ω</div>
                <div className="message-bubble" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                  <p style={{ fontWeight: 500 }}>Welcome to the Enterprise AI Reasoning Playground.</p>
                  <p style={{ marginTop: '6px', color: 'var(--text-secondary)' }}>
                    I can dispatch tasks across 11 autonomous agents, parse files, execute secure SQL queries, traverse the Neo4j Knowledge Graph, and enforce guardrails. How can I help your automation workflow?
                  </p>
                </div>
              </div>

              {/* Loop messages list */}
              {displayMessages.map((msg) => (
                <div key={msg.id} className={`chat-message ${msg.role}`}>
                  <div className="sidebar-avatar" style={{
                    background: msg.role === 'user' ? 'var(--color-primary)' : 'var(--bg-tertiary)',
                    border: msg.role === 'user' ? 'none' : '2px solid var(--color-primary)',
                    color: 'white'
                  }}>
                    {msg.role === 'user' ? 'U' : 'AI'}
                  </div>
                  <div className="message-bubble" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                    
                    {/* Render Interactive Source Badges */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div style={{ marginTop: '12px', borderTop: '1px dashed var(--border-color)', paddingTop: '10px' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600 }}>RETRIEVED SOURCE CITATIONS:</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                          {msg.sources.map((src, sIdx) => (
                            <button
                              key={sIdx}
                              onClick={() => setSelectedSourceDetail(src)}
                              className="badge btn-secondary"
                              style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}
                            >
                              {getSourceIcon(src)}
                              <span>{src.replace(/qdrant:|neo4j:|sql:/i, '').trim()}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Reasoning traces details collapsible */}
                    {showTimeline && msg.agentLogs && msg.agentLogs.length > 0 && !msg.isStreaming && (
                      <div className="agent-reasoning-panel" style={{ marginTop: '12px' }}>
                        <details>
                          <summary style={{ cursor: 'pointer', fontSize: '0.8rem', color: 'var(--color-primary)', outline: 'none', fontWeight: 600 }}>
                            🛠️ View Agent Execution Audit Traces ({msg.agentLogs.length} Agents)
                          </summary>
                          <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {msg.agentLogs.map(log => (
                              <div key={log.agent_log_id} className="agent-log-step" style={{ background: 'rgba(0,0,0,0.25)', borderRadius: '8px', border: '1px solid var(--border-color)', padding: '10px 14px' }}>
                                <div className="agent-log-header" style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, fontSize: '0.8rem' }}>
                                  <span style={{ color: 'var(--color-primary)' }}>🤖 {log.agent_name}</span>
                                  <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span style={{ color: 'var(--color-success)', display: 'flex', alignItems: 'center', gap: '2px' }} title="Agent Confidence Score">
                                      <Sparkles size={10} /> {Math.round(log.confidence_score * 100)}%
                                    </span>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }} title="Execution Latency">
                                      <Clock size={10} /> {log.execution_time_ms}ms
                                    </span>
                                  </span>
                                </div>
                                <div style={{ color: 'var(--text-secondary)', marginTop: '4px', fontSize: '0.78rem' }}>
                                  <strong>Task Description:</strong> {log.task_description}
                                </div>
                                <div style={{ color: 'var(--text-primary)', marginTop: '6px', fontSize: '0.78rem', background: 'rgba(255,255,255,0.02)', padding: '6px 10px', borderRadius: '4px', borderLeft: '3px solid var(--color-primary)' }}>
                                  <strong>Result Payload:</strong> {log.output_data}
                                </div>
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Dynamic Live Reasoning timeline for active processing request */}
              {loading && simulatedLogs.length > 0 && (
                <div className="chat-message agent" style={{ flexDirection: 'column', width: '100%', maxWidth: '100%' }}>
                  <div style={{ display: 'flex', gap: '16px', width: '100%' }}>
                    <div className="sidebar-avatar" style={{ border: '2px solid var(--color-warning)', color: 'var(--color-warning)' }}>...</div>
                    <div className="message-bubble" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--color-warning)', width: '100%' }}>
                      <h5 style={{ color: 'var(--color-warning)', marginBottom: '12px', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Activity size={14} className="spinning-icon" /> Live Agent Graph Orchestration Traversal...
                      </h5>
                      
                      {/* Interactive flowchart timeline */}
                      <div className="live-timeline-flow" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {simulatedLogs.map((log, lIdx) => (
                          <div 
                            key={lIdx} 
                            style={{ 
                              display: 'flex', 
                              alignItems: 'center', 
                              gap: '12px', 
                              opacity: activeStepIndex === lIdx ? 1 : 0.7,
                              transform: activeStepIndex === lIdx ? 'scale(1.01)' : 'scale(1)',
                              transition: 'all 0.3s ease',
                              background: activeStepIndex === lIdx ? 'rgba(99,102,241,0.08)' : 'rgba(255,255,255,0.02)',
                              border: activeStepIndex === lIdx ? '1px solid var(--color-primary)' : '1px solid var(--border-color)',
                              padding: '10px 14px',
                              borderRadius: '8px'
                            }}
                          >
                            <div style={{
                              width: '24px',
                              height: '24px',
                              borderRadius: '50%',
                              background: activeStepIndex === lIdx ? 'var(--color-primary)' : 'var(--color-success)',
                              color: 'white',
                              display: 'flex',
                              alignItems: 'center',
                              justify-content: 'center',
                              fontSize: '0.75rem',
                              fontWeight: 'bold'
                            }}>
                              {lIdx + 1}
                            </div>
                            <div style={{ flexGrow: 1 }}>
                              <div style={{ display: 'flex', justifyContent: 'between', alignItems: 'center' }}>
                                <strong style={{ fontSize: '0.85rem', color: activeStepIndex === lIdx ? 'var(--color-primary)' : 'var(--text-primary)' }}>
                                  {log.agent_name}
                                </strong>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <Clock size={10} /> {log.execution_time_ms}ms
                                </span>
                              </div>
                              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                                {log.task_description}
                              </div>
                            </div>
                            {activeStepIndex === lIdx && <ArrowRight size={16} style={{ color: 'var(--color-primary)' }} />}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {loading && simulatedLogs.length === 0 && (
                <div className="chat-message agent">
                  <div className="sidebar-avatar">...</div>
                  <div className="message-bubble" style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>
                    Planner Agent analyzing user prompt and calculating graph routing...
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input area */}
            <form onSubmit={handleSendMessage} className="chat-input-area" style={{ borderTop: '1px solid var(--border-color)' }}>
              <input
                className="input-field"
                type="text"
                placeholder="Ask about project statuses, employee charts, or company policies..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                required
                disabled={loading}
              />
              <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '48px', height: '48px', padding: 0 }}>
                <Send size={16} />
              </button>
            </form>
          </>
        ) : (
          <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '16px' }}>
            <BrainCircuit size={64} style={{ color: 'var(--color-primary)', opacity: 0.4 }} />
            <h4 style={{ fontSize: '1.2rem', color: 'var(--text-secondary)' }}>AI Orchestrator Playground</h4>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', maxWidth: '350px', textAlign: 'center' }}>
              Select a conversation thread in the session catalog or create a new thread to interact with the multi-agent operating system.
            </p>
          </div>
        )}
      </div>

      {/* 3. Popup details modal for source card details */}
      {selectedSourceDetail && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justify-content: 'center',
          zIndex: 999
        }}>
          <div className="glass-card" style={{ width: '500px', maxWidth: '90%', padding: '28px' }}>
            <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
              <FileText size={18} style={{ color: 'var(--color-primary)' }} /> Source Details
            </h4>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '8px' }}>RETRIEVAL CITATION IDENTIFIER:</p>
            <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)', fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--color-primary)', marginBottom: '16px', overflowWrap: 'break-word' }}>
              {selectedSourceDetail}
            </div>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '20px' }}>
              This record was retrieved as part of the RAG pipeline. It was pulled via Qdrant semantic matching or Neo4j node query, and re-ranked using Sentence Transformer similarity metrics.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={() => setSelectedSourceDetail(null)} className="btn btn-primary" style={{ padding: '8px 20px', fontSize: '0.85rem' }}>
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default AIAssistant;
