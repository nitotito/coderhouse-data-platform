param(
    [string]$Profile = "coderhouse-dev",
    [string]$Region = "us-east-1"
)
$ErrorActionPreference = "Continue"
$repo = Split-Path $PSScriptRoot -Parent
$results = @()
$checks = @(
    @{ Name = "identity"; Arguments = @("sts", "get-caller-identity") },
    @{ Name = "glue_database"; Arguments = @("glue", "get-database", "--name", "lakehouse_db") },
    @{ Name = "athena_workgroup"; Arguments = @("athena", "get-work-group", "--work-group", "primary") },
    @{ Name = "flink_status"; Arguments = @("kinesisanalyticsv2", "describe-application", "--application-name", "coderhouse-dev-transactions-flink", "--query", "ApplicationDetail.{Status:ApplicationStatus,Runtime:RuntimeEnvironment,Version:ApplicationVersionId}") }
)
foreach ($check in $checks) {
    $arguments = $check.Arguments + @("--profile", $Profile, "--region", $Region, "--output", "json", "--no-cli-pager")
    $raw = & aws @arguments 2>&1
    $code = $LASTEXITCODE
    $output = ($raw | ForEach-Object { "$_" }) -join [Environment]::NewLine
    $state = if ($code -eq 0) { "PASS" } elseif ($output -match "EntityNotFoundException") { "ABSENT" } else { "BLOCKED" }
    $results += [pscustomobject]@{ Check = $check.Name; State = $state; ExitCode = $code; Output = $output }
    Write-Host "$state $($check.Name)"
}
$report = [pscustomobject]@{
    CheckedAtUtc = [DateTime]::UtcNow.ToString("o")
    Profile = $Profile
    Region = $Region
    Checks = $results
}
$destination = Join-Path $repo "docs/evidence/iceberg-aws-preflight.json"
[IO.File]::WriteAllText($destination, ($report | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
Write-Host "Evidence: $destination"
if ($results.State -contains "BLOCKED") { exit 1 }
