# Terraform Plan — Pre-entrega 1

**Entorno:** dev  
**Región:** us-east-1  
**Proveedor:** hashicorp/aws v6.69.1

## Resultado del despliegue

La infraestructura fue desplegada correctamente mediante Terraform.

El plan inicial contempló:

```text
Plan: 16 to add, 0 to change, 0 to destroy.
```

Tras completar el despliegue y verificar los recursos, el plan final confirmó:

```text
No changes. Your infrastructure matches the configuration.
```

## Evidencia de validación

Se verificaron las asociaciones de las tablas de rutas privadas con el S3 Gateway Endpoint, los permisos IAM de procesamiento y auditoría, y la sincronización del estado remoto.

## Salida completa de terraform plan

A continuación se adjunta la salida real obtenida mediante `terraform plan -no-color` :


Warning: Deprecated Parameter

The parameter "dynamodb_table" is deprecated. Use parameter "use_lockfile" instead.
Acquiring state lock. This may take a few moments...
module.network.data.aws_availability_zones.available: Reading...
module.identity.data.aws_caller_identity.current: Reading...
module.identity.data.aws_iam_policy_document.processing_trust: Reading...
module.network.data.aws_region.current: Reading...
module.network.aws_vpc.main: Refreshing state... [id=vpc-0b85171c643372dba]
aws_s3_bucket.data_lake: Refreshing state... [id=coderhouse-data-lake-672049777597]
module.network.data.aws_region.current: Read complete after 0s [id=us-east-1]
module.identity.data.aws_iam_policy_document.processing_trust: Read complete after 0s [id=1237821689]
module.identity.aws_iam_role.processing: Refreshing state... [id=coderhouse-dev-processing]
module.identity.data.aws_caller_identity.current: Read complete after 0s [id=672049777597]
module.identity.data.aws_iam_policy_document.audit_trust: Reading...
module.identity.data.aws_iam_policy_document.audit_trust: Read complete after 0s [id=81669632]
module.identity.aws_iam_role.audit: Refreshing state... [id=coderhouse-dev-audit]
module.network.data.aws_availability_zones.available: Read complete after 0s [id=us-east-1]
module.network.aws_route_table.private[1]: Refreshing state... [id=rtb-0c79918ca994c2b15]
module.network.aws_route_table.private[0]: Refreshing state... [id=rtb-0d69ac0f1349cb262]
module.network.aws_subnet.private[0]: Refreshing state... [id=subnet-0e484b46487a0220c]
module.network.aws_subnet.private[1]: Refreshing state... [id=subnet-001ae24851059e5ed]
module.network.aws_vpc_endpoint.s3: Refreshing state... [id=vpce-05376664b99da4447]
module.network.aws_route_table_association.private[0]: Refreshing state... [id=rtbassoc-023b6337c44b93796]
module.network.aws_route_table_association.private[1]: Refreshing state... [id=rtbassoc-01cd4f41ab8ae837f]
aws_s3_bucket_versioning.data_lake: Refreshing state... [id=coderhouse-data-lake-672049777597]
aws_s3_bucket_public_access_block.data_lake: Refreshing state... [id=coderhouse-data-lake-672049777597]
aws_s3_bucket_server_side_encryption_configuration.data_lake: Refreshing state... [id=coderhouse-data-lake-672049777597]
module.identity.data.aws_iam_policy_document.audit: Reading...
module.identity.data.aws_iam_policy_document.processing: Reading...
module.identity.data.aws_iam_policy_document.audit: Read complete after 0s [id=3870355238]
module.identity.data.aws_iam_policy_document.processing: Read complete after 0s [id=3847773883]
module.identity.aws_iam_role_policy.audit: Refreshing state... [id=coderhouse-dev-audit:coderhouse-audit-readonly]
module.identity.aws_iam_role_policy.processing: Refreshing state... [id=coderhouse-dev-processing:coderhouse-processing-s3]

No changes. Your infrastructure matches the configuration.

Terraform has compared your real infrastructure against your configuration
and found no differences, so no changes are needed.
