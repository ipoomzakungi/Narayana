# Quickstart: Multi-Turn Crisis Conversation Intake

## 1. Local Backend Checks

```powershell
python -m compileall app scripts
pytest tests/unit/test_intake_models.py
pytest tests/unit/test_intake_guardrails.py
pytest tests/unit/test_case_grouping_service.py
pytest tests/unit/test_intake_session_store.py
pytest tests/unit/test_intake_orchestrator.py
pytest tests/unit/test_intake_provider.py
pytest tests/integration/test_intake_api.py
```

Full regression:

```powershell
pytest
```

## 2. Manual Intake Demo

Start backend locally in mock/default mode:

```powershell
$env:USE_MOCK_SERVICES="true"
$env:ENABLE_MULTI_TURN_INTAKE="false"
uvicorn app.main:app --reload
```

Manual follow-up test:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/intake/from-transcript" `
  -ContentType "application/json" `
  -Body '{
    "session_id": "debug-session",
    "transcript": "น้ำท่วมอยู่ที่หาดใหญ่",
    "language_hint": "th",
    "source_input_mode": "manual"
  }'
```

Expected result:
- `action=ask_followup`
- one concise Thai `response_text`
- location preserved as known field
- missing injury/people fields listed
- no `created_case`

Manual RED escalation test:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/intake/from-transcript" `
  -ContentType "application/json" `
  -Body '{
    "session_id": "red-session",
    "transcript": "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง",
    "language_hint": "th",
    "source_input_mode": "manual"
  }'
```

Expected result:
- `action=create_case` or `escalate_human_review`
- `triage_level=RED`
- `human_review_required=true`
- group/team aligned to rescue and medical risk
- `created_case` present

## 3. Confirm Existing One-Shot Triage Still Works

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/triage/from-transcript" `
  -ContentType "application/json" `
  -Body '{
    "transcript": "น้ำท่วมอยู่ที่หาดใหญ่ มีคนแก่หายใจลำบาก ติดอยู่ชั้นสอง",
    "language_hint": "th"
  }'
```

Expected:
- Existing one-shot triage response remains valid.

## 4. Gated Twilio Intake Test

Keep default off until manual/API tests pass:

```powershell
$env:ENABLE_MULTI_TURN_INTAKE="false"
pytest tests/integration/test_twilio_media_flow.py
```

Enable locally for conversation-aware WebSocket behavior:

```powershell
$env:ENABLE_MULTI_TURN_INTAKE="true"
pytest tests/integration/test_twilio_media_flow.py
```

Expected with enabled path:
- incomplete committed transcript emits `intake.followup`
- high-risk committed transcript emits `triage.case.created`
- route paths remain unchanged

## 5. Frontend Checks

```powershell
cd frontend
npm test -- intake-api-client.test.ts voice-debug-console.test.tsx cases-dashboard.test.tsx
npm run build
```

Manual views:

```text
http://127.0.0.1:3000/voice-debug
http://127.0.0.1:3000/cases
```

Expected:
- `/voice-debug` shows intake follow-up action, response text, collected fields, group/team, missing fields, and warnings.
- `/cases` shows group/team and conversation summary for new records while older records still render.

## 6. Deployment Notes

Do not enable on Azure until tests pass:

```text
ENABLE_MULTI_TURN_INTAKE=false
```

After merge and GHCR backend deploy, enable with:

```powershell
az containerapp update `
  --name narayana-api `
  --resource-group rg-narayana-demo `
  --set-env-vars "ENABLE_MULTI_TURN_INTAKE=true"
```

Do not add Azure Speech/OpenAI, Cosmos DB, ACS, SMS, or dispatch behavior as part of this feature.
