import type { CaseSnapshotResponse } from "@/types/triage";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchRecentCachedCases(limit = 50): Promise<CaseSnapshotResponse> {
  const response = await fetch(`${API_BASE_URL}/api/cases/recent-cached?limit=${limit}`, {
    headers: { Accept: "application/json" },
    cache: "no-store"
  });
  return parseResponse<CaseSnapshotResponse>(response);
}
