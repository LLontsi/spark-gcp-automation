# Project Configuration Outputs
output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}

output "zone" {
  description = "GCP Zone"
  value       = var.zone
}

# VPC Outputs
output "vpc_name" {
  description = "VPC network name"
  value       = module.vpc.vpc_name
}

output "subnet_name" {
  description = "Subnet name"
  value       = module.vpc.subnet_name
}

output "subnet_cidr" {
  description = "Subnet CIDR range"
  value       = module.vpc.subnet_cidr
}

# Compute Outputs
output "master_external_ip" {
  description = "External IP of master node"
  value       = module.compute.master_external_ip
}

output "master_internal_ip" {
  description = "Internal IP of master node"
  value       = module.compute.master_internal_ip
}

output "worker_external_ips" {
  description = "External IPs of worker nodes"
  value       = module.compute.worker_external_ips
}

output "worker_internal_ips" {
  description = "Internal IPs of worker nodes"
  value       = module.compute.worker_internal_ips
}

output "edge_external_ip" {
  description = "External IP of edge node"
  value       = module.compute.edge_external_ip
}

output "edge_internal_ip" {
  description = "Internal IP of edge node"
  value       = module.compute.edge_internal_ip
}

# All IPs Summary
output "all_external_ips" {
  description = "All external IPs by role"
  value       = module.compute.all_external_ips
}

output "all_internal_ips" {
  description = "All internal IPs by role"
  value       = module.compute.all_internal_ips
}

# SSH Connection Commands
output "ssh_commands" {
  description = "SSH commands to connect to instances"
  value = {
    master = "ssh ${var.ssh_user}@${module.compute.master_external_ip}"
    edge   = "ssh ${var.ssh_user}@${module.compute.edge_external_ip}"
    workers = [
      for ip in module.compute.worker_external_ips :
      "ssh ${var.ssh_user}@${ip}"
    ]
  }
}

# Ansible Inventory Hint
output "ansible_inventory_hint" {
  description = "Hint for generating Ansible inventory"
  value       = <<-EOT
    Update ansible/inventory/hosts.yml with these IPs:
    
    Master:  ${module.compute.master_internal_ip}
    Workers: ${join(", ", module.compute.worker_internal_ips)}
    Edge:    ${module.compute.edge_internal_ip}
  EOT
}

# Cluster Summary
output "cluster_summary" {
  description = "Summary of the deployed cluster"
  value       = <<-EOT
    
    ╔════════════════════════════════════════════════════════╗
    ║          Spark Cluster Deployment Summary             ║
    ╚════════════════════════════════════════════════════════╝
    
    Cluster Name: ${var.cluster_name}
    Region:       ${var.region}
    Zone:         ${var.zone}
    
    ┌─────────────────────────────────────────────────────┐
    │ Master Node                                          │
    ├─────────────────────────────────────────────────────┤
    │ Name:         spark-master                          │
    │ Internal IP:  ${module.compute.master_internal_ip}
    │ External IP:  ${module.compute.master_external_ip}
    │ Web UI:       http://${module.compute.master_external_ip}:8080
    └─────────────────────────────────────────────────────┘
    
    ┌─────────────────────────────────────────────────────┐
    │ Worker Nodes (${var.num_workers})                                      │
    ├─────────────────────────────────────────────────────┤
    ${join("\n    ", [for idx, ip in module.compute.worker_internal_ips : "│ Worker ${idx + 1}: ${ip} (ext: ${module.compute.worker_external_ips[idx]})"])}
    └─────────────────────────────────────────────────────┘
    
    ┌─────────────────────────────────────────────────────┐
    │ Edge Node                                            │
    ├─────────────────────────────────────────────────────┤
    │ Name:         spark-edge                            │
    │ Internal IP:  ${module.compute.edge_internal_ip}
    │ External IP:  ${module.compute.edge_external_ip}
    └─────────────────────────────────────────────────────┘
    
    Next Steps:
    1. Run Ansible playbooks to configure Spark
    2. Test connectivity: ssh ${var.ssh_user}@${module.compute.master_external_ip}
    3. Access Spark UI: http://${module.compute.master_external_ip}:8080
    
  EOT
}
