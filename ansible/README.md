# Ansible Configuration for Spark Cluster

Ansible playbooks and roles to configure Apache Spark cluster on GCP.

## Structure
```
ansible/
├── playbooks/
│   └── site.yml           # Main playbook
├── roles/
│   ├── common/            # Common system configuration
│   ├── java/              # Java installation
│   ├── spark-common/      # Spark installation
│   ├── spark-master/      # Spark Master configuration
│   ├── spark-worker/      # Spark Worker configuration
│   └── spark-edge/        # Edge node (client) configuration
├── inventory/
│   └── hosts.yml          # Inventory file
└── group_vars/
    ├── all.yml            # Global variables
    └── spark_cluster.yml  # Cluster-specific variables
```

## Prerequisites

1. Terraform infrastructure deployed
2. SSH access configured to all nodes
3. Ansible >= 2.15 installed locally

## Installation
```bash
# Install Ansible
pip install ansible

# Install required collections
ansible-galaxy collection install community.general
```

## Configuration

1. Update `inventory/hosts.yml` with actual IP addresses from Terraform:
```bash
   cd terraform
   terraform output
```

2. Copy the external IPs to `inventory/hosts.yml`

## Usage

### Test Connectivity
```bash
ansible all -i inventory/hosts.yml -m ping
```

### Run Full Deployment
```bash
ansible-playbook -i inventory/hosts.yml playbooks/site.yml
```

### Run Specific Roles
```bash
# Only common configuration
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags common

# Only Spark installation
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags spark
```

## Testing

After deployment, test the cluster:
```bash
# SSH to edge node
ssh ansible@<edge_external_ip>

# Run WordCount test
cd ~/spark-jobs
./run_wordcount.sh
```

## Roles Description

### common
- System updates
- Package installation
- System tuning (swap, limits)
- Directory creation

### java
- OpenJDK 11 installation
- JAVA_HOME configuration

### spark-common
- Spark download and installation
- Configuration files (spark-env.sh, spark-defaults.conf)
- PATH configuration

### spark-master
- Spark Master service
- Workers configuration
- Web UI

### spark-worker
- Spark Worker service
- Master connection
- Resource configuration

### spark-edge
- Client tools
- WordCount scripts
- Testing utilities

## Troubleshooting

### Check service status
```bash
systemctl status spark-master  # On master
systemctl status spark-worker  # On workers
```

### View logs
```bash
tail -f /opt/spark/current/logs/*
```

### Restart services
```bash
systemctl restart spark-master  # On master
systemctl restart spark-worker  # On workers
```

## Variables

Key variables in `group_vars/all.yml`:
- `spark_version`: Spark version to install
- `spark_worker_cores`: CPU cores per worker
- `spark_worker_memory`: Memory per worker
- `spark_master_ip`: Master node IP
