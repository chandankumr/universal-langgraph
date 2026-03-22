import React, { useState } from 'react';
import { useRouter } from 'next/router'; // ✅ Use Next.js router
import api from '../services/api';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  // Check auth on load
  React.useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await api.post('/api/v1/query', {
        question: input,
        conversation_history: messages
      });

      const assistantMessage = { 
        role: 'assistant', 
        content: response.data.answer 
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.' 
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'system-ui' }}>
      {/* Header */}
      <div style={{ padding: '15px', borderBottom: '1px solid #ddd', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>💬 Universal LangGraph</h3>
        <button onClick={handleLogout} style={{ padding: '8px 15px', cursor: 'pointer' }}>Logout</button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: '20px', backgroundColor: '#f9f9f9' }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#888', marginTop: '100px' }}>
            <h1>Welcome!</h1>
            <p>Ask me anything about your documents.</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                marginBottom: '15px',
                padding: '15px',
                borderRadius: '10px',
                backgroundColor: msg.role === 'user' ? '#007bff' : '#ffffff',
                color: msg.role === 'user' ? 'white' : 'black',
                maxWidth: '70%',
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                marginLeft: msg.role === 'user' ? 'auto' : '0',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
              }}
            >
              {msg.content}
            </div>
          ))
        )}
        {loading && <div style={{ padding: '15px', color: '#888', fontStyle: 'italic' }}>Thinking...</div>}
      </div>

      {/* Input */}
      <div style={{ padding: '20px', borderTop: '1px solid #ddd', backgroundColor: 'white' }}>
        <div style={{ display: 'flex', gap: '10px', maxWidth: '800px', margin: '0 auto' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask a question..."
            disabled={loading}
            style={{
              flex: 1,
              padding: '15px',
              borderRadius: '5px',
              border: '1px solid #ddd',
              fontSize: '16px'
            }}
          />
          <button
            onClick={sendMessage}
            disabled={loading}
            style={{
              padding: '15px 30px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '16px'
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}