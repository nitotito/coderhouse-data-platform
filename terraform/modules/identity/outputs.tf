
output "processing_role_arn" {
  description = "ARN del rol de procesamiento"
  value       = aws_iam_role.processing.arn
}

output "audit_role_arn" {
  description = "ARN del rol de auditoria"
  value       = aws_iam_role.audit.arn
}
