
# Allow Monitoring UIs
resource "google_compute_firewall" "allow_monitoring_ui" {
  name    = "${var.network_name}-allow-monitoring-ui"
  project = var.project_id
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = ["3000", "9090", "9100"] # Grafana, Prometheus, Node Exporter
  }

  source_ranges = var.allowed_ui_ips
  target_tags   = concat(var.tags_master, var.tags_workers, var.tags_edge)

  description = "Allow access to Grafana, Prometheus, and Node Exporter"
}
