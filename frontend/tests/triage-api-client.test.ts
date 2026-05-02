import { afterEach, describe, expect, it, vi } from "vitest";

import { createCase, triageFromTranscript } from "@/lib/triage-api-client";
import type { TriageResult } from "@/types/triage";

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

afterEach(() => {
  vi.restoreAllMocks();
});

describe("triage api client", () => {
  it("submits transcript to backend", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(triage)));

    const result = await triageFromTranscript({ transcript: "น้ำท่วม", language_hint: "th" });

    expect(result.triage_level).toBe("RED");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/triage/from-transcript", expect.objectContaining({ method: "POST" }));
  });

  it("creates a case record", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
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

    const record = await createCase(triage, "mock");

    expect(record.case.status).toBe("pending");
    expect(record.source_provider).toBe("mock");
  });
});
