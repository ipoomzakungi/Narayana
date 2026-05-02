import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VoiceDebugConsole } from "@/components/voice/VoiceDebugConsole";
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
});
