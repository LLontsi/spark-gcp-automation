terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# VPC Network
resource "google_compute_network" "spark_vpc" {
  name                    = var.vpc_name
  project                 = var.project_id
  auto_create_subnetworks = false
  description             = var.description
  routing_mode            = "REGIONAL"
}

# Subnet for Spark cluster
resource "google_compute_subnetwork" "spark_subnet" {
  name          = var.subnet_name
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.spark_vpc.id
  ip_cidr_range = var.subnet_cidr
  description   = "Subnet for Spark cluster nodes"

  # Enable Private Google Access for GCS
  private_ip_google_access = true

  # Secondary range for pods (if using GKE later)
  # secondary_ip_range {
  #   range_name    = "pods"
  #   ip_cidr_range = "10.1.0.0/16"
  # }
}

# Cloud Router for NAT (optional, for outbound internet)
resource "google_compute_router" "spark_router" {
  name    = "${var.vpc_name}-router"
  project = var.project_id
  region  = var.region
  network = google_compute_network.spark_vpc.id

  bgp {
    asn = 64514
  }
}

# Cloud NAT for outbound internet access
resource "google_compute_router_nat" "spark_nat" {
  name    = "${var.vpc_name}-nat"
  project = var.project_id
  router  = google_compute_router.spark_router.name
  region  = var.region

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
