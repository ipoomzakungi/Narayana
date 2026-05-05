# Feature Specification: Azure Realtime Voice Provider Spike

**Feature Branch**: `010-azure-realtime-voice`
**Created**: 2026-05-05
**Status**: Draft
**Input**: User description: "Add an experimental Azure realtime voice provider spike to Narayana. Test whether Azure Voice Live API or Azure OpenAI GPT Realtime API can reduce call latency compared with the current STT to OpenAI to TTS pipeline while keeping the current path as default and safe fallback."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve Current Twilio Call Flow (Priority: P1)

As a Narayana demo operator, I want the current Twilio voice call path to remain unchanged unless realtime voice is explicitly enabled, so that the working crisis intake demo stays reliable.

**Why this priority**: The existing Twilio Media Stream, VAD, intake, TTS, and dashboard path is already validated. The realtime provider is a spike and must not destabilize the demo.

**Independent Test**: Start a Twilio or simulated Twilio call with realtime voice disabled and verify the existing greeting, turn-based intake, optional speak-back, case creation, and call audit behavior still work.

**Acceptance Scenarios**:

1. **Given** realtime voice is disabled, **When** a Twilio media stream sends caller audio, **Then** Narayana uses the existing turn-based voice pipeline and does not attempt a realtime provider connection.
2. **Given** realtime voice is disabled, **When** a caller triggers a follow-up or case creation, **Then** the response payloads and Twilio route paths remain compatible with the current deployed backend.
3. **Given** no realtime provider credentials are configured, **When** the backend starts, **Then** startup succeeds and the current mock/local demo path remains available.

---

### User Story 2 - Manually Test Azure Realtime Voice (Priority: P2)

As a hackathon developer, I want to enable one experimental Azure realtime provider for a test call, so that I can measure whether direct realtime audio interaction feels faster than the current turn-based pipeline.

**Why this priority**: The spike only creates value if the team can run a controlled manual test using either Azure Voice Live or Azure OpenAI GPT Realtime credentials.

**Independent Test**: Enable realtime voice with valid provider settings, place or simulate a Twilio call, and verify inbound audio is forwarded to the realtime provider and outbound audio chunks are streamed back to Twilio.

**Acceptance Scenarios**:

1. **Given** realtime voice is enabled and the Azure Voice Live option is selected with valid settings, **When** caller audio arrives from Twilio, **Then** Narayana connects to the selected realtime provider and forwards caller audio without waiting for a full turn-based STT/TTS cycle.
2. **Given** realtime voice is enabled and the Azure OpenAI GPT Realtime option is selected with valid settings, **When** caller audio arrives from Twilio, **Then** Narayana connects to the selected realtime provider and streams returned audio chunks back to the same Twilio call.
3. **Given** realtime audio output is received, **When** Narayana sends audio to Twilio, **Then** the call receives Twilio-compatible media events and the debug/audit stream records the realtime output event.

---

### User Story 3 - Fallback Safely on Realtime Failure (Priority: P3)

As a crisis demo operator, I want realtime provider failures to fall back to the current safe voice path, so that provider instability does not drop the call or bypass crisis safety rules.

**Why this priority**: Realtime availability, regional support, and preview API behavior can vary. The system must remain useful during a demo even if realtime provider setup fails.

**Independent Test**: Enable realtime voice with missing, invalid, or failing provider settings and verify the call continues through the existing turn-based pipeline with clear warnings.

**Acceptance Scenarios**:

1. **Given** realtime voice is enabled but required provider settings are missing, **When** a Twilio call starts, **Then** Narayana records a realtime configuration warning and uses the current turn-based path.
2. **Given** the realtime provider connection fails mid-call, **When** caller audio continues arriving, **Then** Narayana logs the failure, keeps the WebSocket alive where possible, and processes subsequent caller turns through the current fallback path.
3. **Given** the realtime provider returns an error or unsafe text, **When** Narayana handles the response, **Then** existing crisis-only safety constraints remain active and the assistant never claims rescue has been dispatched or gives a diagnosis.

---

### User Story 4 - Compare Latency Across Voice Paths (Priority: P4)

As a hackathon developer, I want readable latency logs for the current and realtime voice paths, so that I can decide whether the realtime spike improves the demo enough to pursue.

**Why this priority**: The purpose of the spike is latency validation. Without comparable timing data, the team cannot make a credible decision.

**Independent Test**: Run a simulated or live call and inspect logs/audit events for connection, input audio, output audio, response start, response completion, fallback, and per-stage latency measurements.

**Acceptance Scenarios**:

1. **Given** realtime voice is enabled, **When** Narayana connects and processes audio, **Then** logs include realtime connection, input audio sent, output audio received, response started, response completed, and latency measurements.
2. **Given** realtime voice falls back to the current path, **When** fallback occurs, **Then** logs include the realtime error reason and timing up to fallback.
3. **Given** the current path is used, **When** a caller turn completes, **Then** existing turn-based latency logging remains available for comparison.

### Edge Cases

