# Research: Azure Container Apps Deployment and Twilio Real-Call Test Support

## Decision: Use Azure Container Apps for the backend public URL

**Rationale**: Twilio Media Streams require a public backend that can serve both HTTP webhook requests and WebSocket media stream connections. Azure Container Apps is the selected backend target and aligns with the Azure-focused hackathon goal.

**Alternatives considered**:

- Vercel for backend: rejected because the requirement says Vercel may be used for the frontend only and the backend must support Twilio Media Stream WebSockets.
- Local tunnel only: rejected because it is useful for debugging but not enough for a repeatable deployed demo.

## Decision: Use a Python slim Docker image and uvicorn on port 8000

**Rationale**: The existing backend is a FastAPI app with `uvicorn` already in `requirements.txt`. Binding to `0.0.0.0:8000` matches the requested runtime command and Container Apps ingress target.

**Alternatives considered**:

- Gunicorn plus uvicorn workers: rejected for this tooling spike because the simplest uvicorn command is sufficient for a hackathon validation build.
- Multi-stage image: rejected for now because the backend has no compile step and the image can stay simple.

## Decision: Exclude local data and secrets from the container image

**Rationale**: `.env`, `.env.*`, `.data/`, local audio WAVs, local case JSON, node dependencies, and caches must not be copied into the deployment image. Runtime secrets and public URLs are supplied as environment variables during deployment.

**Alternatives considered**:

- Copy the full repo: rejected because it risks packaging secrets/local artifacts and frontend build outputs.
- Generate `.env` inside the image: rejected because secrets must remain outside the image.

## Decision: Deployment script validates variables and supports `az containerapp up` first

**Rationale**: `az containerapp up` is the lowest-friction path when available. The script should detect whether it can use it, otherwise print concrete fallback commands for registry build and Container Apps create/update. This keeps the script helpful on machines with different Azure CLI setups.

**Alternatives considered**:

- Hard fail when `az containerapp up` is unavailable: rejected because the user requested a fallback command path.
- Implement a fully general production IaC template: rejected because this is deployment tooling for a hackathon demo, not production infrastructure.

## Decision: Helper scripts use Python standard library

**Rationale**: `requests` is not in the current backend requirements. Python standard-library `urllib`, `xml.etree.ElementTree`, and `base64` are sufficient for checking public webhooks and issuing a simple Twilio REST call.

**Alternatives considered**:

- Add `requests`: rejected to keep dependency churn low.
- Use Twilio Python SDK: rejected because the helper can call the REST API directly and tests must not hit the network.

## Decision: Automated tests cover helper functions only

**Rationale**: The feature explicitly says tests must not call Azure or Twilio. Unit tests should validate environment checks, URL construction, TwiML parsing, and request construction using mocked network functions.

**Alternatives considered**:

- End-to-end deployment tests: rejected because they require cloud credentials and live infrastructure.
- Real Twilio API tests: rejected because they require credentials and could place calls.

## Decision: Keep backend voice/telephony behavior unchanged

**Rationale**: The existing telephony spike already validates local mic, simulated Twilio media, and the shared `AudioSessionProcessor`. This feature is tooling-only, so modifying voice processing would increase risk without helping deployment.

**Alternatives considered**:

- Change Twilio media route for deployment: rejected because the current route already supports the required webhook and WebSocket contracts.
