import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import api from '../services/api';

export default function Settings() {
  const router = useRouter();
  const [models, setModels] = useState([]);
  const [currentModel, setCurrentModel] = useState(null);
  const [selectedProvider, setSelectedProvider] = useState('ollama');
  const [selectedModel, setSelectedModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [status, setStatus] = useState('');
  const [vectorDb, setVectorDb] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }
    loadSettings();
  }, [router]);

  const loadSettings = async () => {
    try {
      const [modelsRes, currentRes, dbRes] = await Promise.all([
        api.get('/api/v1/models'),
        api.get('/api/v1/models/current'),
        api.get('/api/v1/vector-db/info')
      ]);
      setModels(modelsRes.data);
      setCurrentModel(currentRes.data);
      setVectorDb(dbRes.data);
      setSelectedModel(currentRes.data.model);
      setSelectedProvider(currentRes.data.provider);
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const handleSwitchModel = async () => {
    try {
      const formData = new FormData();
      formData.append('provider', selectedProvider);
      formData.append('model', selectedModel);
      if (apiKey) formData.append('api_key', apiKey);

      // await api.post('/api/v1/models/switch', formData);
      await api.post('/api/v1/models/switch', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setStatus('✅ Model switched! Restart backend to apply.');
    } catch (error) {
      console.error('Switch error:', error);
      setStatus('❌ Failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1>⚙️ Settings</h1>
        <button onClick={handleLogout} style={styles.logoutBtn}>Logout</button>
      </div>

      <div style={styles.content}>
        {/* Model Selection */}
        <div style={styles.card}>
          <h3>🤖 Select AI Model</h3>
          
          <div style={styles.formGroup}>
            <label>Provider:</label>
            <select 
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              style={styles.select}
            >
              <option value="ollama">️ Ollama (Local - Free)</option>
              <option value="groq">⚡ Groq (Cloud - Free Tier)</option>
              <option value="google">🔮 Google Gemini (Cloud - Free Tier)</option>
              <option value="openai">🟢 OpenAI (Cloud - Paid)</option>
              <option value="azure_openai">☁️ Azure OpenAI (Cloud - Enterprise)</option>
            </select>
          </div>

          <div style={styles.formGroup}>
            <label>Model:</label>
            <select 
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={styles.select}
            >
              {models
                .filter(m => m.provider === selectedProvider)
                .map(m => (
                  <option key={m.model} value={m.model}>
                    {m.model} {m.free ? '(Free)' : '(Paid)'}
                  </option>
                ))
              }
            </select>
          </div>

          {(selectedProvider === 'openai' || selectedProvider === 'groq' || selectedProvider === 'google') && (
            <div style={styles.formGroup}>
              <label>API Key:</label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your API key"
                style={styles.input}
              />
            </div>
          )}

          <button onClick={handleSwitchModel} style={styles.btnPrimary}>
            Switch Model
          </button>

          {status && <p style={styles.status}>{status}</p>}

          {currentModel && (
            <div style={styles.currentInfo}>
              <p><strong>Current:</strong> {currentModel.provider} / {currentModel.model}</p>
            </div>
          )}
        </div>

        {/* Vector DB Info */}
        {vectorDb && (
          <div style={styles.card}>
            <h3>🗄️ Vector Database</h3>
            <div style={styles.infoRow}>
              <span>Type:</span>
              <strong>{vectorDb.type}</strong>
            </div>
            <div style={styles.infoRow}>
              <span>Persist Directory:</span>
              <code>{vectorDb.persist_directory}</code>
            </div>
            <div style={styles.infoRow}>
              <span>Collection:</span>
              <strong>{vectorDb.collection}</strong>
            </div>
          </div>
        )}

        {/* Available Models Table */}
        <div style={styles.card}>
          <h3>📋 Available Models</h3>
          <table style={styles.table}>
            <thead>
              <tr>
                <th>Provider</th>
                <th>Model</th>
                <th>Type</th>
                <th>Free</th>
              </tr>
            </thead>
            <tbody>
              {models.map(m => (
                <tr key={m.model}>
                  <td>{m.provider}</td>
                  <td>{m.model}</td>
                  <td>{m.type}</td>
                  <td>{m.free ? '✅' : '❌'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Navigation */}
      <div style={styles.nav}>
        <a href="/chat" style={styles.navLink}>💬 Chat</a>
        <a href="/documents" style={styles.navLink}>📄 Documents</a>
        <a href="/settings" style={{...styles.navLink, fontWeight: 'bold'}}>⚙️ Settings</a>
      </div>
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', backgroundColor: '#f5f5f5', fontFamily: 'system-ui' },
  header: { padding: '20px', backgroundColor: '#1a1a2e', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  logoutBtn: { padding: '10px 20px', backgroundColor: '#e94560', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' },
  content: { padding: '20px', maxWidth: '800px', margin: '0 auto' },
  card: { backgroundColor: 'white', padding: '25px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', marginBottom: '20px' },
  formGroup: { marginBottom: '20px' },
  select: { width: '100%', padding: '12px', borderRadius: '5px', border: '1px solid #ddd', marginTop: '8px', fontSize: '14px' },
  input: { width: '100%', padding: '12px', borderRadius: '5px', border: '1px solid #ddd', marginTop: '8px', boxSizing: 'border-box' },
  btnPrimary: { padding: '12px 30px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '16px' },
  status: { marginTop: '15px', padding: '10px', backgroundColor: '#d4edda', borderRadius: '5px', color: '#155724' },
  currentInfo: { marginTop: '20px', padding: '15px', backgroundColor: '#e7f3ff', borderRadius: '5px' },
  infoRow: { display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid #eee' },
  table: { width: '100%', borderCollapse: 'collapse', marginTop: '15px' },
  nav: { display: 'flex', justifyContent: 'center', gap: '30px', padding: '20px', backgroundColor: 'white', borderTop: '1px solid #ddd' },
  navLink: { color: '#333', textDecoration: 'none', fontSize: '16px' }
};



















// import React, { useState } from 'react';
// import { useRouter } from 'next/router';
// import api from '../services/api';

// export default function Settings() {
//   const [openAiKey, setOpenAiKey] = useState('');
//   const [status, setStatus] = useState('');
//   const router = useRouter();

//   const saveApiKey = async () => {
//     try {
//       // Note: This endpoint might need authentication implemented in backend first
//       await api.post('/api/v1/keys', {
//         provider: 'openai',
//         api_key: openAiKey
//       });
//       setStatus('✅ API Key saved!');
//     } catch (error) {
//       setStatus('❌ Failed to save API key (Backend may require auth)');
//     }
//   };

//   const handleLogout = () => {
//     localStorage.removeItem('token');
//     router.push('/login');
//   };

//   return (
//     <div style={{ padding: '40px', fontFamily: 'system-ui' }}>
//       <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
//         <h1>⚙️ Settings</h1>
//         <button onClick={handleLogout} style={{ padding: '10px 20px', cursor: 'pointer' }}>Logout</button>
//       </div>

//       <div style={{ maxWidth: '600px', backgroundColor: 'white', padding: '30px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
//         <h3>OpenAI API Key</h3>
//         <p style={{ color: '#666', marginBottom: '15px' }}>Enter your key to enable cloud LLMs.</p>
        
//         <input
//           type="password"
//           value={openAiKey}
//           onChange={(e) => setOpenAiKey(e.target.value)}
//           placeholder="sk-..."
//           style={{
//             width: '100%',
//             padding: '12px',
//             marginBottom: '15px',
//             borderRadius: '5px',
//             border: '1px solid #ddd',
//             boxSizing: 'border-box'
//           }}
//         />
//         <button
//           onClick={saveApiKey}
//           style={{
//             padding: '12px 25px',
//             backgroundColor: '#007bff',
//             color: 'white',
//             border: 'none',
//             borderRadius: '5px',
//             cursor: 'pointer'
//           }}
//         >
//           Save Key
//         </button>
//         {status && <p style={{ marginTop: '15px', fontWeight: 'bold' }}>{status}</p>}
//       </div>
//     </div>
//   );
// }