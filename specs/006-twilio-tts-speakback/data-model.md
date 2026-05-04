# Data Model: Optional Twilio TTS Speak-Back

## SpeakBackSettings

Fields:
- `enable_twilio_tts_response`: boolean, default false.
- `azure_speech_voice`: string, default `th-TH-PremwadeeNeural`.
- `tts_max_chars`: integer, default 220.
- `tts_output_format`: string, default `mulaw_8khz`.
- Existing Azure Speech key/region fields indicate TTS configuration.

Validation:
- Speak-back is attempted only when enabled, Twilio stream ID exists, response text is non-empty, and Azure Speech key/region are configured.
- Default disabled behavior must require no Azure credentials.

## TTSRequest

Fields:
- `text`: non-empty string.
- `language`: optional string, default `th`.
- `voice`: optional override for manual tests only.

Validation:
- Blank text is invalid.
- Text is sanitized and length-limited before synthesis.
- Unsafe dispatch, ambulance-arrival, diagnosis, or closure/rejection language is replaced with a safe concise response.

## TTSResult

Fields:
- `configured`: boolean.
- `voice`: selected voice.
- `audio_format`: expected `mulaw_8khz`.
- `payloads`: list of base64 mu-law chunks for internal WebSocket send.
- `payload_count`: number of chunks.
- `total_bytes`: total raw mu-law bytes before base64.
- `estimated_duration_ms`: estimated playback duration.
- `warnings`: list of non-secret warnings.

Validation:
- Internal service may carry payloads; public test response must not return payloads.
- `payload_count` must be zero when unconfigured or synthesis fails.
- `warnings` must not include secrets or audio payloads.

## TwilioPlaybackMessage

Media event fields:
- `event`: `media`.
- `streamSid`: Twilio stream identifier from the start event.
- `media.payload`: base64 mu-law audio chunk.

Mark event fields:
- `event`: `mark`.
- `streamSid`: Twilio stream identifier.
- `mark.name`: playback marker name such as `narayana_tts_<timestamp>`.

Validation:
- `streamSid` is required for outbound Twilio playback.
- Media payload must be non-empty base64.
- Mark is sent after all media chunks when synthesis succeeds.

## TTSHealthSummary

Fields:
- `twilio_tts_response_enabled`: boolean.
- `azure_speech_tts_configured`: boolean.
- `azure_speech_voice`: string.

Validation:
- Health endpoint reports enabled/configured independently from mock voice/intake mode.
- Missing credentials should be visible through existing missing-variable warnings or TTS test response.

## TTSTestResponse

Fields:
- `configured`: boolean.
- `voice`: selected voice.
- `audio_format`: `mulaw_8khz`.
- `payload_count`: integer.
- `total_bytes`: integer.
- `estimated_duration_ms`: integer.
- `warnings`: list of strings.
- `missing_variables`: list of missing TTS-related variable names.

Validation:
- Must not include raw payloads by default.
- When unconfigured, response is 200 with `configured=false` and missing variables.
