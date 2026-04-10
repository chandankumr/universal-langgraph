import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router'; // ✅ Use Next.js router
import api from '../services/api';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const [currentModel, setCurrentModel] = useState(null);
  const [searchMethod, setSearchMethod] = useState('vector'); // 'vector' or 'vectorless'

  const messagesEndRef = useRef(null);

  // Check auth on load
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  useEffect(() => {
    loadCurrentModel();
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Load messages from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(`chat-${router.query.thread || 'default'}`);
    if (saved) {
      setMessages(JSON.parse(saved));
    }
  }, [router]);

  // Save messages when they change
  useEffect(() => {
    scrollToBottom();
    if (messages.length > 0) {
      localStorage.setItem(`chat-default`, JSON.stringify(messages));
    }
  }, [messages]); // Runs every time a token is added

  const loadCurrentModel = async () => {
    try {
      const response = await api.get('/api/v1/models/current');
      setCurrentModel(response.data);
    } catch (error) {
      console.error('Error loading model:', error);
      // Set default if fails
      setCurrentModel({ provider: 'ollama', model: 'llama3.1:8b' });
    }
  };

  // const sendMessage = async () => {
  //   if (!input.trim()) return;

  //   const userMessage = { role: 'user', content: input };
  //   setMessages([...messages, userMessage]);
  //   setInput('');
  //   setLoading(true);

  //   try {
  //     const response = await api.post('/api/v1/query', {
  //       question: input,
  //       conversation_history: messages
  //     });

  //     const assistantMessage = { 
  //       role: 'assistant', 
  //       content: response.data.answer 
  //     };
  //     setMessages(prev => [...prev, assistantMessage]);
  //   } catch (error) {
  //     console.error('Error:', error);
  //     const errorMessage = { 
  //       role: 'assistant', 
  //       content: 'Sorry, I encountered an error. Please try again.' 
  //     };
  //     setMessages(prev => [...prev, errorMessage]);
  //   } finally {
  //     setLoading(false);
  //   }
  // };

  const sendMessage = async () => {
    if (!input.trim()) return;

    // 1. Add User Message immediately
    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    // 2. Prepare empty Assistant Message
    let assistantContent = '';
    
    // Add a placeholder assistant message to the UI so we have something to update
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    try {
      const response = await fetch(`http://localhost:8000/api/v1/query/stream?search_method=${searchMethod}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ question: input })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          const trimmedLine = line.trim();
          
          // Check for "data:" prefix instead of space
          if (trimmedLine.startsWith('data:')) {
            try {
              // Remove "data:" prefix and parse JSON
              const jsonStr = trimmedLine.replace('data:', '').trim();
              if (!jsonStr) continue;

              const data = JSON.parse(jsonStr);

              if (data.token) {
                assistantContent += data.token;
                
                // Update the last message (the assistant's placeholder)
                setMessages(prev => {
                  const newMessages = [...prev];
                  // Update the very last message with new content
                  newMessages[newMessages.length - 1] = { 
                    role: 'assistant', 
                    content: assistantContent 
                  };
                  return newMessages;
                });
              } else if (data.error) {
                console.error('Stream Error:', data.error);
                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { 
                    role: 'assistant', 
                    content: `Error: ${data.error}` 
                  };
                  return newMessages;
                });
              }
            } catch (e) {
              console.warn('Failed to parse JSON chunk:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming failed:', error);
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = { 
          role: 'assistant', 
          content: `Sorry, streaming failed: ${error.message}` 
        };
        return newMessages;
      });
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
      {/* <div style={{ padding: '15px', borderBottom: '1px solid #ddd', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>💬 Universal LangGraph</h3>
        <button onClick={handleLogout} style={{ padding: '8px 15px', cursor: 'pointer' }}>Logout</button>
      </div> */}
      <div style={{ padding: '15px', borderBottom: '1px solid #ddd', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0 }}>💬 Universal LangGraph</h3>
          <small style={{ color: '#888' }}>Model: {currentModel?.model || 'Loading...'}</small>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginRight: '10px', fontSize: '14px' }}>
            <span style={{ color: searchMethod === 'vector' ? '#007bff' : '#888', fontWeight: searchMethod === 'vector' ? 'bold' : 'normal' }}>Vector</span>
            <label style={{ position: 'relative', display: 'inline-block', width: '50px', height: '24px' }}>
              <input 
                type="checkbox" 
                checked={searchMethod === 'vectorless'} 
                onChange={(e) => setSearchMethod(e.target.checked ? 'vectorless' : 'vector')}
                style={{ opacity: 0, width: 0, height: 0 }} 
              />
              <span style={{
                position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0,
                backgroundColor: searchMethod === 'vectorless' ? '#28a745' : '#ccc',
                transition: '.4s', borderRadius: '24px'
              }}></span>
              <span style={{
                position: 'absolute', content: '""', height: '16px', width: '16px', left: searchMethod === 'vectorless' ? '29px' : '4px', bottom: '4px',
                backgroundColor: 'white', transition: '.4s', borderRadius: '50%'
              }}></span>
            </label>
            <span style={{ color: searchMethod === 'vectorless' ? '#28a745' : '#888', fontWeight: searchMethod === 'vectorless' ? 'bold' : 'normal' }}>Vectorless</span>
          </div>

          <a href="/documents" style={{ padding: '8px 15px', backgroundColor: '#28a745', color: 'white', textDecoration: 'none', borderRadius: '5px' }}>📄 Documents</a>
          <button onClick={handleLogout} style={{ padding: '8px 15px', cursor: 'pointer' }}>Logout</button>
        </div>
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
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                wordWrap: 'break-word'
              }}
            >
              {msg.content}
            </div>
          ))
        )}
        {/* Add this invisible div at the very end */}
        <div ref={messagesEndRef} /> 
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