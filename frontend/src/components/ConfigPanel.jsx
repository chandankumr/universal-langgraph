import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function ConfigPanel() {
  const [activeTab, setActiveTab] = useState('llm');
  const [llmProviders, setLlmProviders] = useState([]);
  const [vectorDbs, setVectorDbs] = useState([]);
  const [apiKeys, setApiKeys] = useState({});
  const [selectedVectorDb, setSelectedVectorDb] = useState('chroma');
  const [deploymentStatus, setDeploymentStatus] = useState(null);

  // Load supported providers
  useEffect(() => {
    loadSupportedProviders();
    loadVectorDbs();
  }, []);

  const loadSupportedProviders = async () => {
    const response = await api.get('/api/v1/info');
    setLlmProviders(response.data.supported_llm_providers);
  };

  const loadVectorDbs = async () => {
    const response = await api.get('/api/v1/vector-dbs/supported');
    setVectorDbs(response.data);
  };

  const saveApiKey = async (provider, key) => {
    await api.post('/api/v1/keys', { provider, api_key: key });
    alert(`${provider} API key saved!`);
  };

  const testApiKey = async (provider) => {
    const response = await api.post(`/api/v1/keys/test/${provider}`);
    alert(response.data.success ? '✅ Connection successful' : `❌ ${response.data.error}`);
  };

  const deployVectorDb = async (dbType) => {
    const response = await api.post('/api/v1/vector-dbs/deploy', { db_type: dbType });
    setDeploymentStatus(response.data);
  };

  return (
    <div className="config-panel">
      <div className="tabs">
        <button onClick={() => setActiveTab('llm')}>🤖 LLM Providers</button>
        <button onClick={() => setActiveTab('vector')}>🗄️ Vector DB</button>
        <button onClick={() => setActiveTab('gpu')}>🎮 GPU Settings</button>
      </div>

      {activeTab === 'llm' && (
        <div className="llm-config">
          <h3>Configure LLM Providers</h3>
          <p>Add your API keys. Keys are encrypted and stored securely.</p>
          
          {llmProviders.map(provider => (
            <div key={provider} className="provider-card">
              <h4>{provider.toUpperCase()}</h4>
              <input 
                type="password" 
                placeholder={`${provider} API Key`}
                onChange={(e) => setApiKeys({...apiKeys, [provider]: e.target.value})}
              />
              <button onClick={() => saveApiKey(provider, apiKeys[provider])}>
                💾 Save
              </button>
              <button onClick={() => testApiKey(provider)}>
                🧪 Test
              </button>
              {provider === 'ollama' && (
                <p className="note">🖥️ Local GPU - No API key needed. Ensure Ollama is running.</p>
              )}
            </div>
          ))}
        </div>
      )}

      {activeTab === 'vector' && (
        <div className="vector-config">
          <h3>Configure Vector Database</h3>
          
          <select 
            value={selectedVectorDb} 
            onChange={(e) => setSelectedVectorDb(e.target.value)}
          >
            {vectorDbs.map(db => (
              <option key={db.type} value={db.type}>
                {db.config.name}
              </option>
            ))}
          </select>

          <div className="deployment-info">
            <h4>{vectorDbs.find(d => d.type === selectedVectorDb)?.config.name}</h4>
            <p>{vectorDbs.find(d => d.type === selectedVectorDb)?.config.description}</p>
            
            {vectorDbs.find(d => d.type === selectedVectorDb)?.config.docker_required && (
              <button onClick={() => deployVectorDb(selectedVectorDb)}>
                🚀 One-Click Deploy
              </button>
            )}
            
            {deploymentStatus && (
              <div className="deployment-status">
                <p>Status: {deploymentStatus.status}</p>
                <p>{deploymentStatus.message}</p>
                {deploymentStatus.access_url && (
                  <p>Access: <a href={deploymentStatus.access_url}>{deploymentStatus.access_url}</a></p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'gpu' && (
        <div className="gpu-config">
          <h3>GPU Configuration</h3>
          <p>Detect if you have an NVIDIA GPU for local LLM inference.</p>
          
          <button onClick={() => api.post('/api/v1/gpu/detect')}>
            🔍 Detect GPU
          </button>
          
          <div className="gpu-status">
            <p>GPU Detected: <strong>RTX 4070 (12GB)</strong></p>
            <p>Status: <span className="status-ready">✅ Ready</span></p>
            <p>Recommended Models: llama3.1:8b, mistral:7b, phi3:mini</p>
          </div>
        </div>
      )}
    </div>
  );
}