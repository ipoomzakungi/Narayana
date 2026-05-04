# Research: Twilio Initial Greeting

## Decision: Reuse Existing Azure Speech TTS Service

**Rationale**: Narayana already has `AzureSpeechTTSService` for safe text sanitization, SSML profile support, Azure Speech synthesis, Twilio-compatible mu-law output, payload chunking, and warning metadata. Reusing it avoids two separate spoken-output safety paths.

**Alternatives considered**:

- Add a separate greeting synthesis service. Rejected because it would duplicate safety filtering and Azure Speech behavior.
- Use Twilio provider-native voice by default before media stream connection. Rejected for the primary path because the project prefers Azure Speech TTS voice control and one TTS stack. Keep fallback disabled and optional.

## Decision: Send Greeting After Twilio Start Event

**Rationale**: Twilio outbound media events require the stream identifier provided by the media stream start event. Sending the greeting after start preserves the current webhook and WebSocket contract and allows the same WebSocket to carry outbound greeting audio.

**Alternatives considered**:

- Return a provider-native spoken prompt before `<Connect>`. Rejected as the default because it bypasses Azure Speech TTS and can change caller experience before the media stream begins.
- Wait for the first caller audio frame before greeting. Rejected because the feature goal is to speak first.

## Decision: Add a Dedicated Greeting TTS Profile

**Rationale**: Greeting needs calm, clear, slightly slow speech that is distinct from RED escalation and unclear-speech profiles. A dedicated `greeting` profile can default to `-5%` rate and `0%` pitch while still sharing the same SSML builder.

**Alternatives considered**:

- Use `normal` profile. Rejected because the requested demo behavior is explicitly slightly slow and greeting-specific.
- Use `followup` profile. Acceptable fallback, but a dedicated enum value makes health/debug/test output clearer.

## Decision: Fail Open and Continue Listening

**Rationale**: Crisis intake must not depend on the greeting. If synthesis is unconfigured, fails, returns empty audio, or Twilio media sending fails, Narayana should log the failure and continue listening.

**Alternatives considered**:

- Close the WebSocket or report a fatal error. Rejected because it would block emergency intake.
- Disable the call when TTS is missing. Rejected because local/mock Twilio ingress must continue to work without speech credentials.

## Decision: Keep Greeting State In Memory Per Call

**Rationale**: The only required state is whether greeting playback has already been attempted for the active call. That state lives naturally in the WebSocket session and does not need persistence.

**Alternatives considered**:

- Store greeting attempts in case records. Rejected because greeting occurs before any case may exist and is operational debug data, not crisis case data.
