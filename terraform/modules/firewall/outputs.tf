output "firewall_ssh_name" {
  description = "Name of the SSH firewall rule"
  value       = google_compute_firewall.allow_ssh.name
}

output "firewall_internal_name" {
  description = "Name of the internal communication firewall rule"
  value       = google_compute_firewall.allow_internal.name
}

output "firewall_spark_master_ui_name" {
  description = "Name of the Spark Master UI firewall rule"
  value       = google_compute_firewall.allow_spark_master_ui.name
}

output "firewall_spark_master_name" {
  description = "Name of the Spark Master firewall rule"
  value       = google_compute_firewall.allow_spark_master.name
}

output "firewall_spark_worker_ui_name" {
  description = "Name of the Spark Worker UI firewall rule"
  value       = google_compute_firewall.allow_spark_worker_ui.name
}