- Realtime provider selected but credentials, deployment, endpoint, model, or API version are missing.
- Realtime provider connects successfully but disconnects before a response is complete.
- Realtime provider returns audio in a format that cannot be streamed to Twilio without normalization.
- Caller barges in while realtime audio is being streamed back.
- Twilio stream ends while a realtime provider connection is still open.
- Realtime provider emits text or audio that conflicts with crisis-intake guardrails.
- Provider latency is worse than the current pipeline and must be observable without affecting the default path.
- Current mock mode is active while realtime voice is disabled.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST keep realtime voice disabled by default.
- **FR-002**: System MUST provide a runtime configuration option named `REALTIME_PROVIDER` with supported values `none`, `azure_voice_live`, and `azure_openai_realtime`.
- **FR-003**: System MUST provide a runtime configuration option named `ENABLE_REALTIME_VOICE` that explicitly controls whether Twilio audio is routed to a realtime provider.
- **FR-004**: System MUST support realtime provider configuration fields for endpoint, API key, deployment, API version, Voice Live endpoint, and Voice Live model.
- **FR-005**: System MUST define a common realtime voice provider contract with connect, send audio frame, receive audio event, and close behaviors.
- **FR-006**: System MUST expose experimental provider choices for Azure Voice Live and Azure OpenAI GPT Realtime without making either required for normal startup.
- **FR-007**: System MUST route Twilio media frames to the selected realtime provider only when realtime voice is enabled and a non-`none` provider is selected.
- **FR-008**: System MUST stream realtime provider audio output back to Twilio as media events when the provider returns playable audio.
- **FR-009**: System MUST keep the existing turn-based STT, intake/model, and TTS pipeline available as fallback at all times.
- **FR-010**: System MUST fallback to the existing turn-based pipeline when realtime configuration is incomplete, connection fails, audio streaming fails, provider output fails, or provider closes unexpectedly.
- **FR-011**: System MUST apply the existing crisis-intake scope and safety constraints to realtime interactions, including no rescue dispatch claims, no diagnosis, crisis-only behavior, and safe fallback on uncertainty.
- **FR-012**: System MUST log realtime lifecycle events for connected, input audio sent, output audio received, response started, response completed, and errors.
- **FR-013**: System MUST record latency measurements for realtime connection setup, input audio forwarding, first output audio received, response completion, and fallback timing where measurable.
- **FR-014**: System MUST not log secrets, API keys, authorization headers, or raw audio payloads.
- **FR-015**: System MUST preserve existing Twilio webhook and media WebSocket route paths.
- **FR-016**: System MUST preserve current local microphone, manual transcript, mock mode, dashboard, call audit, and Twilio fallback behavior when realtime voice is disabled.
- **FR-017**: System MUST clearly indicate through logs or health/debug output which realtime provider is selected, whether realtime voice is enabled, and whether required settings are configured.
- **FR-018**: System MUST allow manual validation with real Azure realtime credentials while automated tests remain runnable without Azure or Twilio credentials.

### Key Entities *(include if feature involves data)*

- **Realtime Provider Configuration**: Selected realtime provider, enabled flag, configured endpoints/deployments/models, and whether required values are present.
- **Realtime Voice Session**: A per-call connection attempt to a selected realtime provider, linked to a call/session identifier and lifecycle status.
- **Realtime Audio Event**: A normalized event representing caller audio sent to the provider, provider audio returned to Twilio, response start/completion, or provider error.
- **Latency Measurement**: Timing metadata for provider connection, input forwarding, first output, completion, fallback, and current-pipeline comparison points.
- **Fallback Decision**: The reason and timestamp for switching from realtime voice back to the existing turn-based pipeline.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With realtime voice disabled, all existing Twilio call, local microphone, intake, TTS, and dashboard test flows pass unchanged.
- **SC-002**: With realtime voice enabled and valid provider settings, a manual Twilio test call can produce at least one realtime audio output event sent back to the caller.
- **SC-003**: When realtime provider setup fails, the call falls back to the existing turn-based path without backend startup failure or call-route removal.
- **SC-004**: Realtime lifecycle logs include connection, input audio sent, output audio received, response start, response completion, error, and latency data for manual comparison.
- **SC-005**: No logs or committed files expose realtime API keys, authorization values, or raw audio payloads.
- **SC-006**: Safety review confirms realtime responses do not claim dispatch, do not diagnose, and remain scoped to crisis intake.
- **SC-007**: Automated tests can run successfully with no Azure realtime credentials configured.

## Assumptions

- The realtime spike is experimental and may depend on Azure regional availability, preview API behavior, or model deployment availability.
- The current turn-based voice pipeline remains the production demo path until realtime reliability and latency are proven.
- Twilio Media Streams remains the only phone ingress path for this spike.
- Azure Communication Services, SMS, emergency dispatch integrations, Cosmos DB provisioning, and production authentication remain out of scope.
- Manual realtime validation will be performed only after credentials and eligible Azure resources are available outside the repository.
