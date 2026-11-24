// Same address as the website: in development Vite forwards /api and /health to the backend
// (see vite.config.ts); in production the backend serves this website itself.
// Set VITE_API_URL only if the backend runs on a different address.
const BASE_URL: string = (import.meta as any).env?.VITE_API_URL || '';

// Retrieve authorization token from localStorage
const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// Generic fetch wrapper helper
const request = async (
  endpoint: string,
  options: RequestInit = {}
): Promise<any> => {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
    ...(options.headers || {}),
  } as Record<string, string>;

  // Convert relative endpoints to absolute URLs if needed
  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, { ...options, headers });
    
    if (response.status === 401) {
      // Clear credentials on authentication expired
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      // FastAPI sends `detail` as text, or as a list of validation problems
      const detail = Array.isArray(errorData.detail)
        ? errorData.detail.map((d: any) => d.msg || String(d)).join('; ')
        : errorData.detail;
      const error = new Error(detail || 'An error occurred during network request.') as Error & { status?: number };
      error.status = response.status;
      throw error;
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Request failed:', error);
    throw error;
  }
};

export const api = {
  auth: {
    login: async (email: string, password: string) => {
      const res = await request('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('user', JSON.stringify({
        employee_id: res.employee_id,
        email: res.email,
        role: res.role,
        first_name: res.first_name,
        last_name: res.last_name
      }));
      return res;
    },
    logout: () => {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    },
    getProfile: () => request('/api/auth/profile'),
    getPermissions: () => request('/api/auth/permissions'),
  },
  
  employees: {
    list: (params: {
      search?: string;
      department_id?: number;
      role_id?: number;
      manager_id?: number;
      status?: string;
      skip?: number;
      limit?: number;
    } = {}) => {
      const query = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') query.append(k, String(v));
      });
      return request(`/api/employees?${query.toString()}`);
    },
    getHierarchy: () => request('/api/employees/hierarchy'),
    get: (id: number) => request(`/api/employees/${id}`),
    update: (id: number, data: any) => request(`/api/employees/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
    delete: (id: number) => request(`/api/employees/${id}`, {
      method: 'DELETE',
    }),
  },
  
  projects: {
    list: (params: {
      search?: string;
      department_id?: number;
      manager_id?: number;
      client_id?: number;
      status?: string;
      skip?: number;
      limit?: number;
    } = {}) => {
      const query = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') query.append(k, String(v));
      });
      return request(`/api/projects?${query.toString()}`);
    },
    get: (id: number) => request(`/api/projects/${id}`),
    getTasks: (id: number, status?: string) => {
      const q = status ? `?status=${status}` : '';
      return request(`/api/projects/${id}/tasks${q}`);
    },
    getMilestones: (id: number) => request(`/api/projects/${id}/milestones`),
  },
  
  knowledge: {
    listDocuments: (params: {
      search?: string;
      project_id?: number;
      department_id?: number;
      doc_type?: string;
      skip?: number;
      limit?: number;
    } = {}) => {
      const query = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') query.append(k, String(v));
      });
      return request(`/api/knowledge/documents?${query.toString()}`);
    },
    listPolicies: (params: {
      search?: string;
      department_id?: number;
      skip?: number;
      limit?: number;
    } = {}) => {
      const query = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') query.append(k, String(v));
      });
      return request(`/api/knowledge/policies?${query.toString()}`);
    },
    semanticSearch: (params: {
      query: string;
      collection?: string;
      limit?: number;
      project_id?: number;
      department_id?: number;
    }) => {
      const q = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') q.append(k, String(v));
      });
      return request(`/api/knowledge/semantic-search?${q.toString()}`);
    },
    // What the current role may see: "content" (open and read), "titles" (list only) or "none"
    access: () => request('/api/knowledge/access'),
    openDocument: (id: number) => request(`/api/knowledge/documents/${id}`),
    openPolicy: (id: number) => request(`/api/knowledge/policies/${id}`),
    // Source search used inside the AI Assistant (database keyword matches + vector matches when available)
    search: (query: string, scope: string = 'all', limit: number = 8) => {
      const q = new URLSearchParams({ query, scope, limit: String(limit) });
      return request(`/api/knowledge/search?${q.toString()}`);
    },
  },
  
  communications: {
    getEmails: () => request('/api/communications/emails'),
    getMeetings: () => request('/api/communications/meetings'),
    getChats: () => request('/api/communications/chats'),
    getChat: (id: number) => request(`/api/communications/chats/${id}`),
    // A chat created without a title is named automatically from its first question
    createChat: (title?: string) => request('/api/communications/chats', {
      method: 'POST',
      body: JSON.stringify(title ? { title } : {}),
    }),
    renameChat: (id: number, title: string) => request(`/api/communications/chats/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    }),
    deleteChat: (id: number) => request(`/api/communications/chats/${id}`, {
      method: 'DELETE',
    }),
    sendMessage: (id: number, text: string) => request(`/api/communications/chats/${id}/message`, {
      method: 'POST',
      body: JSON.stringify({ message: text }),
    }),
  },
  
  ingestion: {
    syncQdrant: () => request('/api/ingestion/qdrant', { method: 'POST' }),
    syncNeo4j: () => request('/api/ingestion/neo4j', { method: 'POST' }),
  },
  workflows: {
    types: () => request('/api/workflows/types'),
    run: (data: { workflow_type: string; title: string; payload: string; document_id?: number; requires_approval?: boolean }) => request('/api/workflows/run', { method: 'POST', body: JSON.stringify(data) }),
    requests: (scope: 'mine' | 'all' = 'mine') => request(`/api/workflows/requests?scope=${scope}`),
    runs: () => request('/api/workflows/runs'),
    approvals: () => request('/api/workflows/approvals'),
    decide: (approvalId: number, approved: boolean, note: string) => request(`/api/workflows/approvals/${approvalId}`, { method: 'POST', body: JSON.stringify({ approved, note }) }),
  },
  analytics: { overview: () => request('/api/analytics/overview') },
  monitoring: {
    dashboard: () => request('/api/monitoring/dashboard'),
    llm: () => request('/api/monitoring/llm'),
    testLlm: () => request('/api/monitoring/llm/test', { method: 'POST' }),
  },
  evaluations: {
    run: () => request('/api/evaluations/run', { method: 'POST' }),
    history: () => request('/api/evaluations/history'),
  },
  system: { dependencies: () => request('/health/dependencies') },
};
