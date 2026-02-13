module "networking_primary" {
  source = "./modules/networking"
  providers = {
    aws = aws.primary
  }

  project_name = var.project_name
  environment  = var.environment
  region       = var.primary_region
  vpc_cidr     = var.vpc_cidr_primary
}

module "networking_secondary" {
  source = "./modules/networking"
  providers = {
    aws = aws.secondary
  }

  project_name = var.project_name
  environment  = var.environment
  region       = var.secondary_region
  vpc_cidr     = var.vpc_cidr_secondary
}

resource "aws_rds_global_cluster" "this" {
  provider                  = aws.primary
  global_cluster_identifier = "${var.project_name}-${var.environment}-global"
  engine                    = "aurora-postgresql"
  engine_version            = "15.4"
  database_name             = "gateway_production"
}

module "database_primary" {
  source = "./modules/database"
  providers = {
    aws = aws.primary
  }

  project_name       = var.project_name
  environment        = var.environment
  region             = var.primary_region
  vpc_id             = module.networking_primary.vpc_id
  private_subnet_ids = module.networking_primary.private_subnets
  global_cluster_id  = aws_rds_global_cluster.this.id
  is_primary         = true
}

module "database_secondary" {
  source = "./modules/database"
  providers = {
    aws = aws.secondary
  }

  project_name       = var.project_name
  environment        = var.environment
  region             = var.secondary_region
  vpc_id             = module.networking_secondary.vpc_id
  private_subnet_ids = module.networking_secondary.private_subnets
  global_cluster_id  = aws_rds_global_cluster.this.id
  is_primary         = false

  depends_on = [module.database_primary]
}

resource "aws_elasticache_global_replication_group" "this" {
  provider = aws.primary
  global_replication_group_id_suffix = "${var.project_name}-${var.environment}-global"
  primary_replication_group_id      = module.cache_primary.replication_group_id
}

module "cache_primary" {
  source = "./modules/cache"
  providers = {
    aws = aws.primary
  }

  project_name       = var.project_name
  environment        = var.environment
  region             = var.primary_region
  vpc_id             = module.networking_primary.vpc_id
  private_subnet_ids = module.networking_primary.private_subnets
  is_primary         = true
  # In Terraform, we often need to bootstrap the primary first then join it to global
  # To avoid circular dependency, we might need a two-step process or manual ID reference
  global_replication_group_id = "" 
}

module "cache_secondary" {
  source = "./modules/cache"
  providers = {
    aws = aws.secondary
  }

  project_name       = var.project_name
  environment        = var.environment
  region             = var.secondary_region
  vpc_id             = module.networking_secondary.vpc_id
  private_subnet_ids = module.networking_secondary.private_subnets
  global_replication_group_id = aws_elasticache_global_replication_group.this.global_replication_group_id
  is_primary         = false

  depends_on = [aws_elasticache_global_replication_group.this]
}

module "compute_primary" {
  source = "./modules/compute"
  providers = {
    aws = aws.primary
  }

  project_name      = var.project_name
  environment       = var.environment
  region            = var.primary_region
  vpc_id            = module.networking_primary.vpc_id
  public_subnet_ids = module.networking_primary.public_subnets
  private_subnet_ids = module.networking_primary.private_subnets
  container_image   = var.container_image
  db_endpoint       = module.database_primary.cluster_endpoint
  redis_endpoint    = module.cache_primary.primary_endpoint_address
}

module "compute_secondary" {
  source = "./modules/compute"
  providers = {
    aws = aws.secondary
  }

  project_name      = var.project_name
  environment       = var.environment
  region            = var.secondary_region
  vpc_id            = module.networking_secondary.vpc_id
  public_subnet_ids = module.networking_secondary.public_subnets
  private_subnet_ids = module.networking_secondary.private_subnets
  container_image   = var.container_image
  db_endpoint       = module.database_secondary.cluster_reader_endpoint # Read replica in secondary
  redis_endpoint    = module.cache_secondary.reader_endpoint_address   # Read replica in secondary
}

module "security_primary" {
  source = "./modules/security"
  providers = {
    aws = aws.primary
  }

  project_name = var.project_name
  environment  = var.environment
  region       = var.primary_region
}

module "security_secondary" {
  source = "./modules/security"
  providers = {
    aws = aws.secondary
  }

  project_name = var.project_name
  environment  = var.environment
  region       = var.secondary_region
}

module "monitoring_primary" {
  source = "./modules/monitoring"
  providers = {
    aws = aws.primary
  }

  project_name = var.project_name
  environment  = var.environment
  region       = var.primary_region
}

module "monitoring_secondary" {
  source = "./modules/monitoring"
  providers = {
    aws = aws.secondary
  }

  project_name = var.project_name
  environment  = var.environment
  region       = var.secondary_region
}

output "primary_alb_dns" {
  value = module.compute_primary.alb_dns_name
}

output "secondary_alb_dns" {
  value = module.compute_secondary.alb_dns_name
}
