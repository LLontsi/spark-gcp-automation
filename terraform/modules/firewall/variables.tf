variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "network_name" {
  description = "Name of the VPC network"
  type        = string
}

variable "allowed_ssh_ips" {
  description = "List of IP ranges allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Change to your IP for security
}

variable "allowed_ui_ips" {
  description = "List of IP ranges allowed for Web UI access"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Change to your IP for security
}

variable "tags_master" {
  description = "Network tags for master node"
  type        = list(string)
  default     = ["spark-master"]
}

variable "tags_workers" {
  description = "Network tags for worker nodes"
  type        = list(string)
  default     = ["spark-worker"]
}

variable "tags_edge" {
  description = "Network tags for edge node"
  type        = list(string)
  default     = ["spark-edge"]
}
