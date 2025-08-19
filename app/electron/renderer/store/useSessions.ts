import { create } from 'zustand';

export interface Message {
  id: string;
  type: 'user' | 'agent';
  text: string;
  timestamp: Date;
  isTyping?: boolean;
}

export interface Session {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

interface SessionStore {
  sessions: Session[];
  currentSessionId: string | null;
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  
  // Actions
  createSession: () => string;
  selectSession: (sessionId: string) => void;
  addMessage: (sessionId: string, message: Message) => void;
  updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => void;
  setConnectionStatus: (status: SessionStore['connectionStatus']) => void;
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  connectionStatus: 'disconnected',

  createSession: () => {
    const sessionId = `session-${Date.now()}`;
    const newSession: Session = {
      id: sessionId,
      title: `대화 ${new Date().toLocaleString('ko-KR')}`,
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    set((state) => ({
      sessions: [newSession, ...state.sessions],
      currentSessionId: sessionId,
    }));

    return sessionId;
  },

  selectSession: (sessionId) => {
    set({ currentSessionId: sessionId });
  },

  addMessage: (sessionId, message) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              messages: [...session.messages, message],
              updatedAt: new Date(),
            }
          : session
      ),
    }));
  },

  updateMessage: (sessionId, messageId, updates) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              messages: session.messages.map((msg) =>
                msg.id === messageId ? { ...msg, ...updates } : msg
              ),
            }
          : session
      ),
    }));
  },

  setConnectionStatus: (status) => {
    set({ connectionStatus: status });
  },
}));
