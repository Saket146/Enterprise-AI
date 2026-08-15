import React, { useState } from 'react';
import { api } from '../services/api';

interface LoginProps {
  onLoginSuccess: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await api.auth.login(email, password);
      onLoginSuccess();
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="glass-card login-card animated-fade-in">
        <div className="login-header">
          <div style={{ display: 'inline-block' }} className="sidebar-logo-icon">Ω</div>
          <h2>Enterprise AI OS</h2>
          <p>Multi-Agent Intelligence Platform</p>
        </div>

        {error && (
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid var(--color-danger)',
            color: 'white',
            padding: '12px',
            borderRadius: '8px',
            marginBottom: '20px',
            fontSize: '0.85rem',
            textAlign: 'center'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="email">Work Email</label>
            <input
              className="input-field"
              type="email"
              id="email"
              placeholder="e.g. admin@enterprise.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              className="input-field"
              type="password"
              id="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '12px' }}
            type="submit"
            disabled={loading}
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <p>Default Testing Credentials:</p>
          <p style={{ marginTop: '4px', fontFamily: 'monospace' }}>admin@enterprise.com / adminpass</p>
        </div>
      </div>
    </div>
  );
};
export default Login;
