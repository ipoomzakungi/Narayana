[CmdletBinding()]
param(
    [string]$ResourceGroup = $(if ($env:AZURE_RESOURCE_GROUP) { $env:AZURE_RESOURCE_GROUP } else { "rg-narayana-demo" }),
    [string]$Location = $(if ($env:AZURE_LOCATION) { $env:AZURE_LOCATION } else { "southeastasia" }),
    [string]$ContainerAppName = $(if ($env:AZURE_CONTAINER_APP_NAME) { $env:AZURE_CONTAINER_APP_NAME } else { "narayana-api" }),
    [string]$ContainerEnvName = $(if ($env:AZURE_CONTAINER_ENV_NAME) { $env:AZURE_CONTAINER_ENV_NAME } else { "narayana-env" }),
    [string]$Image = $(if ($env:GHCR_IMAGE) { $env:GHCR_IMAGE } else { "ghcr.io/ipoomzakungi/narayana-backend:latest" }),
    [string]$TwilioPhoneNumber = $(if ($env:TWILIO_PHONE_NUMBER) { $env:TWILIO_PHONE_NUMBER } else { "+16082005400" }),
    [string]$TwilioWebhookPublicBaseUrl = $(if ($env:TWILIO_WEBHOOK_PUBLIC_BASE_URL) { $env:TWILIO_WEBHOOK_PUBLIC_BASE_URL } else { "https://placeholder" }),
    [string]$UseMockServices = $(if ($env:USE_MOCK_SERVICES) { $env:USE_MOCK_SERVICES } else { "true" }),
    [string]$VoiceInputMode = $(if ($env:VOICE_INPUT_MODE) { $env:VOICE_INPUT_MODE } else { "twilio_call" }),
    [string]$TelephonyProvider = $(if ($env:TELEPHONY_PROVIDER) { $env:TELEPHONY_PROVIDER } else { "twilio" }),
    [string]$CorsAllowOrigins = $env:CORS_ALLOW_ORIGINS,
    [string]$GhcrUsername = $env:GHCR_USERNAME,
    [string]$GhcrToken = $env:GHCR_PAT
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI 'az' was not found. Install Azure CLI, run 'az login', and retry."
}

$accountId = az account show --query id -o tsv 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($accountId)) {
    throw "Azure CLI is not logged in. Run 'az login' and select the expected subscription before retrying."
}

$requiredValues = @{
    AZURE_RESOURCE_GROUP = $ResourceGroup
    AZURE_LOCATION = $Location
    AZURE_CONTAINER_APP_NAME = $ContainerAppName
    AZURE_CONTAINER_ENV_NAME = $ContainerEnvName
    GHCR_IMAGE = $Image
    TWILIO_PHONE_NUMBER = $TwilioPhoneNumber
}

$missing = @()
foreach ($key in $requiredValues.Keys) {
    if ([string]::IsNullOrWhiteSpace([string]$requiredValues[$key])) {
        $missing += $key
    }
}
if ($missing.Count -gt 0) {
    throw "Missing required deployment values: $($missing -join ', ')"
}

if ($UseMockServices -ne "true") {
    throw "This GHCR deployment script is for mock-mode Twilio testing only. Set USE_MOCK_SERVICES=true."
}

$envVars = @(
    "USE_MOCK_SERVICES=$UseMockServices",
    "VOICE_INPUT_MODE=$VoiceInputMode",
    "TELEPHONY_PROVIDER=$TelephonyProvider",
    "TWILIO_PHONE_NUMBER=$TwilioPhoneNumber",
    "TWILIO_WEBHOOK_PUBLIC_BASE_URL=$TwilioWebhookPublicBaseUrl"
)
if (-not [string]::IsNullOrWhiteSpace($CorsAllowOrigins)) {
    $envVars += "CORS_ALLOW_ORIGINS=$CorsAllowOrigins"
}

$registryArgs = @()
if (-not [string]::IsNullOrWhiteSpace($GhcrUsername) -and -not [string]::IsNullOrWhiteSpace($GhcrToken)) {
    $registryArgs = @(
        "--registry-server", "ghcr.io",
        "--registry-username", $GhcrUsername,
        "--registry-password", $GhcrToken
    )
}

Write-Host "Using Azure subscription: $accountId"
Write-Host "Ensuring resource group '$ResourceGroup' exists..."
az group create --name $ResourceGroup --location $Location --output none
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$envExists = $false
az containerapp env show --name $ContainerEnvName --resource-group $ResourceGroup --output none 2>$null
if ($LASTEXITCODE -eq 0) {
    $envExists = $true
}

if (-not $envExists) {
    Write-Host "Creating Container Apps environment '$ContainerEnvName'..."
    az containerapp env create `
        --name $ContainerEnvName `
        --resource-group $ResourceGroup `
        --location $Location `
        --output none
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$appExists = $false
az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --output none 2>$null
if ($LASTEXITCODE -eq 0) {
    $appExists = $true
}

if ($appExists) {
    Write-Host "Updating Container App '$ContainerAppName' from GHCR image '$Image'..."
    if ($registryArgs.Count -gt 0) {
        az containerapp registry set `
            --name $ContainerAppName `
            --resource-group $ResourceGroup `
            --server ghcr.io `
            --username $GhcrUsername `
            --password $GhcrToken `
            --output none
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    az containerapp update `
        --name $ContainerAppName `
        --resource-group $ResourceGroup `
        --image $Image `
        --set-env-vars $envVars `
        --output none
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "Creating Container App '$ContainerAppName' from GHCR image '$Image'..."
    az containerapp create `
        --name $ContainerAppName `
        --resource-group $ResourceGroup `
        --environment $ContainerEnvName `
        --image $Image `
        --ingress external `
        --target-port 8000 `
        --env-vars $envVars `
        @registryArgs `
        --output none
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$fqdn = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query properties.configuration.ingress.fqdn `
    -o tsv
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($fqdn)) {
    throw "Deployment completed, but the Container App FQDN could not be read."
}

$realBaseUrl = "https://$fqdn"
Write-Host "Updating TWILIO_WEBHOOK_PUBLIC_BASE_URL to $realBaseUrl..."
az containerapp update `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --set-env-vars "TWILIO_WEBHOOK_PUBLIC_BASE_URL=$realBaseUrl" `
    --output none
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Container App URL:"
Write-Host $realBaseUrl
Write-Host ""
Write-Host "Final Twilio webhook URL:"
Write-Host "$realBaseUrl/api/telephony/twilio/incoming-call"
