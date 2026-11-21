
output "stream_arn" {
  description = "ARN del stream Kinesis"
  value       = aws_kinesis_stream.transactions.arn
}

output "stream_name" {
  description = "Nombre del stream Kinesis"
  value       = aws_kinesis_stream.transactions.name
}

output "firehose_name" {
  description = "Nombre del delivery stream, si está habilitado"
  value       = try(aws_kinesis_firehose_delivery_stream.bronze[0].name, null)
}

output "firehose_role_arn" {
  description = "ARN del rol IAM de Firehose, si está habilitado"
  value       = try(aws_iam_role.firehose[0].arn, null)
}
