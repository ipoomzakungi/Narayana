# Quickstart: Crisis Scope Guardrails

## Local Verification

Run the full local gates:

```powershell
python -m compileall app scripts
pytest
cd frontend
npm test
npm run build
```

## Manual Off-Topic Intake Test

Start the backend locally and submit repeated off-topic turns to the intake endpoint:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/intake/from-transcript" `
  -ContentType "application/json" `
  -Body '{"session_id":"scope-demo","transcript":"เล่าเรื่องตลกให้ฟังหน่อย","language_hint":"th","source_input_mode":"manual"}'
```

Expected first response:

```text
ขออภัยค่ะ ระบบนี้ใช้สำหรับรับแจ้งเหตุหรือขอความช่วยเหลือเท่านั้น หากต้องการแจ้งเหตุ กรุณาบอกสถานการณ์และสถานที่ค่ะ
```

Send another unrelated transcript, then a third. The third should set `call_end_recommended=true` and `call_end_reason=repeated_off_topic`.

## Emergency Override Test

After an off-topic redirect, submit:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/intake/from-transcript" `
  -ContentType "application/json" `
  -Body '{"session_id":"scope-demo","transcript":"ช่วยด้วย น้ำท่วม มีคนแก่หายใจลำบากติดอยู่ชั้นสอง","language_hint":"th","source_input_mode":"manual"}'
```

Expected:

- off-topic counters reset or stop increasing
- normal crisis intake/escalation continues
- RED/high-risk rules still apply

## Twilio No-Reply Demo Settings

Use short thresholds for controlled testing only:

```powershell
$env:USE_MOCK_SERVICES="true"
$env:ENABLE_MULTI_TURN_INTAKE="true"
$env:ENABLE_TWILIO_TTS_RESPONSE="true"
$env:ENABLE_TWILIO_INITIAL_GREETING="true"
$env:CALL_NO_REPLY_SECONDS="10"
$env:CALL_NO_REPLY_PROMPT_SECONDS="15"
$env:CALL_MAX_NO_REPLY_PROMPTS="2"
$env:CALL_END_ON_NO_REPLY="true"
```

Expected call behavior:

1. Initial greeting plays.
2. If no caller speech is received, Narayana says: `ยังอยู่ในสายไหมคะ หากต้องการแจ้งเหตุ กรุณาเล่าสถานการณ์สั้น ๆ ได้เลยค่ะ`.
3. If silence continues after the configured maximum prompts, Narayana says: `หากไม่มีการตอบกลับ ระบบจะสิ้นสุดสายนี้นะคะ`.
4. The WebSocket closes safely after the final prompt path.

## Logs and Debug

Watch for:

```text
scope.off_topic
scope.emergency_override
call.no_reply_prompt
call.no_reply_close
```

Debug UI should show:

- `off_topic_count`
- `no_reply_prompt_count`
- `call_end_recommended`
- `call_end_reason`
- last assistant redirect
- guardrail warnings

No Azure OpenAI secrets, ACS, SMS, web search, or dispatch integration are required.
