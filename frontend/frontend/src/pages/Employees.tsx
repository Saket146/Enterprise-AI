import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Search, Filter, Shield, Briefcase, Mail, MapPin } from 'lucide-react';

interface EmployeeItem {
  employee_id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  office_location: string;
  employment_status: string;
  department?: { department_name: string };
  role?: { role_name: string };
}

interface HierarchyNode {
  employee_id: number;
  first_name: string;
  last_name: string;
  email: string;
  role: string | null;
  department: string | null;
  subordinates: HierarchyNode[];
}

export const Employees: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'directory' | 'hierarchy'>('directory');
  const [employees, setEmployees] = useState<EmployeeItem[]>([]);
  const [hierarchy, setHierarchy] = useState<HierarchyNode[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [search, setSearch] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  // Load employee directory
  const loadDirectory = async () => {
    setLoading(true);
    try {
      const res = await api.employees.list({
        search,
        status: status || undefined,
        skip: page * 10,
        limit: 10
      });
      setEmployees(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load employee list:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load corporate hierarchy tree
  const loadHierarchy = async () => {
    setLoading(true);
    try {
      const res = await api.employees.getHierarchy();
      setHierarchy(res || []);
    } catch (err) {
      console.error('Failed to load corporate hierarchy:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'directory') {
      loadDirectory();
    } else {
      loadHierarchy();
    }
  }, [activeTab, search, status, page]);

  // Collapsible hierarchy node component
  const OrgTreeNode: React.FC<{ node: HierarchyNode }> = ({ node }) => {
    const [collapsed, setCollapsed] = useState(false);
    const hasChildren = node.subordinates && node.subordinates.length > 0;

    return (
      <div style={{ marginBottom: '12px' }}>
        <div 
          className="tree-node" 
          onClick={() => hasChildren && setCollapsed(!collapsed)}
          style={{ cursor: hasChildren ? 'pointer' : 'default', borderLeft: '4px solid var(--color-primary)' }}
        >
          <div className="tree-node-title">
            {node.first_name} {node.last_name}
          </div>
          <div className="tree-node-subtitle">
            {node.role || 'Unspecified Role'} • <span style={{ color: 'var(--text-muted)' }}>{node.department || 'No Dept'}</span>
          </div>
          {hasChildren && (
            <span style={{ fontSize: '0.7rem', color: 'var(--color-primary)', marginTop: '4px', display: 'block' }}>
              {collapsed ? `[+] Show Direct Reports (${node.subordinates.length})` : '[-] Hide Direct Reports'}
            </span>
          )}
        </div>
        
        {hasChildren && !collapsed && (
          <div className="tree-children">
            {node.subordinates.map(sub => (
              <OrgTreeNode key={sub.employee_id} node={sub} />
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="animated-fade-in" style={{ height: '100%' }}>
      {/* Tab Selectors */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <button
          onClick={() => setActiveTab('directory')}
          className={`btn ${activeTab === 'directory' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.85rem' }}
        >
          Workforce Directory
        </button>
        <button
          onClick={() => setActiveTab('hierarchy')}
          className={`btn ${activeTab === 'hierarchy' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.85rem' }}
        >
          Reporting Hierarchy
        </button>
      </div>

      {activeTab === 'directory' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Filters Bar */}
          <div className="glass-card" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center', padding: '16px' }}>
            <div style={{ position: 'relative', flexGrow: 1, minWidth: '240px' }}>
              <input
                className="input-field"
                type="text"
                placeholder="Search by employee name, email, location..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                style={{ paddingLeft: '40px' }}
              />
              <Search size={16} style={{ position: 'absolute', left: '16px', top: '15px', color: 'var(--text-secondary)' }} />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '200px' }}>
              <Filter size={16} style={{ color: 'var(--text-secondary)' }} />
              <select
                className="input-field"
                value={status}
                onChange={(e) => { setStatus(e.target.value); setPage(0); }}
                style={{ padding: '10px' }}
              >
                <option value="">All Employment Statuses</option>
                <option value="Active">Active Only</option>
                <option value="Terminated">Terminated</option>
                <option value="On Leave">On Leave</option>
              </select>
            </div>
          </div>

          {/* Directory Content */}
          <div className="glass-card">
            {loading ? (
              <p style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Loading directory records...</p>
            ) : employees.length === 0 ? (
              <p style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No employee records found matching query.</p>
            ) : (
              <div className="table-container">
                <table className="enterprise-table">
                  <thead>
                    <tr>
                      <th>Full Name</th>
                      <th>Work Email</th>
                      <th>Structure Info</th>
                      <th>Location</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {employees.map(emp => (
                      <tr key={emp.employee_id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{emp.first_name} {emp.last_name}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                            <Shield size={12} /> ID: {emp.employee_id}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}>
                            <Mail size={12} style={{ color: 'var(--text-secondary)' }} /> {emp.email}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}>
                            <Briefcase size={12} style={{ color: 'var(--text-secondary)' }} />
                            <div>
                              <div>{emp.role?.role_name || 'Unspecified'}</div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{emp.department?.department_name || 'No Dept'}</div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}>
                            <MapPin size={12} style={{ color: 'var(--text-secondary)' }} /> {emp.office_location || 'Remote'}
                          </div>
                        </td>
                        <td>
                          <span className={`badge ${emp.employment_status === 'Active' ? 'badge-success' : 'badge-warning'}`}>
                            {emp.employment_status || 'Active'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {total > 10 && (
              <div style={{ display: 'flex', justifyItems: 'center', justifyContent: 'center', gap: '16px', marginTop: '24px' }}>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                >
                  Previous
                </button>
                <span style={{ alignSelf: 'center', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  Page {page + 1} of {Math.ceil(total / 10)}
                </span>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                  onClick={() => setPage(page + 1)}
                  disabled={(page + 1) * 10 >= total}
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Org Tree Chart Tab */
        <div className="glass-card" style={{ overflowX: 'auto', minHeight: '400px' }}>
          <h3 style={{ marginBottom: '20px' }}>Enterprise Reporting Structure Graph</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '24px' }}>
            A hierarchical map showing lines of reporting starting from executive officers. Click on nodes with subordinates to collapse/expand departments.
          </p>

          {loading ? (
            <p style={{ color: 'var(--text-secondary)' }}>Retrieving hierarchy nodes...</p>
          ) : hierarchy.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No hierarchical structural data returned.</p>
          ) : (
            <div style={{ padding: '16px', maxWidth: '600px' }}>
              {hierarchy.map(rootNode => (
                <OrgTreeNode key={rootNode.employee_id} node={rootNode} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default Employees;
