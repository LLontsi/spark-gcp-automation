# Project Configuration
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "europe-west1-b"
}

# Cluster Configuration
variable "cluster_name" {
  description = "Name of the Spark cluster"
  type        = string
  default     = "spark"
}

variable "num_workers" {
  description = "Number of worker nodes"
  type        = number
  default     = 3
}

# Network Configuration
variable "subnet_cidr" {
  description = "CIDR block for the subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "allowed_ssh_ips" {
  description = "List of IP ranges allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"] # CHANGE THIS for security!
}

variable "allowed_ui_ips" {
  description = "List of IP ranges allowed for Web UI access"
  type        = list(string)
  default     = ["0.0.0.0/0"] # CHANGE THIS for security!
}

# Instance Configuration
variable "machine_type_master" {
  description = "Machine type for master node"
  type        = string
  default     = "n1-standard-4"
}

variable "machine_type_worker" {
  description = "Machine type for worker nodes"
  type        = string
  default     = "n1-standard-4"
}

variable "machine_type_edge" {
  description = "Machine type for edge node"
  type        = string
  default     = "n1-standard-2"
}

variable "disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 50
}

# SSH Configuration
variable "ssh_user" {
  description = "SSH username for instances"
  type        = string
  default     = "ansible"
}

variable "ssh_public_key" {
  description = "SSH public key for accessing instances"
  type        = string
  default     = ""
}
