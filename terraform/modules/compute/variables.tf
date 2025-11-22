variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "zone" {
  description = "GCP Zone"
  type        = string
}

variable "network_self_link" {
  description = "Self link of the VPC network"
  type        = string
}

variable "subnet_self_link" {
  description = "Self link of the subnet"
  type        = string
}

variable "cluster_name" {
  description = "Name prefix for the cluster"
  type        = string
  default     = "spark"
}

variable "machine_type_master" {
  description = "Machine type for master node"
  type        = string
  default     = "n1-standard-4" # 4 vCPU, 15 GB RAM
}

variable "machine_type_worker" {
  description = "Machine type for worker nodes"
  type        = string
  default     = "n1-standard-4" # 4 vCPU, 15 GB RAM
}

variable "machine_type_edge" {
  description = "Machine type for edge node"
  type        = string
  default     = "n1-standard-2" # 2 vCPU, 7.5 GB RAM
}

variable "num_workers" {
  description = "Number of worker nodes"
  type        = number
  default     = 3
}

variable "disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 50
}

variable "disk_type" {
  description = "Boot disk type"
  type        = string
  default     = "pd-standard" # Can be pd-standard or pd-ssd
}

variable "image_family" {
  description = "OS image family"
  type        = string
  default     = "ubuntu-2204-lts"
}

variable "image_project" {
  description = "Project containing the OS image"
  type        = string
  default     = "ubuntu-os-cloud"
}

variable "ssh_user" {
  description = "SSH username"
  type        = string
  default     = "ansible"
}

variable "ssh_public_key" {
  description = "SSH public key for accessing instances"
  type        = string
  default     = ""
}

variable "tags_master" {
  description = "Network tags for master node"
  type        = list(string)
  default     = ["spark-master"]
}

variable "tags_worker" {
  description = "Network tags for worker nodes"
  type        = list(string)
  default     = ["spark-worker"]
}

variable "tags_edge" {
  description = "Network tags for edge node"
  type        = list(string)
  default     = ["spark-edge"]
}
