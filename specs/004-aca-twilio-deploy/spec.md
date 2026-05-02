# Feature Specification: Azure Container Apps Deployment and Twilio Real-Call Test Support

**Feature Branch**: `003-telephony-adapter-spike`  
**Created**: 2026-05-03  
**Status**: Draft  
**Input**: User description: "Add Azure Container Apps deployment and Twilio real-call test support for Narayana. Backend must run on Azure Container Apps, frontend may use Vercel only, Twilio US voice number is +16082005400, backend needs WebSocket support for Twilio Media Streams, and tests must not call Azure or Twilio."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deploy Public Voice Backend (Priority: P1)

As a hackathon developer, I want to package and deploy the Narayana backend to a public WebSocket-capable hosting target so that Twilio Media Streams can reach the live voice gateway.

**Why this priority**: Real Twilio calls cannot validate the existing media WebSocket until the backend has a stable public URL that supports HTTP endpoints and WebSocket traffic.

**Independent Test**: Can be tested by building the backend package locally, deploying with mock mode enabled, and confirming the public health endpoint responds from the deployed URL.

**Acceptance Scenarios**:

1. **Given** the developer has an Azure subscription and container registry access, **When** they run the deployment workflow with required values, **Then** a public backend URL is produced for the Narayana API.
2. **Given** mock mode is enabled for the deployed backend, **When** the public health endpoint is checked, **Then** the response clearly reports mock/provider configuration without requiring Azure Speech or Twilio credentials.
3. **Given** the frontend is hosted separately, **When** the backend is deployed, **Then** the backend remains the authoritative host for the Twilio webhook and media WebSocket.

---

### User Story 2 - Verify Public Twilio Webhook (Priority: P2)

As a developer configuring the Twilio US voice number `+16082005400`, I want a repeatable way to verify the public webhook before placing real calls so that configuration mistakes are caught quickly.

**Why this priority**: Webhook URL, public base URL, and TwiML mistakes are common blockers for real-call demos. A fake webhook test reduces debugging time before using the phone network.

**Independent Test**: Can be tested by running a public webhook checker against the deployed backend URL and verifying both health and TwiML response shape.

**Acceptance Scenarios**:

1. **Given** a deployed backend URL, **When** the checker runs, **Then** it verifies the public health endpoint is reachable.
2. **Given** the Twilio webhook endpoint is reachable, **When** the checker sends a fake incoming-call payload, **Then** it confirms the response contains valid TwiML that points to the media WebSocket.
3. **Given** required URL values are missing or malformed, **When** the checker runs, **Then** it fails with a clear message and does not call real Twilio services.

---

### User Story 3 - Place Controlled Twilio Test Calls (Priority: P3)

As a developer with Twilio credentials, I want a helper that can place an outbound call from the configured US voice number to a verified test phone so that inbound media stream behavior can be validated without manual Twilio console steps.

**Why this priority**: Real-call validation is useful after deployment and webhook checks pass, but it must stay controlled, credential-gated, and safe for hackathon testing.

**Independent Test**: Can be tested without real Twilio credentials by verifying helper validation behavior and, manually with credentials, by calling a verified Thai phone after enabling required account permissions.

**Acceptance Scenarios**:

1. **Given** Twilio credentials, the US voice number `+16082005400`, a public backend URL, and a verified destination phone are configured, **When** the outbound helper runs, **Then** it requests a Twilio voice call using the public Narayana webhook URL.
2. **Given** required Twilio values are missing, **When** the outbound helper runs, **Then** it fails before making any network request and names the missing values.
3. **Given** the target is a Thai phone number, **When** the developer follows setup documentation, **Then** the documentation instructs them to configure verified caller ID and Thailand outbound geo permissions before calling.

---

### User Story 4 - Document Deployment and Real-Call Limits (Priority: P4)

As a reviewer or teammate, I want the deployment and Twilio call-test steps documented with limitations so that the demo does not imply production emergency readiness.

**Why this priority**: The feature enables real phone testing, which can be mistaken for production readiness unless the limits are explicit.

**Independent Test**: Can be tested by reviewing the documentation for the required setup sections and explicit scope limitations.

**Acceptance Scenarios**:

1. **Given** a teammate reads the setup documentation, **When** they follow the deployment section, **Then** they can identify required environment variables and why the backend cannot be hosted on frontend-only infrastructure.
2. **Given** a reviewer reads the Twilio section, **When** they evaluate the demo scope, **Then** they see explicit statements that ACS production support, SMS, and emergency dispatch are not implemented.

---

### Edge Cases

