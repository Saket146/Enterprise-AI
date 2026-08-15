const BASE_URL = 'http://localhost:8000';

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
      throw new Error(errorData.detail || 'An error occurred during network request.');
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
  },
  
  communications: {
    getEmails: () => request('/api/communications/emails'),
    getMeetings: () => request('/api/communications/meetings'),
    getChats: () => request('/api/communications/chats'),
    getChat: (id: number) => request(`/api/communications/chats/${id}`),
    createChat: (title: string) => request(`/api/communications/chats?title=${encodeURIComponent(title)}`, {
      method: 'POST',
    }),
    sendMessage: (id: number, text: string) => request(`/api/communications/chats/${id}/message?message=${encodeURIComponent(text)}`, {
      method: 'POST',
    }),
  },
  
  ingestion: {
    syncQdrant: () => request('/api/ingestion/qdrant', { method: 'POST' }),
    syncNeo4j: () => request('/api/ingestion/neo4j', { method: 'POST' }),
  }
};
