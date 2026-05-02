[CmdletBinding()]
param(
    [string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$Location = $env:AZURE_LOCATION,
    [string]$ContainerAppName = $env:AZURE_CONTAINER_APP_NAME,
    [string]$ContainerEnvName = $(if ($env:AZURE_CONTAINER_ENV_NAME) { $env:AZURE_CONTAINER_ENV_NAME } else { "narayana-env" }),
    [string]$RegistryName = $env:AZURE_REGISTRY_NAME,
    [string]$ImageName = $(if ($env:AZURE_IMAGE_NAME) { $env:AZURE_IMAGE_NAME } else { "narayana-backend:latest" }),
    [string]$TwilioPhoneNumber = $(if ($env:TWILIO_PHONE_NUMBER) { $env:TWILIO_PHONE_NUMBER } else { "+16082005400" }),
    [string]$TwilioWebhookPublicBaseUrl = $env:TWILIO_WEBHOOK_PUBLIC_BASE_URL,
    [string]$UseMockServices = $(if ($env:USE_MOCK_SERVICES) { $env:USE_MOCK_SERVICES } else { "true" }),
    [string]$VoiceInputMode = $(if ($env:VOICE_INPUT_MODE) { $env:VOICE_INPUT_MODE } else { "twilio_call" }),
    [string]$TelephonyProvider = $(if ($env:TELEPHONY_PROVIDER) { $env:TELEPHONY_PROVIDER } else { "twilio" }),
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

function Require-Values {
    param([hashtable]$Values)
    $missing = @()
    foreach ($key in $Values.Keys) {
        if ([string]::IsNullOrWhiteSpace([string]$Values[$key])) {
            $missing += $key
        }
    }
    if ($missing.Count -gt 0) {
        throw "Missing required deployment values: $($missing -join ', ')"
    }
}

function Test-AzContainerAppUp {
    try {
        az containerapp up --help *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

Require-Values @{
    AZURE_RESOURCE_GROUP = $ResourceGroup
    AZURE_LOCATION = $Location
    AZURE_CONTAINER_APP_NAME = $ContainerAppName
    TWILIO_PHONE_NUMBER = $TwilioPhoneNumber
    TWILIO_WEBHOOK_PUBLIC_BASE_URL = $TwilioWebhookPublicBaseUrl
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI 'az' was not found. Install Azure CLI, run 'az login', and retry."
}

$envVars = @(
    "USE_MOCK_SERVICES=$UseMockServices",
    "VOICE_INPUT_MODE=$VoiceInputMode",
    "TELEPHONY_PROVIDER=$TelephonyProvider",
    "TWILIO_PHONE_NUMBER=$TwilioPhoneNumber",
    "TWILIO_WEBHOOK_PUBLIC_BASE_URL=$TwilioWebhookPublicBaseUrl"
)

$canUseContainerAppUp = Test-AzContainerAppUp

if ($canUseContainerAppUp -and -not $PrintOnly) {
    Write-Host "Deploying Narayana backend with az containerapp up..."
    az containerapp up `
        --name $ContainerAppName `
        --resource-group $ResourceGroup `
        --location $Location `
        --source . `
        --ingress external `
        --target-port 8000 `
        --env-vars $envVars

    Write-Host "Deployment requested. Set your Twilio voice webhook to:"
    Write-Host "$TwilioWebhookPublicBaseUrl/api/telephony/twilio/incoming-call"
    exit $LASTEXITCODE
}

Write-Host "az containerapp up is unavailable or -PrintOnly was used."
Write-Host "Use these fallback commands after filling optional registry values."
Write-Host ""
Write-Host "az group create --name $ResourceGroup --location $Location"
if ([string]::IsNullOrWhiteSpace($RegistryName)) {
    Write-Host "# Set AZURE_REGISTRY_NAME before running fallback ACR commands."
    Write-Host '$env:AZURE_REGISTRY_NAME="narayanaregistry"'
    $RegistryName = "<registry-name>"
}
Write-Host "az acr create --resource-group $ResourceGroup --name $RegistryName --sku Basic"
Write-Host "az acr build --registry $RegistryName --image $ImageName ."
Write-Host "az containerapp env create --name $ContainerEnvName --resource-group $ResourceGroup --location $Location"
Write-Host "az containerapp create --name $ContainerAppName --resource-group $ResourceGroup --environment $ContainerEnvName --image $RegistryName.azurecr.io/$ImageName --ingress external --target-port 8000 --env-vars $($envVars -join ' ')"
Write-Host ""
Write-Host "Expected Twilio webhook:"
Write-Host "$TwilioWebhookPublicBaseUrl/api/telephony/twilio/incoming-call"
