terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Replace with your bucket and lock table
    # bucket         = "lkg-terraform-state"
    # key            = "production/terraform.tfstate"
    # region         = "us-east-1"
    # dynamodb_table = "lkg-terraform-locks"
    # encrypt        = true
  }
}

provider "aws" {
  region = var.primary_region
  alias  = "primary"

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Region      = var.primary_region
    }
  }
}

provider "aws" {
  region = var.secondary_region
  alias  = "secondary"

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Region      = var.secondary_region
    }
  }
}
