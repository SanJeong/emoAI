import React from 'react';
import { useSessionStore } from '../store/useSessions';

const SessionList: React.FC = () => {
  const { sessions, currentSessionId, createSession, selectSession } = useSessionStore();

  const handleNewSession = () => {
    createSession();
  };

  return (
    <div className="session-list">
      <div className="session-header">
        <h3>대화 목록</h3>
        <button className="new-session-btn" onClick={handleNewSession}>
          + 새 대화
        </button>
      </div>
      
      <div className="sessions">
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`session-item ${session.id === currentSessionId ? 'active' : ''}`}
            onClick={() => selectSession(session.id)}
          >
            <div className="session-title">{session.title}</div>
            <div className="session-preview">
              {session.messages[session.messages.length - 1]?.text.slice(0, 50) || '대화를 시작하세요...'}
            </div>
            <div className="session-time">
              {session.updatedAt.toLocaleTimeString('ko-KR', { 
                hour: '2-digit', 
                minute: '2-digit' 
              })}
            </div>
          </div>
        ))}
        
        {sessions.length === 0 && (
          <div className="empty-state">
            <p>대화가 없습니다.</p>
            <p>새 대화를 시작해보세요!</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionList;
