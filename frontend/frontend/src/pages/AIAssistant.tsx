import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../services/api';
import { Markdown } from '../components/Markdown';
import {
  ArrowUp, Check, ChevronDown, ChevronRight, Copy, Database, FileText, GitMerge,
  MessageSquare, MoreHorizontal, Pencil, Plus, Search, ShieldAlert, Sparkles, Trash2, X,
} from 'lucide-react';

interface ChatSummary {
  session_id: number;
  session_title: string;
  started_at: string;
  last_activity_at: string;
  message_count: number;
}

interface Source { label: string; type: string; }

interface Step {
  agent: string;
  description: string;
  duration_ms: number | null;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  steps?: Step[];
  notice?: boolean;   // a local notice (blocked message or error), not stored on the server
}

interface SearchResult {
  title: string;
  type: string;
  text: string;
  details: string[];
  score: number;
  store: string;
  restricted?: boolean;   // the title is visible, the text is not (role cannot open it)
}

const SUGGESTIONS = [
  { title: 'Look someone up', prompt: 'Who is the CEO?' },
  { title: 'Count and compare', prompt: 'How many employees are there by department?' },
  { title: 'Find a policy', prompt: 'What is the leave management policy?' },
  { title: 'Check my work', prompt: 'What are my open tasks?' },
];

// Plain-language names for the agents that work on an answer
const STEP_NAMES: Record<string, string> = {
  PlannerAgent: 'Understood the question',
  RetrievalAgent: 'Searched company data',
  HRAgent: 'Checked employee and policy records',
  FinanceAgent: 'Checked budget records',
  SalesAgent: 'Checked client and contract records',
  EngineeringAgent: 'Checked project records',
  AnalyticsAgent: 'Calculated from company data',
  DocumentAgent: 'Searched documents',
  ReportGeneratorAgent: 'Wrote the answer',
  CriticAgent: 'Reviewed the answer',
  VerificationAgent: 'Verified facts and removed personal data',
};

