import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Employees } from './pages/Employees';
import { Projects } from './pages/Projects';
import { Knowledge } from './pages/Knowledge';
import { Communications } from './pages/Communications';
import { AIAssistant } from './pages/AIAssistant';

import {
  LayoutDashboard, Users, Briefcase, FileText, Mail, BrainCircuit, LogOut, Terminal
} from 'lucide-react';
import './styles/index.css';

type PageView = 'dashboard' | 'employees' | 'projects' | 'knowledge' | 'communications' | 'ai-assistant';

export const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [activePage, setActivePage] = useState<PageView>('dashboard');
  const [currentUser, setCurrentUser] = useState<any>(null);

  // Check login state on mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    if (token && storedUser) {
      setIsAuthenticated(true);
      setCurrentUser(JSON.parse(storedUser));
    }
  }, []);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      setCurrentUser(JSON.parse(storedUser));
    }
    setActivePage('dashboard');
  };

  const handleLogout = () => {
    api.auth.logout();
    setIsAuthenticated(false);
    setCurrentUser(null);
  };

  // Guard: If not logged in, force Login view
  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  // Render view container
  const renderActivePage = () => {
    switch (activePage) {
      case 'dashboard':
        return <Dashboard />;
      case 'employees':
        return <Employees />;
      case 'projects':
        return <Projects />;
      case 'knowledge':
        return <Knowledge />;
      case 'communications':
        return <Communications />;
      case 'ai-assistant':
        return <AIAssistant />;
      default:
        return <Dashboard />;
    }
  };

  const getPageTitle = () => {
    switch (activePage) {
      case 'dashboard': return 'Command Dashboard';
      case 'employees': return 'Workforce Directory';
      case 'projects': return 'Enterprise Project Boards';
      case 'knowledge': return 'Central Knowledge Catalog';
      case 'communications': return 'Communications Hub';
      case 'ai-assistant': return 'Multi-Agent AI Playground';
      default: return 'Enterprise AI OS';
    }
  };

  return (
    <div className="app-container">
      {/* 1. Navigation Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-logo-icon">Ω</div>
          <span className="sidebar-brand-text">Enterprise AI OS</span>
        </div>

        <ul className="sidebar-menu">
          <li
            onClick={() => setActivePage('dashboard')}
            className={`sidebar-menu-item ${activePage === 'dashboard' ? 'active' : ''}`}
          >
            <LayoutDashboard size={18} /> Command Dashboard
          </li>
          
          <li
            onClick={() => setActivePage('employees')}
            className={`sidebar-menu-item ${activePage === 'employees' ? 'active' : ''}`}
          >
            <Users size={18} /> Workforce Directory
          </li>

          <li
            onClick={() => setActivePage('projects')}
            className={`sidebar-menu-item ${activePage === 'projects' ? 'active' : ''}`}
          >
            <Briefcase size={18} /> Project Boards
          </li>

          <li
            onClick={() => setActivePage('knowledge')}
            className={`sidebar-menu-item ${activePage === 'knowledge' ? 'active' : ''}`}
          >
            <FileText size={18} /> Knowledge Explorer
          </li>

          <li
            onClick={() => setActivePage('communications')}
            className={`sidebar-menu-item ${activePage === 'communications' ? 'active' : ''}`}
          >
            <Mail size={18} /> Communications
          </li>

          <li
            onClick={() => setActivePage('ai-assistant')}
            className={`sidebar-menu-item ${activePage === 'ai-assistant' ? 'active' : ''}`}
          >
            <BrainCircuit size={18} /> AI Assistants
          </li>
        </ul>

        {/* Logged in User profile footer */}
        {currentUser && (
          <div className="sidebar-user">
            <div className="sidebar-user-info">
              <div className="sidebar-avatar">
                {currentUser.first_name?.[0]}{currentUser.last_name?.[0]}
              </div>
              <div className="sidebar-user-details">
                <div className="sidebar-username">{currentUser.first_name} {currentUser.last_name}</div>
                <div className="sidebar-user-role">{currentUser.role}</div>
              </div>
            </div>
            <button 
              onClick={handleLogout}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              title="Sign Out"
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </aside>

      {/* 2. Main View Pane */}
      <div className="main-wrapper">
        <header className="top-bar">
          <h1 className="page-title">{getPageTitle()}</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px', backgroundColor: 'var(--bg-tertiary)', padding: '6px 12px', borderRadius: '20px', border: '1px solid var(--border-color)' }}>
              <Terminal size={14} style={{ color: 'var(--color-primary)' }} /> Live OS Environment
            </span>
          </div>
        </header>

        <main className="main-content">
          {renderActivePage()}
        </main>
      </div>
    </div>
  );
};
export default App;
