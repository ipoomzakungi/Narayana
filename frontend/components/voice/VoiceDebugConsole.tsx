"use client";

import React, { useRef, useState } from "react";

import { startMicStreaming } from "@/lib/audio-client";
import { intakeFromTranscript } from "@/lib/intake-api-client";
import { createCase, triageFromTranscript } from "@/lib/triage-api-client";
import { createVoiceWsClient, type VoiceWsClient } from "@/lib/voice-ws-client";
import type {
  AudioDebugEvent,
  CallMetadata,
  CaseRepositoryRecord,
  IntakeResponse,
  ScopeDebugFields,
  SourceInputMode,
  TTSDebugStatus,
  TranscriptSource,
  TriageResult,
  VadState,
  VoiceWsMessage
} from "@/types/triage";

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
  const [intakeResponse, setIntakeResponse] = useState<IntakeResponse | null>(null);
  const [events, setEvents] = useState<AudioDebugEvent[]>([]);
  const [vadState, setVadState] = useState<VadState>("listening");
  const [providerMode, setProviderMode] = useState("mock");
  const [transcriptSource, setTranscriptSource] = useState<TranscriptSource | "manual">("manual");
  const [audioRef, setAudioRef] = useState<string | null>(null);
  const [providerWarnings, setProviderWarnings] = useState<string[]>([]);
  const [sourceInputMode, setSourceInputMode] = useState<SourceInputMode | null>(null);
  const [callMetadata, setCallMetadata] = useState<CallMetadata | null>(null);
  const [ttsStatus, setTtsStatus] = useState<TTSDebugStatus | null>(null);
  const [scopeDebug, setScopeDebug] = useState<ScopeDebugFields | null>(null);
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
      setProviderMode("mock");
      setTranscriptSource("manual");
      setAudioRef(null);
      setProviderWarnings([]);
      setSourceInputMode(null);
      setCallMetadata(null);
      setTtsStatus(null);
      setScopeDebug(null);
      setIntakeResponse(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create case");
    } finally {
      setLoading(false);
    }
  }

  async function submitIntakeTranscript() {
    setLoading(true);
    setError(null);
    try {
      const response = await intakeFromTranscript({
        session_id: "debug-session",
        transcript,
        language_hint: "th",
        source_input_mode: "manual"
      });
      setIntakeResponse(response);
      setProviderMode("mock");
      setTranscriptSource("manual");
      setAudioRef(null);
      setProviderWarnings(response.guardrail_warnings);
      setSourceInputMode(null);
      setCallMetadata(null);
      setTtsStatus(null);
      setScopeDebug({
        off_topic_count: response.off_topic_count,
        redirect_count: response.redirect_count,
        no_reply_prompt_count: response.no_reply_prompt_count,
        call_end_recommended: response.call_end_recommended,
        call_end_reason: response.call_end_reason,
        last_assistant_redirect: response.last_assistant_redirect,
        guardrail_warnings: response.guardrail_warnings,
        response_text: response.response_text
      });
      if (response.created_case) {
        setCaseRecord(response.created_case);
        setTriage(response.created_case.case);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to process intake");
    } finally {
      setLoading(false);
    }
  }

  function handleWsMessage(message: VoiceWsMessage) {
    if (message.type === "session.started") {
      setProviderMode(message.provider_mode);
      setVadState(message.state);
      setSourceInputMode(message.source_input_mode ?? null);
      setCallMetadata(message.call_metadata ?? null);
      setTtsStatus(null);
      setScopeDebug(null);
      return;
    }
    if (message.type === "debug.event") {
      setEvents((current) => [message.event, ...current].slice(0, 40));
      if (message.event.state) setVadState(message.event.state);
      return;
    }
    if (message.type === "intake.followup") {
      setTranscript(message.transcript);
      setIntakeResponse({
        session_id: message.session_id,
        action: message.action,
        response_text: message.response_text,
        partial_state: message.partial_state,
        case_group: message.case_group,
        recommended_team: message.recommended_team,
        triage_level: message.triage_level,
        human_review_required: message.human_review_required,
        missing_fields: message.missing_fields,
        reason: message.reason,
        guardrail_warnings: message.guardrail_warnings,
        created_case: null
      });
      setProviderMode(message.provider_mode ?? providerMode);
      if (message.transcript_source) setTranscriptSource(message.transcript_source);
      setAudioRef(message.audio_ref ?? null);
      setProviderWarnings([...(message.warnings ?? []), ...message.guardrail_warnings]);
      setTtsStatus(message.tts ?? null);
      setScopeDebug({
        off_topic_count: message.off_topic_count ?? message.partial_state.off_topic_count,
        redirect_count: message.redirect_count ?? message.partial_state.redirect_count,
        no_reply_prompt_count: message.no_reply_prompt_count ?? message.partial_state.no_reply_prompt_count,
        call_end_recommended: message.call_end_recommended ?? message.partial_state.call_end_recommended,
        call_end_reason: message.call_end_reason ?? message.partial_state.call_end_reason,
        last_assistant_redirect: message.last_assistant_redirect ?? message.partial_state.last_assistant_redirect,
        guardrail_warnings: message.guardrail_warnings,
        response_text: message.response_text
      });
      setSourceInputMode(message.source_input_mode ?? null);
      setCallMetadata(message.call_metadata ?? null);
      setVadState("listening");
      return;
    }
    if (message.type === "triage.case.created") {
      setTranscript(message.transcript);
      setTriage(message.record.case);
      setCaseRecord(message.record);
      setProviderMode(message.provider_mode);
      setTranscriptSource(message.transcript_source);
      setAudioRef(message.audio_ref);
      setProviderWarnings(message.warnings);
      setTtsStatus(message.tts ?? null);
      setSourceInputMode(message.source_input_mode ?? null);
      setCallMetadata(message.call_metadata ?? null);
      if (message.intake) {
        setIntakeResponse({
          session_id: message.session_id,
          action: message.intake.action,
          response_text: message.response_text ?? "",
          partial_state: message.intake.partial_state,
          case_group: message.intake.case_group,
          recommended_team: message.intake.recommended_team,
          triage_level: message.record.case.triage_level,
          human_review_required: message.record.case.human_review_required,
          missing_fields: message.intake.missing_fields,
          reason: message.intake.reason,
          guardrail_warnings: message.intake.guardrail_warnings,
          created_case: message.record
        });
      }
      setScopeDebug({
        off_topic_count: message.off_topic_count ?? message.intake?.partial_state.off_topic_count,
        redirect_count: message.redirect_count ?? message.intake?.partial_state.redirect_count,
        no_reply_prompt_count: message.no_reply_prompt_count ?? message.intake?.partial_state.no_reply_prompt_count,
        call_end_recommended: message.call_end_recommended ?? message.intake?.partial_state.call_end_recommended,
        call_end_reason: message.call_end_reason ?? message.intake?.partial_state.call_end_reason,
        last_assistant_redirect: message.last_assistant_redirect ?? message.intake?.partial_state.last_assistant_redirect,
        guardrail_warnings: message.intake?.guardrail_warnings,
        response_text: message.response_text ?? undefined
      });
      setVadState("listening");
      return;
    }
    if (message.type === "call.no_reply_prompt" || message.type === "call.ending") {
      setScopeDebug({
        off_topic_count: message.off_topic_count,
        redirect_count: message.redirect_count,
        no_reply_prompt_count: message.no_reply_prompt_count,
        call_end_recommended: message.call_end_recommended,
        call_end_reason: message.call_end_reason,
        last_assistant_redirect: message.last_assistant_redirect,
        guardrail_warnings: message.guardrail_warnings,
        response_text: message.response_text
      });
      setProviderWarnings(message.guardrail_warnings ?? []);
      setVadState(message.type === "call.ending" ? "silence" : "listening");
      return;
    }
    if (message.type === "error") {
      setError(message.detail);
    }
  }

  async function startRecording() {
    setError(null);
    setEvents([]);
    setProviderWarnings([]);
    setAudioRef(null);
    setSourceInputMode(null);
    setCallMetadata(null);
    setTtsStatus(null);
    setScopeDebug(null);
    setIntakeResponse(null);
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
            <div className="grid grid-cols-3 gap-2">
              <button
                className="border border-slate-900 bg-slate-950 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                type="button"
                onClick={submitTranscript}
                disabled={loading}
              >
                {loading ? "Creating..." : "Create Case"}
              </button>
              <button
                className="border border-sky-700 bg-sky-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                type="button"
                onClick={submitIntakeTranscript}
                disabled={loading}
              >
                {loading ? "Thinking..." : "Intake"}
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
            <dl className="mt-3 grid gap-2 text-xs text-slate-700">
              <div className="grid grid-cols-[110px_1fr] gap-2">
                <dt className="text-slate-500">Source</dt>
                <dd className="font-medium">{providerMode}</dd>
              </div>
              <div className="grid grid-cols-[110px_1fr] gap-2">
                <dt className="text-slate-500">Input</dt>
                <dd className="font-medium">{sourceInputMode ?? "local_mic"}</dd>
              </div>
              <div className="grid grid-cols-[110px_1fr] gap-2">
                <dt className="text-slate-500">Transcript</dt>
                <dd className="font-medium">{transcriptSource}</dd>
              </div>
              <div className="grid grid-cols-[110px_1fr] gap-2">
                <dt className="text-slate-500">Audio Ref</dt>
                <dd className="break-all font-medium">{audioRef ?? "-"}</dd>
              </div>
              <div className="grid grid-cols-[110px_1fr] gap-2">
                <dt className="text-slate-500">Twilio TTS</dt>
                <dd className="font-medium">
                  {ttsStatus
                    ? `${ttsStatus.enabled ? "enabled" : "disabled"} / ${ttsStatus.configured ? "configured" : "unconfigured"}`
                    : "-"}
                </dd>
              </div>
              <div className="grid grid-cols-[110px_1fr] gap-2">
                <dt className="text-slate-500">TTS Voice</dt>
                <dd className="font-medium">{ttsStatus?.voice ?? "-"}</dd>
              </div>
              <div className="grid grid-cols-[110px_1fr] gap-2">
                <dt className="text-slate-500">TTS Profile</dt>
                <dd className="font-medium">
                  {ttsStatus ? `${ttsStatus.profile ?? "normal"} / ${ttsStatus.ssml_enabled ? "SSML" : "text"}` : "-"}
                </dd>
              </div>
            </dl>
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
          {providerWarnings.length > 0 ? (
            <div className="mt-4 border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              <h2 className="text-sm font-semibold">Provider Warnings</h2>
              <ul className="mt-2 space-y-1">
                {providerWarnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {ttsStatus?.warnings && ttsStatus.warnings.length > 0 ? (
            <div className="mt-4 border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              <h2 className="text-sm font-semibold">TTS Warnings</h2>
              <ul className="mt-2 space-y-1">
                {ttsStatus.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {callMetadata ? (
            <div className="mt-4 border border-command-line bg-command-panel p-3 text-xs text-slate-700">
              <h2 className="text-sm font-semibold text-slate-950">Call Metadata</h2>
              <dl className="mt-2 grid gap-2">
                <div className="grid grid-cols-[90px_1fr] gap-2">
                  <dt className="text-slate-500">Provider</dt>
                  <dd className="font-medium">{callMetadata.provider}</dd>
                </div>
                <div className="grid grid-cols-[90px_1fr] gap-2">
                  <dt className="text-slate-500">Call ID</dt>
                  <dd className="break-all font-medium">{callMetadata.call_id}</dd>
                </div>
                <div className="grid grid-cols-[90px_1fr] gap-2">
                  <dt className="text-slate-500">From</dt>
                  <dd className="font-medium">{callMetadata.from_number ?? "-"}</dd>
                </div>
                <div className="grid grid-cols-[90px_1fr] gap-2">
                  <dt className="text-slate-500">To</dt>
                  <dd className="font-medium">{callMetadata.to_number ?? "-"}</dd>
                </div>
                <div className="grid grid-cols-[90px_1fr] gap-2">
                  <dt className="text-slate-500">Country</dt>
                  <dd className="font-medium">{callMetadata.country ?? "-"}</dd>
                </div>
                <div className="grid grid-cols-[90px_1fr] gap-2">
                  <dt className="text-slate-500">Codec</dt>
                  <dd className="font-medium">
                    {callMetadata.codec} / {callMetadata.sample_rate} Hz
                  </dd>
                </div>
              </dl>
            </div>
          ) : null}
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
              <div>
                <dt className="text-slate-500">Transcript Source</dt>
                <dd className="font-medium">{transcriptSource}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Provider</dt>
                <dd className="font-medium">{providerMode}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Group</dt>
                <dd className="font-medium">{caseRecord?.case_group ?? caseRecord?.case.case_group ?? intakeResponse?.case_group ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Team</dt>
                <dd className="font-medium">{caseRecord?.recommended_team ?? caseRecord?.case.recommended_team ?? intakeResponse?.recommended_team ?? "-"}</dd>
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
            <h2 className="text-base font-semibold">Intake Decision</h2>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Action</dt>
                <dd className="font-medium">{intakeResponse?.action ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Group</dt>
                <dd className="font-medium">{intakeResponse?.case_group ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Team</dt>
                <dd className="font-medium">{intakeResponse?.recommended_team ?? "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Missing</dt>
                <dd className="font-medium">{intakeResponse?.missing_fields.join(", ") || "-"}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-slate-500">Response Text</dt>
                <dd className="font-medium">{intakeResponse?.response_text || "-"}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-slate-500">Reason</dt>
                <dd className="font-medium">{intakeResponse?.reason || "-"}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-slate-500">Guardrails</dt>
                <dd className="font-medium">{intakeResponse?.guardrail_warnings.join(", ") || "-"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Off Topic</dt>
                <dd className="font-medium">{scopeDebug?.off_topic_count ?? intakeResponse?.partial_state.off_topic_count ?? 0}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Redirects</dt>
                <dd className="font-medium">{scopeDebug?.redirect_count ?? intakeResponse?.partial_state.redirect_count ?? 0}</dd>
              </div>
              <div>
                <dt className="text-slate-500">No Reply</dt>
                <dd className="font-medium">{scopeDebug?.no_reply_prompt_count ?? intakeResponse?.partial_state.no_reply_prompt_count ?? 0}</dd>
              </div>
              <div>
                <dt className="text-slate-500">End Call</dt>
                <dd className="font-medium">
                  {(scopeDebug?.call_end_recommended ?? intakeResponse?.partial_state.call_end_recommended) ? "recommended" : "no"}
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-slate-500">Close Reason</dt>
                <dd className="font-medium">{scopeDebug?.call_end_reason ?? intakeResponse?.partial_state.call_end_reason ?? "-"}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-slate-500">Last Redirect</dt>
                <dd className="font-medium">
                  {scopeDebug?.last_assistant_redirect ?? intakeResponse?.partial_state.last_assistant_redirect ?? "-"}
                </dd>
              </div>
            </dl>
            <div className="mt-4 border-t border-command-line pt-4">
              <h3 className="text-sm font-semibold">Conversation Turns</h3>
              <div className="mt-2 grid max-h-40 gap-2 overflow-auto text-xs">
                {(intakeResponse?.partial_state.conversation_turns ?? []).length === 0 ? (
                  <p className="text-slate-500">No intake turns yet.</p>
                ) : (
                  intakeResponse?.partial_state.conversation_turns.map((turn) => (
                    <div key={`${turn.turn_index}-${turn.created_at}`} className="border border-command-line bg-command-panel p-2">
                      <span className="font-semibold">{turn.speaker}</span>
                      <p className="mt-1 text-slate-700">{turn.text}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="border border-command-line bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold">Structured JSON</h2>
            <pre className="mt-4 max-h-[440px] overflow-auto bg-slate-950 p-3 text-xs text-slate-100">
              {JSON.stringify({ case: caseRecord?.case ?? triage ?? null, intake: intakeResponse }, null, 2)}
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
