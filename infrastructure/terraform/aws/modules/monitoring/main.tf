variable "project_name" { type = string }
variable "environment" { type = string }
variable "region" { type = string }

resource "aws_prometheus_workspace" "this" {
  alias = "${var.project_name}-${var.environment}-${var.region}"
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${var.environment}-${var.region}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${var.project_name}-${var.environment}-service-${var.region}", "ClusterName", "${var.project_name}-${var.environment}-cluster-${var.region}"]
          ]
          period = 300
          stat   = "Average"
          region = var.region
          title  = "ECS CPU Utilization"
        }
      }
    ]
  })
}

output "prometheus_endpoint" {
  value = aws_prometheus_workspace.this.prometheus_endpoint
}
