// frontend/src/pages/index.jsx
import React from 'react';
import { useRouter } from 'next/router';

export default function Home() {
  const router = useRouter();

  React.useEffect(() => {
    // Redirect to chat page
    router.push('/chat');
  }, [router]);

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh',
      fontFamily: 'system-ui'
    }}>
      <div style={{ textAlign: 'center' }}>
        <h1>🚀 Universal LangGraph Platform</h1>
        <p>Loading...</p>
        <p>If not redirected, <a href="/chat">click here</a></p>
      </div>
    </div>
  );
}