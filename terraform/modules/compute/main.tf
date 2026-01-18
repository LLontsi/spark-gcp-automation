terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}
# Master Node
resource "google_compute_instance" "spark_master" {
  name         = "${var.cluster_name}-master"
  project      = var.project_id
  machine_type = var.machine_type_master
  zone         = var.zone

  tags = var.tags_master

  boot_disk {
    initialize_params {
      image = "${var.image_project}/${var.image_family}"
      size  = var.disk_size
      type  = var.disk_type
    }
  }

  network_interface {
    network    = var.network_self_link
    subnetwork = var.subnet_self_link

    # Reserve specific internal IP
    network_ip = "10.0.0.10"

    # Assign external IP (remove for production)
    access_config {
      # Ephemeral IP
    }
  }

  metadata = {
    ssh-keys = var.ssh_public_key != "" ? "${var.ssh_user}:${var.ssh_public_key}" : ""
    role     = "master"
    cluster  = var.cluster_name
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    # Set hostname
    hostnamectl set-hostname spark-master
    
    # Update /etc/hosts
    echo "10.0.0.10 spark-master" >> /etc/hosts
    echo "10.0.0.11 spark-worker-1" >> /etc/hosts
    echo "10.0.0.12 spark-worker-2" >> /etc/hosts
    echo "10.0.0.13 spark-worker-3" >> /etc/hosts
    echo "10.0.0.20 spark-edge" >> /etc/hosts
    
    # System updates
    apt-get update
  EOF

  labels = {
    role    = "master"
    cluster = var.cluster_name
  }

  allow_stopping_for_update = true
}

# Worker Nodes
resource "google_compute_instance" "spark_workers" {
  count = var.num_workers

  name         = "${var.cluster_name}-worker-${count.index + 1}"
  project      = var.project_id
  machine_type = var.machine_type_worker
  zone         = var.zone

  tags = var.tags_worker

  boot_disk {
    initialize_params {
      image = "${var.image_project}/${var.image_family}"
      size  = var.disk_size
      type  = var.disk_type
    }
  }

  network_interface {
    network    = var.network_self_link
    subnetwork = var.subnet_self_link

    # Reserve specific internal IPs
    network_ip = "10.0.0.${11 + count.index}"

    # Assign external IP (remove for production)
    access_config {
      # Ephemeral IP
    }
  }

  metadata = {
    ssh-keys = var.ssh_public_key != "" ? "${var.ssh_user}:${var.ssh_public_key}" : ""
    role     = "worker"
    cluster  = var.cluster_name
    index    = count.index + 1
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    # Set hostname
    hostnamectl set-hostname spark-worker-${count.index + 1}
    
    # Update /etc/hosts
    echo "10.0.0.10 spark-master" >> /etc/hosts
    echo "10.0.0.11 spark-worker-1" >> /etc/hosts
    echo "10.0.0.12 spark-worker-2" >> /etc/hosts
    echo "10.0.0.13 spark-worker-3" >> /etc/hosts
    echo "10.0.0.20 spark-edge" >> /etc/hosts
    
    # System updates
    apt-get update
  EOF

  labels = {
    role    = "worker"
    cluster = var.cluster_name
    index   = tostring(count.index + 1)
  }

  allow_stopping_for_update = true
}

# Edge Node
resource "google_compute_instance" "spark_edge" {
  name         = "${var.cluster_name}-edge"
  project      = var.project_id
  machine_type = var.machine_type_edge
  zone         = var.zone

  tags = var.tags_edge

  boot_disk {
    initialize_params {
      image = "${var.image_project}/${var.image_family}"
      size  = var.disk_size
      type  = var.disk_type
    }
  }

  network_interface {
    network    = var.network_self_link
    subnetwork = var.subnet_self_link

    # Reserve specific internal IP
    network_ip = "10.0.0.20"

    # Assign external IP (remove for production)
    access_config {
      # Ephemeral IP
    }
  }

  metadata = {
    ssh-keys = var.ssh_public_key != "" ? "${var.ssh_user}:${var.ssh_public_key}" : ""
    role     = "edge"
    cluster  = var.cluster_name
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    # Set hostname
    hostnamectl set-hostname spark-edge
    
    # Update /etc/hosts
    echo "10.0.0.10 spark-master" >> /etc/hosts
    echo "10.0.0.11 spark-worker-1" >> /etc/hosts
    echo "10.0.0.12 spark-worker-2" >> /etc/hosts
    echo "10.0.0.13 spark-worker-3" >> /etc/hosts
    echo "10.0.0.20 spark-edge" >> /etc/hosts
    
    # System updates
    apt-get update
  EOF

  labels = {
    role    = "edge"
    cluster = var.cluster_name
  }

  allow_stopping_for_update = true
}

# HDFS NameNode persistent disk (for metadata)
resource "google_compute_disk" "hdfs_namenode" {
  name    = "${var.cluster_name}-hdfs-namenode-disk"
  project = var.project_id
  type    = "pd-ssd"
  zone    = var.zone
  size    = 20 # 20GB for HDFS metadata (reduced for GCP free tier)

  labels = {
    role    = "hdfs-namenode"
    cluster = var.cluster_name
  }
}

# Attach NameNode disk to master
resource "google_compute_attached_disk" "namenode_attachment" {
  disk     = google_compute_disk.hdfs_namenode.id
  instance = google_compute_instance.spark_master.id
}

# HDFS DataNode persistent disks (one per worker)
resource "google_compute_disk" "hdfs_datanode" {
  count = var.num_workers

  name    = "${var.cluster_name}-hdfs-datanode-${count.index + 1}-disk"
  project = var.project_id
  type    = "pd-ssd"
  zone    = var.zone
  size    = 40 # 40GB per worker (reduced for GCP free tier: 300GB limit)

  labels = {
    role    = "hdfs-datanode"
    cluster = var.cluster_name
    index   = tostring(count.index + 1)
  }
}

# Attach DataNode disks to workers
resource "google_compute_attached_disk" "datanode_attachment" {
  count = var.num_workers

  disk     = google_compute_disk.hdfs_datanode[count.index].id
  instance = google_compute_instance.spark_workers[count.index].id
}
