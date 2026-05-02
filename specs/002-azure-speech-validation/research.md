# Research: Azure Speech Validation Build

## Decision: Persist committed PCM16 turns as WAV with the standard library

**Rationale**: Incoming browser audio frames are already normalized and validated as PCM16 mono frames. Python's `wave` module can write a valid WAV header with sample width, channel count, and sample rate without adding dependencies. This keeps the enhancement small and testable.

**Alternatives considered**:

- Keep raw PCM only: rejected because Azure Speech file recognition and manual replay are easier with WAV.
- Add an audio processing dependency: rejected because no resampling or complex transcoding is required for this validation path.
- Persist every incoming frame as separate files: rejected because turn-level WAV files match the speech recognition unit and keep debugging simpler.

## Decision: Buffer audio at the WebSocket route boundary

**Rationale**: The WebSocket route already receives every audio frame and sees `TurnManager` commit events. Keeping buffering there avoids coupling Azure provider code to live WebSocket concerns and avoids changing VAD decisions.

**Alternatives considered**:

- Move buffering into `TurnManager`: rejected because `TurnManager` should remain responsible for state transitions and timing, not file persistence.
- Move buffering into the Azure provider: rejected because mock mode and debug output also need audio reference metadata, and providers should process committed turns rather than own frame streams.

## Decision: Use a small ring buffer for pre-speech padding

**Rationale**: The existing manager reports `pre_speech_padding_ms` but does not retain frames. A ring buffer sized from frame duration and padding milliseconds can include the frames immediately before speech start without changing the VAD API.

**Alternatives considered**:

- Skip pre-speech padding: acceptable as a fallback, but less reliable for clipped first syllables.
- Rewrite turn detection to own all buffers: rejected as too broad for a minimal enhancement.

## Decision: Add transcript provenance to provider results

**Rationale**: Operators and reviewers need to distinguish mock transcripts, real speech-to-text transcripts, and fallback text. Adding `transcript_source` and `audio_ref` to the provider result gives the route and UI a single contract to display.

**Alternatives considered**:

- Infer source from provider mode only: rejected because Azure provider may return a fallback and mock provider may be selected due to missing credentials.
- Store provenance only in debug events: rejected because case-created messages and UI state need the data directly.

## Decision: Azure provider failure returns safe fallback, not mock crisis text

**Rationale**: A hardcoded Thai flood transcript in the Azure failure path hides speech recognition failures and can create misleading cases. Failure should produce low confidence, human review, missing/unclear transcript evidence, and provider warnings.

**Alternatives considered**:

- Fall back to deterministic mock transcript: rejected because it violates the validation goal.
- Raise a WebSocket error and skip case creation: rejected because crisis intake should surface review-required uncertainty instead of dropping the turn.

## Decision: Credential-gated Azure tests remain manual or skipped

**Rationale**: The normal test suite must pass for reviewers without Azure credentials. Unit tests can mock the speech recognizer seam and assert behavior, while a README manual flow validates real Azure Speech with a Thai WAV file.

**Alternatives considered**:

- Require Azure credentials in CI/local tests: rejected because it blocks offline review and hackathon handoff.
- Do not test Azure provider behavior: rejected because failure safety and audio_ref usage are critical.
