import type { IntakeSessionListResponse, IntakeSessionState } from "@/types/triage";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchIntakeSessions(limit = 50): Promise<IntakeSessionListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/intake/sessions?limit=${limit}`, {
    headers: { Accept: "application/json" },
    cache: "no-store"
  });
  return parseResponse<IntakeSessionListResponse>(response);
}

export async function fetchIntakeSession(sessionId: string): Promise<IntakeSessionState> {
  const response = await fetch(`${API_BASE_URL}/api/intake/sessions/${encodeURIComponent(sessionId)}`, {
    headers: { Accept: "application/json" },
    cache: "no-store"
  });
  return parseResponse<IntakeSessionState>(response);
}

export async function fetchIntakeSessionByCallId(callId: string): Promise<IntakeSessionState> {
  const response = await fetch(`${API_BASE_URL}/api/intake/calls/${encodeURIComponent(callId)}`, {
    headers: { Accept: "application/json" },
    cache: "no-store"
  });
  return parseResponse<IntakeSessionState>(response);
}
