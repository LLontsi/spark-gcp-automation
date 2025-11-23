# Compute Module

This module creates the Compute Engine instances for the Spark cluster.

## Resources Created

- 1x Master Node (Spark Master + coordination)
- 3x Worker Nodes (Spark Workers)
- 1x Edge Node (Job submission)

## Instance Configuration

### Master Node
- **Name**: `spark-master`
- **Internal IP**: `10.0.0.10`
- **Machine Type**: `n1-standard-4` (4 vCPU, 15 GB RAM)
- **Role**: Spark Master, cluster coordination

### Worker Nodes
- **Names**: `spark-worker-1`, `spark-worker-2`, `spark-worker-3`
- **Internal IPs**: `10.0.0.11`, `10.0.0.12`, `10.0.0.13`
- **Machine Type**: `n1-standard-4` (4 vCPU, 15 GB RAM)
- **Role**: Spark Workers, data processing

### Edge Node
- **Name**: `spark-edge`
- **Internal IP**: `10.0.0.20`
- **Machine Type**: `n1-standard-2` (2 vCPU, 7.5 GB RAM)
- **Role**: Job submission, client access

## Usage
```hcl
module "compute" {
  source = "./modules/compute"

  project_id         = var.project_id
  region             = var.region
  zone               = var.zone
  network_self_link  = module.vpc.vpc_self_link
  subnet_self_link   = module.vpc.subnet_self_link
  cluster_name       = "spark"
  num_workers        = 3
  ssh_public_key     = file("~/.ssh/id_rsa.pub")
}
```

## Inputs

| Name | Description | Type | Default |
|------|-------------|------|---------|
| project_id | GCP Project ID | string | required |
| region | GCP Region | string | required |
| zone | GCP Zone | string | required |
| network_self_link | VPC self link | string | required |
| subnet_self_link | Subnet self link | string | required |
| cluster_name | Cluster name prefix | string | spark |
| num_workers | Number of workers | number | 3 |
| machine_type_master | Master machine type | string | n1-standard-4 |
| machine_type_worker | Worker machine type | string | n1-standard-4 |
| machine_type_edge | Edge machine type | string | n1-standard-2 |

## Outputs

| Name | Description |
|------|-------------|
| master_external_ip | Master external IP |
| worker_external_ips | Worker external IPs |
| edge_external_ip | Edge external IP |
| all_internal_ips | All internal IPs |

