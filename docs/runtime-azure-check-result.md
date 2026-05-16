# Azure Runtime Check Result

Date: 2026-05-16
Tested commit: `4723234198c3472fc252578eb34ce70840bebaec`

## Azure Account

- Subscription name: `Azure subscription 1`
- Subscription id: `adcfa840-4838-4553-9bf8-bf7bb55973fe`
- Tenant: `KMITL`

## Required Local Environment

The active shell did not have these required variables set:

- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_CONTAINER_APP_NAME`
- `AZURE_OPENAI_RESOURCE_NAME`
- `AZURE_SPEECH_RESOURCE_NAME`
- `AZURE_LOCATION`
- `AZURE_REALTIME_API_KEY`
- `AZURE_SPEECH_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `TWILIO_WEBHOOK_PUBLIC_BASE_URL`

The active shell also did not have optional Cosmos variables set:

- `COSMOS_DB_ENDPOINT`
- `COSMOS_DB_KEY`
- `COSMOS_DB_DATABASE`
- `COSMOS_DB_CONTAINER`

Created `.local.runtime.env.template` with placeholders only. No real secrets were written.

Ignored local env files `.env.azure.local` and `.env.realtime.local` were inspected for key names only. They define Azure Speech/Voice Live related keys, including `AZURE_REALTIME_API_KEY`, `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, `AZURE_SPEECH_RESOURCE_GROUP`, `AZURE_SPEECH_RESOURCE_NAME`, `AZURE_VOICE_LIVE_ENDPOINT`, `AZURE_VOICE_LIVE_MODEL`, `AZURE_VOICE_LIVE_RESOURCE_GROUP`, and `AZURE_VOICE_LIVE_RESOURCE_NAME`.

Those files do not define the Container App names, Twilio credentials, Azure OpenAI resource name, realtime endpoint, realtime deployment, or realtime API version.

## Container App Discovery

The Container App was discovered by matching the known FQDN:

- Resource group: `rg-narayana-demo`
- Container App: `narayana-api`
- Location: `Southeast Asia`
- FQDN: `narayana-api.graypond-039de86c.southeastasia.azurecontainerapps.io`
- Image: `ghcr.io/ipoomzakungi/narayana-backend:latest`
- Active revisions mode: `Single`

The discovered FQDN matches the expected demo backend URL.

## Container App Environment

Existing env vars include:

- `ASSISTANT_DISPLAY_NAME`
- `AZURE_REALTIME_API_KEY` as secretref `azure-realtime-key`
- `AZURE_SPEECH_KEY` as secretref `azure-speech-key`
- `AZURE_SPEECH_REGION`
- `AZURE_SPEECH_VOICE`
- `AZURE_VOICE_LIVE_ENDPOINT`
- `AZURE_VOICE_LIVE_MODEL`
- `CALL_MAX_NO_REPLY_PROMPTS`
- `CALL_MAX_OFF_TOPIC_REDIRECTS`
- `CALL_NO_REPLY_SECONDS`
- `CORS_ALLOW_ORIGINS`
- `ENABLE_MULTI_TURN_INTAKE`
- `ENABLE_REALTIME_VOICE`
- `ENABLE_TWILIO_INITIAL_GREETING`
- `ENABLE_TWILIO_TTS_RESPONSE`
- `REALTIME_PROVIDER`
- `TELEPHONY_PROVIDER`
- `TTS_MAX_CHARS`
- `TTS_OUTPUT_FORMAT`
- `TTS_PITCH_NORMAL`
- `TTS_PITCH_RED`
- `TTS_RATE_FOLLOWUP`
- `TTS_RATE_NORMAL`
- `TTS_RATE_RED`
- `TTS_RATE_UNCLEAR`
- `TTS_USE_SSML`
- `TTS_VOLUME`
- `TWILIO_INITIAL_GREETING_TEXT`
- `TWILIO_PHONE_NUMBER`
- `TWILIO_WEBHOOK_PUBLIC_BASE_URL`
- `USE_MOCK_SERVICES`
- `VOICE_INPUT_MODE`

Required target vars missing from the deployed Container App:

- `REALTIME_INPUT_AUDIO_FORMAT`
- `REALTIME_TWILIO_AUDIO_PASSTHROUGH`
- `AZURE_REALTIME_ENDPOINT`
- `AZURE_REALTIME_DEPLOYMENT`
- `AZURE_REALTIME_API_VERSION`
- `TWILIO_INITIAL_GREETING_PROFILE`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `CALL_AUDIT_ENABLED`
- `CALL_AUDIT_LOG_TRANSCRIPTS`

Note: The deployed realtime and speech secret refs use `azure-realtime-key` and `azure-speech-key`, while the requested demo secret names are `azure-realtime-api-key` and `azure-speech-key`.

## Azure OpenAI Availability

No Cognitive Services account of kind `OpenAI` was visible in the current subscription. The only Cognitive Services account found in `rg-narayana-demo` was:

- `speech-narayana-demo`, kind `SpeechServices`, location `southeastasia`, SKU `F0`

The Voice Live resource named by the ignored local env files also resolves to `speech-narayana-demo`, kind `SpeechServices`, not an Azure OpenAI resource.

Because no Azure OpenAI resource was visible and `AZURE_OPENAI_RESOURCE_NAME` was missing, deployment listing and `list-models` could not be run for an Azure OpenAI resource.

Availability result:

- `gpt-realtime-1.5`: not detected; no Azure OpenAI resource visible
- `gpt-realtime`: not detected; no Azure OpenAI resource visible
- `gpt-realtime-2`: not detected; no Azure OpenAI resource visible
- `gpt-4o-realtime`: not detected; no Azure OpenAI resource visible

Selected realtime deployment: none.

No `AZURE_REALTIME_DEPLOYMENT` value was guessed.
