import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Search, BrainCircuit, FileText, Landmark, Clock, Percent } from 'lucide-react';

interface DocumentItem {
  document_id: number;
  title: string;
  document_type: string;
  file_name: string;
  created_at: string;
  creator?: { first_name: string; last_name: string };
  department?: { department_name: string };
}

interface PolicyItem {
  policy_id: number;
  policy_name: string;
  version: string;
  effective_date: string;
  description: string;
  department?: { department_name: string };
}

interface VectorSearchHit {
  score: number;
  text: string;
  metadata: {
    title?: string;
    policy_name?: string;
    type?: string;
    timestamp?: string;
  };
}

export const Knowledge: React.FC = () => {
  const [activeSpace, setActiveSpace] = useState<'documents' | 'policies' | 'vector'>('documents');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [policies, setPolicies] = useState<PolicyItem[]>([]);
  const [vectorHits, setVectorHits] = useState<VectorSearchHit[]>([]);
  const [search, setSearch] = useState<string>('');
  const [vectorQuery, setVectorQuery] = useState<string>('');
  const [vectorCollection, setVectorCollection] = useState<string>('documents');
  const [loading, setLoading] = useState<boolean>(true);

  // Load Relational database lists
  const loadRelational = async () => {
    setLoading(true);
    try {
      if (activeSpace === 'documents') {
        const res = await api.knowledge.listDocuments({ search });
        setDocuments(res || []);
      } else if (activeSpace === 'policies') {
        const res = await api.knowledge.listPolicies({ search });
        setPolicies(res || []);
      }
    } catch (err) {
      console.error('Failed to load knowledge assets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeSpace !== 'vector') {
      loadRelational();
    }
  }, [activeSpace, search]);

  const handleVectorSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vectorQuery.trim()) return;

    setLoading(true);
    try {
      const res = await api.knowledge.semanticSearch({
        query: vectorQuery,
        collection: vectorCollection,
        limit: 5
      });
      // Handle either global object mapping or collection list array
      if (Array.isArray(res)) {
        setVectorHits(res);
      } else {
        // Global search gives a map
        const merged: VectorSearchHit[] = [];
        Object.entries(res).forEach(([colName, hits]: [string, any]) => {
          hits.forEach((h: any) => {
            merged.push({
              ...h,
              metadata: {
                ...h.metadata,
                type: colName.toUpperCase()
              }
            });
          });
        });
        setVectorHits(merged.sort((a, b) => b.score - a.score));
      }
    } catch (err) {
      console.error('Semantic search failed:', err);
    } finally {
      setLoading(false);
    }
  };

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

        <button
          onClick={() => { setActiveSpace('vector'); setVectorHits([]); }}
          className={`btn ${activeSpace === 'vector' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ width: '100%', justifyContent: 'flex-start', padding: '12px 16px' }}
        >
          <BrainCircuit size={16} /> AI Vector Search (RAG)
        </button>
      </div>

      {/* 2. Main Explorer Area */}
      <div className="split-main" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {activeSpace !== 'vector' ? (
          <>
            {/* Relational Catalog View */}
            <div className="glass-card" style={{ display: 'flex', gap: '16px', alignItems: 'center', padding: '16px' }}>
              <div style={{ position: 'relative', flexGrow: 1 }}>
                <input
                  className="input-field"
                  type="text"
                  placeholder={`Search ${activeSpace}...`}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{ paddingLeft: '40px' }}
                />
                <Search size={16} style={{ position: 'absolute', left: '16px', top: '15px', color: 'var(--text-secondary)' }} />
              </div>
            </div>

            <div className="glass-card">
              {loading ? (
                <p style={{ color: 'var(--text-secondary)' }}>Loading catalog items...</p>
              ) : activeSpace === 'documents' ? (
                // Documents List
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
                        </tr>
                      </thead>
                      <tbody>
                        {documents.map(doc => (
                          <tr key={doc.document_id}>
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
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )
              ) : (
                // Policies List
                policies.length === 0 ? (
                  <p>No policy assets found.</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {policies.map(pol => (
                      <div key={pol.policy_id} style={{ padding: '20px', border: '1px solid var(--border-color)', borderRadius: '12px', backgroundColor: 'rgba(255, 255, 255, 0.01)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <h4 style={{ fontSize: '1.05rem', fontWeight: 600 }}>{pol.policy_name}</h4>
                          <span className="badge badge-success">Version {pol.version}</span>
                        </div>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
                          Effective: {pol.effective_date} • Department: {pol.department?.department_name || 'All'}
                        </p>
                        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                          {pol.description}
                        </p>
                      </div>
                    ))}
                  </div>
                )
              )}
            </div>
          </>
        ) : (
          /* Semantic Vector Search View */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div className="glass-card">
              <h3 style={{ marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <BrainCircuit size={20} className="text-primary" /> AI Semantic Explorer (Qdrant Neural Search)
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '24px' }}>
                Type queries to run semantic match neural scans against Qdrant. Computes cosine similarity values against vector embeddings of documents, policies, emails, and chats.
              </p>

              <form onSubmit={handleVectorSearch} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ position: 'relative', flexGrow: 1, minWidth: '240px' }}>
                  <input
                    className="input-field"
                    type="text"
                    placeholder="Ask a question or enter a search query..."
                    value={vectorQuery}
                    onChange={(e) => setVectorQuery(e.target.value)}
                    style={{ paddingLeft: '40px' }}
                    required
                  />
                  <Search size={16} style={{ position: 'absolute', left: '16px', top: '15px', color: 'var(--text-secondary)' }} />
                </div>

                <select
                  className="input-field"
                  value={vectorCollection}
                  onChange={(e) => setVectorCollection(e.target.value)}
                  style={{ width: '180px', padding: '10px' }}
                >
                  <option value="global">Global Search</option>
                  <option value="documents">Documents</option>
                  <option value="policies">Policies</option>
                  <option value="emails">Emails</option>
                  <option value="meetings">Meetings</option>
                  <option value="chats">Chats</option>
                </select>

                <button className="btn btn-primary" type="submit" disabled={loading}>
                  Run Query
                </button>
              </form>
            </div>

            {loading ? (
              <div className="glass-card" style={{ padding: '32px', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-secondary)' }}>Searching vector databases...</p>
              </div>
            ) : vectorHits.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {vectorHits.map((hit, i) => (
                  <div
                    key={i}
                    className="glass-card"
                    style={{
                      borderLeft: '4px solid var(--color-primary)',
                      backgroundColor: 'rgba(255, 255, 255, 0.01)'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-primary)', textTransform: 'uppercase' }}>
                        Source: {hit.metadata.title || hit.metadata.policy_name || hit.metadata.type || 'Collection Hit'}
                      </span>
                      <span className="badge badge-success" style={{ fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Percent size={10} /> Similarity: {Math.round(hit.score * 100)}%
                      </span>
                    </div>

                    <p style={{
                      fontSize: '0.9rem',
                      color: 'var(--text-secondary)',
                      lineHeight: 1.6,
                      backgroundColor: 'rgba(0,0,0,0.2)',
                      padding: '12px',
                      borderRadius: '8px',
                      fontFamily: 'var(--font-sans)',
                      border: '1px solid var(--border-color)'
                    }}>
                      "{hit.text}"
                    </p>
                  </div>
                ))}
              </div>
            ) : vectorQuery ? (
              <div className="glass-card" style={{ padding: '32px', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-secondary)' }}>No neural matches found for query.</p>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};
export default Knowledge;
