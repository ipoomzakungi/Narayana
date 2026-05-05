import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchIntakeSession, fetchIntakeSessionByCallId, fetchIntakeSessions } from "@/lib/intake-session-api-client";

const session = {
  session_id: "twilio_CA_TEST",
  call_id: "CA_TEST",
  source_input_mode: "twilio_call",
  conversation_turns: [],
  timeline_events: [],
  collected_fields: {
    language: "th",
    incident_type: "unknown",
    location_text: "",
    people_affected: null,
    injuries: "",
    immediate_needs: [],
    caller_phone_optional: null,
    landmarks: [],
    urgency_signals: [],
    missing_fields: []
  },
  confidence: 0,
  human_review_required: false,
  followup_count: 0,
  max_followups: 3,
  recommended_team: "",
  status: "active",
  guardrail_warnings: [],
  decision_audit: [],
  created_at: "2026-05-05T00:00:00Z",
  updated_at: "2026-05-05T00:00:00Z"
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("intake session api client", () => {
  it("fetches recent sessions", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ generated_at: "2026-05-05T00:00:00Z", count: 1, limit: 50, sessions: [session] }))
    );

    await expect(fetchIntakeSessions()).resolves.toMatchObject({ count: 1 });
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/intake/sessions?limit=50", expect.any(Object));
  });

  it("fetches by session and call id", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify(session)));

    await expect(fetchIntakeSession("twilio_CA_TEST")).resolves.toMatchObject({ session_id: "twilio_CA_TEST" });
    await expect(fetchIntakeSessionByCallId("CA_TEST")).resolves.toMatchObject({ call_id: "CA_TEST" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
