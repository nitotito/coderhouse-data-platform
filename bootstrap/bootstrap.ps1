
$ErrorActionPreference = "Stop"

$Profile = "coderhouse-dev"
$Region = "us-east-1"
$AccountId = "672049777597"

$Bucket = "coderhouse-terraform-$AccountId"
$Table = "coderhouse-terraform-locks"

function Invoke-Aws {
    & aws @args --profile $Profile --region $Region

    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI fallo con codigo $LASTEXITCODE"
    }
}

Write-Host "Verificando backend Terraform..."

# Verificar bucket
aws s3api head-bucket `
    --bucket $Bucket `
    --profile $Profile 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Creando bucket S3..."

    Invoke-Aws s3api create-bucket `
        --bucket $Bucket
}
else {
    Write-Host "El bucket ya existe."
}

# Bloquear acceso publico
Invoke-Aws s3api put-public-access-block `
    --bucket $Bucket `
    --public-access-block-configuration `
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Habilitar versionado
Invoke-Aws s3api put-bucket-versioning `
    --bucket $Bucket `
    --versioning-configuration Status=Enabled

# Configurar cifrado SSE-S3
$Encryption = @{
    Rules = @(
        @{
            ApplyServerSideEncryptionByDefault = @{
                SSEAlgorithm = "AES256"
            }
        }
    )
} | ConvertTo-Json -Depth 5 -Compress

$TempFile = Join-Path $env:TEMP "coderhouse-s3-encryption.json"

$Encryption | Set-Content `
    -Path $TempFile `
    -Encoding ascii

Invoke-Aws s3api put-bucket-encryption `
    --bucket $Bucket `
    --server-side-encryption-configuration "file://$TempFile"

Remove-Item $TempFile -ErrorAction SilentlyContinue

# Verificar tabla DynamoDB
$TableExists = aws dynamodb describe-table `
    --table-name $Table `
    --region $Region `
    --profile $Profile `
    --query "Table.TableStatus" `
    --output text 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Creando tabla DynamoDB..."

    Invoke-Aws dynamodb create-table `
        --table-name $Table `
        --attribute-definitions AttributeName=LockID,AttributeType=S `
        --key-schema AttributeName=LockID,KeyType=HASH `
        --billing-mode PAY_PER_REQUEST
}
else {
    Write-Host "La tabla DynamoDB existe: $TableExists"
}

Write-Host "Bootstrap finalizado correctamente."
