import { ToolCall, AppServer, AppSession, StreamType } from "@mentra/sdk";
import path from "path";
import { setupExpressRoutes } from "./webview";
import { handleToolCall } from "./tools";
import {
  BackendWebSocketClient,
  NotificationMessage,
  PersonSwitchMessage,
} from "./websocket";

const PACKAGE_NAME =
  process.env.PACKAGE_NAME ??
  (() => {
    throw new Error("PACKAGE_NAME is not set in .env file");
  })();
const MENTRAOS_API_KEY =
  process.env.MENTRAOS_API_KEY ??
  (() => {
    throw new Error("MENTRAOS_API_KEY is not set in .env file");
  })();
const PORT = parseInt(process.env.PORT || "3000");
const BACKEND_WS_URL = process.env.BACKEND_WS_URL || "ws://localhost:8765";

class ExampleMentraOSApp extends AppServer {
  constructor() {
    super({
      packageName: PACKAGE_NAME,
      apiKey: MENTRAOS_API_KEY,
      port: PORT,
      publicDir: path.join(__dirname, "../public"),
    });

    // Set up Express routes
    setupExpressRoutes(this);
  }

  /** Map to store active user sessions */
  private userSessionsMap = new Map<string, AppSession>();

  /**
   * Handles tool calls from the MentraOS system
   * @param toolCall - The tool call request
   * @returns Promise resolving to the tool call response or undefined
   */
  protected async onToolCall(toolCall: ToolCall): Promise<string | undefined> {
    return handleToolCall(
      toolCall,
      toolCall.userId,
      this.userSessionsMap.get(toolCall.userId)
    );
  }

  /**
   * Handles new user sessions
   * Sets up event listeners and displays welcome message
   * @param session - The app session instance
   * @param sessionId - Unique session identifier
   * @param userId - User identifier
   */
  protected async onSession(
    session: AppSession,
    sessionId: string,
    userId: string
  ): Promise<void> {
    this.userSessionsMap.set(userId, session);

    // Initialize WebSocket client for this session
    const wsClient = new BackendWebSocketClient(BACKEND_WS_URL);

    // Display state
    let currentPersonName: string = "Unknown";
    let currentPersonBlurb: string = "No interaction";
    const notifications: Array<{
      title: string;
      message: string;
      timestamp: number;
    }> = [];
    const MAX_NOTIFICATIONS = 3;
    const NOTIFICATION_DISPLAY_TIME = 5000; // 5 seconds

    /**
     * Update the display with current person info and notifications
     */
    const updateDisplay = (): void => {
      const lines: string[] = [];

      // Line 1: Person name
      lines.push(currentPersonName);

      // Line 2: Person blurb
      lines.push(currentPersonBlurb);

      // Lines 3+: Recent notifications
      const recentNotifications = notifications.slice(0, MAX_NOTIFICATIONS);
      if (recentNotifications.length > 0) {
        lines.push(""); // Empty line separator
        recentNotifications.forEach((notif) => {
          lines.push(`${notif.title}: ${notif.message}`);
        });
      }

      session.layouts.showTextWall(lines.join("\n"));
    };

    /**
     * Add a notification and update display
     */
    const addNotification = (title: string, message: string): void => {
      notifications.unshift({
        title,
        message,
        timestamp: Date.now(),
      });

      // Keep only recent notifications
      if (notifications.length > MAX_NOTIFICATIONS) {
        notifications.pop();
      }

      updateDisplay();

      // Auto-remove notification after display time
      setTimeout(() => {
        const index = notifications.findIndex(
          (n) => n.title === title && n.message === message
        );
        if (index !== -1) {
          notifications.splice(index, 1);
          updateDisplay();
        }
      }, NOTIFICATION_DISPLAY_TIME);
    };

    // Set up WebSocket message handlers
    wsClient.onMessage((message) => {
      if (message.type === "notification") {
        const notifMsg = message as NotificationMessage;
        console.log(`[Notification] ${notifMsg.title}: ${notifMsg.message}`);
        addNotification(notifMsg.title, notifMsg.message);
      } else if (message.type === "switch_interaction_person") {
        const personMsg = message as PersonSwitchMessage;
        console.log(
          `[Person Switch] ${personMsg.person_name} (${personMsg.person_id})`
        );
        currentPersonName = personMsg.person_name;
        currentPersonBlurb = personMsg.blurb;
        updateDisplay();
      }
    });

    // Connect WebSocket
    wsClient.connect();

    // Subscribe to audio chunks (async subscription)
    await session.subscribe(StreamType.AUDIO_CHUNK);

    // Listen for audio chunks
    session.events.onAudioChunk((data) => {
      // AudioChunk interface: { type: StreamType.AUDIO_CHUNK, arrayBuffer: ArrayBufferLike, sampleRate?: number }
      if (data.arrayBuffer) {
        // Forward audio chunk to backend via WebSocket
        // The arrayBuffer is ArrayBufferLike (can be ArrayBuffer, SharedArrayBuffer, etc.)
        wsClient.sendAudioChunk(data.arrayBuffer);

        // Optional: log sample rate if available
        if (data.sampleRate) {
          console.log(`[AudioChunk] Sample rate: ${data.sampleRate}Hz`);
        }
      } else {
        console.warn("[AudioChunk] Received audio chunk without arrayBuffer");
      }
    });

    // Show initial display
    updateDisplay();

    // Cleanup: disconnect WebSocket and remove session
    this.addCleanupHandler(() => {
      wsClient.disconnect();
      this.userSessionsMap.delete(userId);
    });
  }
}

// Start the server
const app = new ExampleMentraOSApp();

app.start().catch(console.error);
