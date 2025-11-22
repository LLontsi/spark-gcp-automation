# Master Node Outputs
output "master_name" {
  description = "Name of the master instance"
  value       = google_compute_instance.spark_master.name
}

output "master_internal_ip" {
  description = "Internal IP of the master instance"
  value       = google_compute_instance.spark_master.network_interface[0].network_ip
}

output "master_external_ip" {
  description = "External IP of the master instance"
  value       = google_compute_instance.spark_master.network_interface[0].access_config[0].nat_ip
}

output "master_self_link" {
  description = "Self link of the master instance"
  value       = google_compute_instance.spark_master.self_link
}

# Worker Nodes Outputs
output "worker_names" {
  description = "Names of all worker instances"
  value       = google_compute_instance.spark_workers[*].name
}

output "worker_internal_ips" {
  description = "Internal IPs of all worker instances"
  value       = google_compute_instance.spark_workers[*].network_interface[0].network_ip
}

output "worker_external_ips" {
  description = "External IPs of all worker instances"
  value       = google_compute_instance.spark_workers[*].network_interface[0].access_config[0].nat_ip
}

output "worker_self_links" {
  description = "Self links of all worker instances"
  value       = google_compute_instance.spark_workers[*].self_link
}

# Edge Node Outputs
output "edge_name" {
  description = "Name of the edge instance"
  value       = google_compute_instance.spark_edge.name
}

output "edge_internal_ip" {
  description = "Internal IP of the edge instance"
  value       = google_compute_instance.spark_edge.network_interface[0].network_ip
}

output "edge_external_ip" {
  description = "External IP of the edge instance"
  value       = google_compute_instance.spark_edge.network_interface[0].access_config[0].nat_ip
}

output "edge_self_link" {
  description = "Self link of the edge instance"
  value       = google_compute_instance.spark_edge.self_link
}

# All IPs Summary
output "all_internal_ips" {
  description = "Map of all internal IPs by role"
  value = {
    master  = google_compute_instance.spark_master.network_interface[0].network_ip
    workers = google_compute_instance.spark_workers[*].network_interface[0].network_ip
    edge    = google_compute_instance.spark_edge.network_interface[0].network_ip
  }
}

output "all_external_ips" {
  description = "Map of all external IPs by role"
  value = {
    master  = google_compute_instance.spark_master.network_interface[0].access_config[0].nat_ip
    workers = google_compute_instance.spark_workers[*].network_interface[0].access_config[0].nat_ip
    edge    = google_compute_instance.spark_edge.network_interface[0].access_config[0].nat_ip
  }
}
