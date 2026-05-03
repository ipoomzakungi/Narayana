import type { IntakeResponse } from "@/types/triage";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface IntakeFromTranscriptInput {
  session_id: string;
  transcript: string;
  language_hint?: string;
  source_input_mode?: string;
  call_id?: string | null;
  caller_phone_optional?: string | null;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function intakeFromTranscript(input: IntakeFromTranscriptInput): Promise<IntakeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/intake/from-transcript`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: input.session_id,
      transcript: input.transcript,
      language_hint: input.language_hint ?? "th",
      source_input_mode: input.source_input_mode ?? "manual",
      call_id: input.call_id ?? null,
      caller_phone_optional: input.caller_phone_optional ?? null
    })
  });
  return parseResponse<IntakeResponse>(response);
}
