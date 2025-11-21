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

# Local variables
locals {
  cluster_name = var.cluster_name
  common_tags = {
    project     = "spark-cluster"
    environment = "development"
    managed_by  = "terraform"
  }
}

# Outputs to use variables
output "cluster_configuration" {
  description = "Cluster configuration"
  value = {
    name   = local.cluster_name
    region = var.region
    zone   = var.zone
  }
}