import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import api from '../services/api';

export default function Admin() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [postgresTables, setPostgresTables] = useState([]);
  const [vectorDbStatus, setVectorDbStatus] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }
    loadAdminData();
  }, [router]);

  const loadAdminData = async () => {
    try {
      const [tablesRes, vectorRes, statsRes] = await Promise.all([
        api.get('/api/v1/admin/postgres/tables'),
        api.get('/api/v1/vector-dbs/status'),
        api.get('/api/v1/documents/stats')
      ]);

      setPostgresTables(tablesRes.data);
      setVectorDbStatus(vectorRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error('Error loading admin ', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  if (loading) {
    return <div style={styles.loading}>Loading admin dashboard...</div>;
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1>🔧 Admin Dashboard</h1>
        <button onClick={handleLogout} style={styles.logoutBtn}>Logout</button>
      </div>

      <div style={styles.grid}>
        {/* PostgreSQL Tables */}
        <div style={styles.card}>
          <h3>🐘 PostgreSQL Database</h3>
          <p style={styles.subtitle}>langgraph_platform</p>
          
          <table style={styles.table}>
            <thead>
              <tr>
                <th>Table Name</th>
                <th>Row Count</th>
                <th>Purpose</th>
              </tr>
            </thead>
            <tbody>
              {postgresTables.map(table => (
                <tr key={table.name}>
                  <td style={styles.code}>{table.name}</td>
                  <td>{table.row_count}</td>
                  <td>{table.description}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={styles.infoBox}>
            <strong>💡 Purpose:</strong> Stores user accounts, authentication, 
            document metadata, conversation history, and user preferences.
          </div>
        </div>

        {/* Vector Databases */}
        <div style={styles.card}>
          <h3>🗄️ Vector Databases</h3>
          <p style={styles.subtitle}>Semantic Search & Embeddings</p>
          
          {vectorDbStatus && (
            <>
              <div style={styles.statRow}>
                <span>Current DB:</span>
                <strong>{vectorDbStatus.current_db}</strong>
              </div>
              
              <div style={styles.dbList}>
                {Object.entries(vectorDbStatus.databases || {}).map(([type, info]) => (
                  <div key={type} style={{
                    ...styles.dbBadge,
                    backgroundColor: info.is_active ? '#4caf50' : '#f5f5f5',
                    color: info.is_active ? 'white' : '#666',
                    border: info.configured ? '2px solid #4caf50' : '2px solid #ddd'
                  }}>
                    <div style={styles.dbBadgeHeader}>
                      <span>{type}</span>
                      {info.configured ? '✅' : '⚠️'}
                    </div>
                    <div style={styles.dbBadgeStatus}>
                      {info.is_active ? '● Active' : '○ Available'}
                    </div>
                  </div>
                ))}
              </div>

              <div style={styles.infoBox}>
                <strong>💡 Purpose:</strong> Stores document embeddings for semantic 
                search. Documents are chunked and converted to vectors for AI retrieval.
              </div>
            </>
          )}
        </div>

        {/* Storage Stats */}
        {stats && (
          <div style={styles.card}>
            <h3>📊 Storage Statistics</h3>
            <div style={styles.statGrid}>
              <div style={styles.statBox}>
                <div style={styles.statValue}>{stats.total_documents}</div>
                <div style={styles.statLabel}>Documents</div>
              </div>
              <div style={styles.statBox}>
                <div style={styles.statValue}>{stats.total_chunks}</div>
                <div style={styles.statLabel}>Vector Chunks</div>
              </div>
              <div style={styles.statBox}>
                <div style={styles.statValue}>{stats.total_size_mb} MB</div>
                <div style={styles.statLabel}>Storage Used</div>
              </div>
              <div style={styles.statBox}>
                <div style={styles.statValue}>{stats.usage_percent}%</div>
                <div style={styles.statLabel}>Capacity</div>
              </div>
            </div>
          </div>
        )}

        {/* System Info */}
        <div style={styles.card}>
          <h3>⚙️ System Information</h3>
          <div style={styles.statRow}>
            <span>Backend:</span>
            <strong>FastAPI (Python 3.11)</strong>
          </div>
          <div style={styles.statRow}>
            <span>Frontend:</span>
            <strong>Next.js (React)</strong>
          </div>
          <div style={styles.statRow}>
            <span>LangGraph:</span>
            <strong>Agentic Workflows</strong>
          </div>
          <div style={styles.statRow}>
            <span>Embeddings:</span>
            <strong>BAAI/bge-small-en-v1.5</strong>
          </div>
          <div style={styles.statRow}>
            <span>Deployed:</span>
            <strong>Docker (Mac M1)</strong>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div style={styles.nav}>
        <a href="/chat" style={styles.navLink}>💬 Chat</a>
        <a href="/documents" style={styles.navLink}>📄 Documents</a>
        <a href="/settings" style={styles.navLink}>⚙️ Settings</a>
        <a href="/admin" style={{...styles.navLink, fontWeight: 'bold'}}>🔧 Admin</a>
      </div>
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', backgroundColor: '#f5f5f5', fontFamily: 'system-ui' },
  header: { padding: '20px', backgroundColor: '#1a1a2e', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  logoutBtn: { padding: '10px 20px', backgroundColor: '#e94560', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '20px', padding: '20px' },
  card: { backgroundColor: 'white', padding: '25px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' },
  subtitle: { color: '#888', fontSize: '14px', marginBottom: '20px' },
  table: { width: '100%', borderCollapse: 'collapse', marginBottom: '20px' },
  code: { fontFamily: 'monospace', backgroundColor: '#f5f5f5', padding: '4px 8px', borderRadius: '3px' },
  statRow: { display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid #eee' },
  dbList: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginTop: '15px' },
  dbBadge: { padding: '15px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s' },
  dbBadgeHeader: { display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', marginBottom: '5px' },
  dbBadgeStatus: { fontSize: '12px', opacity: 0.8 },
  infoBox: { marginTop: '20px', padding: '15px', backgroundColor: '#e7f3ff', borderRadius: '5px', borderLeft: '4px solid #007bff' },
  statGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' },
  statBox: { padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px', textAlign: 'center' },
  statValue: { fontSize: '28px', fontWeight: 'bold', color: '#007bff' },
  statLabel: { fontSize: '12px', color: '#888', marginTop: '5px' },
  nav: { display: 'flex', justifyContent: 'center', gap: '30px', padding: '20px', backgroundColor: 'white', borderTop: '1px solid #ddd' },
  navLink: { color: '#333', textDecoration: 'none', fontSize: '16px' },
  loading: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontSize: '20px' }
};