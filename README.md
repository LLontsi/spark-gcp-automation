# Spark GCP Automation

Automated deployment and management of Apache Spark clusters on Google Cloud Platform using Infrastructure as Code.

[![Terraform](https://img.shields.io/badge/Terraform-1.6+-623CE4?logo=terraform)](https://www.terraform.io/)
[![Ansible](https://img.shields.io/badge/Ansible-2.15+-EE0000?logo=ansible)](https://www.ansible.com/)
[![GCP](https://img.shields.io/badge/GCP-Compute_Engine-4285F4?logo=google-cloud)](https://cloud.google.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Overview

This project provides a complete automation solution for deploying production-ready Apache Spark clusters on Google Cloud Platform. It combines Terraform for infrastructure provisioning, Ansible for configuration management, and a custom CLI for cluster lifecycle management.

**Key Features:**
- Fully automated cluster deployment in under 10 minutes
- Integrated monitoring stack (Prometheus + Grafana + Node Exporter)
- Scalable architecture (1-3 worker nodes)
- Security-hardened with configurable firewall rules
- Interactive CLI for cluster management
- CI/CD integration with automated security scanning

## Architecture

The deployed infrastructure consists of:

| Component | Count | Purpose | Specifications |
|-----------|-------|---------|----------------|
| Master Node | 1 | Spark Master + Prometheus + Grafana | n1-standard-4 (4 vCPU, 15GB RAM) |
| Worker Nodes | 1-3 | Spark Workers (Standalone Mode) | n1-standard-4 (4 vCPU, 15GB RAM) |
| Edge Node | 1 | Job submission + Client tools | n1-standard-2 (2 vCPU, 7.5GB RAM) |

**Network Architecture:**
- Custom VPC with private subnet (10.0.0.0/24)
- Firewall rules for SSH, Spark UI, and monitoring ports
- Internal communication over private IPs
- External access via configurable IP allowlists

**Monitoring Stack:**
- Prometheus (port 9090) - Metrics collection
- Grafana (port 3000) - Visualization dashboards
- Node Exporter (port 9100) - System metrics

## Prerequisites

### Required Software

- **Terraform** >= 1.6.0 ([Installation Guide](https://www.terraform.io/downloads))
- **Ansible** >= 2.15 ([Installation Guide](https://docs.ansible.com/ansible/latest/installation_guide/))
- **Python** >= 3.8
- **Google Cloud SDK** ([Installation Guide](https://cloud.google.com/sdk/docs/install))

### GCP Requirements

1. **GCP Project** with billing enabled
2. **Service Account** with the following IAM roles:
   - `Compute Admin`
   - `Compute Network Admin`
   - `Service Account User`
3. **Enabled APIs:**
   - Compute Engine API
   - Cloud Resource Manager API

### Local Setup

1. **SSH Key Pair**: Generate if not already present
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/gcp_spark -C "ansible@spark-cluster"
   ```

2. **Service Account Key**: Download JSON credentials file
   ```bash
   gcloud iam service-accounts keys create ~/gcp-credentials.json \
     --iam-account=your-sa@your-project.iam.gserviceaccount.com
   ```

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/spark-gcp-automation.git
cd spark-gcp-automation
```

### 2. Configure Environment

```bash
# Set GCP credentials
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/gcp-credentials.json"
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"

# Optional: Configure SSH key path (default: ~/.ssh/gcp_spark)
export SPARK_SSH_KEY="$HOME/.ssh/gcp_spark"
```

### 3. Configure Terraform Variables

Create `terraform/terraform.tfvars`:

```hcl
project_id     = "your-gcp-project-id"
region         = "us-central1"
zone           = "us-central1-a"
cluster_name   = "spark"
num_workers    = 2

# IMPORTANT: Restrict for production
allowed_ssh_ips = ["YOUR_IP/32"]  # Replace with your IP
allowed_ui_ips  = ["YOUR_IP/32"]

ssh_public_key = "ssh-rsa AAAAB3... your-key-here"
```

See `terraform/terraform.tfvars.secure.template` for complete configuration options.

## Usage

### Interactive CLI (Recommended)

The project includes a custom CLI for simplified cluster management:

```bash
./manage.py
```

#### Available Commands

| Command | Description |
|---------|-------------|
| `deploy [-w N] [-b]` | Deploy cluster with N workers (optional background mode) |
| `status` | Display cluster status and architecture |
| `scale N` | Scale cluster to N workers |
| `ssh <target>` | SSH into master, edge, or worker nodes |
| `run [options] [file]` | Execute Spark job |
| `run -u <file>` | Upload local file and execute |
| `logs` | Tail deployment logs |
| `destroy` | Tear down infrastructure |

#### Example Workflow

```bash
(spark-cluster) deploy -w 2          # Deploy with 2 workers
(spark-cluster) status                # Verify deployment
(spark-cluster) run                   # Run default WordCount test
(spark-cluster) run -u mydata.txt     # Upload and process custom file
(spark-cluster) ssh master            # Access master node
(spark-cluster) destroy               # Clean up resources
```

### Manual Deployment

If you prefer manual control:

#### Step 1: Provision Infrastructure

```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

#### Step 2: Update Inventory

```bash
cd ../ansible
./update_inventory.sh
```

#### Step 3: Configure Cluster

```bash
ansible-playbook -i inventory/hosts.yml playbooks/site.yml
```

#### Step 4: Verify Deployment

```bash
# Check cluster status
ansible all -i inventory/hosts.yml -m ping

# Access Spark Master UI
open http://MASTER_EXTERNAL_IP:8080

# Access Grafana
open http://MASTER_EXTERNAL_IP:3000
```

## Configuration

### Terraform Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `project_id` | **required** | GCP project ID |
| `region` | `europe-west1` | GCP region |
| `zone` | `europe-west1-b` | GCP zone |
| `cluster_name` | `spark` | Cluster name prefix |
| `num_workers` | `3` | Number of worker nodes |
| `machine_type_master` | `n1-standard-4` | Master instance type |
| `machine_type_worker` | `n1-standard-4` | Worker instance type |
| `machine_type_edge` | `n1-standard-2` | Edge instance type |
| `disk_size` | `50` | Boot disk size (GB) |
| `allowed_ssh_ips` | `["0.0.0.0/0"]` | SSH access allowlist |
| `allowed_ui_ips` | `["0.0.0.0/0"]` | Web UI access allowlist |

### Ansible Variables

Edit `ansible/group_vars/all.yml` to customize:

- Spark version and configuration
- JVM memory settings
- Network ports
- System locale and timezone

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SPARK_SSH_KEY` | `~/.ssh/gcp_spark` | Path to SSH private key |
| `GOOGLE_APPLICATION_CREDENTIALS` | - | GCP service account JSON |
| `GOOGLE_CLOUD_PROJECT` | - | GCP project ID |

## Monitoring

### Accessing Dashboards

After deployment, monitoring dashboards are available at:

- **Spark Master UI**: `http://MASTER_IP:8080`
- **Grafana**: `http://MASTER_IP:3000` (admin/admin)
- **Prometheus**: `http://MASTER_IP:9090`

### Grafana Dashboard

The pre-configured dashboard displays:
- CPU and memory usage per node
- Network I/O statistics
- Disk utilization
- Spark worker status

**Note**: Grafana now displays friendly node names (e.g., `spark-worker-1`) instead of IPs.

## Testing

### WordCount Example

Verify cluster functionality with the built-in WordCount test:

```bash
# Using CLI
./manage.py
(spark-cluster) run

# Manual execution
ssh ansible@EDGE_IP
cd ~/spark-jobs
./run_wordcount.sh /tmp/sample.txt

# View results (output is in part-* files)
cat /tmp/wordcount-output/part-*
```

### Custom Applications

Upload and execute custom Spark applications:

```bash
# Via CLI (automatic upload to all nodes)
(spark-cluster) run -u /path/to/local/data.txt

# Manual submission
scp myapp.py ansible@EDGE_IP:~/
ssh ansible@EDGE_IP
spark-submit \
  --master spark://MASTER_INTERNAL_IP:7077 \
  --deploy-mode client \
  myapp.py
```

## Troubleshooting

### Common Issues

**Issue**: Terraform fails with "quota exceeded"
- **Solution**: Check GCP quotas for Compute Engine. Request increase if needed.

**Issue**: Ansible connection refused
- **Solution**: Wait 60 seconds after `terraform apply` for VMs to fully boot.

**Issue**: Monitoring shows no data
- **Solution**: Verify firewall rules allow ports 9090, 9100, 3000. Check Prometheus targets at `http://MASTER_IP:9090/targets`.

**Issue**: Worker nodes not registering with master
- **Solution**: Verify `spark_master_ip` in `ansible/group_vars/all.yml` matches actual master IP.

**Issue**: SSH host key verification errors after recreating infrastructure
- **Solution**: This is expected. The CLI automatically bypasses host key checking. If using manual SSH, add `-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no`.

**Issue**: WordCount results show only `_SUCCESS` file
- **Solution**: Results are in `part-*` files. View with: `cat /tmp/wordcount-output/part-*`

### Logs

- **Terraform**: Standard output during apply
- **Ansible**: `ansible/ansible.log`
- **Deployment**: `./deploy.log` (when using CLI)
- **Spark**: `/opt/spark/logs/` on cluster nodes

## Security Best Practices

1. **Restrict Network Access**
   - Replace `0.0.0.0/0` in `allowed_ssh_ips` with your IP
   - Use VPN or bastion host for production

2. **Credentials Management**
   - Never commit `terraform.tfvars` or `.env`
   - Use secret management (GCP Secret Manager, HashiCorp Vault)
   - Rotate SSH keys regularly

3. **Enable State Locking**
   - Configure remote backend (see `terraform/backend.tf.template`)
   - Prevents concurrent modifications

4. **Regular Updates**
   - Monitor security advisories for Spark, Terraform, Ansible
   - Apply OS security patches via Ansible

## Performance Optimization

The project includes several performance enhancements:

- **Parallel File Uploads**: Uses threading for 10x faster data distribution
- **Ansible Connection Pooling**: Reduces SSH overhead by 30%
- **Fact Caching**: Saves ~30 seconds per Ansible run
- **Inventory Caching**: CLI response time < 1ms

**Expected Deployment Time**: 5-6 minutes (from `terraform apply` to ready cluster)

## Project Structure

```
spark-gcp-automation/
├── .github/
│   └── workflows/
│       └── general-checks.yml      # CI/CD pipeline
├── ansible/
│   ├── group_vars/                 # Ansible variables
│   ├── inventory/                  # Dynamic inventory
│   ├── playbooks/                  # Ansible playbooks
│   └── roles/                      # Ansible roles
│       ├── common/                 # Base system setup
│       ├── java/                   # JDK installation
│       ├── spark-master/           # Spark Master config
│       ├── spark-worker/           # Spark Worker config
│       ├── spark-edge/             # Edge node setup
│       ├── monitoring-common/      # Node Exporter
│       ├── prometheus/             # Prometheus server
│       └── grafana/                # Grafana dashboards
├── terraform/
│   ├── modules/
│   │   ├── vpc/                    # Network configuration
│   │   ├── firewall/               # Security rules
│   │   └── compute/                # VM instances
│   ├── main.tf                     # Root module
│   ├── variables.tf                # Input variables
│   └── outputs.tf                  # Output values
├── manage.py                       # CLI entrypoint
└── README.md

```

## Contributing

Contributions are welcome. Please follow these guidelines:

1. **Code Style**
   - Terraform: Use `terraform fmt`
   - Python: Follow PEP 8
   - Ansible: Use `ansible-lint`

2. **Testing**
   - Test changes on a non-production GCP project
   - Verify `terraform plan` shows expected changes
   - Run full deployment cycle before submitting PR

3. **Pull Requests**
   - Create feature branch from `main`
   - Include clear description of changes
   - Update documentation if needed

## Roadmap

- [ ] HDFS integration for distributed storage
- [ ] Auto-scaling based on workload
- [ ] Multi-region deployment support
- [ ] Spot instance support for cost optimization
- [ ] Integration with Cloud Storage (GCS)
- [ ] Kubernetes deployment option

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## Authors

- **LONTSIE LAMBOU Ronaldinho** 
- **LADO SAHA** 

## Acknowledgments

- Apache Spark Community
- HashiCorp Terraform
- Ansible Project
- Google Cloud Platform

---

For questions or support, please open an issue on GitHub.