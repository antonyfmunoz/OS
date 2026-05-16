/**
 * Auto-reconnecting WebSocket manager for UMH Operator Workstation.
 */
export class WsClient {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, ((data: Record<string, unknown>) => void)[]> = new Map();
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private shouldReconnect = true;

  constructor(url: string) {
    this.url = url;
  }

  connect(): void {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.reconnectDelay = 1000;
        this.emit('connected', {});
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data as string) as Record<string, unknown>;
          const type = (data.type as string) || 'unknown';
          this.emit(type, data);
        } catch {
          // Ignore unparseable messages
        }
      };

      this.ws.onclose = () => {
        this.emit('disconnected', {});
        if (this.shouldReconnect) {
          setTimeout(() => this.connect(), this.reconnectDelay);
          this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
        }
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch {
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(), this.reconnectDelay);
      }
    }
  }

  send(type: string, payload: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...payload }));
    }
  }

  on(type: string, handler: (data: Record<string, unknown>) => void): void {
    const existing = this.handlers.get(type) || [];
    existing.push(handler);
    this.handlers.set(type, existing);
  }

  off(type: string, handler: (data: Record<string, unknown>) => void): void {
    const existing = this.handlers.get(type) || [];
    this.handlers.set(type, existing.filter(h => h !== handler));
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.ws?.close();
    this.ws = null;
  }

  private emit(type: string, data: Record<string, unknown>): void {
    const handlers = this.handlers.get(type) || [];
    for (const handler of handlers) {
      handler(data);
    }
  }
}
