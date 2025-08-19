import React from 'react';
import { Message } from '../store/useSessions';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  return (
    <div className={`message-bubble ${message.type}`}>
      <div className="message-content">
        {message.text}
      </div>
      <div className="message-time">
        {message.timestamp.toLocaleTimeString('ko-KR', {
          hour: '2-digit',
          minute: '2-digit',
        })}
      </div>
    </div>
  );
};

export default MessageBubble;
