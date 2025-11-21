variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "my-spark-project"
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