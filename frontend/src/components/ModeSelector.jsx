export default function ModeSelector({ mode, setMode }) {
  return (
    <div className="mode-selector">
      <button 
        className={mode === 'chat' ? 'active' : ''} 
        onClick={() => setMode('chat')}
      >
        💬 Chat (Fast Q&A)
      </button>
      <button 
        className={mode === 'research' ? 'active' : ''} 
        onClick={() => setMode('research')}
      >
        🔬 AutoResearch (Deep Dive)
      </button>
    </div>
  );
}