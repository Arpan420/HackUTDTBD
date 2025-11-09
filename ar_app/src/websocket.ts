/**
 * WebSocket client for connecting to backend audio processing server.
 */

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface NotificationMessage extends WebSocketMessage {
  type: "notification";
  title: string;
  message: string;
}

export interface PersonSwitchMessage extends WebSocketMessage {
  type: "switch_interaction_person";
  person_id: string | null;
  person_name: string;
  blurb: string;
}

export type MessageHandler = (message: WebSocketMessage) => void;

export class BackendWebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectInterval: number = 3000; // 3 seconds
  private reconnectTimer: NodeJS.Timeout | null = null;
  private messageHandlers: MessageHandler[] = [];
  private isConnecting: boolean = false;

  constructor(url: string) {
    this.url = url;
  }

  /**
   * Connect to the WebSocket server
   */
  connect(): void {
    if (
      this.isConnecting ||
      (this.ws && this.ws.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    this.isConnecting = true;
    console.log(`[WebSocket] Connecting to ${this.url}`);

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("[WebSocket] Connected");
        this.isConnecting = false;
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          if (typeof event.data === "string") {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } else {
            console.warn("[WebSocket] Received non-text message");
          }
        } catch (error) {
          console.error("[WebSocket] Error parsing message:", error);
        }
      };

      this.ws.onerror = (error) => {
        console.error("[WebSocket] Error:", error);
        this.isConnecting = false;
      };

      this.ws.onclose = () => {
        console.log("[WebSocket] Connection closed");
        this.isConnecting = false;
        this.ws = null;
        this.scheduleReconnect();
      };
    } catch (error) {
      console.error("[WebSocket] Failed to create connection:", error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Send audio chunk to the backend
   * @param audioData - ArrayBufferLike (ArrayBuffer, SharedArrayBuffer, or typed array buffer)
   */
  sendAudioChunk(audioData: ArrayBufferLike): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      // WebSocket.send() accepts ArrayBuffer, so we ensure it's an ArrayBuffer
      // If it's already an ArrayBuffer, use it directly
      // If it's a typed array view, we need to get the underlying buffer
      let buffer: ArrayBuffer;

      if (audioData instanceof ArrayBuffer) {
        buffer = audioData;
      } else if (audioData instanceof SharedArrayBuffer) {
        // Convert SharedArrayBuffer to ArrayBuffer (WebSocket doesn't support SharedArrayBuffer)
        buffer = audioData.slice(0);
      } else if (
        audioData &&
        typeof audioData === "object" &&
        "buffer" in audioData &&
        "byteOffset" in audioData &&
        "byteLength" in audioData
      ) {
        // It's a typed array view (Int8Array, Int16Array, Uint8Array, etc.)
        // Get the underlying ArrayBuffer
        const typedArray = audioData as {
          buffer: ArrayBuffer;
          byteOffset: number;
          byteLength: number;
        };
        buffer = typedArray.buffer.slice(
          typedArray.byteOffset,
          typedArray.byteOffset + typedArray.byteLength
        );
      } else {
        // Fallback: try to convert to ArrayBuffer
        console.warn(
          "[WebSocket] Unknown audio data type, attempting conversion"
        );
        buffer = new Uint8Array(audioData as any).buffer;
      }

      this.ws.send(buffer);
    } else {
      console.warn("[WebSocket] Cannot send audio chunk - not connected");
    }
  }

  /**
   * Send control message to the backend
   */
  sendControlMessage(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn("[WebSocket] Cannot send control message - not connected");
    }
  }

  /**
   * Add a message handler
   */
  onMessage(handler: MessageHandler): void {
    this.messageHandlers.push(handler);
  }

  /**
   * Remove a message handler
   */
  offMessage(handler: MessageHandler): void {
    this.messageHandlers = this.messageHandlers.filter((h) => h !== handler);
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  private handleMessage(message: WebSocketMessage): void {
    this.messageHandlers.forEach((handler) => {
      try {
        handler(message);
      } catch (error) {
        console.error("[WebSocket] Error in message handler:", error);
      }
    });
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return;
    }
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectInterval);
  }
}
