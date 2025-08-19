import React, { useState, useRef, useEffect } from 'react';
import { useSessionStore } from '../store/useSessions';
import { wsClient } from '../services/wsClient';
import MessageBubble from './MessageBubble';
import TypingBubble from './TypingBubble';

const ChatPane: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [typingText, setTypingText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const { 
    sessions, 
    currentSessionId, 
    addMessage, 
    updateMessage,
    connectionStatus 
  } = useSessionStore();

  const currentSession = sessions.find(s => s.id === currentSessionId);

  useEffect(() => {
    if (currentSessionId) {
      wsClient.connect(currentSessionId);
    }

    // WebSocket 이벤트 리스너
    const handleMessage = (data: any) => {
      console.log('ChatPane에서 메시지 받음:', data);
      
      if (currentSessionId) {
        const messageId = `msg-${Date.now()}`;
        
        console.log('메시지 텍스트:', data.text);
        console.log('메시지 길이:', data.text ? data.text.length : 0);
        
        // 타이핑 시작
        setIsTyping(true);
        setTypingText(data.text);
        
        // 메시지 추가 (타이핑 상태)
        addMessage(currentSessionId, {
          id: messageId,
          type: 'agent',
          text: data.text,
          timestamp: new Date(),
          isTyping: true,
        });
      }
    };

    const handleEOT = () => {
      setIsTyping(false);
      setTypingText('');
    };

    wsClient.on('message', handleMessage);
    wsClient.on('eot', handleEOT);

    return () => {
      wsClient.off('message', handleMessage);
      wsClient.off('eot', handleEOT);
    };
  }, [currentSessionId, addMessage]);

  useEffect(() => {
    // 새 메시지가 추가될 때 자동으로 스크롤을 맨 아래로
    const messagesContainer = messagesEndRef.current?.parentElement;
    if (messagesContainer) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainer;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      
      // 사용자가 맨 아래 근처에 있을 때만 자동 스크롤
      if (isNearBottom) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }, [currentSession?.messages]);

  const handleSend = () => {
    if (!inputText.trim() || !currentSessionId) return;

    const messageId = `msg-${Date.now()}`;
    
    // 사용자 메시지 추가
    addMessage(currentSessionId, {
      id: messageId,
      type: 'user',
      text: inputText,
      timestamp: new Date(),
    });

    // WebSocket으로 전송
    wsClient.sendMessage(inputText, messageId);

    setInputText('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTypingComplete = (messageId: string) => {
    if (currentSessionId) {
      updateMessage(currentSessionId, messageId, { isTyping: false });
    }
    setIsTyping(false);
    setTypingText('');
  };

  if (!currentSession) {
    return <div className="chat-pane">세션을 선택하세요</div>;
  }

  return (
    <div className="chat-pane">
      <div className="chat-header">
        <h3>{currentSession.title}</h3>
        <div className={`connection-status ${connectionStatus}`}>
          {connectionStatus === 'connected' ? '● 연결됨' : '○ 연결 끊김'}
        </div>
      </div>

      <div className="messages">
        {currentSession.messages.map((message) => (
          message.isTyping ? (
            <TypingBubble
              key={message.id}
              text={message.text}
              onComplete={() => handleTypingComplete(message.id)}
            />
          ) : (
            <MessageBubble key={message.id} message={message} />
          )
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="메시지를 입력하세요..."
          disabled={connectionStatus !== 'connected'}
        />
        <button 
          onClick={handleSend}
          disabled={!inputText.trim() || connectionStatus !== 'connected'}
        >
          전송
        </button>
      </div>
    </div>
  );
};

export default ChatPane;
