# Deployment Guide

## Prerequisites

### Required Software

1. **Terraform** >= 1.6.0 ([Download](https://www.terraform.io/downloads))
2. **Ansible** >= 2.15 ([Install](https://docs.ansible.com/ansible/latest/installation_guide/))
3. **Python** >= 3.8
4. **Google Cloud SDK** ([Install](https://cloud.google.com/sdk/docs/install))

### GCP Requirements

1. **GCP Account** with billing enabled
2. **Service Account** with roles:
   - Compute Admin
   - Compute Network Admin
   - Service Account User
3. **APIs Enabled**:
   ```bash
   gcloud services enable compute.googleapis.com
   gcloud services enable cloudresourcemanager.googleapis.com
   ```

### Local Setup

1. **Generate SSH Key** (if not exists):
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/gcp_spark -C "ansible@spark-cluster"
   ```

2. **Create Service Account Key**:
   ```bash
   gcloud iam service-accounts keys create ~/gcp-credentials.json \
     --iam-account=YOUR-SA@YOUR-PROJECT.iam.gserviceaccount.com
   ```

3. **Set Environment Variables**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="$HOME/gcp-credentials.json"
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   export SPARK_SSH_KEY="$HOME/.ssh/gcp_spark"  # Optional, this is default
   ```

## Deployment Method 1: Interactive CLI (Recommended)

### Step 1: Configure Terraform Variables

Create `terraform/terraform.tfvars`:

```hcl
project_id    = "your-gcp-project"
region        = "us-central1"
zone          = "us-central1-a"
cluster_name  = "spark"
num_workers   = 2  # N workers supported

# IMPORTANT: Restrict for security
allowed_ssh_ips = ["YOUR_IP/32"]
allowed_ui_ips  = ["YOUR_IP/32"]

ssh_public_key = "ssh-rsa AAAAB3... your-public-key"
```

See `terraform/terraform.tfvars.secure.template` for all options.

### Step 2: Deploy Cluster

```bash
./manage.py
```

In the interactive shell:

```bash
(spark-cluster) deploy -w 2          # Deploy with 2 workers
```

**What happens**:
1. Terraform provisions GCP resources (~2-3 min)
2. Inventory file generated automatically
3. Ansible configures cluster (~3-4 min)
4. Total time: ~5-6 minutes

### Step 3: Verify Deployment

```bash
(spark-cluster) status                # View cluster info
```

You should see:
- Cluster architecture diagram
- Node IPs and services
- Access URLs for Spark UI, Grafana, Prometheus

### Step 4: Access Services

**Spark Master UI**: `http://MASTER_IP:8080`  
**Grafana**: `http://MASTER_IP:3000` (admin/admin)  
**Prometheus**: `http://MASTER_IP:9090`

### Step 5: Run Test Job

```bash
(spark-cluster) run                   # Run default WordCount test
```

**Expected output**:
```
   Cluster Configuration:
   Workers detected: 2
   Executors: 2
   Cores per executor: 3
   Memory per executor: 11G

[Spark job output...]

WordCount completed!
Results in: /tmp/wordcount-output
```

**View results** (SSH to edge):
```bash
(spark-cluster) ssh edge
cat /tmp/wordcount-output/part-*
```

### Step 6: Scale Cluster (Optional)

```bash
(spark-cluster) scale 3               # Scale to 3 workers
```

This re-deploys with updated worker count. Monitoring and Spark automatically detect new nodes.

### Step 7: Clean Up

```bash
(spark-cluster) destroy               # Confirm with 'y'
```

## Deployment Method 2: Manual Steps

If you prefer manual control:

### Step 1: Initialize Terraform

```bash
cd terraform
terraform init
```

### Step 2: Plan Infrastructure

```bash
terraform plan -var="num_workers=2" -out=tfplan
```

### Step 3: Apply Plan

```bash
terraform apply tfplan
```

### Step 4: Generate Inventory

```bash
cd ../ansible
./update_inventory.sh
```

**Result**: `ansible/inventory/hosts.yml` created with node IPs.

### Step 5: Configure Cluster

```bash
ansible-playbook -i inventory/hosts.yml playbooks/site.yml
```

**Duration**: ~3-4 minutes

### Step 6: Verify Ansible

```bash
ansible all -i inventory/hosts.yml -m ping
```

Expected: `SUCCESS` from all nodes.

### Step 7: Run WordCount Test

```bash
# Get edge node IP from inventory
EDGE_IP=$(grep -A1 'spark-edge' inventory/hosts.yml | grep ansible_host | awk '{print $2}')

# SSH and run test
ssh -i ~/.ssh/gcp_spark ansible@$EDGE_IP
cd ~/spark-jobs
./run_wordcount.sh
```

## CLI Command Reference

| Command | Description |
|---------|-------------|
| `deploy [-w N] [-b]` | Deploy cluster (1-N workers, optional background) |
| `status` | Show cluster status and architecture |
| `scale N` | Scale to 1-N workers |
| `ssh <target>` | SSH to master/edge/worker-N |
| `run` | Run WordCount on default sample |
| `run -u <file>` | Upload local file and run WordCount |
| `logs` | Tail deployment logs (Ctrl+C to exit) |
| `destroy` | Destroy all infrastructure |
| `exit` | Quit CLI |

## Post-Deployment Configuration

### Change Grafana Password

```bash
ssh -i ~/.ssh/gcp_spark ansible@MASTER_IP
sudo grafana-cli admin reset-admin-password NEW_PASSWORD
```

### Add Custom Spark Application

```bash
# Upload your application
(spark-cluster) run -u /path/to/your/data.csv

# Or manual submission
scp your_app.py ansible@EDGE_IP:~/
ssh ansible@EDGE_IP
spark-submit \
  --master spark://MASTER_INTERNAL_IP:7077 \
  --executor-memory 11G \
  --executor-cores 3 \
  your_app.py
```

### Enable Remote State (Production)

1. Create GCS bucket:
   ```bash
   gsutil mb gs://your-tfstate-bucket
   ```

2. Copy `terraform/backend.tf.template` to `terraform/backend.tf`

3. Edit with your bucket name

4. Re-initialize:
   ```bash
   terraform init -migrate-state
   ```

## Monitoring Setup

After deployment:

1. **Access Grafana**: `http://MASTER_IP:3000`
2. **Login**: admin / admin
3. **Change password** when prompted
4. **View Dashboard**: "Spark Cluster Overview"

**Metrics Available**:
- CPU usage per node (shows node names, not IPs)
- Memory utilization
- Network I/O
- Disk I/O
- Node status

## Troubleshooting

### Deployment Fails at Terraform

**Issue**: Quota exceeded  
**Solution**: Check GCP quotas for region. Request increase if needed.

**Issue**: Authentication error  
**Solution**: Verify `GOOGLE_APPLICATION_CREDENTIALS` path and permissions.

### Deployment Fails at Ansible

**Issue**: SSH connection refused  
**Solution**: Wait 60 seconds after Terraform for VMs to fully boot. Re-run `deploy`.

**Issue**: `python3-pip` not found  
**Solution**: Already fixed via `get-pip.py` bootstrap. Re-deploy if still occurs.

### Workers Not Registering

**Check**:
1. Spark Master UI (`http://MASTER_IP:8080`) shows workers
2. Verify `spark_master_ip` is correct: `ssh master → hostname -I`
3. Check firewall rules allow internal traffic

### Monitoring Shows No Data

**Check**:
1. Prometheus targets: `http://MASTER_IP:9090/targets`
2. All targets should show "UP" state
3. Verify Node Exporter running: `ssh worker-1 → systemctl status node_exporter`

### SSH Host Key Errors

**Solution**: Already handled by CLI with `-o UserKnownHostsFile=/dev/null`. If using manual SSH, add same flags.

## Logs Location

- **Deployment**: `./deploy.log` (if using CLI with `-b`)
- **Terraform**: stdout during apply
- **Ansible**: `ansible/ansible.log`
- **Spark**: `/opt/spark/logs/` on cluster nodes
- **Prometheus**: `journalctl -u prometheus`
- **Grafana**: `journalctl -u grafana-server`

## Upgrade Procedure

To upgrade Spark version:

1. Edit `ansible/group_vars/all.yml`:
   ```yaml
   spark_version: "3.5.1"  # New version
   ```

2. Re-run Ansible:
   ```bash
   cd ansible
   ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags spark-common,spark-master,spark-worker
   ```

3. Restart services on all nodes

## Cost Estimation

**2-Worker Cluster (n1-standard-4 + n1-standard-2)**:
- Master: ~$180/month
- Workers (2x): ~$360/month  
- Edge: ~$90/month
- **Total**: ~$630/month (if running 24/7)

**GCP Free Trial**: $300 credit covers ~2 weeks of continuous operation or several months of testing.

**Cost Optimization**:
- Use `destroy` when not needed
- Consider preemptible VMs for dev/test (not implemented yet)
- Use `scale 1` for minimal testing

## Next Steps

- Integrate with GCS for distributed storage
- Set up CI/CD for automated deployments
- Configure SSL/TLS for web UIs
- Implement auto-scaling based on workload
- Add Kerberos authentication for production