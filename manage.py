#!/usr/bin/env python3
import cmd
import os
import subprocess
import sys
import yaml
import time

class SparkClusterCLI(cmd.Cmd):
    intro = r"""
   _____                   __        ______     __ 
  / ___/____  ____ ______/ /__     / ____/____/ /_
  \__ \/ __ \/ __ `/ ___/ //_/____/ /   / __  / __/
 ___/ / /_/ / /_/ / /  / ,< /____/ /___/ /_/ / /_  
/____/ .___/\__,_/_/  /_/|_|     \____/\__,_/\__/  
    /_/                                            
    
Welcome to the Spark Cluster Manager.
Type 'help' or '?' to list commands.
Type 'help <command>' for specific command usage.
"""
    prompt = '(spark-cluster) '

    def __init__(self):
        super().__init__()
        self.inventory_file = 'ansible/inventory/hosts.yml'

    def do_about(self, arg):
        """Show project presentation and details."""
        print("""
================================================================
          Spark on GCP Automation w/ Monitoring
================================================================
This project automates the deployment of an Apache Spark cluster
on Google Cloud Platform using Terraform and Ansible.

Features:
- Infrastructure as Code (Terraform)
- Configuration Management (Ansible)
- Distributed Processing (Spark 3.5.0)
- Functional Testing (WordCount on Edge Node)
- Full Monitoring Stack (Prometheus + Grafana + Node Exporter)

Authors: 
    > LONTSIE LAMBOU Ronaldinho
    > LADO SAHA
Version: v1.1.0 (Innovations Branch)
================================================================
""")


    def do_deploy(self, arg):
        """
        Deploy and configure the cluster.
        
        Usage: deploy
        
        Steps:
        1. Runs 'terraform apply' to provision VMs (Master, Workers, Edge).
        2. Runs 'update_inventory.sh' to generate Ansible hosts file.
        3. Runs 'ansible-playbook' to install Java, Spark, and Monitoring.
        """
        print("[INFO] Starting deployment...")
        # 1. Terraform Apply
        print("\n[1/3] Provisioning Infrastructure with Terraform...")
        try:
            subprocess.run(['terraform', 'apply', '-auto-approve'], cwd='terraform', check=True)
        except subprocess.CalledProcessError:
            print("[FAIL] Terraform failed.")
            return

        # 2. Update Inventory
        print("\n[2/3] Updating Ansible Inventory...")
        try:
            subprocess.run(['./update_inventory.sh'], cwd='ansible', check=True)
        except subprocess.CalledProcessError:
            print("[FAIL] Inventory update failed.")
            return

        # 3. Ansible Configuration
        print("\n[3/3] Configuring Cluster with Ansible...")
        try:
            env = os.environ.copy()
            env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
            subprocess.run(['ansible-playbook', '-i', 'inventory/hosts.yml', 'playbooks/site.yml'], 
                           cwd='ansible', env=env, check=True)
        except subprocess.CalledProcessError:
            print("[FAIL] Ansible configuration failed.")
            return
        
        print("\n[SUCCESS] Deployment Complete!")

    def do_destroy(self, arg):
        """
        Destroy the cluster infrastructure.
        
        Usage: destroy
        
        Warning: This will permanently delete all GCP resources (VMs, Network, Firewall).
        """
        confirm = input("[WARN] Are you sure you want to DESTROY the cluster? (y/N): ")
        if confirm.lower() == 'y':
            print("[INFO] Destroying infrastructure...")
            subprocess.run(['terraform', 'destroy', '-auto-approve'], cwd='terraform')
            print("[SUCCESS] Destruction Complete.")
        else:
            print("Here is your cluster back")

    def do_test(self, arg):
        """
        Run the functional test.
        
        Usage: test
        
        Actions:
        - Connects to the Edge node via SSH.
        - Submits a sample Spark job (WordCount) to the cluster.
        - Verifies that the job completes and produces output.
        """
        print("[INFO] Running functional test...")
        edge_ip = self._get_ip('edge')
        if not edge_ip:
            print("[FAIL] Could not find Edge node IP. Is the cluster deployed?")
            return
        
        cmd = f"ssh -o StrictHostKeyChecking=no -i ~/.ssh/gcp_spark ansible@{edge_ip} 'cd ~/spark-jobs && ./run_wordcount.sh'"
        subprocess.run(cmd, shell=True)

    def do_ssh(self, arg):
        """
        SSH into a specific node.
        
        Usage: ssh [target]
        
        Parameters:
        - target: 'master', 'edge', 'worker-1', 'worker-2', etc. (Default: master)
        
        Example:
        - ssh edge
        - ssh worker-1
        """
        target = arg.strip()
        if not target:
            target = 'master'
        
        ip = self._get_ip(target)
        if ip:
            print(f"[INFO] Connecting to {target} ({ip})...")
            subprocess.run(f"ssh -o StrictHostKeyChecking=no -i ~/.ssh/gcp_spark ansible@{ip}", shell=True)
        else:
            print(f"[FAIL] Unknown host: {target}")

    def do_status(self, arg):
        """Show cluster status and architecture."""
        if not os.path.exists(self.inventory_file):
            print("[FAIL] Inventory not found. Cluster might not be deployed.")
            return

        with open(self.inventory_file) as f:
            data = yaml.safe_load(f)

        master_ip = data['all']['children']['master']['hosts']['spark-master']['ansible_host']
        edge_ip = data['all']['children']['edge']['hosts']['spark-edge']['ansible_host']
        workers = data['all']['children']['workers']['hosts']

        print("\n[Cluster Architecture]")
        print("========================")
        print(f"      [ Internet ]")
        print(f"           |")
        print(f"      [ Firewall ]")
        print(f"           |")
        print(f"           v")
        print(f" +-----------------------+       +----------------------+")
        print(f" |      EDGE NODE        | ----> |     MASTER NODE      |")
        print(f" | IP: {edge_ip:<15}   |       | IP: {master_ip:<16} |")
        print(f" | (Client Gateway)      |       | (Resource Manager)   |")
        print(f" +-----------------------+       | (Prometheus/Grafana) |")
        print(f"                                 +----------------------+")
        print(f"                                            |")
        print(f"                                            v")
        print(f"                             +------------------------------+")
        for name, info in workers.items():
            print(f"                             | {name:<20} |")
            print(f"                             | IP: {info['ansible_host']:<16}     |")
        print(f"                             +------------------------------+")

        print("\n[Services]")
        print(f" - Spark Master UI:  http://{master_ip}:8080")
        print(f" - Grafana:          http://{master_ip}:3000 (admin/admin)")
        print(f" - Prometheus:       http://{master_ip}:9090")
        print(f" - Spark History:    http://{master_ip}:18080 (if configured)")

    def _get_ip(self, host_alias):
        if not os.path.exists(self.inventory_file):
            return None
        with open(self.inventory_file) as f:
            data = yaml.safe_load(f)
        
        if host_alias == 'master':
            return data['all']['children']['master']['hosts']['spark-master']['ansible_host']
        elif host_alias == 'edge':
            return data['all']['children']['edge']['hosts']['spark-edge']['ansible_host']
        elif host_alias == 'worker-1':
             return data['all']['children']['workers']['hosts']['spark-worker-1']['ansible_host']
        elif 'worker' in host_alias:
             # Try to find exact match or dynamic search
             if host_alias in data['all']['children']['workers']['hosts']:
                 return data['all']['children']['workers']['hosts'][host_alias]['ansible_host']
             # Simple alias logic
             for w in data['all']['children']['workers']['hosts']:
                 if host_alias in w:
                      return data['all']['children']['workers']['hosts'][w]['ansible_host']
        return None

    def do_exit(self, arg):
        """Exit the shell."""
        print("Bye!")
        return True

if __name__ == '__main__':
    if len(sys.argv) > 1:
        SparkClusterCLI().onecmd(' '.join(sys.argv[1:]))
    else:
        SparkClusterCLI().cmdloop()
