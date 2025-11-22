terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Allow SSH from specified IPs
resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.network_name}-allow-ssh"
  project = var.project_id
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.allowed_ssh_ips
  target_tags   = concat(var.tags_master, var.tags_workers, var.tags_edge)

  description = "Allow SSH access to all Spark nodes"
}

# Allow internal communication within VPC
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.network_name}-allow-internal"
  project = var.project_id
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_tags = concat(var.tags_master, var.tags_workers, var.tags_edge)
  target_tags = concat(var.tags_master, var.tags_workers, var.tags_edge)

  description = "Allow all internal communication between Spark nodes"
}

# Allow Spark Master UI from specified IPs
resource "google_compute_firewall" "allow_spark_master_ui" {
  name    = "${var.network_name}-allow-spark-master-ui"
  project = var.project_id
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = ["8080"] # Spark Master Web UI
  }

  source_ranges = var.allowed_ui_ips
  target_tags   = var.tags_master

  description = "Allow access to Spark Master Web UI"
}

# Allow Spark Master port (for workers and edge)
resource "google_compute_firewall" "allow_spark_master" {
  name    = "${var.network_name}-allow-spark-master"
  project = var.project_id
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = ["7077"] # Spark Master
  }

  source_tags = concat(var.tags_workers, var.tags_edge)
  target_tags = var.tags_master

  description = "Allow Spark Master communication"
}

# Allow Spark Worker UI from VPC
resource "google_compute_firewall" "allow_spark_worker_ui" {
  name    = "${var.network_name}-allow-spark-worker-ui"
  project = var.project_id
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = ["8081"] # Spark Worker Web UI
  }

  source_ranges = var.allowed_ui_ips
  target_tags   = var.tags_workers

  description = "Allow access to Spark Worker Web UI"
}

# Allow HDFS NameNode UI (optional, if using HDFS)
resource "google_compute_firewall" "allow_hdfs_namenode_ui" {
  name    = "${var.network_name}-allow-hdfs-namenode-ui"
  project = var.project_id
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = ["9870", "50070"] # HDFS NameNode Web UI (Hadoop 3.x uses 9870, 2.x uses 50070)
  }

  source_ranges = var.allowed_ui_ips
  target_tags   = var.tags_master

  description = "Allow access to HDFS NameNode Web UI (if HDFS is used)"
}

# Allow HDFS DataNode communication (optional, if using HDFS)
resource "google_compute_firewall" "allow_hdfs_datanode" {
  name    = "${var.network_name}-allow-hdfs-datanode"
  project = var.project_id
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = ["9866", "9867", "50010", "50020", "50075"] # HDFS DataNode ports
  }

  source_tags = concat(var.tags_master, var.tags_workers, var.tags_edge)
  target_tags = var.tags_workers

  description = "Allow HDFS DataNode communication (if HDFS is used)"
}

# Allow HDFS NameNode communication (optional, if using HDFS)
resource "google_compute_firewall" "allow_hdfs_namenode" {
  name    = "${var.network_name}-allow-hdfs-namenode"
  project = var.project_id
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = ["9000", "9820", "8020"] # HDFS NameNode ports
  }

  source_tags = concat(var.tags_workers, var.tags_edge)
  target_tags = var.tags_master

  description = "Allow HDFS NameNode communication (if HDFS is used)"
}
