variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "lkg-gateway"
}

variable "environment" {
  description = "Environment (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "primary_region" {
  description = "Primary AWS region"
  type        = string
  default     = "us-east-1"
}

variable "secondary_region" {
  description = "Secondary AWS region for DR/Replication"
  type        = string
  default     = "eu-west-1"
}

variable "vpc_cidr_primary" {
  description = "CIDR block for the primary VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "vpc_cidr_secondary" {
  description = "CIDR block for the secondary VPC"
  type        = string
  default     = "10.1.0.0/16"
}

variable "container_image" {
  description = "Docker image for the gateway app"
  type        = string
  default     = "xxxxxxxxx.dkr.ecr.us-east-1.amazonaws.com/lkg-gateway:latest"
}
