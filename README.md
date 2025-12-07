# spark-gcp-automation
Automated Apache Spark deployment on GCP using Terraform and Ansible

# 🚀 Apache Spark Automation on GCP

[![Terraform](https://img.shields.io/badge/Terraform-1.6+-623CE4?logo=terraform)](https://www.terraform.io/)
[![Ansible](https://img.shields.io/badge/Ansible-2.15+-EE0000?logo=ansible)](https://www.ansible.com/)
[![GCP](https://img.shields.io/badge/GCP-Compute_Engine-4285F4?logo=google-cloud)](https://cloud.google.com/)

> Automated deployment of Apache Spark cluster on Google Cloud Platform using Infrastructure as Code (IaC)

## 📋 Project Overview

This project automates the deployment of an Apache Spark cluster on GCP using:
- **Terraform** for infrastructure provisioning
- **Ansible** for configuration management
- **GitHub Actions** for CI/CD

### Architecture
- 1x Master Node (Spark Master)
- 3x Worker Nodes (Spark Workers)
- 1x Edge Node (Job Submission)
- Custom VPC with security configurations

## 🛠️ Prerequisites

- Terraform >= 1.6.0
- Ansible >= 2.15
- Python >= 3.8
- GCP Account with billing enabled
- GCP Service Account with appropriate IAM roles

## 🚦 Quick Start
```bash
# 1. Clone the repository
git clone https://github.com/yourusername/spark-gcp-automation.git
cd spark-gcp-automation

# 2. Configure GCP credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"

# 3. Deploy infrastructure
cd terraform
terraform init
terraform plan
terraform apply

# 4. Configure Spark cluster
4. Configure Spark cluster
cd ../ansible
./update_inventory.sh
ansible-playbook -i inventory/hosts.yml playbooks/site.yml
```

## 📂 Project Structure
```
.
├── .github/          # GitHub workflows and templates
├── terraform/        # Infrastructure as Code
├── ansible/          # Configuration management
├── scripts/          # Utility scripts
├── tests/            # Test files
└── docs/             # Documentation
```

## 🧪 Testing

Run the WordCount application to validate deployment:
```bash
# Get the Edge node IP from inventory
ssh ansible@<EDGE_EXTERNAL_IP>

# On the Edge node:
cd ~/spark-jobs
./run_wordcount.sh

```

## 👥 Team

- **Lontsi** - DevOps & Infrastructure
- **Lado** - Configuration & Automation

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and pull request process.