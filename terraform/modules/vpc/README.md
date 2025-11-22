# VPC Module

This module creates a VPC network for the Spark cluster on GCP.

## Resources Created

- VPC Network (custom mode)
- Subnet with Private Google Access enabled
- Cloud Router
- Cloud NAT for outbound internet access

## Usage
```hcl
module "vpc" {
  source = "./modules/vpc"

  project_id  = var.project_id
  region      = var.region
  vpc_name    = "spark-vpc"
  subnet_name = "spark-subnet"
  subnet_cidr = "10.0.0.0/24"
}
```

## Inputs

| Name | Description | Type | Default |
|------|-------------|------|---------|
| project_id | GCP Project ID | string | required |
| region | GCP Region | string | europe-west1 |
| vpc_name | VPC name | string | spark-vpc |
| subnet_name | Subnet name | string | spark-subnet |
| subnet_cidr | Subnet CIDR | string | 10.0.0.0/24 |

## Outputs

| Name | Description |
|------|-------------|
| vpc_id | VPC ID |
| vpc_name | VPC name |
| subnet_id | Subnet ID |
| subnet_name | Subnet name |
| subnet_cidr | Subnet CIDR range |

## Network Architecture
```
Internet
    |
    v
Cloud NAT
    |
    v
VPC (spark-vpc)
    |
    +-- Subnet: spark-subnet (10.0.0.0/24)
        |
        +-- spark-master (10.0.0.10)
        +-- spark-worker-1 (10.0.0.11)
        +-- spark-worker-2 (10.0.0.12)
        +-- spark-worker-3 (10.0.0.13)
        +-- spark-edge (10.0.0.20)
```

## Features

- Private Google Access enabled for GCS access
- Cloud NAT for outbound internet (package downloads)
- Regional routing mode
- Logs enabled for NAT
