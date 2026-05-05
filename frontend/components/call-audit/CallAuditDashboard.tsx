"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";

import { fetchIntakeSession, fetchIntakeSessions } from "@/lib/intake-session-api-client";
import type { CallAuditTimelineEvent, ConversationTurn, IntakeSessionListResponse, IntakeSessionState } from "@/types/triage";

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(date);
}

function timelineFromSession(session: IntakeSessionState): CallAuditTimelineEvent[] {
  const timeline = session.timeline_events ?? [];
  if (timeline.length > 0) return timeline;
  return session.conversation_turns.map((turn: ConversationTurn) => ({
    event_id: `${session.session_id}-${turn.turn_index}`,
    type: `${turn.speaker}.turn`,
    speaker: turn.speaker,
    text: turn.text,
    guardrail_warnings: [],
    metadata: {},
    created_at: turn.created_at
  }));
}

function SessionButton({
  session,
  active,
  onSelect
}: {
  session: IntakeSessionState;
  active: boolean;
  onSelect: (sessionId: string) => void;
}) {
  return (
    <button
      type="button"
      className={`w-full border p-3 text-left shadow-sm ${active ? "border-slate-950 bg-slate-950 text-white" : "border-command-line bg-white text-slate-950"}`}
      onClick={() => onSelect(session.session_id)}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold">{session.session_id}</span>
        <span className="text-xs">{session.triage_level ?? "-"}</span>
      </div>
      <p className={`mt-1 text-xs ${active ? "text-slate-200" : "text-slate-500"}`}>{session.call_id ?? "no call id"}</p>
      <p className={`mt-2 text-xs ${active ? "text-slate-300" : "text-slate-600"}`}>
        {session.case_group ?? "unclassified"} / {session.final_case_id ?? "no case"}
      </p>
      <p className={`mt-2 text-xs ${active ? "text-slate-300" : "text-slate-500"}`}>{formatDateTime(session.updated_at)}</p>
    </button>
  );
}

function TimelineEventRow({ event }: { event: CallAuditTimelineEvent }) {
  const speaker = event.speaker ?? "system";
  return (
    <article className="border border-command-line bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span className="border border-command-line px-2 py-0.5 font-semibold text-slate-950">{event.type}</span>
        <span>{speaker}</span>
        <span>{formatDateTime(event.created_at)}</span>
        {event.tts_status ? <span>TTS {event.tts_status}</span> : null}
        {event.tts_profile ? <span>{event.tts_profile}</span> : null}
      </div>
      {event.text ? <p className="mt-2 text-sm text-slate-900">{event.text}</p> : null}
      <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
        {event.triage_level ? <span className="border border-command-line px-2 py-0.5">triage {event.triage_level}</span> : null}
        {event.case_group ? <span className="border border-command-line px-2 py-0.5">group {event.case_group}</span> : null}
        {event.recommended_team ? <span className="border border-command-line px-2 py-0.5">team {event.recommended_team}</span> : null}
      </div>
      {event.guardrail_warnings.length > 0 ? (
        <p className="mt-2 text-xs text-red-700">Warnings: {event.guardrail_warnings.join(", ")}</p>
      ) : null}
    </article>
  );
}

export function CallAuditDashboard() {
  const [snapshot, setSnapshot] = useState<IntakeSessionListResponse | null>(null);
  const [selectedSession, setSelectedSession] = useState<IntakeSessionState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchIntakeSessions(50);
      setSnapshot(data);
      const firstSessionId = data.sessions[0]?.session_id;
      setSelectedSession(firstSessionId ? await fetchIntakeSession(firstSessionId) : null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load call audit sessions");
    } finally {
      setLoading(false);
    }
  }, []);

  const selectSession = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      setSelectedSession(await fetchIntakeSession(sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load call audit session");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const timeline = useMemo(() => (selectedSession ? timelineFromSession(selectedSession) : []), [selectedSession]);

  return (
    <main className="min-h-screen bg-[#eef1f5] px-4 py-5 text-slate-950 md:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="flex flex-col gap-4 border-b border-command-line pb-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">Call Audit</h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-600">
              Recent caller and assistant timeline for Narayana crisis intake debugging.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span className="border border-command-line bg-white px-2 py-1">Sessions {snapshot?.count ?? 0}</span>
            <span className="border border-command-line bg-white px-2 py-1">Generated {formatDateTime(snapshot?.generated_at)}</span>
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

        {error ? <div className="mt-4 border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</div> : null}

        <section className="mt-5 grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="grid content-start gap-2">
            {(snapshot?.sessions ?? []).length === 0 && !loading ? (
              <div className="border border-command-line bg-white p-5 text-sm text-slate-600 shadow-sm">No call sessions yet.</div>
            ) : null}
            {(snapshot?.sessions ?? []).map((session) => (
              <SessionButton
                key={session.session_id}
                session={session}
                active={selectedSession?.session_id === session.session_id}
                onSelect={selectSession}
              />
            ))}
          </aside>

          <section className="min-w-0">
            {selectedSession ? (
              <div className="border border-command-line bg-white p-4 shadow-sm">
                <div className="grid gap-3 md:grid-cols-3">
                  <div>
                    <p className="text-xs text-slate-500">Session</p>
                    <p className="mt-1 text-sm font-semibold">{selectedSession.session_id}</p>
                    <p className="mt-1 text-xs text-slate-500">{selectedSession.call_id ?? "-"}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Case</p>
                    <p className="mt-1 text-sm font-semibold">{selectedSession.final_case_id ?? "not created"}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {selectedSession.case_group ?? "-"} / {selectedSession.recommended_team || "-"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Lifecycle</p>
                    <p className="mt-1 text-sm font-semibold">{selectedSession.call_end_reason || "active or completed"}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      no reply {selectedSession.no_reply_prompt_count ?? 0} / off topic {selectedSession.off_topic_count ?? 0}
                    </p>
                  </div>
                </div>
              </div>
            ) : null}

            <div className="mt-3 grid gap-3">
              {timeline.length === 0 && !loading ? (
                <div className="border border-command-line bg-white p-5 text-sm text-slate-600 shadow-sm">No timeline events for this session.</div>
              ) : null}
              {timeline.map((event) => (
                <TimelineEventRow key={event.event_id} event={event} />
              ))}
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}
