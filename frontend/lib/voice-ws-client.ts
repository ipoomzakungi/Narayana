import type { ProviderMode, VoiceWsMessage } from "@/types/triage";

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

export interface VoiceWsClient {
  socket: WebSocket;
  sendFrame(frame: Record<string, unknown>): void;
  sendPlaybackStarted(): void;
  sendPlaybackCompleted(): void;
  close(): void;
}

export function createVoiceWsClient(options: {
  sessionId: string;
  providerMode?: ProviderMode;
  onMessage: (message: VoiceWsMessage) => void;
  onError: (error: Event) => void;
}): VoiceWsClient {
  const socket = new WebSocket(`${WS_BASE_URL}/ws/local-audio`);
  socket.addEventListener("open", () => {
    socket.send(
      JSON.stringify({
        type: "session.start",
        session_id: options.sessionId,
        provider_mode: options.providerMode
      })
    );
  });
  socket.addEventListener("message", (event) => {
    options.onMessage(JSON.parse(event.data) as VoiceWsMessage);
  });
  socket.addEventListener("error", options.onError);

  return {
    socket,
    sendFrame(frame: Record<string, unknown>) {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "audio.frame", ...frame }));
      }
    },
    sendPlaybackStarted() {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "assistant.playback.started" }));
      }
    },
    sendPlaybackCompleted() {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "assistant.playback.completed" }));
      }
    },
    close() {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "session.close" }));
      }
      socket.close();
    }
  };
}
