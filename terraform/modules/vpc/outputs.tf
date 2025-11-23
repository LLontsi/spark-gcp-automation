output "vpc_id" {
  description = "The ID of the VPC"
  value       = google_compute_network.spark_vpc.id
}

output "vpc_name" {
  description = "The name of the VPC"
  value       = google_compute_network.spark_vpc.name
}

output "vpc_self_link" {
  description = "The self link of the VPC"
  value       = google_compute_network.spark_vpc.self_link
}

output "subnet_id" {
  description = "The ID of the subnet"
  value       = google_compute_subnetwork.spark_subnet.id
}

output "subnet_name" {
  description = "The name of the subnet"
  value       = google_compute_subnetwork.spark_subnet.name
}

output "subnet_self_link" {
  description = "The self link of the subnet"
  value       = google_compute_subnetwork.spark_subnet.self_link
}

output "subnet_cidr" {
  description = "The CIDR range of the subnet"
  value       = google_compute_subnetwork.spark_subnet.ip_cidr_range
}

output "router_name" {
  description = "The name of the Cloud Router"
  value       = google_compute_router.spark_router.name
}