- Required deployment values are absent, partially set, or malformed.
- The public backend URL is reachable over HTTP but not WebSocket-capable.
- The configured public base URL has a trailing slash or uses the wrong scheme.
- The Twilio number webhook points to a stale deployment URL.
- The Twilio account cannot call Thailand until verified caller ID and geo permissions are configured.
- Twilio trial-account restrictions block outbound calling to unverified numbers.
- Helper scripts are run on a machine without expected command-line tools.
- The frontend is deployed successfully but points to a missing or wrong backend URL.
- A real phone test succeeds at the telephony layer but the system still runs in mock mode for safety.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a container packaging path for the Narayana backend suitable for public deployment with WebSocket support.
- **FR-002**: The deployment workflow MUST support a mock-first configuration with `USE_MOCK_SERVICES=true`, `VOICE_INPUT_MODE=twilio_call`, `TELEPHONY_PROVIDER=twilio`, `TWILIO_PHONE_NUMBER=+16082005400`, and a public Twilio webhook base URL.
- **FR-003**: The deployment workflow MUST clearly identify all required deployment values before attempting deployment.
- **FR-004**: The deployment workflow MUST fail with actionable messages when required local tools, cloud resource names, or environment values are missing.
- **FR-005**: The system MUST provide a public webhook checker that verifies the deployed health endpoint and fake Twilio incoming-call TwiML response.
- **FR-006**: The public webhook checker MUST NOT call real Twilio or Azure management APIs.
- **FR-007**: The system MUST provide an outbound call helper that can request a Twilio voice call only when all required Twilio credentials, source number, destination number, and public webhook URL are present.
- **FR-008**: The outbound call helper MUST fail before any network request when required call-test values are missing.
- **FR-009**: Environment examples MUST include `TWILIO_OUTBOUND_TO` and optional `AZURE_CONTAINER_APP_URL`.
- **FR-010**: Documentation MUST explain Azure Container Apps backend deployment, required environment variables, Twilio number webhook configuration, fake webhook test, inbound call test, outbound call test, verified caller ID setup, and Thailand outbound geo permissions.
- **FR-011**: Documentation MUST state that Vercel is acceptable for the frontend only and is not the backend host for Twilio Media Streams.
- **FR-012**: Documentation MUST state that ACS production implementation, SMS sending, and emergency dispatch remain out of scope.
- **FR-013**: Automated tests MUST cover helper validation and URL/TwiML helper behavior without calling Azure or Twilio.
- **FR-014**: Existing local microphone, simulated Twilio stream, and mock mode behavior MUST remain unchanged.

### Key Entities *(include if feature involves data)*

- **Deployment Configuration**: Values needed to package and deploy the public backend, including app name, resource group, location, registry/image details, public URL, and runtime environment variables.
- **Public Backend Endpoint**: The externally reachable base URL used by health checks, Twilio webhooks, and media stream URL generation.
- **Twilio Call Test Configuration**: Credentials and call-test values required to place a controlled outbound voice call from the US Twilio number to a verified destination.
- **Webhook Check Result**: The outcome of health and fake Twilio webhook checks, including pass/fail status, response details, and actionable errors.
- **Deployment Limitation**: Documented boundaries that prevent users from treating the demo as production telephony, SMS, ACS, or emergency dispatch capability.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can identify all required deployment values before deployment in under 5 minutes from the documentation.
- **SC-002**: The public webhook checker verifies health and TwiML response shape in under 30 seconds against a reachable deployed backend.
- **SC-003**: Helper validation tests run with zero Azure or Twilio credentials and complete without making external provider calls.
- **SC-004**: The outbound call helper reports every missing required call-test value in one run before attempting a provider request.
- **SC-005**: Documentation includes all three explicit exclusions: no ACS production implementation, no SMS, and no emergency dispatch.
- **SC-006**: Existing local and simulated voice demo tests continue to pass after the deployment and call-test additions.

## Assumptions

- The current branch `003-telephony-adapter-spike` remains the implementation branch for this follow-on work.
- The backend public deployment target must support both normal HTTP requests and WebSocket traffic.
- Mock mode is the first deployment validation mode; Azure Speech/OpenAI validation can be configured later with existing environment variables.
- The Twilio US voice number for this feature is `+16082005400`.
- The outbound Thai phone test is manual and requires user-owned Twilio credentials, verified caller ID setup, and permitted Thailand outbound calling.
- Frontend deployment can remain separate, but all Twilio webhook and media stream traffic must target the backend deployment.
- Automated tests validate helper behavior only and do not contact Azure, Twilio, SMS providers, ACS, or emergency services.
