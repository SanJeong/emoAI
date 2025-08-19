import React, { useEffect } from 'react';
import SessionList from './components/SessionList';
import ChatPane from './components/ChatPane';
import { useSessionStore } from './store/useSessions';
import { wsClient } from './services/wsClient';

function App() {
  const { currentSessionId, setConnectionStatus } = useSessionStore();

  useEffect(() => {
    // WebSocket 연결 상태 모니터링
    const handleConnect = () => setConnectionStatus('connected');
    const handleDisconnect = () => setConnectionStatus('disconnected');
    const handleError = () => setConnectionStatus('error');

    wsClient.on('connect', handleConnect);
    wsClient.on('disconnect', handleDisconnect);
    wsClient.on('error', handleError);

    return () => {
      wsClient.off('connect', handleConnect);
      wsClient.off('disconnect', handleDisconnect);
      wsClient.off('error', handleError);
    };
  }, [setConnectionStatus]);

  return (
    <div className="app">
      <div className="sidebar">
        <SessionList />
      </div>
      <div className="main-content">
        {currentSessionId ? (
          <ChatPane />
        ) : (
          <div className="welcome">
            <h2>EmoAI에 오신 것을 환영합니다</h2>
            <p>왼쪽에서 새 대화를 시작하거나 기존 대화를 선택하세요.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
