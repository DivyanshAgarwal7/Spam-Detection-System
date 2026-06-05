import { useState } from 'react';
import api from '../utils/axiosInstance';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Login = () => {
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email || !form.password) { setError('Please fill in all fields.'); return; }

    setLoading(true);
    try {
      const res = await api.post('/api/auth/login', form);
      localStorage.setItem('token', res.data.token);
      localStorage.setItem('user', JSON.stringify(res.data.user));
      login(res.data.user);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>📩 Spam Detector</h2>
        <p style={styles.subtitle}>Sign in to your account</p>

        {error && <div style={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div style={styles.formGroup}>
            <label style={styles.label}>Email</label>
            <input type="email" name="email" value={form.email} onChange={handleChange}
              placeholder="you@example.com" style={styles.input} />
          </div>
          <div style={styles.formGroup}>
            <label style={styles.label}>Password</label>
            <input type="password" name="password" value={form.password} onChange={handleChange}
              placeholder="••••••••" style={styles.input} />
          </div>
          <button type="submit" disabled={loading}
            style={{ ...styles.button, opacity: loading ? 0.6 : 1 }}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p style={styles.switchText}>
          Don't have an account?{' '}
          <Link to="/register" style={styles.link}>Register here</Link>
        </p>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh', display: 'flex', alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #1a1a2e, #16213e)',
    padding: '20px',
  },
  card: {
    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '16px', padding: '40px', width: '100%', maxWidth: '420px', color: '#fff',
  },
  title: { textAlign: 'center', fontSize: '24px', marginBottom: '6px' },
  subtitle: { textAlign: 'center', opacity: 0.6, marginBottom: '28px', fontSize: '14px' },
  error: {
    background: 'rgba(248,113,113,0.15)', border: '1px solid rgba(248,113,113,0.4)',
    color: '#f87171', padding: '10px 14px', borderRadius: '8px',
    marginBottom: '16px', fontSize: '14px',
  },
  formGroup: { marginBottom: '18px' },
  label: { display: 'block', marginBottom: '6px', fontSize: '14px', opacity: 0.8 },
  input: {
    width: '100%', padding: '10px 14px',
    background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)',
    borderRadius: '8px', color: '#fff', fontSize: '15px',
    outline: 'none', boxSizing: 'border-box',
  },
  button: {
    width: '100%', padding: '12px',
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    color: '#fff', border: 'none', borderRadius: '8px',
    fontSize: '16px', fontWeight: '600', cursor: 'pointer', marginTop: '8px',
  },
  switchText: { textAlign: 'center', marginTop: '20px', fontSize: '14px', opacity: 0.7 },
  link: { color: '#818cf8', textDecoration: 'none' },
};

export default Login;
