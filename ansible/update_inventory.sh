#!/bin/bash

set -e

echo "Updating Ansible inventory from Terraform outputs..."

# Go to terraform directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../terraform"
INVENTORY_FILE="$SCRIPT_DIR/inventory/hosts.yml"

cd "$TERRAFORM_DIR"

# Check if terraform state exists
if [ ! -f "terraform.tfstate" ]; then
    echo "Error: Terraform state not found. Please deploy infrastructure first."
    echo "Run: cd terraform && terraform apply"
    exit 1
fi

# Get IPs from Terraform
echo "Retrieving IPs from Terraform..."

MASTER_IP=$(terraform output -raw master_external_ip 2>/dev/null || echo "")
EDGE_IP=$(terraform output -raw edge_external_ip 2>/dev/null || echo "")
WORKER_IPS=$(terraform output -json worker_external_ips 2>/dev/null || echo "[]")

# Parse worker IPs
WORKER1_IP=$(echo "$WORKER_IPS" | jq -r '.[0] // empty')
WORKER2_IP=$(echo "$WORKER_IPS" | jq -r '.[1] // empty')
WORKER3_IP=$(echo "$WORKER_IPS" | jq -r '.[2] // empty')

# Check if we got the IPs
if [ -z "$MASTER_IP" ] || [ "$MASTER_IP" == "null" ]; then
    echo "Error: Could not retrieve IPs from Terraform."
    echo "Is the infrastructure deployed?"
    exit 1
fi

echo "Retrieved IPs:"
echo "  Master:   $MASTER_IP"
echo "  Worker 1: $WORKER1_IP"
if [ -n "$WORKER2_IP" ] && [ "$WORKER2_IP" != "null" ]; then
    echo "  Worker 2: $WORKER2_IP"
fi
if [ -n "$WORKER3_IP" ] && [ "$WORKER3_IP" != "null" ]; then
    echo "  Worker 3: $WORKER3_IP"
fi
echo "  Edge:     $EDGE_IP"

# Count workers
NUM_WORKERS=1
if [ -n "$WORKER2_IP" ] && [ "$WORKER2_IP" != "null" ]; then
    NUM_WORKERS=2
fi
if [ -n "$WORKER3_IP" ] && [ "$WORKER3_IP" != "null" ]; then
    NUM_WORKERS=3
fi

# Generate inventory
echo ""
echo "Generating inventory file..."

cat > "$INVENTORY_FILE" << EOF
---
all:
  children:
    spark_cluster:
      children:
        master:
          hosts:
            spark-master:
              ansible_host: $MASTER_IP

        workers:
          hosts:
            spark-worker-1:
              ansible_host: $WORKER1_IP
EOF

# Add worker 2 if exists
if [ $NUM_WORKERS -ge 2 ]; then
cat >> "$INVENTORY_FILE" << EOF
            spark-worker-2:
              ansible_host: $WORKER2_IP
EOF
fi

# Add worker 3 if exists
if [ $NUM_WORKERS -ge 3 ]; then
cat >> "$INVENTORY_FILE" << EOF
            spark-worker-3:
              ansible_host: $WORKER3_IP
EOF
fi

# Add edge and vars
cat >> "$INVENTORY_FILE" << EOF

        edge:
          hosts:
            spark-edge:
              ansible_host: $EDGE_IP

  vars:
    ansible_user: ansible
    ansible_ssh_private_key_file: ~/.ssh/spark-cluster-key
    ansible_python_interpreter: /usr/bin/python3
EOF

echo ""
echo "✅ Inventory updated successfully!"
echo "File: $INVENTORY_FILE"
echo ""
echo "Test connectivity with:"
echo "  ansible all -i ansible/inventory/hosts.yml -m ping"
