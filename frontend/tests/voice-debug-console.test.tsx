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
        state: "listening",
        source_input_mode: "twilio_call",
        call_metadata: {
          provider: "twilio",
          call_id: "CA123",
          from_number: "+15550001111",
          to_number: "+15552223333",
          country: "US",
          codec: "mulaw",
          sample_rate: 8000,
          started_at: "2026-05-02T00:00:00Z"
        }
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
        source_input_mode: "twilio_call",
        call_metadata: {
          provider: "twilio",
          call_id: "CA123",
          from_number: "+15550001111",
          to_number: "+15552223333",
          country: "US",
          codec: "mulaw",
          sample_rate: 8000,
          started_at: "2026-05-02T00:00:00Z"
        },
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
    expect(screen.getAllByText("twilio_call").length).toBeGreaterThan(0);
    expect(screen.getAllByText("twilio").length).toBeGreaterThan(0);
    expect(screen.getByText("CA123")).toBeInTheDocument();
    expect(screen.getByText("+15550001111")).toBeInTheDocument();
    expect(screen.getByText("+15552223333")).toBeInTheDocument();
    expect(screen.getByText("US")).toBeInTheDocument();
    expect(screen.getByText("mulaw / 8000 Hz")).toBeInTheDocument();
  });

  it("submits manual transcript to intake and renders follow-up state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          session_id: "debug-session",
          action: "ask_followup",
          response_text: "มีใครบาดเจ็บหรือหายใจลำบากไหมคะ?",
          partial_state: {
            session_id: "debug-session",
            source_input_mode: "manual",
            conversation_turns: [
              {
                speaker: "caller",
                text: "น้ำท่วมอยู่ที่หาดใหญ่",
                created_at: "2026-05-02T00:00:00Z",
                turn_index: 0
              },
              {
                speaker: "assistant",
                text: "มีใครบาดเจ็บหรือหายใจลำบากไหมคะ?",
                created_at: "2026-05-02T00:00:01Z",
                turn_index: 1
              }
            ],
            collected_fields: {
              language: "th",
              incident_type: "flood",
              location_text: "หาดใหญ่",
              people_affected: null,
              injuries: "",
              immediate_needs: [],
              caller_phone_optional: null,
              landmarks: [],
              urgency_signals: [],
              missing_fields: ["injuries"]
            },
            confidence: 0.68,
            human_review_required: true,
            followup_count: 1,
            max_followups: 3,
            case_group: "flood",
            recommended_team: "flood_response",
            status: "waiting_for_followup",
            guardrail_warnings: [],
            decision_audit: [],
            created_at: "2026-05-02T00:00:00Z",
            updated_at: "2026-05-02T00:00:01Z"
          },
          case_group: "flood",
          recommended_team: "flood_response",
          triage_level: "YELLOW",
          human_review_required: true,
          missing_fields: ["injuries"],
          reason: "Critical intake fields are still missing.",
          guardrail_warnings: [],
          created_case: null
        })
      )
    );

    render(<VoiceDebugConsole />);
    fireEvent.change(screen.getByLabelText("Transcript"), { target: { value: "น้ำท่วมอยู่ที่หาดใหญ่" } });
    fireEvent.click(screen.getByRole("button", { name: "Intake" }));

    await waitFor(() => expect(screen.getByText("ask_followup")).toBeInTheDocument());
    expect(screen.getAllByText("flood").length).toBeGreaterThan(0);
    expect(screen.getAllByText("flood_response").length).toBeGreaterThan(0);
    expect(screen.getByText("injuries")).toBeInTheDocument();
    expect(screen.getAllByText("มีใครบาดเจ็บหรือหายใจลำบากไหมคะ?").length).toBeGreaterThan(0);
    expect(screen.getByText("caller")).toBeInTheDocument();
    expect(screen.getByText("assistant")).toBeInTheDocument();
  });

  it("renders websocket intake follow-up payloads", async () => {
    render(<VoiceDebugConsole />);

    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    await waitFor(() => expect(mocks.createVoiceWsClient).toHaveBeenCalled());

    act(() => {
      mocks.lastWsOptions?.onMessage({
        type: "intake.followup",
        session_id: "twilio_CA123",
        transcript: "น้ำท่วมอยู่ที่หาดใหญ่",
        action: "ask_followup",
        response_text: "มีใครบาดเจ็บไหมคะ?",
        partial_state: {
          session_id: "twilio_CA123",
          source_input_mode: "twilio_call",
          conversation_turns: [
            {
              speaker: "caller",
              text: "น้ำท่วมอยู่ที่หาดใหญ่",
              created_at: "2026-05-02T00:00:00Z",
              turn_index: 0
            }
          ],
          collected_fields: {
            language: "th",
            incident_type: "flood",
            location_text: "หาดใหญ่",
            people_affected: null,
            injuries: "",
            immediate_needs: [],
            caller_phone_optional: null,
            landmarks: [],
            urgency_signals: [],
            missing_fields: ["injuries"]
          },
          confidence: 0.68,
          human_review_required: true,
          followup_count: 1,
          max_followups: 3,
          case_group: "flood",
          recommended_team: "flood_response",
          status: "waiting_for_followup",
          guardrail_warnings: ["human_review:elderly_vulnerable"],
          decision_audit: [],
          off_topic_count: 1,
          redirect_count: 1,
          no_reply_prompt_count: 0,
          call_end_recommended: false,
          call_end_reason: "",
          last_assistant_redirect: "ขออภัยค่ะ ระบบนี้ใช้สำหรับรับแจ้งเหตุหรือขอความช่วยเหลือเท่านั้น หากต้องการแจ้งเหตุ กรุณาบอกสถานการณ์และสถานที่ค่ะ",
          created_at: "2026-05-02T00:00:00Z",
          updated_at: "2026-05-02T00:00:01Z"
        },
        case_group: "flood",
        recommended_team: "flood_response",
        triage_level: "YELLOW",
        human_review_required: true,
        missing_fields: ["injuries"],
        reason: "Critical intake fields are still missing.",
        guardrail_warnings: ["human_review:elderly_vulnerable"],
        off_topic_count: 1,
        redirect_count: 1,
        no_reply_prompt_count: 0,
        call_end_recommended: false,
        call_end_reason: "",
        last_assistant_redirect: "ขออภัยค่ะ ระบบนี้ใช้สำหรับรับแจ้งเหตุหรือขอความช่วยเหลือเท่านั้น หากต้องการแจ้งเหตุ กรุณาบอกสถานการณ์และสถานที่ค่ะ",
        source_input_mode: "twilio_call",
        tts: {
          enabled: true,
          configured: true,
          voice: "th-TH-PremwadeeNeural",
          audio_format: "mulaw_8khz",
          stream_sid_present: true,
          warnings: ["tts sanitized"]
        }
      });
    });

    expect(screen.getByText("ask_followup")).toBeInTheDocument();
    expect(screen.getByText("มีใครบาดเจ็บไหมคะ?")).toBeInTheDocument();
    expect(screen.getAllByText("human_review:elderly_vulnerable").length).toBeGreaterThan(0);
    expect(screen.getAllByText("twilio_call").length).toBeGreaterThan(0);
    expect(screen.getByText("enabled / configured")).toBeInTheDocument();
    expect(screen.getByText("th-TH-PremwadeeNeural")).toBeInTheDocument();
    expect(screen.getByText("tts sanitized")).toBeInTheDocument();
    expect(screen.getByText("Off Topic")).toBeInTheDocument();
    expect(screen.getByText("Redirects")).toBeInTheDocument();
    expect(screen.getByText("No Reply")).toBeInTheDocument();
    expect(screen.getByText("End Call")).toBeInTheDocument();
    expect(screen.getAllByText("1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("no").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ระบบนี้ใช้สำหรับรับแจ้งเหตุ/).length).toBeGreaterThan(0);
  });

  it("renders no-reply and call ending debug payloads", async () => {
    render(<VoiceDebugConsole />);

    fireEvent.click(screen.getByRole("button", { name: "Start" }));
    await waitFor(() => expect(mocks.createVoiceWsClient).toHaveBeenCalled());

    act(() => {
      mocks.lastWsOptions?.onMessage({
        type: "call.ending",
        session_id: "twilio_CA123",
        response_text: "หากไม่มีการตอบกลับ ระบบจะสิ้นสุดสายนี้นะคะ",
        no_reply_prompt_count: 2,
        call_end_recommended: true,
        call_end_reason: "no_reply",
        guardrail_warnings: ["call:end_recommended:no_reply"],
        last_assistant_redirect: "หากไม่มีการตอบกลับ ระบบจะสิ้นสุดสายนี้นะคะ"
      });
    });

    expect(screen.getByText("หากไม่มีการตอบกลับ ระบบจะสิ้นสุดสายนี้นะคะ")).toBeInTheDocument();
    expect(screen.getByText("recommended")).toBeInTheDocument();
    expect(screen.getByText("no_reply")).toBeInTheDocument();
    expect(screen.getByText("call:end_recommended:no_reply")).toBeInTheDocument();
  });
});
