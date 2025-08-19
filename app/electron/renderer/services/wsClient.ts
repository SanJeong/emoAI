interface WSMessage {
  type: string;
  [key: string]: any;
}

class WebSocketClient {
  private listeners: { [event: string]: Function[] } = {};
  private ws: WebSocket | null = null;
  private url: string = 'ws://127.0.0.1:8787/ws/chat';
  private reconnectTimeout: number | null = null;
  private sessionId: string | null = null;

  on(event: string, callback: Function) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  off(event: string, callback: Function) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  emit(event: string, ...args: any[]) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(...args));
    }
  }

  connect(sessionId: string) {
    this.sessionId = sessionId;
    
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.disconnect();
    }

    const wsUrl = `${this.url}?session_id=${sessionId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket 연결됨');
      this.emit('connect');
      
      // 세션 열기 메시지
      this.send({
        type: 'open_session',
        session_id: sessionId,
      });
    };

    this.ws.onmessage = (event) => {
      try {
        const data: WSMessage = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error('메시지 파싱 오류:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket 오류:', error);
      this.emit('error', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket 연결 종료');
      this.emit('disconnect');
      this.attemptReconnect();
    };
  }

  private handleMessage(data: WSMessage) {
    console.log('WebSocket 메시지 받음:', data);
    
    switch (data.type) {
      case 'final_text':
        console.log('final_text 메시지:', data.text);
        console.log('텍스트 길이:', data.text ? data.text.length : 0);
        
        this.emit('message', {
          id: data.message_id,
          text: data.text,
          type: 'agent',
        });
        break;
        
      case 'meta':
        this.emit('meta', data);
        break;
        
      case 'eot':
        this.emit('eot');
        break;
        
      case 'error':
        this.emit('error', data.error);
        break;
        
      default:
        console.log('알 수 없는 메시지 타입:', data.type);
    }
  }

  sendMessage(text: string, messageId: string) {
    if (!this.sessionId) {
      console.error('세션 ID가 없습니다');
      return;
    }

    this.send({
      type: 'user_message',
      session_id: this.sessionId,
      message_id: messageId,
      text: text,
      client_style: {
        formality: '반말',
      },
    });
  }

  private send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.error('WebSocket이 연결되지 않음');
    }
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private attemptReconnect() {
    if (this.sessionId && !this.reconnectTimeout) {
      this.reconnectTimeout = setTimeout(() => {
        console.log('재연결 시도...');
        this.connect(this.sessionId!);
      }, 3000);
    }
  }
}

export const wsClient = new WebSocketClient();
