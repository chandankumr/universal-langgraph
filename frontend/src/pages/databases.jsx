import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import api from '../services/api';

export default function Databases() {
  const [databases, setDatabases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState(null);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    // Basic Auth Check
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }
    fetchDatabases();
  }, [router]);

  const fetchDatabases = async () => {
    try {
      const response = await api.get('/api/v1/vector-dbs/supported');
      setDatabases(response.data);
    } catch (err) {
      setError('Failed to load supported databases.');
      if (err.response?.status === 401) router.push('/login');
    } finally {
      setLoading(false);
    }
  };

  const handleDeploy = async (dbType) => {
    setDeploying(dbType);
    try {
      await api.post('/api/v1/vector-dbs/deploy', { db_type: dbType });
      alert(`✅ Successfully triggered deployment for ${dbType}!`);
      // Optionally re-fetch statuses here if your API supports it
    } catch (err) {
      alert(`❌ Failed to deploy ${dbType}: ${err.response?.data?.detail || err.message}`);
    } finally {
      setDeploying(null);
    }
  };

  return (
    <div style={{ padding: '40px', maxWidth: '900px', margin: '0 auto', fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <h2>🗄️ Vector Databases</h2>
        <button onClick={() => router.push('/chat')} style={{ padding: '10px 20px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
          Back to Chat
        </button>
      </div>

      {error && <div style={{ padding: '15px', backgroundColor: '#f8d7da', color: '#721c24', borderRadius: '5px', marginBottom: '20px' }}>{error}</div>}

      {loading ? (
        <p>Loading database configurations...</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
          {databases.map((db, idx) => (
            <div key={idx} style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: 'white', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
              <h3 style={{ marginTop: '0', textTransform: 'capitalize' }}>{db.type}</h3>
              
              <div style={{ marginBottom: '20px', fontSize: '14px', color: '#555' }}>
                <p><strong>Configured Port:</strong> {db.config?.port || 'N/A'}</p>
                <p><strong>Status:</strong> Available to Deploy</p>
              </div>

              <button
                onClick={() => handleDeploy(db.type)}
                disabled={deploying === db.type}
                style={{
                  width: '100%',
                  padding: '10px',
                  backgroundColor: deploying === db.type ? '#17a2b8' : '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px',
                  cursor: deploying === db.type ? 'wait' : 'pointer'
                }}
              >
                {deploying === db.type ? 'Deploying...' : 'Deploy Instance'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}