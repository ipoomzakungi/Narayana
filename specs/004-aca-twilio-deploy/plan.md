# Implementation Plan: Azure Container Apps Deployment and Twilio Real-Call Test Support

**Branch**: `003-telephony-adapter-spike` | **Date**: 2026-05-03 | **Spec**: `specs/004-aca-twilio-deploy/spec.md`
**Input**: Feature specification from `specs/004-aca-twilio-deploy/spec.md`

## Summary

Add deployment and testing tooling that lets the Narayana backend run publicly on Azure Container Apps for Twilio Media Streams while keeping the frontend deployable separately. This feature adds a backend `Dockerfile`, `.dockerignore`, PowerShell deployment helper, public webhook checker, Twilio outbound call helper, helper-only unit tests, README guidance, and environment examples.

The implementation must not change `AudioSessionProcessor`, `/ws/local-audio`, `/ws/telephony/twilio/{call_id}`, ACS behavior, SMS, or dispatch behavior. Mock mode remains the first deployment path:

```dotenv
USE_MOCK_SERVICES=true
VOICE_INPUT_MODE=twilio_call
TELEPHONY_PROVIDER=twilio
TWILIO_PHONE_NUMBER=+16082005400
TWILIO_WEBHOOK_PUBLIC_BASE_URL=https://<container-app-url>
```

## Technical Context

**Language/Version**: Python 3.11 backend tooling and tests; Windows PowerShell for Azure deployment helper; Docker Linux container runtime for FastAPI backend.  
**Primary Dependencies**: Existing FastAPI/uvicorn backend, pytest, Python standard library for helper scripts, Docker, Azure CLI, Azure Container Apps extension, optional Twilio REST API over HTTPS. No `requests` dependency is required for new scripts.  
**Storage**: No new application storage. Container image must exclude `.env`, `.env.*`, `.data/`, local audio, local case JSON, caches, and frontend build artifacts.  
**Testing**: `python -m compileall app scripts`, `pytest`, plus existing frontend gates when final verification is requested. New tests cover helper functions only and must not call Azure or Twilio.  
**Target Platform**: Backend container running on Azure Container Apps with public HTTP and WebSocket support on port `8000`; frontend may remain local, Azure Static Web Apps, Vercel, or another static host.  
**Project Type**: FastAPI backend plus Next.js frontend plus deployment/helper scripts.  
**Performance Goals**: Startup command binds to `0.0.0.0:8000`; webhook checker should finish within 30 seconds against a reachable public URL.  
**Constraints**: Tooling only; no backend voice pipeline changes; no ACS production implementation; no SMS; no emergency dispatch; no real provider calls in automated tests; secrets must not be committed or baked into the Docker image.  
**Scale/Scope**: One backend Docker image, one Azure Container Apps deployment script, two Python helper scripts, one helper test module, README/env updates.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file still contains placeholders and defines no enforceable project-specific gates. This plan applies the active Narayana safety and tooling constraints:

- Backend public deployment must support Twilio webhook and media WebSocket traffic.
- Tooling must fail clearly when required values are missing.
- Automated tests must not call Azure, Twilio, SMS providers, ACS, or emergency services.
- Secrets and local data must not be included in the container image.
- No change to voice processing, ACS disabled behavior, SMS, or dispatch behavior.

Pre-design status: PASS. No unresolved clarifications.

Post-design status: PASS. Research, data model, contracts, and quickstart preserve tooling-only scope.

## Project Structure

### Documentation (this feature)

```text
specs/004-aca-twilio-deploy/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── azure-container-apps-deploy.md
│   ├── check-public-webhook.md
│   ├── docker-runtime.md
│   └── twilio-outbound-call.md
└── tasks.md
```

### Source Code (repository root)

```text
Dockerfile
.dockerignore
.env.example
README.md

scripts/
├── azure_container_apps_deploy.ps1
├── check_public_webhook.py
└── twilio_outbound_call.py

tests/
└── unit/
    └── test_twilio_test_helpers.py
```

**Structure Decision**: Add deployment and helper tooling at the repository root and `scripts/`. Keep backend source, frontend source, and existing audio/telephony services unchanged.

## Implementation Approach

1. Add a root `Dockerfile` using a Python slim image, install `requirements.txt`, copy backend/runtime files, expose port `8000`, and run `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
2. Add `.dockerignore` to exclude `.env`, `.env.*`, `.data/`, `.git/`, frontend dependencies/build outputs, caches, test caches, and local editor/OS files.
3. Add `scripts/azure_container_apps_deploy.ps1` to validate required deployment variables and either run `az containerapp up` when available or print clear fallback commands for registry build and Container Apps creation/update.
4. Add `scripts/check_public_webhook.py` using Python standard library only. It reads `TWILIO_WEBHOOK_PUBLIC_BASE_URL`, normalizes the base URL, checks `/api/health/azure`, posts fake `CallSid=CA_TEST` to `/api/telephony/twilio/incoming-call`, and verifies returned XML includes `/ws/telephony/twilio/CA_TEST`.
5. Add `scripts/twilio_outbound_call.py` using Python standard library only. It validates `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `TWILIO_OUTBOUND_TO`, and `TWILIO_WEBHOOK_PUBLIC_BASE_URL`; then posts to Twilio REST API only after validation succeeds.
6. Add unit tests in `tests/unit/test_twilio_test_helpers.py` for URL normalization, missing env validation, TwiML parsing, Twilio API request construction, and no-network behavior through mocked standard-library openers.
7. Update `.env.example` with `TWILIO_OUTBOUND_TO` and optional `AZURE_CONTAINER_APP_URL`.
8. Update `README.md` with Azure Container Apps deployment, required environment variables, Twilio number webhook setup for `+16082005400`, fake webhook test, inbound call test, outbound verified Thai phone test, verified caller ID, Twilio Geo Permissions for Thailand, Vercel frontend-only explanation, and explicit exclusions.
9. Final verification should run `python -m compileall app scripts`, `pytest`, `cd frontend && npm test`, and `cd frontend && npm run build`.

## Complexity Tracking

No constitution violations or complexity exceptions are required.
