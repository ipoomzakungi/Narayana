import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CallAuditDashboard } from "@/components/call-audit/CallAuditDashboard";
import type { IntakeSessionListResponse, IntakeSessionState } from "@/types/triage";

const session: IntakeSessionState = {
  session_id: "twilio_CA_TEST",
  call_id: "CA_TEST",
  source_input_mode: "twilio_call",
  conversation_turns: [
    { speaker: "caller", text: "น้ำท่วมอยู่ที่หาดใหญ่", created_at: "2026-05-05T00:00:01Z", turn_index: 0 }
  ],
  timeline_events: [
    {
      event_id: "evt_1",
      type: "caller.turn.transcribed",
      speaker: "caller",
      text: "น้ำท่วมอยู่ที่หาดใหญ่",
      guardrail_warnings: [],
      metadata: { transcript_source: "mock" },
      created_at: "2026-05-05T00:00:01Z"
    },
    {
      event_id: "evt_2",
      type: "tts.completed",
      speaker: "assistant",
      text: "มีใครบาดเจ็บไหมคะ?",
      tts_profile: "followup",
      tts_status: "completed",
      case_group: "flood",
      recommended_team: "rescue",
      guardrail_warnings: ["scope:ok"],
      metadata: { mark_name: "narayana_tts_test" },
      created_at: "2026-05-05T00:00:02Z"
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
  triage_level: "YELLOW",
  confidence: 0.7,
  human_review_required: true,
  followup_count: 1,
  max_followups: 3,
  case_group: "flood",
  recommended_team: "rescue",
  final_case_id: null,
  status: "waiting_for_followup",
  guardrail_warnings: ["scope:ok"],
  decision_audit: [],
  off_topic_count: 0,
  no_reply_prompt_count: 1,
  call_end_reason: "",
  created_at: "2026-05-05T00:00:00Z",
  updated_at: "2026-05-05T00:00:02Z"
};

const listResponse: IntakeSessionListResponse = {
  generated_at: "2026-05-05T00:00:03Z",
  count: 1,
  limit: 50,
  sessions: [session]
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("CallAuditDashboard", () => {
  it("renders recent sessions and selected timeline", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/intake/sessions?")) {
        return new Response(JSON.stringify(listResponse), { headers: { "Content-Type": "application/json" } });
      }
      return new Response(JSON.stringify(session), { headers: { "Content-Type": "application/json" } });
    });

    render(<CallAuditDashboard />);

    await waitFor(() => expect(screen.getAllByText("twilio_CA_TEST").length).toBeGreaterThan(0));
    expect(screen.getByText("caller.turn.transcribed")).toBeInTheDocument();
    expect(screen.getByText("น้ำท่วมอยู่ที่หาดใหญ่")).toBeInTheDocument();
    expect(screen.getByText("tts.completed")).toBeInTheDocument();
    expect(screen.getByText("Warnings: scope:ok")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Refresh sessions" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
  });
});
