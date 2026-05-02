import type { CaseRepositoryRecord, ProviderMode, TriageResult } from "@/types/triage";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface TriageFromTranscriptInput {
  transcript: string;
  language_hint?: string;
  provider_mode?: ProviderMode;
  caller_phone_optional?: string | null;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function triageFromTranscript(input: TriageFromTranscriptInput): Promise<TriageResult> {
  const response = await fetch(`${API_BASE_URL}/api/triage/from-transcript`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      transcript: input.transcript,
      language_hint: input.language_hint ?? "th",
      provider_mode: input.provider_mode,
      caller_phone_optional: input.caller_phone_optional ?? null
    })
  });
  return parseResponse<TriageResult>(response);
}

export async function createCase(
  caseResult: TriageResult,
  sourceProvider: ProviderMode = "mock",
  sessionId?: string
): Promise<CaseRepositoryRecord> {
  const response = await fetch(`${API_BASE_URL}/api/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      case: caseResult,
      session_id: sessionId ?? null,
      source_provider: sourceProvider
    })
  });
  return parseResponse<CaseRepositoryRecord>(response);
}