const relativeTime = (iso: string): string => {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const minutes = Math.round((Date.now() - then) / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} d ago`;
  return new Date(iso).toLocaleDateString();
};

const sourceIcon = (type: string) => {
  if (type === 'documents') return <FileText size={12} />;
  if (type === 'graph') return <GitMerge size={12} />;
  return <Database size={12} />;
};

export const AIAssistant: React.FC = () => {
  const user = useMemo(() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch { return {}; }
  }, []);

  // Chat list
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [chatsLoading, setChatsLoading] = useState(true);
  const [chatFilter, setChatFilter] = useState('');
  const [activeId, setActiveId] = useState<number | null>(null);   // null = a new, not yet saved chat
  const [menuFor, setMenuFor] = useState<number | null>(null);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<ChatSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [listError, setListError] = useState('');

  // Conversation
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [openSteps, setOpenSteps] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Source search panel (the former "AI Vector Search" of the Knowledge Explorer)
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchScope, setSearchScope] = useState('all');
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searchVector, setSearchVector] = useState(true);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState('');

  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const skipLoadFor = useRef<number | null>(null);
  const renameDone = useRef(false);   // Enter/Escape already handled the rename; ignore the blur that follows

  const activeChat = chats.find((c) => c.session_id === activeId) || null;

  const loadChats = useCallback(async () => {
    try {
      const res = await api.communications.getChats();
      setChats(Array.isArray(res) ? res : []);
      setListError('');
    } catch (err: any) {
      setListError(err?.message || 'Could not load your chats.');
    } finally {
      setChatsLoading(false);
    }
  }, []);

  useEffect(() => { loadChats(); }, [loadChats]);

  // Load the messages of the selected chat
  useEffect(() => {
    if (activeId === null) { return; }
    if (skipLoadFor.current === activeId) { skipLoadFor.current = null; return; }
    let cancelled = false;
    setMessagesLoading(true);
    setMessages([]);
    api.communications.getChat(activeId)
      .then((detail) => { if (!cancelled) setMessages(detail.messages || []); })
      .catch((err: any) => {
        if (!cancelled) setMessages([{ id: 'load-error', role: 'assistant', notice: true, content: err?.message || 'This chat could not be loaded.' }]);
      })
      .finally(() => { if (!cancelled) setMessagesLoading(false); });
    return () => { cancelled = true; };
  }, [activeId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, sending]);

  // Close the row menu when clicking anywhere else
  useEffect(() => {
    if (menuFor === null) return;
    const close = () => setMenuFor(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [menuFor]);

  // Grow the input with its content
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [input]);

  const startNewChat = () => {
    setActiveId(null);
    setMessages([]);
    setInput('');
    setRenamingId(null);
    inputRef.current?.focus();
  };

  const selectChat = (id: number) => {
    if (id === activeId || sending) return;
    setRenamingId(null);
    setActiveId(id);
  };

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || sending) return;

    setSending(true);
    setInput('');
    const tempId = `pending-${Date.now()}`;
    setMessages((prev) => [...prev, { id: tempId, role: 'user', content: question }]);

    let chatId = activeId;
    let createdNow = false;
    try {
      if (chatId === null) {
        // The chat is created on the first question and named automatically by the server
        const created = await api.communications.createChat();
        chatId = created.session_id as number;
        createdNow = true;
        skipLoadFor.current = chatId;
        setChats((prev) => [created, ...prev]);
        setActiveId(chatId);
      }

      const reply = await api.communications.sendMessage(chatId, question);
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempId),
        reply.user_message,
        reply.answer,
      ]);
      setChats((prev) => {
        const updated = prev.map((c) => c.session_id === chatId
          ? { ...c, session_title: reply.session_title, last_activity_at: new Date().toISOString(), message_count: c.message_count + 2 }
          : c);
        // Most recently used chat first
        const current = updated.find((c) => c.session_id === chatId);
        return current ? [current, ...updated.filter((c) => c.session_id !== chatId)] : updated;
      });
    } catch (err: any) {
      const blocked = err?.status === 400;
      setMessages((prev) => [
        ...prev,
        {
          id: `notice-${Date.now()}`,
          role: 'assistant',
          notice: true,
          content: blocked
            ? `${err.message || "I can't process that message."} Please rephrase your question.`
            : `Something went wrong and I couldn't answer. ${err?.message || ''}`,
        },
      ]);
      if (createdNow && chatId !== null) {
        // Nothing was saved in the brand-new chat: remove it instead of leaving an empty "New chat" behind
        const emptyId = chatId;
        api.communications.deleteChat(emptyId).catch(() => undefined);
        setChats((prev) => prev.filter((c) => c.session_id !== emptyId));
        skipLoadFor.current = null;
        setActiveId(null);
      }
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); send(input); };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); }
  };

  // ---- Rename ---------------------------------------------------------
  const beginRename = (chat: ChatSummary) => {
    setMenuFor(null);
    renameDone.current = false;
    setRenamingId(chat.session_id);
    setRenameValue(chat.session_title);
  };

  const cancelRename = () => {
    renameDone.current = true;
    setRenamingId(null);
  };

  const commitRename = async () => {
    const id = renamingId;
    if (id === null || renameDone.current) return;
    renameDone.current = true;
    const title = renameValue.trim();
    const current = chats.find((c) => c.session_id === id);
    setRenamingId(null);
    if (!title || !current || title === current.session_title) return;
    try {
      const updated = await api.communications.renameChat(id, title);
      setChats((prev) => prev.map((c) => (c.session_id === id ? { ...c, session_title: updated.session_title } : c)));
    } catch (err: any) {
      setListError(err?.message || 'The chat could not be renamed.');
    }
  };

  // ---- Delete ---------------------------------------------------------
  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.communications.deleteChat(deleteTarget.session_id);
      setChats((prev) => prev.filter((c) => c.session_id !== deleteTarget.session_id));
      if (activeId === deleteTarget.session_id) { setActiveId(null); setMessages([]); }
      setDeleteTarget(null);
    } catch (err: any) {
      setListError(err?.message || 'The chat could not be deleted.');
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  };

  const copyAnswer = async (msg: ChatMessage) => {
    try {
      await navigator.clipboard.writeText(msg.content);
      setCopiedId(msg.id);
      setTimeout(() => setCopiedId((current) => (current === msg.id ? null : current)), 1500);
    } catch { /* clipboard not available */ }
  };

  // ---- Source search --------------------------------------------------
  const runSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim().length < 2) return;
    setSearching(true);
    setSearchError('');
    try {
      const res = await api.knowledge.search(searchQuery.trim(), searchScope);
      setSearchResults(res.results || []);
      setSearchVector(Boolean(res.vector_search_available));
    } catch (err: any) {
      setSearchResults(null);
      setSearchError(err?.message || 'The search failed.');
    } finally {
      setSearching(false);
    }
  };

  const askAbout = (result: SearchResult) => {
    setInput(`Tell me about "${result.title}"`);
    inputRef.current?.focus();
  };

  const visibleChats = chats.filter((c) => c.session_title.toLowerCase().includes(chatFilter.trim().toLowerCase()));
  const showWelcome = messages.length === 0 && !messagesLoading && !sending;

  return (
    <div className="animated-fade-in ai-layout">
      {/* ---------------- Chat list ---------------- */}
      <aside className="glass-card ai-sidebar">
        <button className="btn btn-primary ai-new-chat" onClick={startNewChat} disabled={sending}>
          <Plus size={16} /> New chat
        </button>

        <div className="ai-filter">
          <Search size={14} />
          <input
            type="text"
            placeholder="Search your chats"
            value={chatFilter}
            onChange={(e) => setChatFilter(e.target.value)}
            aria-label="Search your chats"
          />
        </div>

        {listError && <div className="ai-inline-error">{listError}</div>}

        <div className="ai-chat-list">
          {chatsLoading ? (
            <p className="ai-muted">Loading chats...</p>
          ) : visibleChats.length === 0 ? (
            <p className="ai-muted">{chats.length === 0 ? 'No chats yet. Ask your first question to start one.' : 'No chats match your search.'}</p>
          ) : (
            visibleChats.map((chat) => (
              <div
                key={chat.session_id}
                className={`ai-chat-row ${activeId === chat.session_id ? 'active' : ''}`}
                onClick={() => selectChat(chat.session_id)}
              >
                {renamingId === chat.session_id ? (
                  <input
                    className="ai-rename-input"
                    autoFocus
                    value={renameValue}
                    maxLength={120}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onBlur={commitRename}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitRename();
                      if (e.key === 'Escape') cancelRename();
                    }}
                    aria-label="Chat name"
                  />
                ) : (
                  <>
                    <div className="ai-chat-row-text">
                      <div className="ai-chat-title" title={chat.session_title}>{chat.session_title}</div>
                      <div className="ai-chat-time">{relativeTime(chat.last_activity_at)}</div>
                    </div>
                    <button
                      className="ai-icon-btn ai-row-menu-btn"
                      title="Chat options"
                      aria-label="Chat options"
                      onClick={(e) => { e.stopPropagation(); setMenuFor(menuFor === chat.session_id ? null : chat.session_id); }}
                    >
                      <MoreHorizontal size={16} />
                    </button>
                    {menuFor === chat.session_id && (
                      <div className="ai-row-menu" onClick={(e) => e.stopPropagation()}>
                        <button onClick={() => beginRename(chat)}><Pencil size={14} /> Rename</button>
                        <button className="danger" onClick={() => { setMenuFor(null); setDeleteTarget(chat); }}><Trash2 size={14} /> Delete</button>
                      </div>
                    )}
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </aside>

      {/* ---------------- Conversation ---------------- */}
      <section className="glass-card ai-main">
        <header className="ai-header">
          <div className="ai-header-title">
            <MessageSquare size={16} />
            <span title={activeChat?.session_title || 'New chat'}>{activeChat?.session_title || 'New chat'}</span>
            {activeChat && (
              <>
                <button className="ai-icon-btn" title="Rename chat" aria-label="Rename chat" onClick={() => beginRename(activeChat)}><Pencil size={14} /></button>
                <button className="ai-icon-btn" title="Delete chat" aria-label="Delete chat" onClick={() => setDeleteTarget(activeChat)}><Trash2 size={14} /></button>
              </>
            )}
          </div>
          <button className={`btn btn-secondary ai-search-toggle ${searchOpen ? 'on' : ''}`} onClick={() => setSearchOpen(!searchOpen)}>
            <Search size={14} /> Search sources
          </button>
        </header>

        <div className="ai-messages">
          <div className="ai-column">
            {messagesLoading && <p className="ai-muted" style={{ textAlign: 'center' }}>Loading conversation...</p>}

            {showWelcome && (
              <div className="ai-welcome">
                <div className="ai-welcome-icon"><Sparkles size={26} /></div>
                <h2>{user.first_name ? `Hi ${user.first_name}, what would you like to know?` : 'What would you like to know?'}</h2>
                <p>
                  Ask about people, departments, projects, clients, budgets and policies.
                  Answers come from the company database and only include what your role{user.role ? ` (${user.role})` : ''} is allowed to see.
                </p>
                <div className="ai-suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button key={s.prompt} onClick={() => send(s.prompt)}>
                      <strong>{s.title}</strong>
                      <span>{s.prompt}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              msg.role === 'user' ? (
                <div key={msg.id} className="ai-msg ai-msg-user">
                  <div className="ai-user-bubble">{msg.content}</div>
                </div>
              ) : (
                <div key={msg.id} className={`ai-msg ai-msg-assistant ${msg.notice ? 'notice' : ''}`}>
                  <div className="ai-avatar">{msg.notice ? <ShieldAlert size={15} /> : <Sparkles size={15} />}</div>
                  <div className="ai-answer">
                    <Markdown text={msg.content} />

                    {msg.sources && msg.sources.length > 0 && (
                      <div className="ai-sources">
                        <span className="ai-sources-label">Sources</span>
                        {msg.sources.map((src, idx) => (
                          <span key={idx} className="ai-source-chip" title={src.label}>{sourceIcon(src.type)} {src.label}</span>
                        ))}
                      </div>
                    )}

                    {!msg.notice && (
                      <div className="ai-answer-actions">
                        <button className="ai-link-btn" onClick={() => copyAnswer(msg)}>
                          {copiedId === msg.id ? <><Check size={13} /> Copied</> : <><Copy size={13} /> Copy</>}
                        </button>
                        {msg.steps && msg.steps.length > 0 && (
                          <button className="ai-link-btn" onClick={() => setOpenSteps((prev) => ({ ...prev, [msg.id]: !prev[msg.id] }))}>
                            {openSteps[msg.id] ? <ChevronDown size={13} /> : <ChevronRight size={13} />} How this was answered
                          </button>
                        )}
                      </div>
                    )}

                    {msg.steps && openSteps[msg.id] && (
                      <ol className="ai-steps">
                        {msg.steps.map((step, idx) => (
                          <li key={idx}>
                            <div className="ai-step-name">{STEP_NAMES[step.agent] || step.agent}</div>
                            <div className="ai-step-meta">
                              {step.duration_ms !== null && step.duration_ms !== undefined ? `${step.duration_ms} ms` : ''}
                            </div>
                          </li>
                        ))}
                      </ol>
                    )}
                  </div>
                </div>
              )
            ))}

            {sending && (
              <div className="ai-msg ai-msg-assistant">
                <div className="ai-avatar"><Sparkles size={15} /></div>
                <div className="ai-thinking" aria-live="polite">
                  <span className="ai-dot" /><span className="ai-dot" /><span className="ai-dot" />
                  <span className="ai-thinking-text">Looking through company data...</span>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        </div>

        <form className="ai-composer" onSubmit={handleSubmit}>
          <div className="ai-column">
            <div className="ai-composer-box">
              <textarea
                ref={inputRef}
                rows={1}
                placeholder="Ask a question about the company..."
                value={input}
                maxLength={4000}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={sending}
                aria-label="Your question"
              />
              <button type="submit" className="ai-send" disabled={sending || !input.trim()} title="Send" aria-label="Send">
                <ArrowUp size={18} />
              </button>
            </div>
            <div className="ai-composer-hint">Enter to send, Shift + Enter for a new line. Answers are checked against company data, but verify anything important.</div>
          </div>
        </form>
      </section>

      {/* ---------------- Source search ---------------- */}
      {searchOpen && (
        <aside className="glass-card ai-search-panel">
          <div className="ai-search-head">
            <h3><Search size={16} /> Search sources</h3>
            <button className="ai-icon-btn" onClick={() => setSearchOpen(false)} title="Close" aria-label="Close search"><X size={16} /></button>
          </div>
          <p className="ai-muted">
            Find policies, documents, your emails, your meetings and past chats. What you can open depends on your role.
          </p>
          <form onSubmit={runSearch} className="ai-search-form">
            <input
              className="input-field"
              type="text"
              placeholder="e.g. remote work policy"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search text"
            />
            <div className="ai-search-row">
              <select className="input-field" value={searchScope} onChange={(e) => setSearchScope(e.target.value)} aria-label="Where to search">
                <option value="all">Everything</option>
                <option value="policies">Policies</option>
                <option value="documents">Documents</option>
                <option value="emails">My emails</option>
                <option value="meetings">My meetings</option>
                <option value="chats">My past chats</option>
              </select>
              <button className="btn btn-primary" type="submit" disabled={searching || searchQuery.trim().length < 2}>
                {searching ? 'Searching...' : 'Search'}
              </button>
            </div>
          </form>

          {searchError && <div className="ai-inline-error">{searchError}</div>}

          {searchResults !== null && !searchVector && (
            <div className="ai-search-note">
              Semantic search (Qdrant) is not running, so these are keyword matches from the policies and documents tables only.
            </div>
          )}

          <div className="ai-search-results">
            {searchResults !== null && searchResults.length === 0 && !searching && (
              <p className="ai-muted">Nothing matched. Try different words.</p>
            )}
            {(searchResults || []).map((result, idx) => (
              <div key={idx} className="ai-search-result">
                <div className="ai-search-result-head">
                  <span className="badge badge-success">{result.type}</span>
                  <span className="ai-search-score" title={`Found in ${result.store}`}>{Math.round(result.score * 100)}% match</span>
                </div>
                <div className="ai-search-result-title">{result.title}</div>
                {result.details.length > 0 && <div className="ai-search-result-meta">{result.details.join(' · ')}</div>}
                <p className={result.restricted ? 'ai-search-restricted' : ''}>{result.text.length > 320 ? `${result.text.slice(0, 320)}...` : result.text}</p>
                {!result.restricted && <button className="ai-link-btn" onClick={() => askAbout(result)}>Ask about this</button>}
              </div>
            ))}
          </div>
        </aside>
      )}

      {/* ---------------- Delete confirmation ---------------- */}
      {deleteTarget && (
        <div className="ai-modal-backdrop" onClick={() => !deleting && setDeleteTarget(null)}>
          <div className="glass-card ai-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <h3>Delete this chat?</h3>
            <p>
              "{deleteTarget.session_title}" and all of its messages will be permanently deleted. This can't be undone.
            </p>
            <div className="ai-modal-actions">
              <button className="btn btn-secondary" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</button>
              <button className="btn ai-btn-danger" onClick={confirmDelete} disabled={deleting}>{deleting ? 'Deleting...' : 'Delete chat'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default AIAssistant;
