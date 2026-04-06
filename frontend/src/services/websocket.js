class WebSocketService {
  constructor() {
    this.ws = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this._heartbeatTimer = null;
    this._heartbeatIntervalMs = 30000; // Send ping every 30s
    this._pongTimeout = null;
    this._pongTimeoutMs = 10000; // Wait 10s for pong before considering dead
  }

  connect(url) {
    // Use environment variable, fallback to localhost for dev
    const wsUrl = url || `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/detections`;

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this._startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle pong response from server
        if (data.status === 'pong') {
          this._clearPongTimeout();
          return;
        }

        this.emit(data.type || 'message', data);
      } catch (error) {
        console.error('WebSocket message parse error:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this._stopHeartbeat();
      this.attemptReconnect(wsUrl);
    };
  }

  attemptReconnect(url) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;

      // Exponential backoff: 1s, 2s, 4s, 8s, 16s, ... capped at 60s
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 60000);
      console.log(`Reconnecting in ${delay / 1000}s... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

      setTimeout(() => {
        this.connect(url);
      }, delay);
    } else {
      console.warn('Max WebSocket reconnect attempts reached.');
    }
  }

  // ── Heartbeat ────────────────────────────────────────────────────
  _startHeartbeat() {
    this._stopHeartbeat();
    this._heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping');

        // Set a pong timeout — if server doesn't respond, force reconnect
        this._pongTimeout = setTimeout(() => {
          console.warn('WebSocket pong timeout — connection may be dead, closing.');
          if (this.ws) {
            this.ws.close();
          }
        }, this._pongTimeoutMs);
      }
    }, this._heartbeatIntervalMs);
  }

  _stopHeartbeat() {
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer);
      this._heartbeatTimer = null;
    }
    this._clearPongTimeout();
  }

  _clearPongTimeout() {
    if (this._pongTimeout) {
      clearTimeout(this._pongTimeout);
      this._pongTimeout = null;
    }
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    this._stopHeartbeat();
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export default new WebSocketService();