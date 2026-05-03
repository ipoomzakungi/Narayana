"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";

import { fetchRecentCachedCases } from "@/lib/cases-api-client";
import type { CaseRepositoryRecord, CaseSnapshotResponse, TriageLevel } from "@/types/triage";

function triageClass(level: TriageLevel) {
  if (level === "RED") return "bg-red-600 text-white";
  if (level === "YELLOW") return "bg-yellow-400 text-slate-950";
  return "bg-emerald-600 text-white";
}

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function countLevel(cases: CaseRepositoryRecord[], level: TriageLevel) {
  return cases.filter((record) => record.case.triage_level === level).length;
}

function SummaryTile({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="border border-command-line bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</p>
      <p className={`mt-3 text-3xl font-semibold tracking-normal ${tone}`}>{value}</p>
    </div>
  );
}

function intakeSummary(record: CaseRepositoryRecord) {
  return record.conversation_summary ?? record.case.conversation_summary ?? record.case.ai_summary;
}

function CaseRow({ record }: { record: CaseRepositoryRecord }) {
  const caseGroup = record.case_group ?? record.case.case_group ?? "-";
  const recommendedTeam = record.recommended_team ?? record.case.recommended_team ?? "-";

  return (
    <article className="grid gap-3 border border-command-line bg-white p-4 shadow-sm xl:grid-cols-[96px_120px_140px_minmax(140px,1fr)_minmax(240px,2fr)_110px_130px]">
      <div>
        <span className={`inline-flex min-w-16 justify-center px-2 py-1 text-xs font-semibold ${triageClass(record.case.triage_level)}`}>
          {record.case.triage_level}
        </span>
      </div>
      <div>
        <p className="text-xs text-slate-500">Incident</p>
        <p className="mt-1 text-sm font-semibold text-slate-950">{record.case.incident_type}</p>
      </div>
      <div>
        <p className="text-xs text-slate-500">Group</p>
        <p className="mt-1 text-sm font-semibold text-slate-950">{caseGroup}</p>
        <p className="mt-2 text-xs text-slate-500">{recommendedTeam}</p>
      </div>
      <div>
        <p className="text-xs text-slate-500">Location</p>
        <p className="mt-1 text-sm font-medium text-slate-800">{record.case.location_text || "-"}</p>
      </div>
      <div>
        <p className="text-xs text-slate-500">Summary</p>
        <p className="mt-1 text-sm text-slate-800">{intakeSummary(record)}</p>
        <p className="mt-2 text-xs text-slate-500">
          {record.source_provider} {record.session_id ? `/ ${record.session_id}` : ""}
        </p>
      </div>
      <div>
        <p className="text-xs text-slate-500">Status</p>
        <p className="mt-1 text-sm font-semibold text-slate-950">{record.case.status}</p>
      </div>
      <div>
        <p className="text-xs text-slate-500">Review</p>
        <p className="mt-1 text-sm font-semibold text-slate-950">{record.case.human_review_required ? "required" : "not required"}</p>
        <p className="mt-2 text-xs text-slate-500">{formatDateTime(record.case.created_at)}</p>
      </div>
    </article>
  );
}

export function CasesDashboard() {
  const [snapshot, setSnapshot] = useState<CaseSnapshotResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRecentCachedCases(50);
      setSnapshot(data);
      setLastRefreshedAt(new Date().toISOString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load recent cases");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => {
      void refresh();
    }, 60_000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const cases = snapshot?.cases ?? [];
  const summary = useMemo(
    () => ({
      red: countLevel(cases, "RED"),
      yellow: countLevel(cases, "YELLOW"),
      green: countLevel(cases, "GREEN"),
      pending: cases.filter((record) => record.case.status === "pending").length
    }),
    [cases]
  );

  return (
    <main className="min-h-screen bg-[#eef1f5] px-4 py-5 text-slate-950 md:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="flex flex-col gap-4 border-b border-command-line pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">Narayana Cases</h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-600">
              Cached crisis intake dashboard for operator review. Narayana is an intake and triage assistant, not an official emergency hotline replacement.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span className="border border-command-line bg-white px-2 py-1">Last refreshed {formatDateTime(lastRefreshedAt)}</span>
            <span className="border border-command-line bg-white px-2 py-1">Source {snapshot?.source ?? "-"}</span>
            <span className="border border-command-line bg-white px-2 py-1">Expires {formatDateTime(snapshot?.expires_at)}</span>
            <button
              className="border border-slate-900 bg-slate-950 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
              type="button"
              onClick={refresh}
              disabled={loading}
            >
              {loading ? "Refreshing" : "Refresh"}
            </button>
          </div>
        </header>

        <section className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryTile label="RED" value={summary.red} tone="text-red-700" />
          <SummaryTile label="YELLOW" value={summary.yellow} tone="text-yellow-700" />
          <SummaryTile label="GREEN" value={summary.green} tone="text-emerald-700" />
          <SummaryTile label="Pending" value={summary.pending} tone="text-slate-950" />
        </section>

        {error ? <div className="mt-4 border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</div> : null}

        <section className="mt-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Recent Cases</h2>
            <span className="text-sm text-slate-600">{snapshot ? `${snapshot.count} cases cached for ${snapshot.ttl_seconds}s` : "Loading cases"}</span>
          </div>
          <div className="grid gap-3">
            {cases.length === 0 && !loading ? (
              <div className="border border-command-line bg-white p-6 text-sm text-slate-600 shadow-sm">No recent cases yet.</div>
            ) : null}
            {cases.map((record) => (
              <CaseRow key={record.case.case_id} record={record} />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
