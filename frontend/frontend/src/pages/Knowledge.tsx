import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import { Markdown } from '../components/Markdown';
import { Search, BrainCircuit, FileText, Landmark, Clock, Lock, BookOpen, Hourglass, KeyRound, X } from 'lucide-react';

interface DocumentItem {
  document_id: number;
  title: string;
  document_type: string;
  file_name: string;
  created_at: string;
  creator?: { first_name: string; last_name: string };
  department?: { department_name: string };
  my_access?: 'open' | 'pending' | 'request';   // may read it / access requested / may ask for access
}

interface PolicyItem {
  policy_id: number;
  policy_name: string;
  version: string;
  effective_date: string;
  department?: { department_name: string };
}

interface KnowledgeAccess {
  can_list: boolean;
  can_open_policies: boolean;
  can_open_all_documents: boolean;
  can_request_documents: boolean;
  reader_roles: string;
}

interface OpenItem {
  title: string;
  meta: string[];
  content: string;
}

interface KnowledgeProps {
  onOpenAssistant?: () => void;
}

export const Knowledge: React.FC<KnowledgeProps> = ({ onOpenAssistant }) => {
  const [access, setAccess] = useState<KnowledgeAccess | null>(null);
  const [activeSpace, setActiveSpace] = useState<'documents' | 'policies'>('documents');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [policies, setPolicies] = useState<PolicyItem[]>([]);
  const [search, setSearch] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [listError, setListError] = useState<string>('');

  // Reader
  const [openItem, setOpenItem] = useState<OpenItem | null>(null);
  const [opening, setOpening] = useState<boolean>(false);
  const [openError, setOpenError] = useState<string>('');

  // Access request for one document (decided by a system administrator in the Operations Center)
  const [requestDoc, setRequestDoc] = useState<DocumentItem | null>(null);
  const [requestReason, setRequestReason] = useState<string>('');
  const [requesting, setRequesting] = useState<boolean>(false);
  const [requestError, setRequestError] = useState<string>('');
  const [notice, setNotice] = useState<string>('');

  // 1. What is this role allowed to see here?
  useEffect(() => {
    api.knowledge.access()
      .then((res: KnowledgeAccess) => setAccess(res))
      .catch(() => setAccess({ can_list: false, can_open_policies: false, can_open_all_documents: false, can_request_documents: false, reader_roles: 'the CEO, CTO, CFO or a system administrator' }));
  }, []);

  // 2. Load the list (titles and listing details only; the text is fetched when an item is opened)
  const loadList = useCallback(async () => {
    setLoading(true);
    setListError('');
    try {
      if (activeSpace === 'documents') {
        const res = await api.knowledge.listDocuments({ search, limit: 100 });
        setDocuments(res || []);
      } else {
        const res = await api.knowledge.listPolicies({ search, limit: 100 });
        setPolicies(res || []);
      }
    } catch (err: any) {
      setListError(err?.message || 'The list could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [activeSpace, search]);

  useEffect(() => {
    if (!access?.can_list) return;
    const timer = setTimeout(loadList, 250);   // wait until typing pauses
    return () => clearTimeout(timer);
  }, [access, loadList]);

  const handleDocumentClick = (doc: DocumentItem) => {
    if (doc.my_access === 'open') { openDocument(doc); return; }
    if (doc.my_access === 'request' && access?.can_request_documents) {
      setRequestDoc(doc);
      setRequestReason('');
      setRequestError('');
    }
  };

  const submitAccessRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!requestDoc) return;
    if (requestReason.trim().length < 3) { setRequestError('Please say briefly why you need this document.'); return; }
    setRequesting(true);
    setRequestError('');
    try {
      await api.workflows.run({ workflow_type: 'document_access', title: '', payload: requestReason.trim(), document_id: requestDoc.document_id });
      setDocuments((prev) => prev.map((d) => (d.document_id === requestDoc.document_id ? { ...d, my_access: 'pending' } : d)));
      setNotice(`Access to "${requestDoc.title}" was requested. A system administrator will decide; you can follow it under My requests in the Operations Center.`);
      setRequestDoc(null);
    } catch (err: any) {
      setRequestError(err?.message || 'The request could not be sent.');
    } finally {
      setRequesting(false);
    }
  };

  const openDocument = async (doc: DocumentItem) => {
    setOpening(true);
    setOpenError('');
    setOpenItem({ title: doc.title, meta: [], content: '' });
    try {
      const res = await api.knowledge.openDocument(doc.document_id);
      setOpenItem({
        title: res.title,
        meta: [
          res.document_type,
          res.file_name,
          res.department ? `Department: ${res.department}` : '',
          res.author ? `Author: ${res.author}` : '',
          res.created_at ? `Created: ${new Date(res.created_at).toLocaleDateString()}` : '',
        ].filter(Boolean),
        content: res.content,
      });
    } catch (err: any) {
      setOpenError(err?.message || 'The document could not be opened.');
    } finally {
      setOpening(false);
    }
  };

  const openPolicy = async (pol: PolicyItem) => {
    if (!access?.can_open_policies) return;
    setOpening(true);
    setOpenError('');
    setOpenItem({ title: pol.policy_name, meta: [], content: '' });
    try {
      const res = await api.knowledge.openPolicy(pol.policy_id);
      setOpenItem({
        title: res.policy_name,
        meta: [
          `Version ${res.version}`,
          res.effective_date ? `Effective: ${res.effective_date}` : '',
          `Owner: ${res.department || 'Company-wide'}`,
        ].filter(Boolean),
        content: res.content,
      });
    } catch (err: any) {
      setOpenError(err?.message || 'The policy could not be opened.');
    } finally {
      setOpening(false);
    }
  };

  const closeReader = () => { setOpenItem(null); setOpenError(''); };

  // Close the reader with Escape
  useEffect(() => {
    if (!openItem) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') closeReader(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [openItem]);

  if (access === null) {
    return <p style={{ color: 'var(--text-secondary)' }}>Checking your access...</p>;
  }

  // Interns (and any role without knowledge access) see nothing here - not even titles
  if (!access.can_list) {
    return (
      <div className="animated-fade-in kx-locked glass-card">
        <div className="kx-locked-icon"><Lock size={26} /></div>
        <h3>The Knowledge Explorer is not available for your role</h3>
        <p>Company policies and documents are not visible to your role. If you need one for your work, ask your manager.</p>
      </div>
    );
  }

  const canOpenPolicies = access.can_open_policies;

  return (
    <div className="animated-fade-in split-explorer" style={{ height: '100%' }}>
      {/* 1. Knowledge Space Selectors */}
      <div className="split-sidebar" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <h3 style={{ marginBottom: '16px' }}>Knowledge Spaces</h3>

        <button
          onClick={() => setActiveSpace('documents')}
          className={`btn ${activeSpace === 'documents' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ width: '100%', justifyContent: 'flex-start', padding: '12px 16px' }}
        >
          <FileText size={16} /> Documents Catalog
        </button>

        <button
          onClick={() => setActiveSpace('policies')}
          className={`btn ${activeSpace === 'policies' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ width: '100%', justifyContent: 'flex-start', padding: '12px 16px' }}
        >
          <Landmark size={16} /> Policies Catalog
        </button>

        <div className="kx-access-note">
          {access.can_open_all_documents ? (
            <><BookOpen size={14} /> Your role can open and read every policy and document. Click a row to open it.</>
          ) : (
            <><KeyRound size={14} /> You can read every policy. Documents are listed by title: request access to the ones you need and a system administrator decides.</>
          )}
        </div>

        {/* Question answering and source search live in the AI Assistant */}
        {onOpenAssistant && (
          <div style={{ marginTop: '8px', padding: '14px 16px', border: '1px solid var(--border-color)', borderRadius: '12px', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            Want to ask a question about policies and documents?
            <button
              onClick={onOpenAssistant}
              className="btn btn-secondary"
              style={{ width: '100%', justifyContent: 'center', marginTop: '10px', padding: '10px 12px' }}
            >
              <BrainCircuit size={16} /> Open AI Assistant
            </button>
          </div>
        )}
      </div>

      {/* 2. Main Explorer Area */}
      <div className="split-main" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="glass-card" style={{ display: 'flex', gap: '16px', alignItems: 'center', padding: '16px' }}>
          <div style={{ position: 'relative', flexGrow: 1 }}>
            <input
              className="input-field"
              type="text"
              placeholder={activeSpace === 'documents' ? 'Search documents by title, file name or type...' : 'Search policies by name...'}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ paddingLeft: '40px' }}
            />
            <Search size={16} style={{ position: 'absolute', left: '16px', top: '15px', color: 'var(--text-secondary)' }} />
          </div>
        </div>

        {notice && (
          <div className="kx-notice">
            <span>{notice}</span>
            <button className="ai-icon-btn" onClick={() => setNotice('')} aria-label="Dismiss"><X size={14} /></button>
          </div>
        )}

        <div className="glass-card">
          {listError ? (
            <p style={{ color: '#fca5a5' }}>{listError}</p>
          ) : loading ? (
            <p style={{ color: 'var(--text-secondary)' }}>Loading catalog items...</p>
          ) : activeSpace === 'documents' ? (
            documents.length === 0 ? (
              <p>No documents found.</p>
            ) : (
              <div className="table-container">
                <table className="enterprise-table">
                  <thead>
                    <tr>
                      <th>Document Title</th>
                      <th>Type</th>
                      <th>Department</th>
                      <th>Uploader</th>
                      <th>Created</th>
                      <th style={{ width: '150px' }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map(doc => (
                      <tr
                        key={doc.document_id}
                        className={doc.my_access === 'pending' ? '' : 'kx-row-open'}
                        onClick={() => handleDocumentClick(doc)}
                        title={doc.my_access === 'open' ? 'Open document' : doc.my_access === 'pending' ? 'Your access request is waiting for a decision' : 'Request access to this document'}
                      >
                        <td>
                          <div style={{ fontWeight: 600 }}>{doc.title}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace', marginTop: '2px' }}>{doc.file_name}</div>
                        </td>
                        <td>{doc.document_type}</td>
                        <td>{doc.department?.department_name || 'Global'}</td>
                        <td>{doc.creator ? `${doc.creator.first_name} ${doc.creator.last_name}` : 'System'}</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}>
                            <Clock size={12} /> {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'N/A'}
                          </div>
                        </td>
                        <td>
                          {doc.my_access === 'open'
                            ? <span className="kx-open-link"><BookOpen size={13} /> Open</span>
                            : doc.my_access === 'pending'
                              ? <span className="kx-locked-link"><Hourglass size={13} /> Access requested</span>
                              : <span className="kx-request-link"><KeyRound size={13} /> Request access</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {documents.length === 100 && <p className="kx-more">Showing the first 100 documents. Use the search box to find others.</p>}
              </div>
            )
          ) : (
            policies.length === 0 ? (
              <p>No policies found.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {policies.map(pol => (
                  <div
                    key={pol.policy_id}
                    className={`kx-policy ${canOpenPolicies ? 'kx-row-open' : ''}`}
                    onClick={() => openPolicy(pol)}
                    title={canOpenPolicies ? 'Open policy' : 'Your role cannot open policies'}
                  >
                    <div style={{ minWidth: 0 }}>
                      <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>{pol.policy_name}</h4>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                        Effective: {pol.effective_date} • Owner: {pol.department?.department_name || 'Company-wide'}
                      </p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
                      <span className="badge badge-success">Version {pol.version}</span>
                      {canOpenPolicies
                        ? <span className="kx-open-link"><BookOpen size={13} /> Open</span>
                        : <span className="kx-locked-link"><Lock size={13} /> Title only</span>}
                    </div>
                  </div>
                ))}
                {policies.length === 100 && <p className="kx-more">Showing the first 100 policies. Use the search box to find others.</p>}
              </div>
            )
          )}
        </div>
      </div>

      {/* 3. Request access to a document */}
      {requestDoc && (
        <div className="kx-backdrop" onClick={() => !requesting && setRequestDoc(null)}>
          <form className="kx-reader kx-request" onClick={(e) => e.stopPropagation()} onSubmit={submitAccessRequest} role="dialog" aria-modal="true">
            <div className="kx-reader-head">
              <div style={{ minWidth: 0 }}>
                <h3>Request access</h3>
                <div className="kx-reader-meta">{requestDoc.title}</div>
              </div>
              <button type="button" className="ai-icon-btn" onClick={() => setRequestDoc(null)} title="Close" aria-label="Close"><X size={18} /></button>
            </div>
            <div className="kx-reader-body">
              <p className="kx-request-help">
                Your role sees this document by title only. A system administrator reviews the request in the Operations Center; once it is approved you can open the document here.
              </p>
              <label className="form-label" htmlFor="kx-reason">Why do you need it?</label>
              <textarea
                id="kx-reason"
                className="input-field"
                style={{ minHeight: '96px', resize: 'vertical', lineHeight: 1.5 }}
                maxLength={1000}
                autoFocus
                placeholder="e.g. I am joining this project next week and need the deployment steps."
                value={requestReason}
                onChange={(e) => setRequestReason(e.target.value)}
              />
              {requestError && <p style={{ color: '#fca5a5', fontSize: '0.85rem', marginTop: '10px' }}>{requestError}</p>}
              <div className="kx-request-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setRequestDoc(null)} disabled={requesting}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={requesting}>{requesting ? 'Sending...' : 'Send request'}</button>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* 4. Reader */}
      {openItem && (
        <div className="kx-backdrop" onClick={closeReader}>
          <div className="kx-reader" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label={openItem.title}>
            <div className="kx-reader-head">
              <div style={{ minWidth: 0 }}>
                <h3>{openItem.title}</h3>
                {openItem.meta.length > 0 && <div className="kx-reader-meta">{openItem.meta.join(' • ')}</div>}
              </div>
              <button className="ai-icon-btn" onClick={closeReader} title="Close" aria-label="Close"><X size={18} /></button>
            </div>
            <div className="kx-reader-body">
              {opening ? (
                <p style={{ color: 'var(--text-secondary)' }}>Opening...</p>
              ) : openError ? (
                <p style={{ color: '#fca5a5' }}>{openError}</p>
              ) : openItem.content ? (
                <Markdown text={openItem.content} />
              ) : (
                <p style={{ color: 'var(--text-secondary)' }}>This item has no text.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default Knowledge;
