import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useTypingEffect } from '../lib/typingEffect';

interface TypingBubbleProps {
  text: string;
  onComplete?: () => void;
}

const TypingBubble: React.FC<TypingBubbleProps> = ({ text, onComplete }) => {
  const [displayText, setDisplayText] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const skipRef = useRef(false);

  const handleUpdate = useCallback((updatedText: string) => {
    console.log('TypingBubble displayText 업데이트:', updatedText);
    setDisplayText(updatedText);
  }, []);

  const handleComplete = useCallback(() => {
    setIsComplete(true);
    onComplete?.();
  }, [onComplete]);

  useTypingEffect({
    text,
    onUpdate: handleUpdate,
    onComplete: handleComplete,
    skip: skipRef.current,
  });

  const handleSkip = () => {
    skipRef.current = true;
    setDisplayText(text);
    setIsComplete(true);
    onComplete?.();
  };

  return (
    <div className="message-bubble agent typing">
      <div className="message-content">
        {displayText}
        {!isComplete && <span className="typing-cursor">│</span>}
      </div>
      {!isComplete && (
        <button className="skip-button" onClick={handleSkip}>
          스킵
        </button>
      )}
    </div>
  );
};

export default TypingBubble;
