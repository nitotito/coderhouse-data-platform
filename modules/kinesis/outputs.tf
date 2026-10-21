
output "stream_arn" {
  description = "ARN del stream Kinesis"
  value       = aws_kinesis_stream.transactions.arn
}

output "stream_name" {
  description = "Nombre del stream Kinesis"
  value       = aws_kinesis_stream.transactions.name
}

output "firehose_name" {
  description = "Nombre del delivery stream"
  value       = aws_kinesis_firehose_delivery_stream.bronze.name
}

output "firehose_role_arn" {
  description = "ARN del rol IAM de Firehose"
  value       = aws_iam_role.firehose.arn
}
