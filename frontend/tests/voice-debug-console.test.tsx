import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TriageResult } from "@/types/triage";

const mocks = vi.hoisted(() => ({
  startMicStreaming: vi.fn(),
  createVoiceWsClient: vi.fn(),
  lastWsOptions: undefined as
    | {
        onMessage: (message: unknown) => void;
        onError: (event: Event) => void;
      }
    | undefined,
  client: {
    socket: {} as WebSocket,
    sendFrame: vi.fn(),
    sendPlaybackStarted: vi.fn(),
    sendPlaybackCompleted: vi.fn(),
    close: vi.fn()
  }
}));

vi.mock("@/lib/audio-client", () => ({
  startMicStreaming: mocks.startMicStreaming
}));

vi.mock("@/lib/voice-ws-client", () => ({
  createVoiceWsClient: mocks.createVoiceWsClient
}));

import { VoiceDebugConsole } from "@/components/voice/VoiceDebugConsole";

const triage: TriageResult = {
  case_id: "case_1",
  language: "th",
  incident_type: "flood",
  triage_level: "RED",
  confidence: 0.92,
  location_text: "หาดใหญ่",
  people_affected: null,
  injuries: "elderly person breathing difficulty",
  immediate_needs: ["rescue", "medical"],
  caller_phone_optional: null,
  ai_summary: "Flood with trapped elderly person.",
  triage_reason: "Trapped person and breathing difficulty.",
  human_review_required: true,
  missing_fields: [],
  created_at: "2026-05-02T00:00:00Z",
  updated_at: "2026-05-02T00:00:00Z",
  status: "pending"
};

function mockSuccessfulFetch() {
  return vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(triage)))
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          case: triage,
          session_id: null,
          source_provider: "mock",
          debug_event_count: 0,
          stored_at: "2026-05-02T00:00:00Z"
        })
      )
    );
}

afterEach(() => {
  vi.restoreAllMocks();
});

beforeEach(() => {
  mocks.lastWsOptions = undefined;
  mocks.startMicStreaming.mockResolvedValue(vi.fn());
  mocks.createVoiceWsClient.mockImplementation((options) => {
    mocks.lastWsOptions = options;
    return mocks.client;
  });
});

describe("VoiceDebugConsole", () => {
  it("submits manual transcript and renders RED case preview", async () => {
    mockSuccessfulFetch();

    render(<VoiceDebugConsole />);
    fireEvent.click(screen.getByRole("button", { name: "Create Case" }));

    expect(screen.getByRole("button", { name: "Creating..." })).toBeDisabled();
    await waitFor(() => expect(screen.getByText("RED")).toBeInTheDocument());

    expect(screen.getByText("required")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("Flood with trapped elderly person.")).toBeInTheDocument();
  });

  it("renders backend errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("backend unavailable", { status: 500 }));

    render(<VoiceDebugConsole />);
    fireEvent.click(screen.getByRole("button", { name: "Create Case" }));

    await waitFor(() => expect(screen.getByText("backend unavailable")).toBeInTheDocument());
  });

  it("renders websocket source metadata, audio ref, and warnings", async () => {
    render(<VoiceDebugConsole />);

    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    await waitFor(() => expect(mocks.createVoiceWsClient).toHaveBeenCalled());

    act(() => {
      mocks.lastWsOptions?.onMessage({
        type: "session.started",
        session_id: "session_1",
        provider_mode: "azure_speech_openai",
        state: "listening"
      });
      mocks.lastWsOptions?.onMessage({
        type: "triage.case.created",
        session_id: "session_1",
        transcript: "เสียงไม่ชัด",
        provider_mode: "azure_speech_openai",
        transcript_source: "fallback",
        audio_ref: ".data/audio/session_1/turn_1.wav",
        response_text: null,
        warnings: ["Azure Speech did not return a usable transcript."],
        record: {
          case: {
            ...triage,
            triage_level: "YELLOW",
            confidence: 0.35,
            human_review_required: true,
            ai_summary: "Speech recognition did not produce a usable transcript.",
            triage_reason: "Azure Speech did not return a usable transcript."
          },
          session_id: "session_1",
          source_provider: "azure_speech_openai",
          debug_event_count: 3,
          stored_at: "2026-05-02T00:00:00Z"
        }
      });
    });

    expect(screen.getAllByText("azure_speech_openai").length).toBeGreaterThan(0);
    expect(screen.getAllByText("fallback").length).toBeGreaterThan(0);
    expect(screen.getByText(".data/audio/session_1/turn_1.wav")).toBeInTheDocument();
    expect(screen.getAllByText("Azure Speech did not return a usable transcript.").length).toBeGreaterThan(0);
  });
});
