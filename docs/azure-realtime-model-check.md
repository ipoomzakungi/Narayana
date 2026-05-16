# Azure Realtime Model Check

Use these commands before setting `AZURE_REALTIME_DEPLOYMENT`. Do not set it to `gpt-realtime-1.5` unless your Azure resource/region shows that model is available and you have deployed it.

## Variables

```powershell
$SUBSCRIPTION_ID="<subscription-id>"
$RESOURCE_GROUP="<resource-group>"
$AOAI_ACCOUNT="<azure-openai-or-foundry-resource-name>"
$LOCATION="<resource-location>" # for example eastus2 or swedencentral
$VOICE_RESOURCE="<foundry-or-speech-resource-name>"
az account set --subscription $SUBSCRIPTION_ID
```

## Current Azure OpenAI Deployments

```powershell
az cognitiveservices account deployment list `
  --resource-group $RESOURCE_GROUP `
  --name $AOAI_ACCOUNT `
  --query "[].{name:name,model:properties.model.name,version:properties.model.version,format:properties.model.format,sku:sku.name,capacity:sku.capacity}" `
  --output table
```

Use the deployment `name` from this output as `AZURE_REALTIME_DEPLOYMENT`.

## Available Realtime Models For This Resource

```powershell
az cognitiveservices account list-models `
  --resource-group $RESOURCE_GROUP `
  --name $AOAI_ACCOUNT `
  --query "[?contains(name, 'realtime') || contains(kind, 'realtime') || contains(format, 'realtime')].{name:name,version:version,kind:kind,format:format,skuName:skuName}" `
  --output table
```

If your Azure CLI does not support `list-models`, use Azure Resource Manager directly:

```powershell
az rest `
  --method get `
  --url "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/providers/Microsoft.CognitiveServices/locations/$LOCATION/models?api-version=2024-10-01" `
  --query "value[?contains(name, 'realtime') || contains(properties.name, 'realtime')].{name:name,model:properties.name,version:properties.version,format:properties.format,skus:properties.skus}" `
  --output jsonc
```

## Check Specific Models

```powershell
az cognitiveservices account list-models --resource-group $RESOURCE_GROUP --name $AOAI_ACCOUNT `
  --query "[?name=='gpt-realtime-1.5' || properties.name=='gpt-realtime-1.5']" --output jsonc

az cognitiveservices account list-models --resource-group $RESOURCE_GROUP --name $AOAI_ACCOUNT `
  --query "[?name=='gpt-realtime-2' || properties.name=='gpt-realtime-2']" --output jsonc

az cognitiveservices account list-models --resource-group $RESOURCE_GROUP --name $AOAI_ACCOUNT `
  --query "[?name=='gpt-realtime' || properties.name=='gpt-realtime']" --output jsonc
```

An empty array means that model is not available for that resource/region. Prefer `gpt-realtime-1.5` only when it appears here and a deployment exists or can be created.

## Voice Live API Resource/Region Check

```powershell
az cognitiveservices account show `
  --resource-group $RESOURCE_GROUP `
  --name $VOICE_RESOURCE `
  --query "{name:name,kind:kind,location:location,endpoint:properties.endpoint,customSubDomainName:properties.customSubDomainName}" `
  --output jsonc

az cognitiveservices account list-models `
  --resource-group $RESOURCE_GROUP `
  --name $VOICE_RESOURCE `
  --query "[?contains(name, 'realtime') || contains(kind, 'realtime') || contains(format, 'realtime')].{name:name,version:version,kind:kind,format:format}" `
  --output table
```

Voice Live uses a Foundry or Speech in Foundry Tools resource endpoint like:

```text
wss://<resource-name>.services.ai.azure.com/voice-live/realtime?api-version=2025-10-01&model=<model-or-deployment>
```

or for older resources:

```text
wss://<resource-name>.cognitiveservices.azure.com/voice-live/realtime?api-version=2025-10-01&model=<model-or-deployment>
```

The realtime code keeps deployment/model names configurable:

```env
ENABLE_REALTIME_VOICE=false
REALTIME_PROVIDER=azure_openai_realtime
AZURE_REALTIME_ENDPOINT=https://<resource-name>.openai.azure.com
AZURE_REALTIME_API_KEY=<key>
AZURE_REALTIME_DEPLOYMENT=<deployment-name-from-az-output>
AZURE_REALTIME_API_VERSION=v1
```

For older preview deployments, use `AZURE_REALTIME_API_VERSION=2025-04-01-preview`; the app then uses the preview `/openai/realtime?api-version=...&deployment=...` URL shape.

References:

- [Azure GPT Realtime supported models](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/realtime-audio)
- [Azure GPT Realtime WebSocket endpoint formats](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/realtime-audio-websockets)
- [Azure Voice Live endpoint and auth](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-how-to)
