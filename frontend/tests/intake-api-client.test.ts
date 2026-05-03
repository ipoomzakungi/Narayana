import { afterEach, describe, expect, it, vi } from "vitest";

import { intakeFromTranscript } from "@/lib/intake-api-client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("intakeFromTranscript", () => {
  it("posts session transcript to the multi-turn intake endpoint", async () => {
    const responsePayload = {
      session_id: "debug-session",
      action: "ask_followup",
      response_text: "มีใครบาดเจ็บไหมคะ?",
      partial_state: { session_id: "debug-session", conversation_turns: [], collected_fields: {} },
      case_group: "flood",
      recommended_team: "flood_response",
      triage_level: "YELLOW",
      human_review_required: true,
      missing_fields: ["injuries"],
      reason: "Missing injuries.",
      guardrail_warnings: [],
      created_case: null
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(responsePayload)));

    const result = await intakeFromTranscript({
      session_id: "debug-session",
      transcript: "น้ำท่วมอยู่ที่หาดใหญ่"
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/intake/from-transcript",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          session_id: "debug-session",
          transcript: "น้ำท่วมอยู่ที่หาดใหญ่",
          language_hint: "th",
          source_input_mode: "manual",
          call_id: null,
          caller_phone_optional: null
        })
      })
    );
    expect(result.action).toBe("ask_followup");
  });

  it("throws on backend errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("bad request", { status: 422 }));

    await expect(intakeFromTranscript({ session_id: "debug-session", transcript: "" })).rejects.toThrow("bad request");
  });
});
