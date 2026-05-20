import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CasesDashboard } from "@/components/cases/CasesDashboard";
import type { CaseSnapshotResponse } from "@/types/triage";

const redCase = {
  case_id: "case_red",
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
  created_at: "2026-05-03T06:00:00Z",
  updated_at: "2026-05-03T06:00:00Z",
  status: "pending"
} as const;

const snapshot: CaseSnapshotResponse = {
  generated_at: "2026-05-03T06:00:00Z",
  expires_at: "2026-05-03T06:01:00Z",
  ttl_seconds: 60,
  count: 1,
  source: "repository",
  cases: [
    {
      case: redCase,
      session_id: "twilio_CA_TEST",
      source_provider: "mock",
      debug_event_count: 4,
      stored_at: "2026-05-03T06:00:02Z",
      case_group: "rescue",
      recommended_team: "rescue",
      conversation_summary: "Caller reported flood in Hat Yai with trapped elderly person."
    }
  ]
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("CasesDashboard", () => {
  it("renders cached case response and supports manual refresh", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify(snapshot), { headers: { "Content-Type": "application/json" } }));

    render(<CasesDashboard />);

    await waitFor(() => expect(screen.getByText("Caller reported flood in Hat Yai with trapped elderly person.")).toBeInTheDocument());
    expect(screen.getAllByText("RED").length).toBeGreaterThan(0);
    expect(screen.getAllByText("rescue").length).toBeGreaterThan(0);
    expect(screen.getByText("หาดใหญ่")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("required")).toBeInTheDocument();
    expect(screen.getByText("mock / twilio_CA_TEST")).toBeInTheDocument();
    expect(screen.getByText("Source repository")).toBeInTheDocument();
    expect(screen.getByText("1 cases cached for 60s")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Refresh cases" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it("renders older records without intake fields", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          ...snapshot,
          cases: [
            {
              case: redCase,
              session_id: "session_old",
              source_provider: "mock",
              debug_event_count: 1,
              stored_at: "2026-05-03T06:00:02Z"
            }
          ]
        }),
        { headers: { "Content-Type": "application/json" } }
      )
    );

    render(<CasesDashboard />);

    await waitFor(() => expect(screen.getByText("Flood with trapped elderly person.")).toBeInTheDocument());
    expect(screen.getByText("mock / session_old")).toBeInTheDocument();
  });

  it("hides structured assistant output and treats unknown human review as review required", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          ...snapshot,
          cases: [
            {
              case: {
                ...redCase,
                case_id: "case_unknown",
                triage_level: "YELLOW",
                incident_type: "unknown",
                human_review_required: false,
                ai_summary: '{"facts_extracted":{"location":"bad assistant json"}}',
                conversation_summary: null,
                case_group: "unknown_human_review"
              },
              session_id: "twilio_CA_UNKNOWN",
              source_provider: "azure_openai_realtime",
              debug_event_count: 0,
              stored_at: "2026-05-03T06:00:02Z",
              case_group: "unknown_human_review",
              recommended_team: "human_review",
              conversation_summary: null
            }
          ]
        }),
        { headers: { "Content-Type": "application/json" } }
      )
    );

    render(<CasesDashboard />);

    await waitFor(() => expect(screen.getByText("Needs operator review; no reliable incident summary yet.")).toBeInTheDocument());
    expect(screen.queryByText("bad assistant json")).not.toBeInTheDocument();
    expect(screen.getByText("required")).toBeInTheDocument();
  });
});
