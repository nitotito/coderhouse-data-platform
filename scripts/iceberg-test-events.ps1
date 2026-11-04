param(
    [switch]$Send,
    [string]$Profile = "coderhouse-dev",
    [string]$Region = "us-east-1",
    [string]$StreamName = "dev-transactions-stream",
    [string]$RunId = ("pe5_" + [DateTime]::UtcNow.ToString("yyyyMMdd_HHmmss"))
)
$ErrorActionPreference = "Stop"
$window = [DateTime]::UtcNow
$window = $window.AddTicks(-($window.Ticks % [TimeSpan]::TicksPerMinute))
$method = "card_$RunId"
$rows = @(
    @{ transaction_id = "$RunId-1"; amount = 10.10; payment_method = $method; status = "APPROVED"; timestamp = $window.AddSeconds(1).ToString("o") },
    @{ transaction_id = "$RunId-2"; amount = 20.20; payment_method = $method; status = "approved"; timestamp = $window.AddSeconds(2).ToString("o") },
    @{ transaction_id = "$RunId-rejected"; amount = 999.00; payment_method = $method; status = "rejected"; timestamp = $window.AddSeconds(3).ToString("o") },
    # Timestamp assignment precedes the approved filter. This rejected marker
    # advances the watermark beyond window end + 10 seconds without adding money.
    @{ transaction_id = "$RunId-watermark"; amount = 0; payment_method = $method; status = "rejected"; timestamp = $window.AddSeconds(75).ToString("o") }
)
$rows | ConvertTo-Json -Depth 5
Write-Host "Expected: method=$method; count=2; total=30.30; average=15.150000; UTC window=$($window.ToString('o'))"
if (-not $Send) { Write-Host "Dry run. Use -Send only after AWS cost approval."; return }
foreach ($row in $rows) {
    $json = $row | ConvertTo-Json -Compress
    $data = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    # One key preserves ordering for this test across Kinesis shards.
    aws kinesis put-record --profile $Profile --region $Region --stream-name $StreamName --partition-key $RunId --data $data
    if ($LASTEXITCODE -ne 0) { throw "Kinesis put-record failed" }
}
