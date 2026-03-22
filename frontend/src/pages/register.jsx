import React, { useState } from 'react';
import { useRouter } from 'next/router';
import api from '../services/api';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // 1. Register the user
      await api.post('/api/v1/auth/register', {
        email: email,
        password: password
      });

      // 2. Automatically log them in right after
      const loginResponse = await api.post('/api/v1/auth/login', {
        email: email,
        password: password
      });

      // 3. Store token and redirect
      localStorage.setItem('token', loginResponse.data.access_token);
      router.push('/chat');
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. User might already exist.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#f5f5f5' }}>
      <form onSubmit={handleRegister} style={{ padding: '40px', backgroundColor: 'white', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', width: '400px' }}>
        <h2 style={{ marginBottom: '30px', textAlign: 'center' }}>📝 Create Account</h2>
        
        {error && <div style={{ color: 'red', marginBottom: '15px', textAlign: 'center' }}>{error}</div>}

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #ddd' }}
          />
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '5px' }}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #ddd' }}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{ width: '100%', padding: '15px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '5px', cursor: loading ? 'not-allowed' : 'pointer', fontSize: '16px' }}
        >
          {loading ? 'Creating Account...' : 'Register'}
        </button>

        <p style={{ marginTop: '20px', textAlign: 'center', color: '#555' }}>
          Already have an account? <span onClick={() => router.push('/login')} style={{ color: '#007bff', cursor: 'pointer', textDecoration: 'underline' }}>Login here</span>
        </p>
      </form>
    </div>
  );
}