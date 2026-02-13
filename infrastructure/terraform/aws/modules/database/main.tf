variable "project_name" { type = string }
variable "environment" { type = string }
variable "region" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "global_cluster_id" { type = string }
variable "is_primary" { type = bool }

resource "aws_db_subnet_group" "this" {
  name       = "${var.project_name}-${var.environment}-db-subnet-${var.region}"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${var.project_name}-${var.environment}-db-subnet-${var.region}"
  }
}

resource "aws_security_group" "db" {
  name        = "${var.project_name}-${var.environment}-db-sg-${var.region}"
  description = "Allow DB traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"] # Internal traffic only
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-db-sg-${var.region}"
  }
}

resource "aws_rds_cluster" "this" {
  cluster_identifier      = "${var.project_name}-${var.environment}-cluster-${var.region}"
  engine                  = "aurora-postgresql"
  engine_version          = "15.4"
  global_cluster_identifier = var.global_cluster_id
  
  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  
  # For secondary clusters, many settings are inherited from the global cluster
  master_username        = var.is_primary ? "lkg_admin" : null
  master_password        = var.is_primary ? "change-me-in-production" : null
  
  # Ensure secondary cluster is created after the primary/global setup
  # In a real setup, we'd use complex orchestration, but here we simplify
  
  storage_encrypted = true
  skip_final_snapshot = true

  tags = {
    Name = "${var.project_name}-${var.environment}-cluster-${var.region}"
  }
}

resource "aws_rds_cluster_instance" "this" {
  count              = 2
  identifier         = "${var.project_name}-${var.environment}-db-${count.index}-${var.region}"
  cluster_identifier = aws_rds_cluster.this.id
  instance_class     = "db.t3.medium"
  engine             = aws_rds_cluster.this.engine
  engine_version     = aws_rds_cluster.this.engine_version
  db_subnet_group_name = aws_db_subnet_group.this.name

  tags = {
    Name = "${var.project_name}-${var.environment}-db-${count.index}-${var.region}"
  }
}

output "cluster_endpoint" {
  value = aws_rds_cluster.this.endpoint
}

output "cluster_reader_endpoint" {
  value = aws_rds_cluster.this.reader_endpoint
}
