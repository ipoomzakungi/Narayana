# Data Model: Azure Speech Validation Build

## AudioTurnArtifact

Represents the WAV file created for one committed caller turn.

**Fields**:

- `audio_ref`: string path or debug identifier for the WAV artifact.
- `session_id`: voice session identifier.
- `turn_id`: committed turn identifier.
- `sample_rate_hz`: integer, copied from the accepted audio frames.
- `channels`: integer, fixed to 1 for V1 validation.
- `encoding`: string, fixed to PCM16 input and WAV output.
- `duration_ms`: committed turn duration.
- `frame_count`: number of frames included in the artifact.
- `created_at`: timestamp when the artifact is written.

**Validation Rules**:

- `audio_ref` must be present before real speech validation is attempted.
- `sample_rate_hz` must be positive.
- `channels` must be 1.
- Frames must be PCM16 and 20 ms, matching existing audio validation.
- The WAV file must be readable with correct channel count, sample width, and sample rate.

## TranscriptResult

Represents text produced from a caller turn.

**Fields**:

- `transcript`: recognized or fallback text.
- `transcript_source`: enum: `mock`, `azure_speech_stt`, `fallback`.
- `language`: language hint or recognized language when available.
- `confidence`: numeric confidence when available; fallback confidence is low.
- `audio_ref`: optional audio artifact reference.
- `provider_warnings`: list of visible warning strings.

**Validation Rules**:

- Successful Azure Speech recognition uses `transcript_source=azure_speech_stt`.
- Mock provider output uses `transcript_source=mock`.
- Speech failure or missing audio in Azure provider mode uses `transcript_source=fallback`.
- Fallback transcript must not be the hardcoded Thai flood crisis sample.

## VoiceProviderResult

Extends the existing provider result returned by mock, Azure Speech/OpenAI, and optional Voice Live providers.

**Fields**:

- Existing: `provider_mode`, `transcript`, `language`, `confidence`, `triage`, `response_text`, `provider_warnings`.
- New: `transcript_source`, `audio_ref`.

**Relationships**:

- Contains one `TranscriptResult`.
- Contains one `TriageResult`.
- May reference one `AudioTurnArtifact`.

## CrisisCaseEvent

Represents the WebSocket message sent after a turn creates a case.

**Fields**:

- `type`: `triage.case.created`.
- `session_id`: voice session identifier.
- `transcript`: text used for triage.
- `provider_mode`: source provider mode.
- `transcript_source`: `mock`, `azure_speech_stt`, or `fallback`.
- `audio_ref`: optional audio artifact reference.
- `response_text`: optional safe caller guidance.
- `warnings`: provider warnings.
- `record`: stored case record.

**Validation Rules**:

- `transcript_source` is always present.
- `warnings` is always present, possibly empty.
- Fallback results must have review-required triage after safety rules.

## State Transitions

```text
listening -> speech -> silence threshold -> thinking -> provider result -> case created -> listening
```

Audio buffering mirrors the same lifecycle:

```text
pre-speech ring buffer -> active turn buffer -> WAV artifact -> audio_ref on CallerTurn -> provider processing
```

Failure path:

```text
WAV write failure or Speech failure -> fallback transcript result -> safety rules -> human-review-required case
```
