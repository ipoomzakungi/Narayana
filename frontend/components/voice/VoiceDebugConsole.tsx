"use client";

import React, { useRef, useState } from "react";

import { startMicStreaming } from "@/lib/audio-client";
import { createCase, triageFromTranscript } from "@/lib/triage-api-client";
import { createVoiceWsClient, type VoiceWsClient } from "@/lib/voice-ws-client";
import type { AudioDebugEvent, CaseRepositoryRecord, TriageResult, VadState, VoiceWsMessage } from "@/types/triage";

const SAMPLE_TRANSCRIPT = "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง";

function triageClass(level?: string) {
  if (level === "RED") return "bg-red-600 text-white";
  if (level === "YELLOW") return "bg-yellow-400 text-slate-950";
  if (level === "GREEN") return "bg-emerald-600 text-white";
  return "bg-slate-200 text-slate-700";
}

function stateClass(state: VadState) {
  if (state === "speech") return "bg-orange-500 text-white";
  if (state === "thinking") return "bg-sky-600 text-white";
  if (state === "speaking") return "bg-violet-600 text-white";
  if (state === "listening") return "bg-emerald-600 text-white";
  return "bg-slate-300 text-slate-900";
}

export function VoiceDebugConsole() {
  const [transcript, setTranscript] = useState(SAMPLE_TRANSCRIPT);
  const [triage, setTriage] = useState<TriageResult | null>(null);
  const [caseRecord, setCaseRecord] = useState<CaseRepositoryRecord | null>(null);
  const [events, setEvents] = useState<AudioDebugEvent[]>([]);
  const [vadState, setVadState] = useState<VadState>("listening");
  const [providerMode, setProviderMode] = useState("mock");
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<VoiceWsClient | null>(null);
  const stopMicRef = useRef<(() => void) | null>(null);

  async function submitTranscript() {
    setLoading(true);
    setError(null);
    try {
      const triageResult = await triageFromTranscript({ transcript, language_hint: "th" });
      setTriage(triageResult);
      const record = await createCase(triageResult, "mock");
      setCaseRecord(record);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create case");
    } finally {
      setLoading(false);
    }
  }

  function handleWsMessage(message: VoiceWsMessage) {
    if (message.type === "session.started") {
      setProviderMode(message.provider_mode);
      setVadState(message.state);
      return;
    }
    if (message.type === "debug.event") {
      setEvents((current) => [message.event, ...current].slice(0, 40));
      if (message.event.state) setVadState(message.event.state);
      return;
    }
    if (message.type === "triage.case.created") {
      setTranscript(message.transcript);
      setTriage(message.record.case);
      setCaseRecord(message.record);
      setProviderMode(message.provider_mode);
      setVadState("listening");
      return;
    }
    if (message.type === "error") {
      setError(message.detail);
    }
  }

  async function startRecording() {
    setError(null);
    setEvents([]);
    const sessionId = `session_${Date.now()}`;
    const client = createVoiceWsClient({
      sessionId,
      onMessage: handleWsMessage,
      onError: () => setError("Voice WebSocket failed")
    });
    wsRef.current = client;
    stopMicRef.current = await startMicStreaming((frame) => client.sendFrame({ ...frame, session_id: sessionId }));
    setRecording(true);
  }

  function stopRecording() {
    stopMicRef.current?.();
    stopMicRef.current = null;
    wsRef.current?.close();
    wsRef.current = null;
    setRecording(false);
    setVadState("listening");
  }

  return (
    <main className="min-h-screen bg-[#eef1f5] px-4 py-5 text-slate-950 md:px-8">
      <div className="mx-auto grid max-w-7xl gap-4 xl:grid-cols-[360px_1fr]">
        <section className="border border-command-line bg-white p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold tracking-normal">Narayana AI</h1>
              <p className="mt-1 text-sm text-slate-600">Crisis intake and triage assistant. Not an official emergency hotline replacement.</p>
            </div>
            <span className={`shrink-0 px-2 py-1 text-xs font-semibold ${stateClass(vadState)}`}>{vadState}</span>
          </div>

          <div className="mt-5 space-y-3">
            <label className="block text-sm font-semibold" htmlFor="transcript">
              Transcript
            </label>
            <textarea
              id="transcript"
              className="min-h-36 w-full resize-y border border-command-line bg-command-panel p-3 text-sm outline-none focus:border-slate-600"
              value={transcript}
              onChange={(event) => setTranscript(event.target.value)}
            />
            <div className="grid grid-cols-2 gap-2">
              <button
                className="border border-slate-900 bg-slate-950 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                type="button"
                onClick={submitTranscript}
                disabled={loading}
              >
                {loading ? "Creating..." : "Create Case"}
              </button>
              <button
                className="border border-command-line bg-white px-3 py-2 text-sm font-semibold text-slate-900"
                type="button"
                onClick={() => setTranscript(SAMPLE_TRANSCRIPT)}
              >
                Thai Sample
              </button>
            </div>
          </div>

          <div className="mt-5 border-t border-command-line pt-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">Local Mic</span>
              <span className="text-xs text-slate-600">{providerMode}</span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <button
                className="border border-emerald-700 bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                type="button"
                onClick={startRecording}
                disabled={recording}
              >
                Start
              </button>
              <button
                className="border border-slate-500 bg-white px-3 py-2 text-sm font-semibold text-slate-900 disabled:opacity-50"
                type="button"
                onClick={stopRecording}
                disabled={!recording}
              >
                Stop
              </button>
            </div>
          </div>

          {error ? <div className="mt-4 border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</div> : null}
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="border border-command-line bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold">Case Preview</h2>
              <span className={`px-2 py-1 text-xs font-semibold ${triageClass(triage?.triage_level)}`}>{triage?.triage_level ?? "NONE"}</span>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Case ID</dt>
                <dd className="font-medium">{caseRecord?.case.case_id ?? triage?.case_id ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Status</dt>
                <dd className="font-medium">{caseRecord?.case.status ?? triage?.status ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Incident</dt>
                <dd className="font-medium">{triage?.incident_type ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Confidence</dt>
                <dd className="font-medium">{triage ? `${Math.round(triage.confidence * 100)}%` : "-"}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-slate-500">Location</dt>
                <dd className="font-medium">{triage?.location_text || "-"}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-slate-500">Human Review</dt>
                <dd className="font-medium">{triage ? (triage.human_review_required ? "required" : "not required") : "-"}</dd>
              </div>
            </dl>
            <div className="mt-4 border-t border-command-line pt-4">
              <h3 className="text-sm font-semibold">Summary</h3>
              <p className="mt-2 text-sm text-slate-700">{triage?.ai_summary ?? "-"}</p>
              <h3 className="mt-4 text-sm font-semibold">Triage Reason</h3>
              <p className="mt-2 text-sm text-slate-700">{triage?.triage_reason ?? "-"}</p>
            </div>
          </div>

          <div className="border border-command-line bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold">Structured JSON</h2>
            <pre className="mt-4 max-h-[440px] overflow-auto bg-slate-950 p-3 text-xs text-slate-100">
              {JSON.stringify(caseRecord?.case ?? triage ?? {}, null, 2)}
            </pre>
          </div>

          <div className="border border-command-line bg-white p-4 shadow-sm lg:col-span-2">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold">Voice Debug Timeline</h2>
              <span className={`px-2 py-1 text-xs font-semibold ${stateClass(vadState)}`}>{vadState}</span>
            </div>
            <div className="mt-4 grid max-h-80 gap-2 overflow-auto">
              {events.length === 0 ? (
                <p className="text-sm text-slate-500">No audio events yet.</p>
              ) : (
                events.map((event) => (
                  <div key={event.event_id} className="grid gap-1 border border-command-line bg-command-panel p-2 text-xs sm:grid-cols-[180px_120px_1fr]">
                    <span className="font-semibold">{event.event_type}</span>
                    <span>{event.state ?? "-"}</span>
                    <span className="truncate text-slate-600">{JSON.stringify(event.metadata)}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
