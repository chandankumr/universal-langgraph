import React, { useState } from 'react';
import { useRouter } from 'next/router';
import api from '../services/api';

export default function Settings() {
  const [openAiKey, setOpenAiKey] = useState('');
  const [status, setStatus] = useState('');
  const router = useRouter();

  const saveApiKey = async () => {
    try {
      // Note: This endpoint might need authentication implemented in backend first
      await api.post('/api/v1/keys', {
        provider: 'openai',
        api_key: openAiKey
      });
      setStatus('✅ API Key saved!');
    } catch (error) {
      setStatus('❌ Failed to save API key (Backend may require auth)');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  return (
    <div style={{ padding: '40px', fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <h1>⚙️ Settings</h1>
        <button onClick={handleLogout} style={{ padding: '10px 20px', cursor: 'pointer' }}>Logout</button>
      </div>

      <div style={{ maxWidth: '600px', backgroundColor: 'white', padding: '30px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <h3>OpenAI API Key</h3>
        <p style={{ color: '#666', marginBottom: '15px' }}>Enter your key to enable cloud LLMs.</p>
        
        <input
          type="password"
          value={openAiKey}
          onChange={(e) => setOpenAiKey(e.target.value)}
          placeholder="sk-..."
          style={{
            width: '100%',
            padding: '12px',
            marginBottom: '15px',
            borderRadius: '5px',
            border: '1px solid #ddd',
            boxSizing: 'border-box'
          }}
        />
        <button
          onClick={saveApiKey}
          style={{
            padding: '12px 25px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer'
          }}
        >
          Save Key
        </button>
        {status && <p style={{ marginTop: '15px', fontWeight: 'bold' }}>{status}</p>}
      </div>
    </div>
  );
}