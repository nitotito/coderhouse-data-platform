param([switch]$Run, [string]$Profile = "coderhouse-dev", [string]$Region = "us-east-1")
if (-not $Run) { Write-Host "Use -Run only with AWS deployment/cost approval."; exit 0 }
$ErrorActionPreference = "Continue"
$repo = Split-Path $PSScriptRoot -Parent
$evidence = Join-Path $repo "docs/evidence"
$appName = "coderhouse-dev-transactions-flink"
$bucket = "coderhouse-data-lake-672049777597"
$prefix = "lakehouse/lakehouse_db/transaction_aggregates/"
$started = $false
$runId = "pe5_" + [DateTime]::UtcNow.ToString("yyyyMMdd_HHmmss")
$startedAt = [DateTimeOffset]::UtcNow
$report = [ordered]@{ RunId = $runId; StartedAtUtc = $startedAt.ToString("o"); Status = "RUNNING" }

function Save-Json($Name, $Value) {
    # A concurrency token is unnecessary for delivery evidence.
    if ($null -ne $Value.ApplicationDetail) {
        $Value.ApplicationDetail.PSObject.Properties.Remove("ConditionalToken")
    }
    [IO.File]::WriteAllText((Join-Path $evidence $Name), ($Value | ConvertTo-Json -Depth 60), [Text.UTF8Encoding]::new($false))
}
function Invoke-AwsJson([string[]]$Arguments, [switch]$AllowAbsent) {
    $raw = & aws @Arguments --profile $Profile --region $Region --output json --no-cli-pager 2>&1
    $code = $LASTEXITCODE
    $body = ($raw | ForEach-Object { "$_" }) -join [Environment]::NewLine
    if ($code -ne 0) {
        if ($AllowAbsent -and $body -match "EntityNotFoundException") { return $null }
        throw "AWS $($Arguments[0]) $($Arguments[1]): $body"
    }
    if (-not [string]::IsNullOrWhiteSpace($body)) { return ($body | ConvertFrom-Json) }
}
function App-State {
    $detail = Invoke-AwsJson -Arguments @("kinesisanalyticsv2", "describe-application", "--application-name", $appName)
    return $detail.ApplicationDetail.ApplicationStatus
}
function Query($Name, $Sql) {
    $request = [ordered]@{
        QueryString = $Sql
        QueryExecutionContext = @{ Database = "lakehouse_db"; Catalog = "AwsDataCatalog" }
        ResultConfiguration = @{ OutputLocation = "s3://$bucket/athena-results/pre-entrega-5/" }
        WorkGroup = "primary"
    }
    $requestPath = Join-Path $repo "applications/flink-transactions/target/athena-$Name.json"
    [IO.File]::WriteAllText($requestPath, ($request | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
    $execution = Invoke-AwsJson -Arguments @("athena", "start-query-execution", "--cli-input-json", "file://$requestPath")
    $id = $execution.QueryExecutionId
    Write-Host "Athena $Name query=$id"
    $deadline = [DateTime]::UtcNow.AddMinutes(3)
    do {
        $state = Invoke-AwsJson -Arguments @("athena", "get-query-execution", "--query-execution-id", $id)
        if ($state.QueryExecution.Status.State -in @("FAILED", "CANCELLED")) {
            Save-Json "iceberg-athena-$Name-execution.json" $state
            throw "Athena $Name failed: $($state.QueryExecution.Status.StateChangeReason)"
        }
        if ($state.QueryExecution.Status.State -eq "SUCCEEDED") { break }
        if ([DateTime]::UtcNow -gt $deadline) {
            Invoke-AwsJson -Arguments @("athena", "stop-query-execution", "--query-execution-id", $id) | Out-Null
            throw "Athena $Name timed out"
        }
        Start-Sleep -Seconds 5
    } while ($true)
    Save-Json "iceberg-athena-$Name-execution.json" $state
    $result = Invoke-AwsJson -Arguments @("athena", "get-query-results", "--query-execution-id", $id)
    Save-Json "iceberg-athena-$Name-results.json" $result
    return $result
}

try {
    if ((App-State) -ne "READY") { throw "Application must be READY before this isolated test" }
    $configPath = Join-Path $repo "applications/flink-transactions/target/iceberg-run.json"
    [IO.File]::WriteAllText($configPath, '{"ApplicationRestoreConfiguration":{"ApplicationRestoreType":"SKIP_RESTORE_FROM_SNAPSHOT"}}', [Text.UTF8Encoding]::new($false))
    $started = $true
    Invoke-AwsJson -Arguments @("kinesisanalyticsv2", "start-application", "--application-name", $appName, "--run-configuration", "file://$configPath") | Out-Null
    $deadline = [DateTime]::UtcNow.AddMinutes(8)
    do {
        $status = App-State
        Write-Host "Flink service: $status"
        if ($status -eq "RUNNING") { break }
        if ([DateTime]::UtcNow -gt $deadline) { throw "Flink startup timed out" }
        Start-Sleep -Seconds 10
    } while ($true)
    Save-Json "iceberg-aws-flink-running.json" (Invoke-AwsJson -Arguments @("kinesisanalyticsv2", "describe-application", "--application-name", $appName))
    $deadline = [DateTime]::UtcNow.AddMinutes(3)
    do {
        $table = Invoke-AwsJson -Arguments @("glue", "get-table", "--database-name", "lakehouse_db", "--name", "transaction_aggregates") -AllowAbsent
        if ($null -ne $table) { break }
        if ([DateTime]::UtcNow -gt $deadline) { throw "Iceberg table was not created by Flink" }
        Write-Host "Waiting for Glue Iceberg table"
        Start-Sleep -Seconds 10
    } while ($true)
    Save-Json "iceberg-glue-before-events.json" $table
    $report.InitialMetadataLocation = $table.Table.Parameters.metadata_location
    $producerOutput = & (Join-Path $PSScriptRoot "iceberg-test-events.ps1") -Send -RunId $runId -Profile $Profile -Region $Region
    if ($LASTEXITCODE -ne 0) { throw "Producer failed" }
    [IO.File]::WriteAllText((Join-Path $evidence "iceberg-kinesis-test-events.txt"), ($producerOutput -join [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
    $report.PaymentMethod = "card_$runId"
    $deadline = [DateTime]::UtcNow.AddMinutes(5)
    do {
        $table = Invoke-AwsJson -Arguments @("glue", "get-table", "--database-name", "lakehouse_db", "--name", "transaction_aggregates")
        $location = $table.Table.Parameters.metadata_location
        if ($location -ne $report.InitialMetadataLocation) {
            $key = $location.Substring("s3://$bucket/".Length)
            $metadataPath = Join-Path $evidence "iceberg-metadata.json"
            Invoke-AwsJson -Arguments @("s3api", "get-object", "--bucket", $bucket, "--key", $key, $metadataPath) | Out-Null
            $metadata = Get-Content -Raw $metadataPath | ConvertFrom-Json
            $snapshot = @($metadata.snapshots | Where-Object { $_.'snapshot-id' -eq $metadata.'current-snapshot-id' })
            if ($snapshot.Count -eq 1 -and [long]$snapshot[0].summary.'total-records' -gt 0) { break }
        }
        if ([DateTime]::UtcNow -gt $deadline) { throw "No committed data snapshot after controlled events" }
        Write-Host "Waiting for successful checkpoint and Iceberg data commit"
        Start-Sleep -Seconds 10
    } while ($true)
    Save-Json "iceberg-glue-table.json" $table
    $report.FinalMetadataLocation = $location
    $report.SnapshotId = $metadata.'current-snapshot-id'
    $report.CheckpointId = $snapshot[0].summary.'flink.max-committed-checkpoint-id'
    if ([long]$report.CheckpointId -le 0) { throw "Missing committed Flink checkpoint ID" }
    $sql = "SELECT window_start, window_end, payment_method, transaction_count, total_amount, average_amount FROM lakehouse_db.transaction_aggregates WHERE payment_method = 'card_$runId'"
    $result = Query "validation" $sql
    $rows = @($result.ResultSet.Rows | Select-Object -Skip 1)
    if ($rows.Count -ne 1) { throw "Expected exactly one aggregate, found $($rows.Count)" }
    $values = @($rows[0].Data | ForEach-Object { $_.VarCharValue })
    if ($values[3] -ne "2" -or [decimal]$values[4] -ne [decimal]30.30 -or [decimal]$values[5] -ne [decimal]15.15) { throw "Unexpected Athena result: $($values -join ',')" }
    $report.ValidatedRow = $values
    Query "snapshots" 'SELECT committed_at, snapshot_id, operation, summary FROM "lakehouse_db"."transaction_aggregates$snapshots" ORDER BY committed_at DESC' | Out-Null
    Query "files" 'SELECT file_path, file_format, record_count, file_size_in_bytes FROM "lakehouse_db"."transaction_aggregates$files"' | Out-Null
    Save-Json "iceberg-s3-objects.json" (Invoke-AwsJson -Arguments @("s3api", "list-objects-v2", "--bucket", $bucket, "--prefix", $prefix))
    $errors = Invoke-AwsJson -Arguments @("logs", "filter-log-events", "--log-group-name", "/aws/kinesis-analytics/$appName", "--start-time", "$($startedAt.ToUnixTimeMilliseconds())", "--filter-pattern", "ERROR")
    Save-Json "iceberg-errors.json" $errors
    $report.ErrorLogEvents = @($errors.events).Count
    $concurrency = @($errors.events | Where-Object { $_.message -match "CommitFailedException|CommitStateUnknownException|ConcurrentModificationException" })
    if ($concurrency.Count -gt 0) { throw "Concurrency errors found in test interval" }
    $report.Status = "PASSED"
    Write-Host "PASS Athena count=2 total=30.30 average=15.150000 checkpoint=$($report.CheckpointId)"
} catch {
    $report.Status = "FAILED"
    $report.Error = "$_"
    Write-Host "FAILED: $_"
    try { Save-Json "iceberg-runtime-diagnostic.json" (Invoke-AwsJson -Arguments @("logs", "filter-log-events", "--log-group-name", "/aws/kinesis-analytics/$appName", "--start-time", "$($startedAt.ToUnixTimeMilliseconds())", "--filter-pattern", "ERROR")) } catch { Write-Host "Cannot collect diagnostic logs: $_" }
} finally {
    if ($started) {
        try {
            $status = App-State
            if ($status -notin @("READY", "STOPPING")) {
                Write-Host "Stopping Flink after test"
                Invoke-AwsJson -Arguments @("kinesisanalyticsv2", "stop-application", "--application-name", $appName) | Out-Null
            }
            $deadline = [DateTime]::UtcNow.AddMinutes(6)
            do {
                $status = App-State
                Write-Host "Final Flink state: $status"
                if ($status -eq "READY") { break }
                if ([DateTime]::UtcNow -gt $deadline) { throw "Flink did not reach READY after stop" }
                Start-Sleep -Seconds 10
            } while ($true)
            $report.FinalApplicationState = $status
            Save-Json "iceberg-aws-flink-after.json" (Invoke-AwsJson -Arguments @("kinesisanalyticsv2", "describe-application", "--application-name", $appName))
        } catch { $report.Status = "FAILED"; $report.StopError = "$_"; Write-Host "STOP ERROR: $_" }
    }
    $report.FinishedAtUtc = [DateTimeOffset]::UtcNow.ToString("o")
    Save-Json "iceberg-aws-test-summary.json" $report
}
if ($report.Status -ne "PASSED") { exit 1 }
