variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west1"
}

variable "vpc_name" {
  description = "Name of the VPC network"
  type        = string
  default     = "spark-vpc"
}

variable "subnet_name" {
  description = "Name of the subnet"
  type        = string
  default     = "spark-subnet"
}

variable "subnet_cidr" {
  description = "CIDR block for the subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "description" {
  description = "Description for the VPC"
  type        = string
  default     = "VPC for Spark cluster deployment"
}
