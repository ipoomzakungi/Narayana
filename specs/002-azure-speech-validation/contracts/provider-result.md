# Contract: Voice Provider Result

All voice providers return a common result object after processing either a transcript or a committed caller turn.

## Fields

```json
{
  "provider_mode": "mock",
  "transcript": "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง",
  "transcript_source": "mock",
  "audio_ref": null,
  "language": "th",
  "confidence": 0.92,
  "triage": {},
  "response_text": "รับทราบ ระบบจะส่งข้อมูลให้เจ้าหน้าที่ตรวจสอบ โปรดอยู่ในที่ปลอดภัยถ้าทำได้",
  "provider_warnings": []
}
```

## transcript_source Values

- `mock`: Deterministic mock provider output.
- `azure_speech_stt`: Real speech-to-text output from a committed audio artifact.
- `fallback`: Controlled fallback after speech validation or provider failure.

## Provider Rules

### Mock Provider

- Uses `provider_mode=mock`.
- Uses `transcript_source=mock`.
- May keep using the deterministic Thai sample when processing a synthetic committed turn.
- Must not require Azure credentials.

### Azure Speech/OpenAI Provider

- Uses `provider_mode=azure_speech_openai`.
- If `CallerTurn.audio_ref` exists and speech credentials are configured, it attempts real speech-to-text and returns `transcript_source=azure_speech_stt` on success.
- If a manual transcript is processed through this provider, it may triage the supplied text but must mark `transcript_source=fallback` and warn that speech-to-text was bypassed.
- If speech credentials are missing, audio is missing, recognition fails, or no usable transcript is returned, it returns `transcript_source=fallback`.
- Fallback must include provider warnings and a low-confidence human-review-required triage result.
- Fallback must not use the deterministic Thai flood sample as the transcript.

### Azure Voice Live Provider

- Remains optional/experimental.
- May pass through the same metadata fields when used.
- Must not block the required Azure Speech/OpenAI validation path.

## Safety Rules

After every provider result:

- Apply deterministic safety rules before case creation.
- RED or low-confidence cases require human review.
- Never auto-dispatch, auto-close, reject, or downgrade emergency help.
