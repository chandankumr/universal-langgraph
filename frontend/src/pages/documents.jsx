import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import api from '../services/api';

export default function Documents() {
  const router = useRouter();
  const [documents, setDocuments] = useState([]);
  const [collections, setCollections] = useState([]);
  const [stats, setStats] = useState(null);
  const [vectorDb, setVectorDb] = useState(null);
  const [currentModel, setCurrentModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState('default');
  const [newCollection, setNewCollection] = useState('');

  // Auth check
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  // Load data
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [docsRes, collectionsRes, statsRes, dbRes, modelRes] = await Promise.all([
        api.get('/api/v1/documents'),
        api.get('/api/v1/documents/collections'),
        api.get('/api/v1/documents/stats'),
        api.get('/api/v1/vector-db/info'),
        api.get('/api/v1/models/current')
      ]);

      setDocuments(docsRes.data);
      setCollections(collectionsRes.data);
      setStats(statsRes.data);
      setVectorDb(dbRes.data);
      setCurrentModel(modelRes.data);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('collection_id', selectedCollection);

      await api.post('/api/v1/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      alert('✅ Document uploaded successfully!');
      loadData();
    } catch (error) {
      console.error('Upload error:', error);
      alert('❌ Upload failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await api.delete(`/api/v1/documents/${docId}`);
      alert('✅ Document deleted');
      loadData();
    } catch (error) {
      alert('❌ Delete failed');
    }
  };

  const handleCreateCollection = async () => {
    if (!newCollection.trim()) return;
    setSelectedCollection(newCollection);
    setNewCollection('');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  if (loading) {
    return <div style={styles.loading}>Loading...</div>;
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h1>📄 Document Management</h1>
        <button onClick={handleLogout} style={styles.logoutBtn}>Logout</button>
      </div>

      <div style={styles.grid}>
        {/* Left Panel - Upload & Stats */}
        <div style={styles.panel}>
          {/* Upload Section */}
          <div style={styles.card}>
            <h3>📤 Upload Document</h3>
            
            <div style={styles.formGroup}>
              <label>Select Collection:</label>
              <select 
                value={selectedCollection} 
                onChange={(e) => setSelectedCollection(e.target.value)}
                style={styles.select}
              >
                {collections.map(col => (
                  <option key={col.collection_id} value={col.collection_id}>
                    {col.collection_id} ({col.document_count} docs)
                  </option>
                ))}
                <option value="default">default</option>
              </select>
            </div>

            <div style={styles.formGroup}>
              <label>Create New Collection:</label>
              <div style={styles.inlineForm}>
                <input
                  type="text"
                  value={newCollection}
                  onChange={(e) => setNewCollection(e.target.value)}
                  placeholder="Collection name"
                  style={styles.input}
                />
                <button onClick={handleCreateCollection} style={styles.btnSmall}>Create</button>
              </div>
            </div>

            <div style={styles.uploadSection}>
              <input
                type="file"
                id="file-upload"
                accept=".pdf,.txt,.md,.docx"
                onChange={handleFileUpload}
                disabled={uploading}
                style={{ display: 'none' }}
              />
              <label htmlFor="file-upload" style={styles.uploadBtn}>
                {uploading ? '⏳ Uploading...' : '📁 Choose File'}
              </label>
              <p style={styles.hint}>Supported: PDF, TXT, MD, DOCX</p>
            </div>
          </div>

          {/* Storage Stats */}
          {stats && (
            <div style={styles.card}>
              <h3>💾 Storage Usage</h3>
              <div style={styles.statRow}>
                <span>Documents:</span>
                <strong>{stats.total_documents}</strong>
              </div>
              <div style={styles.statRow}>
                <span>Storage:</span>
                <strong>{stats.total_size_mb} MB / {stats.limit_mb} MB</strong>
              </div>
              <div style={styles.progressBar}>
                <div style={{...styles.progressFill, width: `${stats.usage_percent}%`}}></div>
              </div>
              <p style={styles.hint}>{stats.usage_percent}% used</p>
            </div>
          )}

          {/* Vector DB Info */}
          {vectorDb && (
            <div style={styles.card}>
              <h3>🗄️ Vector Database</h3>
              <div style={styles.statRow}>
                <span>Type:</span>
                <strong>{vectorDb.type}</strong>
              </div>
              <div style={styles.statRow}>
                <span>Collection:</span>
                <strong>{vectorDb.collection}</strong>
              </div>
            </div>
          )}

          {/* Current Model */}
          {currentModel && (
            <div style={styles.card}>
              <h3>🤖 Current Model</h3>
              <div style={styles.statRow}>
                <span>Provider:</span>
                <strong>{currentModel.provider}</strong>
              </div>
              <div style={styles.statRow}>
                <span>Model:</span>
                <strong>{currentModel.model}</strong>
              </div>
              <a href="/settings" style={styles.link}>Change Model →</a>
            </div>
          )}
        </div>

        {/* Right Panel - Document List */}
        <div style={styles.panelWide}>
          <div style={styles.card}>
            <h3>📋 Uploaded Documents ({documents.length})</h3>
            
            {documents.length === 0 ? (
              <div style={styles.emptyState}>
                <p>No documents uploaded yet.</p>
                <p>Upload your first document to start building your knowledge base!</p>
              </div>
            ) : (
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Collection</th>
                    <th>Chunks</th>
                    <th>Size</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map(doc => (
                    <tr key={doc.id}>
                      <td style={styles.filename}>{doc.filename}</td>
                      <td>{doc.file_type.toUpperCase()}</td>
                      <td>{doc.collection_id}</td>
                      <td>{doc.chunk_count}</td>
                      <td>{(doc.file_size / 1024).toFixed(1)} KB</td>
                      <td>
                        <span style={{
                          ...styles.badge,
                          backgroundColor: doc.status === 'ready' ? '#4caf50' : '#ff9800'
                        }}>
                          {doc.status}
                        </span>
                      </td>
                      <td>
                        <button 
                          onClick={() => handleDelete(doc.id)}
                          style={styles.deleteBtn}
                        >
                          🗑️ Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div style={styles.nav}>
        <a href="/chat" style={styles.navLink}>💬 Chat</a>
        <a href="/documents" style={{...styles.navLink, fontWeight: 'bold'}}>📄 Documents</a>
        <a href="/settings" style={styles.navLink}>⚙️ Settings</a>
      </div>
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', backgroundColor: '#f5f5f5', fontFamily: 'system-ui' },
  header: { padding: '20px', backgroundColor: '#1a1a2e', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  logoutBtn: { padding: '10px 20px', backgroundColor: '#e94560', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' },
  grid: { display: 'grid', gridTemplateColumns: '350px 1fr', gap: '20px', padding: '20px' },
  panel: { display: 'flex', flexDirection: 'column', gap: '20px' },
  panelWide: { display: 'flex', flexDirection: 'column' },
  card: { backgroundColor: 'white', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' },
  formGroup: { marginBottom: '15px' },
  select: { width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #ddd', marginTop: '5px' },
  input: { flex: 1, padding: '10px', borderRadius: '5px', border: '1px solid #ddd' },
  inlineForm: { display: 'flex', gap: '10px', marginTop: '5px' },
  btnSmall: { padding: '10px 15px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' },
  uploadSection: { textAlign: 'center', padding: '20px', border: '2px dashed #ddd', borderRadius: '10px' },
  uploadBtn: { display: 'inline-block', padding: '15px 30px', backgroundColor: '#007bff', color: 'white', borderRadius: '5px', cursor: 'pointer', marginTop: '10px' },
  hint: { color: '#888', fontSize: '12px', marginTop: '10px' },
  statRow: { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #eee' },
  progressBar: { height: '10px', backgroundColor: '#eee', borderRadius: '5px', marginTop: '10px', overflow: 'hidden' },
  progressFill: { height: '100%', backgroundColor: '#4caf50', transition: 'width 0.3s' },
  link: { color: '#007bff', textDecoration: 'none', display: 'block', marginTop: '10px' },
  table: { width: '100%', borderCollapse: 'collapse' },
  filename: { maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' },
  badge: { padding: '4px 8px', borderRadius: '3px', color: 'white', fontSize: '12px' },
  deleteBtn: { padding: '5px 10px', backgroundColor: '#e94560', color: 'white', border: 'none', borderRadius: '3px', cursor: 'pointer' },
  nav: { display: 'flex', justifyContent: 'center', gap: '30px', padding: '20px', backgroundColor: 'white', borderTop: '1px solid #ddd' },
  navLink: { color: '#333', textDecoration: 'none', fontSize: '16px' },
  loading: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontSize: '20px' },
  emptyState: { textAlign: 'center', padding: '40px', color: '#888' }
};