variable "project_name" { type = string }
variable "environment" { type = string }
variable "region" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "global_replication_group_id" { type = string }
variable "is_primary" { type = bool }

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.project_name}-${var.environment}-cache-sn-${var.region}"
  subnet_ids = var.private_subnet_ids
}

resource "aws_security_group" "redis" {
  name        = "${var.project_name}-${var.environment}-redis-sg-${var.region}"
  description = "Allow Redis traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-sg-${var.region}"
  }
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id          = "${var.project_name}-${var.environment}-redis-${var.region}"
  description                   = "Redis replication group for ${var.region}"
  node_type                     = "cache.t3.medium"
  port                          = 6379
  subnet_group_name             = aws_elasticache_subnet_group.this.name
  security_group_ids            = [aws_security_group.redis.id]
  
  # Global replication group association
  global_replication_group_id   = var.global_replication_group_id
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  num_cache_clusters        = 2 # Primary + Replica per region

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-${var.region}"
  }
}

output "replication_group_id" {
  value = aws_elasticache_replication_group.this.id
}

output "primary_endpoint_address" {
  value = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "reader_endpoint_address" {
  value = aws_elasticache_replication_group.this.reader_endpoint_address
}
