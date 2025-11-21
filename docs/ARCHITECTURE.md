# Architecture

## Overview

Apache Spark cluster on GCP with the following components:

## Components

### Master Node
- **Role**: Spark Master
- **Instance Type**: n1-standard-2
- **OS**: Ubuntu 22.04 LTS
- **Services**: Spark Master, Web UI (8080)

### Worker Nodes (3x)
- **Role**: Spark Workers
- **Instance Type**: n1-standard-2
- **OS**: Ubuntu 22.04 LTS
- **Services**: Spark Worker

### Edge Node
- **Role**: Job Submission
- **Instance Type**: n1-standard-1
- **OS**: Ubuntu 22.04 LTS
- **Services**: Spark Client

## Network Architecture
```
Internet
    |
    v
GCP VPC (10.0.0.0/16)
    |
    +-- Subnet: spark-subnet (10.0.0.0/24)
        |
        +-- spark-master (10.0.0.10)
        +-- spark-worker-1 (10.0.0.11)
        +-- spark-worker-2 (10.0.0.12)
        +-- spark-worker-3 (10.0.0.13)
        +-- spark-edge (10.0.0.20)
```

## Firewall Rules

- Allow SSH (22) from authorized IPs
- Allow Spark Master UI (8080) from authorized IPs
- Allow Spark Worker UI (8081) from VPC
- Allow internal communication within VPC
