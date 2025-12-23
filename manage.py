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

    def do_clear(self, arg):
        """Clear the terminal."""
        os.system('clear')

    def do_deploy(self, arg):
        """
        Deploy and configure the cluster.
        
        Usage: deploy
        
        Steps:
        1. Runs 'terraform apply' to provision VMs (Master, Workers, Edge).
        2. Runs 'update_inventory.sh' to generate Ansible hosts file.
        3. Runs 'ansible-playbook' to install Java, Spark, and Monitoring.
        """
        print("\t[INFO] Starting deployment...")
        # 1. Terraform Apply
        print("\n\t[1/3] Provisioning Infrastructure with Terraform...")
        try:
            subprocess.run(['terraform', 'apply', '-auto-approve'], cwd='terraform', check=True)
        except subprocess.CalledProcessError:
            print("\t[FAIL] Terraform failed.")
            return

        # 2. Update Inventory
        print("\n\t[2/3] Updating Ansible Inventory...")
        try:
            subprocess.run(['./update_inventory.sh'], cwd='ansible', check=True)
        except subprocess.CalledProcessError:
            print("\t[FAIL] Inventory update failed.")
            return

        # 3. Ansible Configuration
        print("\n\t[3/3] Configuring Cluster with Ansible...")
        try:
            env = os.environ.copy()
            env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
            subprocess.run(['ansible-playbook', '-i', 'inventory/hosts.yml', 'playbooks/site.yml'], 
                           cwd='ansible', env=env, check=True)
        except subprocess.CalledProcessError:
            print("\t[FAIL] Ansible configuration failed.")
            return
        
        print("\n\t[SUCCESS] Deployment Complete!")

    def do_destroy(self, arg):
        """
        Destroy the cluster infrastructure.
        
        Usage: destroy
        
        Warning: This will permanently delete all GCP resources (VMs, Network, Firewall).
        """
        confirm = input("\t[WARN] Are you sure you want to DESTROY the cluster? (y/N): ")
        if confirm.lower() == 'y':
            print("\t[INFO] Destroying infrastructure...")
            subprocess.run(['terraform', 'destroy', '-auto-approve'], cwd='terraform')
            print("\t[SUCCESS] Destruction Complete.")
        else:
            print("\tHere is your cluster back")

    def do_test(self, arg):
        """
        Run the functional test.
        
        Usage: test
        
        Actions:
        - Connects to the Edge node via SSH.
        - Submits a sample Spark job (WordCount) to the cluster.
        - Verifies that the job completes and produces output.
        """
        print("\t[INFO] Running functional test...")
        edge_ip = self._get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Could not find Edge node IP. Is the cluster deployed?")
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
            print(f"\t[INFO] Connecting to {target} ({ip})...")
            subprocess.run(f"ssh -o StrictHostKeyChecking=no -i ~/.ssh/gcp_spark ansible@{ip}", shell=True)
        else:
            print(f"\t[FAIL] Unknown host: {target}")

    def do_status(self, arg):
        """Show cluster status and architecture."""
        if not os.path.exists(self.inventory_file):
            print("\n\t[WARN] Inventory file not found.")
            print("\t       The cluster does not appear to be deployed.")
            print("\t       Run 'deploy' to provision the infrastructure.")
            return

        try:
            with open(self.inventory_file) as f:
                data = yaml.safe_load(f)
            
            if not data or 'all' not in data:
                 raise ValueError("Invalid inventory format")

            master_ip = data['all']['children']['master']['hosts']['spark-master']['ansible_host']
            edge_ip = data['all']['children']['edge']['hosts']['spark-edge']['ansible_host']
            workers = data['all']['children']['workers']['hosts']

        except Exception as e:
            print(f"\n\t[FAIL] Error reading inventory: {e}")
            print("\t       Try running 'deploy' to regenerate it.")
            return

        print("\n\t[Cluster Architecture]")
        print("\t========================")
        print(f"\t      [ Internet ]" )
        print(f"\t           |" )
        print(f"\t      [ Firewall ]" )
        print(f"\t           |" )
        print(f"\t           v" )
        print(f"\t +------------------------+       +-----------------------+")
        print(f"\t |       EDGE NODE        | ----> |      MASTER NODE      |")
        print(f"\t | IP: {edge_ip:<18} |       | IP: {master_ip:<17} |")
        print(f"\t | (Client Gateway)       |       | (Resource Manager)    |")
        print(f"\t +------------------------+       | (Prometheus/Grafana)  |")
        print(f"\t                                  +-----------------------+")
        print(f"\t                                             |")
        print(f"\t                                             v")
        print(f"\t                              +-------------------------------+")
        for name, info in workers.items():
            print(f"\t                              | {name:<29} |")
            print(f"\t                              | IP: {info['ansible_host']:<26} |")
            print(f"\t                              |_______________________________|")

        print("\n\t[Services]")
        print(f"\t - Spark Master UI:  http://{master_ip}:8080")
        print(f"\t - Grafana:          http://{master_ip}:3000 (admin/admin)")
        print(f"\t - Prometheus:       http://{master_ip}:9090")
        print(f"\t - Spark History:    http://{master_ip}:18080 (if configured)")

    def _get_ip(self, host_alias):
        if not os.path.exists(self.inventory_file):
            return None
        try:
            with open(self.inventory_file) as f:
                data = yaml.safe_load(f)
            
            if not data: return None

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
        except Exception:
            return None
        return None

    def do_exit(self, arg):
        """Exit the shell."""
        print("\tBye!")
        return True

if __name__ == '__main__':
    if len(sys.argv) > 1:
        SparkClusterCLI().onecmd(' '.join(sys.argv[1:]))
    else:
        SparkClusterCLI().cmdloop()
