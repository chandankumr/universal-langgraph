import React, { useState } from 'react';
import { useRouter } from 'next/router'; // ✅ Use Next.js router
import api from '../services/api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter(); // ✅ Initialize Next.js router

  // const handleLogin = async (e) => {
  //   e.preventDefault();
  //   setError('');

  //   try {
  //     // For demo, just accept any login
  //     const token = 'demo-token-' + Date.now();
  //     localStorage.setItem('token', token);
      
  //     // ✅ Use Next.js push instead of navigate
  //     router.push('/chat');
  //   } catch (err) {
  //     setError('Login failed. Please try again.');
  //   }
  // };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    try {
      // Call actual login endpoint
      const response = await api.post('/api/v1/auth/login', {
        email: email,
        password: password
      });

      // Store real JWT token
      localStorage.setItem('token', response.data.access_token);
      router.push('/chat');
    } catch (err) {
      // If login fails, create demo account automatically
      try {
        await api.post('/api/v1/auth/register', {
          email: email,
          password: password
        });
        
        // Login after registration
        const loginResponse = await api.post('/api/v1/auth/login', {
          email: email,
          password: password
        });
        
        localStorage.setItem('token', loginResponse.data.access_token);
        router.push('/chat');
      } catch (regError) {
        setError('Login failed. Please try again.');
      }
    }
  };

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      backgroundColor: '#f5f5f5'
    }}>
      <form onSubmit={handleLogin} style={{
        padding: '40px',
        backgroundColor: 'white',
        borderRadius: '10px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
        width: '400px'
      }}>
        <h2 style={{ marginBottom: '30px', textAlign: 'center' }}>🚀 LangGraph Login</h2>
        
        {error && (
          <div style={{ color: 'red', marginBottom: '15px', textAlign: 'center' }}>{error}</div>
        )}

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
          style={{
            width: '100%',
            padding: '15px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          Login
        </button>

        <p style={{ marginTop: '20px', textAlign: 'center', color: '#888' }}>
          Demo: Any email/password works for now
        </p>
      </form>
    </div>
  );
}