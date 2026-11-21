output "application_name" {
  description = "Nombre de la aplicación Managed Flink"
  value       = aws_kinesisanalyticsv2_application.flink.name
}

output "application_arn" {
  description = "ARN de la aplicación Managed Flink"
  value       = aws_kinesisanalyticsv2_application.flink.arn
}

output "log_group_name" {
  description = "Grupo de logs de CloudWatch"
  value       = aws_cloudwatch_log_group.flink.name
}

output "execution_role_arn" {
  description = "ARN del rol IAM de Flink"
  value       = aws_iam_role.flink.arn
}