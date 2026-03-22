// frontend/src/components/LocalAIMode.jsx
export default function LocalAIMode({ onToggle }) {
  const [localMode, setLocalMode] = useState(false);
  const [gpuDetected, setGpuDetected] = useState(null);
  const [ollamaStatus, setOllamaStatus] = useState("not_installed");

  useEffect(() => {
    checkLocalAI();
  }, []);

  const checkLocalAI = async () => {
    // Check GPU
    const gpuResponse = await api.get('/api/v1/system/gpu');
    setGpuDetected(gpuResponse.data);

    // Check Ollama
    try {
      await api.get('/api/v1/system/ollama/health');
      setOllamaStatus("running");
    } catch {
      setOllamaStatus("not_running");
    }
  };

  const enableLocalMode = async () => {
    await api.post('/api/v1/system/local-mode/enable');
    setLocalMode(true);
    onToggle(true);
  };

  return (
    <div className="local-ai-mode">
      <h3>🖥️ Local AI Mode (Karpathy-Style)</h3>
      <p>Run everything on your own hardware. No data leaves your machine.</p>
      
      <div className="system-status">
        <div className="status-item">
          <span>GPU:</span>
          <span className={gpuDetected ? "status-ok" : "status-warn"}>
            {gpuDetected ? `✅ ${gpuDetected.model} (${gpuDetected.vram}GB)` : "❌ Not Detected"}
          </span>
        </div>
        <div className="status-item">
          <span>Ollama:</span>
          <span className={ollamaStatus === "running" ? "status-ok" : "status-warn"}>
            {ollamaStatus === "running" ? "✅ Running" : "❌ Not Running"}
          </span>
        </div>
      </div>

      {gpuDetected && ollamaStatus === "running" ? (
        <button 
          onClick={enableLocalMode}
          className={localMode ? "btn-active" : "btn-primary"}
        >
          {localMode ? "✅ Local Mode Active" : "🚀 Enable Local Mode"}
        </button>
      ) : (
        <div className="setup-guide">
          <p>To enable local mode:</p>
          <ol>
            <li>Install Ollama: <code>curl -fsSL https://ollama.com/install.sh | sh</code></li>
            <li>Pull model: <code>ollama pull llama3.1:8b</code></li>
            <li>Start Ollama: <code>ollama serve</code></li>
          </ol>
        </div>
      )}

      <div className="local-mode-benefits">
        <h4>Benefits:</h4>
        <ul>
          <li>🔒 Complete privacy - no data leaves your machine</li>
          <li>💰 Zero API costs</li>
          <li>⚡ Low latency (no network)</li>
          <li>🎮 Uses your GPU (RTX 4070 = ~50 tokens/sec)</li>
        </ul>
      </div>
    </div>
  );
}