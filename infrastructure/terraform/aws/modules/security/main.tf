variable "project_name" { type = string }
variable "environment" { type = string }
variable "region" { type = string }

resource "aws_kms_key" "this" {
  description             = "KMS key for ${var.project_name} ${var.environment} in ${var.region}"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.project_name}-${var.environment}-${var.region}"
  target_key_id = aws_kms_key.this.key_id
}

resource "aws_secretsmanager_secret" "app_secrets" {
  name       = "${var.project_name}-${var.environment}-secrets-${var.region}"
  kms_key_id = aws_kms_key.this.arn
}

output "kms_key_arn" {
  value = aws_kms_key.this.arn
}

output "secrets_arn" {
  value = aws_secretsmanager_secret.app_secrets.arn
}
