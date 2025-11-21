# Deployment Guide

## Prerequisites

1. GCP Account with billing enabled
2. Terraform >= 1.6.0 installed
3. Ansible >= 2.15 installed
4. GCP Service Account with required permissions

## Step 1: GCP Setup
```bash
# Set your project ID
export GCP_PROJECT_ID="your-project-id"

# Authenticate with GCP
gcloud auth login
gcloud config set project $GCP_PROJECT_ID
```

## Step 2: Deploy Infrastructure
```bash
cd terraform

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -out=tfplan

# Apply the plan
terraform apply tfplan
```

## Step 3: Configure Spark Cluster
```bash
cd ../ansible

# Test connectivity
ansible all -i inventory/gcp.yml -m ping

# Deploy Spark
ansible-playbook -i inventory/gcp.yml playbooks/site.yml
```

## Step 4: Validate Deployment
```bash
# Run WordCount test
cd ../scripts/wordcount
./run_wordcount.sh
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.