export type ProviderMode = "mock" | "azure_speech_openai" | "azure_voice_live";
export type IncidentType = "flood" | "fire" | "medical" | "accident" | "earthquake" | "public_safety" | "unknown";
export type TriageLevel = "RED" | "YELLOW" | "GREEN";
export type CaseStatus = "pending" | "contacted" | "dispatched" | "resolved" | "closed";
export type VadState = "silence" | "speech" | "listening" | "thinking" | "speaking";
export type TranscriptSource = "mock" | "azure_speech_stt" | "fallback";
export type SourceInputMode = "local_mic" | "twilio_call" | "acs_call";
export type IntakeAction = "ask_followup" | "create_case" | "escalate_human_review";
export type CaseGroup =
  | "rescue"
  | "medical"
  | "fire"
  | "flood"
  | "police_public_safety"
  | "tourist_support"
  | "utility_infrastructure"
  | "shelter_supplies"
  | "mental_health_support"
  | "unknown_human_review";

export interface CallMetadata {
  provider: "none" | "twilio" | "acs";
  call_id: string;
  from_number: string | null;
  to_number: string | null;
  country: string | null;
  codec: "mulaw" | "pcm16" | "unknown";
  sample_rate: number;
  started_at: string;
  raw_provider_payload?: Record<string, unknown> | null;
}

export interface TriageResult {
  case_id: string;
  language: string;
  incident_type: IncidentType;
  triage_level: TriageLevel;
  confidence: number;
  location_text: string;
  people_affected: number | null;
  injuries: string;
  immediate_needs: string[];
  caller_phone_optional: string | null;
  ai_summary: string;
  triage_reason: string;
  human_review_required: boolean;
  missing_fields: string[];
  created_at: string;
  updated_at: string;
  status: CaseStatus;
  case_group?: CaseGroup | string | null;
  recommended_team?: string | null;
  conversation_summary?: string | null;
  intake_session_id?: string | null;
  intake_audit?: Record<string, unknown>[];
}

export interface CaseRepositoryRecord {
  case: TriageResult;
  session_id: string | null;
  source_provider: ProviderMode;
  debug_event_count: number;
  stored_at: string;
  case_group?: CaseGroup | string | null;
  recommended_team?: string | null;
  conversation_summary?: string | null;
  intake_session_id?: string | null;
  intake_audit?: Record<string, unknown>[];
}

export interface CaseSnapshotResponse {
  generated_at: string;
  expires_at: string;
  ttl_seconds: number;
  count: number;
  source: "cache" | "repository";
  cases: CaseRepositoryRecord[];
}

export interface AudioDebugEvent {
  event_id: string;
  session_id: string;
  case_id?: string | null;
  event_type: string;
  state?: VadState | null;
  timestamp: string;
  duration_ms?: number | null;
  metadata: Record<string, unknown>;
}

export interface ConversationTurn {
  speaker: "caller" | "assistant" | "system";
  text: string;
  created_at: string;
  turn_index: number;
}

export interface IntakeCollectedFields {
  language: string;
  incident_type: IncidentType;
  location_text: string;
  people_affected: number | null;
  injuries: string;
  immediate_needs: string[];
  caller_phone_optional: string | null;
  landmarks: string[];
  urgency_signals: string[];
  missing_fields: string[];
}

export interface IntakeSessionState {
  session_id: string;
  call_id?: string | null;
  source_input_mode: string;
  conversation_turns: ConversationTurn[];
  collected_fields: IntakeCollectedFields;
  triage_level?: TriageLevel | null;
  confidence: number;
  human_review_required: boolean;
  followup_count: number;
  max_followups: number;
  case_group?: CaseGroup | null;
  recommended_team: string;
  final_case_id?: string | null;
  status: string;
  guardrail_warnings: string[];
  decision_audit: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
}

export interface IntakeResponse {
  session_id: string;
  action: IntakeAction;
  response_text: string;
  partial_state: IntakeSessionState;
  case_group: CaseGroup;
  recommended_team: string;
  triage_level: TriageLevel;
  human_review_required: boolean;
  missing_fields: string[];
  reason: string;
  guardrail_warnings: string[];
  created_case: CaseRepositoryRecord | null;
}

export type VoiceWsMessage =
  | {
      type: "session.started";
      session_id: string;
      provider_mode: ProviderMode;
      state: VadState;
      source_input_mode?: SourceInputMode;
      call_metadata?: CallMetadata;
    }
  | { type: "debug.event"; event: AudioDebugEvent }
  | {
      type: "triage.case.created";
      session_id: string;
      transcript: string;
      provider_mode: ProviderMode;
      transcript_source: TranscriptSource;
      audio_ref: string | null;
      response_text: string | null;
      warnings: string[];
      record: CaseRepositoryRecord;
      intake?: {
        action: IntakeAction;
        case_group: CaseGroup;
        recommended_team: string;
        missing_fields: string[];
        reason: string;
        guardrail_warnings: string[];
        partial_state: IntakeSessionState;
      };
      source_input_mode?: SourceInputMode;
      call_metadata?: CallMetadata;
    }
  | {
      type: "intake.followup";
      session_id: string;
      transcript: string;
      action: IntakeAction;
      response_text: string;
      partial_state: IntakeSessionState;
      case_group: CaseGroup;
      recommended_team: string;
      triage_level: TriageLevel;
      human_review_required: boolean;
      missing_fields: string[];
      reason: string;
      guardrail_warnings: string[];
      warnings?: string[];
      provider_mode?: ProviderMode;
      transcript_source?: TranscriptSource;
      audio_ref?: string | null;
      source_input_mode?: SourceInputMode;
      call_metadata?: CallMetadata;
    }
  | { type: "error"; detail: string }
  | { type: "session.closed"; session_id: string };
