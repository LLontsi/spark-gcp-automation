# Google Cloud Provider Configuration
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  project_id  = var.project_id
  region      = var.region
  vpc_name    = "${var.cluster_name}-vpc"
  subnet_name = "${var.cluster_name}-subnet"
  subnet_cidr = var.subnet_cidr
  description = "VPC for ${var.cluster_name} Spark cluster"
}

# Firewall Module
module "firewall" {
  source = "./modules/firewall"

  project_id      = var.project_id
  network_name    = module.vpc.vpc_name
  allowed_ssh_ips = var.allowed_ssh_ips
  allowed_ui_ips  = var.allowed_ui_ips

  tags_master  = ["${var.cluster_name}-master"]
  tags_workers = ["${var.cluster_name}-worker"]
  tags_edge    = ["${var.cluster_name}-edge"]

  depends_on = [module.vpc]
}

# Compute Module
module "compute" {
  source = "./modules/compute"

  project_id          = var.project_id
  zone                = var.zone
  network_self_link   = module.vpc.vpc_self_link
  subnet_self_link    = module.vpc.subnet_self_link
  cluster_name        = var.cluster_name
  num_workers         = var.num_workers
  machine_type_master = var.machine_type_master
  machine_type_worker = var.machine_type_worker
  machine_type_edge   = var.machine_type_edge
  disk_size           = var.disk_size
  ssh_user            = var.ssh_user
  ssh_public_key      = var.ssh_public_key

  tags_master = ["${var.cluster_name}-master"]
  tags_worker = ["${var.cluster_name}-worker"]
  tags_edge   = ["${var.cluster_name}-edge"]

  depends_on = [module.vpc, module.firewall]
}