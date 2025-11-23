# Terraform Infrastructure

Infrastructure as Code for deploying Apache Spark cluster on Google Cloud Platform.

## 📁 Structure
```
terraform/
├── main.tf                    # Main configuration
├── variables.tf               # Variable definitions
├── outputs.tf                 # Output definitions
├── terraform.tfvars.example   # Example variables file
├── .tflint.hcl               # TFLint configuration
└── modules/
    ├── vpc/                   # VPC module
    ├── firewall/             # Firewall module
    └── compute/              # Compute instances module
```

## 🚀 Quick Start

### 1. Prerequisites

- Terraform >= 1.6.0 installed
- GCP account with billing enabled
- GCP Project created
- `gcloud` CLI configured

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/LLontsi/spark-gcp-automation.git
cd spark-gcp-automation/terraform

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Generate SSH key if needed
ssh-keygen -t rsa -b 4096 -f ~/.ssh/spark-cluster-key -C "ansible"
```

### 3. Configure terraform.tfvars

Edit `terraform.tfvars`:
```hcl
project_id = "your-gcp-project-id"
region     = "europe-west1"
zone       = "europe-west1-b"

# IMPORTANT: Change to your IP for security
allowed_ssh_ips = ["YOUR_IP/32"]
allowed_ui_ips  = ["YOUR_IP/32"]

ssh_user       = "ansible"
ssh_public_key = "ssh-rsa AAAAB3... your-key-here"
```

### 4. Deploy
```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Format code
terraform fmt -recursive

# Plan deployment
terraform plan

# Apply (deploy)
terraform apply

# Get outputs
terraform output
```

### 5. Access
```bash
# SSH to master
ssh ansible@$(terraform output -raw master_external_ip)

# SSH to edge
ssh ansible@$(terraform output -raw edge_external_ip)

# View Spark Master UI
# Open: http://$(terraform output -raw master_external_ip):8080
```

### 6. Destroy
```bash
# When done, destroy all resources
terraform destroy
```

## 📋 Modules

### VPC Module (`modules/vpc/`)

Creates:
- VPC Network (custom mode)
- Subnet with Private Google Access
- Cloud Router
- Cloud NAT

### Firewall Module (`modules/firewall/`)

Creates rules for:
- SSH access
- Spark Master (7077, 8080)
- Spark Worker (8081)
- HDFS (if used)
- Internal communication

### Compute Module (`modules/compute/`)

Creates:
- 1x Master Node (n1-standard-4)
- 3x Worker Nodes (n1-standard-4)
- 1x Edge Node (n1-standard-2)

## 🔒 Security Best Practices

1. **Change default IPs**: Update `allowed_ssh_ips` and `allowed_ui_ips` to your IP
2. **Use SSH keys**: Always use SSH key authentication
3. **Remove external IPs**: For production, use Cloud IAP or VPN
4. **Enable logging**: Cloud Logging is enabled by default
5. **Use service accounts**: Configure with minimal permissions

## 📊 Estimated Costs

Based on europe-west1 pricing (approximate):

| Resource | Type | Quantity | Monthly Cost |
|----------|------|----------|--------------|
| Master | n1-standard-4 | 1 | ~$150 |
| Workers | n1-standard-4 | 3 | ~$450 |
| Edge | n1-standard-2 | 1 | ~$50 |
| Network | VPC/Subnet | 1 | ~$10 |
| Storage | 50GB/instance | 5 | ~$20 |
| **Total** | | | **~$680/month** |

💡 **Tip**: Use `terraform destroy` when not using the cluster!

## 🧪 Testing
```bash
# Validate Terraform
terraform validate

# Check formatting
terraform fmt -check -recursive

# Run TFLint
tflint --recursive

# Plan without applying
terraform plan
```

## 🔧 Troubleshooting

### Issue: "Quota exceeded"
**Solution**: Request quota increase in GCP Console

### Issue: "Permission denied"
**Solution**: Ensure service account has required roles:
- Compute Admin
- Network Admin

### Issue: "SSH connection refused"
**Solution**: 
1. Check firewall rules allow your IP
2. Verify SSH key is configured
3. Wait for instance to fully boot

## 📚 Documentation

- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [GCP Compute Engine](https://cloud.google.com/compute/docs)
- [VPC Documentation](https://cloud.google.com/vpc/docs)

## 🤝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.# Terraform Configuration
