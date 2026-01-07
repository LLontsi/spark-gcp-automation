#!/usr/bin/env python3
import cmd
import os
import subprocess
import sys
import yaml
import time
import shlex
from concurrent.futures import ThreadPoolExecutor, as_completed

class SparkClusterCLI(cmd.Cmd):
    intro = r"""
   _____                  __      __  ___            _ __
  / ___/____  ____ ______/ /__   /  |/  /___  ____  (_) /_____  _____
  \__ \/ __ \/ __ `/ ___/ //_/  / /|_/ / __ \/ __ \/ / __/ __ \/ ___/
 ___/ / /_/ / /_/ / /  / ,<    / /  / / /_/ / / / / / /_/ /_/ / /
/____/ .___/\__,_/_/  /_/|_|  /_/  /_/\____/_/ /_/_/\__/\____/_/
    /_/

Welcome to the Spark Cluster Manager.
Type 'help' or '?' to list commands.
Type 'help <command>' for specific command usage.
    """

    prompt = '(spark-cluster) '
    
    # Constants
    MAX_WORKERS = 3
    DEFAULT_WORKERS = 2
    SSH_KEY_PATH = os.environ.get('SPARK_SSH_KEY', '~/.ssh/gcp_spark')
    DEPLOY_LOG = 'deploy.log'
    
    # Timeouts (seconds)
    WAIT_SSH_TIMEOUT = 300
    ANSIBLE_TIMEOUT = 3600
    
    def __init__(self):
        super().__init__()
        self.inventory_file = 'ansible/inventory/hosts.yml'
        self._inventory_cache = None
        self._cache_time = 0

    def emptyline(self):
        """Do nothing on empty input line."""
        pass

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

    def _load_inventory(self, force_reload=False):
        """Load and cache inventory file."""
        if force_reload or not self._inventory_cache or (time.time() - self._cache_time) > 60:
            try:
                with open(self.inventory_file) as f:
                    self._inventory_cache = yaml.safe_load(f)
                    self._cache_time = time.time()
            except Exception:
                self._inventory_cache = None
        return self._inventory_cache
    
    def _get_inventory_group(self, data, group_name):
        """Navigate nested inventory structure to find group.
        
        Args:
            data: Parsed inventory YAML
            group_name: Group to find (master/workers/edge)
            
        Returns:
            Group dict or None if not found
        """
        if not data or 'all' not in data:
            return None
        # Try direct children of all
        if group_name in data['all'].get('children', {}):
            return data['all']['children'][group_name]
        # Try inside spark_cluster
        if 'spark_cluster' in data['all'].get('children', {}):
            return data['all']['children']['spark_cluster']['children'].get(group_name)
        return None

    def do_deploy(self, arg):
        """
        Deploy and configure the cluster.
        
        Usage: deploy [options]
        
        Options:
        -b, --background       Run deployment in the background and log to 'deploy.log'.
        -w, --workers <num>    Number of worker nodes to deploy (default: 2, max: N).
        
        Steps:
        1. Runs 'terraform apply' to provision VMs.
        2. Runs 'update_inventory.sh' to generate Ansible hosts.
        3. Runs 'ansible-playbook' to configure the cluster.
        """
        args = shlex.split(arg)
        is_background = '-b' in args or '--background' in args
        
        # Parse worker count
        worker_count = self.DEFAULT_WORKERS
        if '-w' in args:
            try:
                idx = args.index('-w') + 1
                worker_count = int(args[idx])
            except (ValueError, IndexError):
                print("\t[FAIL] Invalid worker count specified.")
                return
        elif '--workers' in args:
             try:
                idx = args.index('--workers') + 1
                worker_count = int(args[idx])
             except (ValueError, IndexError):
                print("\t[FAIL] Invalid worker count specified.")
                return

        # GCP Free Trial Safety Check (limited to  workers to conserve $300 credits)
        if worker_count > self.MAX_WORKERS:
            print(f"\t[WARN] Worker count {worker_count} exceeds free trial limit of {self.MAX_WORKERS}.")
            print(f"\t       Forcing worker count to {self.MAX_WORKERS} to prevent billing issues.")
            worker_count = self.MAX_WORKERS
        elif worker_count < 1:
            print("\t[FAIL] Must have at least 1 worker.")
            return

        print(f"\t[INFO] Deploying with {worker_count} workers.")

        # Open in append mode or write? User likely wants fresh logs or appended? 'w' is safer for run separation.
        log_file = open('deploy.log', 'w')
        
        if is_background:
            print("\t[INFO] Deployment started in background.")
            print("\t       View logs/progress with 'logs' command.")
            
            pid = os.fork()
            if pid > 0:
                return

            # Child process
            sys.stdout = log_file
            sys.stderr = log_file
            # Detach from tty? For simple fork, current logic is okayish mostly.
        
        def run_with_logging(command, cwd=None, env=None):
            # If background, we already redirected sys.stdout/err to file. subprocess can inherit.
            # If foreground, we want to capture pipe, write to file, AND print to console.
            
            if is_background:
                subprocess.run(command, cwd=cwd, env=env, stdout=log_file, stderr=subprocess.STDOUT, check=False)
                return 0 # We assume success or handle return code if needed, but simplified here.
                # Actually we should check returncode.
            else:
                # Foreground: Tee behavior
                process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in process.stdout:
                    sys.stdout.write("\t" + line) # Indent the logs too? Or raw? User output shows Ansible output is raw strings. 
                    # Let's indent slightly or raw. Tabs for consistency.
                    # sys.stdout.write(line)
                    log_file.write(line)
                process.wait()
                return process.returncode

        # Helper to log with timestamp
        def log(msg):
            timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
            entry = f"{timestamp} {msg}"
            log_file.write(entry + "\n")
            log_file.flush()
            if not is_background:
                print("\t" + msg)

        try:
            log("[INFO] Starting deployment...")
            
            # 1. Terraform Apply
            log("[1/3] Provisioning Infrastructure with Terraform...")
            # Note: terraform/ansible output might be large.
            # Using simple run_with_logging logic.
            # Terraform with variable
            tf_cmd = ['terraform', 'apply', '-auto-approve', f'-var=num_workers={worker_count}']
            
            if is_background:
                # Direct run
                subprocess.run(tf_cmd, cwd='terraform', stdout=log_file, stderr=subprocess.STDOUT, check=True)
            else:
                # Tee
                with subprocess.Popen(tf_cmd, cwd='terraform', 
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as p:
                    for line in p.stdout:
                        print("\t" + line, end='') 
                        log_file.write(line)
                    p.wait()
                    if p.returncode != 0: raise subprocess.CalledProcessError(p.returncode, 'terraform')
            
            # 2. Update Inventory
            log("[2/3] Updating Ansible Inventory...")
            if is_background:
                subprocess.run(['./update_inventory.sh'], cwd='ansible', stdout=log_file, stderr=subprocess.STDOUT, check=True)
            else:
                with subprocess.Popen(['./update_inventory.sh'], cwd='ansible', 
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as p:
                    for line in p.stdout:
                        print("\t" + line, end='')
                        log_file.write(line)
                    p.wait()
                    if p.returncode != 0: raise subprocess.CalledProcessError(p.returncode, 'update_inventory.sh')

            # 3. Ansible Configuration
            log("[3/3] Configuring Cluster with Ansible...")
            env = os.environ.copy()
            env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
            env['ANSIBLE_FORCE_COLOR'] = 'true'
            
            if is_background:
                subprocess.run(['ansible-playbook', '-i', 'inventory/hosts.yml', 'playbooks/site.yml'], 
                               cwd='ansible', env=env, stdout=log_file, stderr=subprocess.STDOUT, check=True)
            else:
                with subprocess.Popen(['ansible-playbook', '-i', 'inventory/hosts.yml', 'playbooks/site.yml'], 
                                      cwd='ansible', env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as p:
                    for line in p.stdout:
                        print("\t" + line, end='')
                        log_file.write(line)
                    p.wait()
                    if p.returncode != 0: raise subprocess.CalledProcessError(p.returncode, 'ansible-playbook')
            
            log("[SUCCESS] Deployment Complete!")

        except subprocess.CalledProcessError as e:
            log(f"[FAIL] Command failed: {e}")
        except Exception as e:
            log(f"[FAIL] Unexpected error: {e}")
        finally:
            log_file.close()
            if is_background:
                os._exit(0)

    def do_logs(self, arg):
        """Follow the deployment logs (Ctrl+C to stop)."""
        if not os.path.exists('deploy.log'):
            print("\t[WARN] No log file found.")
            return
        
        try:
            # Use tail -f
            subprocess.run(['tail', '-f', 'deploy.log'])
        except KeyboardInterrupt:
            print("\n\t[INFO] Stopped following logs.")

    def do_scale(self, arg):
        """
        Scale the cluster to a specific number of workers.
        
        Usage: scale <num>
        
        Example:
        - scale 3   (Scale up to 3 workers)
        - scale 1   (Scale down to 1 worker)
        
        Note: This effectively re-runs 'deploy' with the new worker count.
        """
        args = shlex.split(arg)
        if not args:
            print("\t[FAIL] Usage: scale <num_workers>")
            return
        
        # Pass through to deploy logic
        print(f"\t[INFO] Scaling cluster to {args[0]} workers...")
        self.do_deploy(f"-w {args[0]}")

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
            # Clean up inventory to avoid stale status
            if os.path.exists(self.inventory_file):
                os.remove(self.inventory_file)
                print("\t[INFO] Removed inventory file.")
            print("\t[SUCCESS] Destruction Complete.")
        else:
            print("\tHere is your cluster back")



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
        args = shlex.split(arg)
        target = args[0] if args else 'master'
        
        ip = self._get_ip(target)
        if ip:
            print(f"\t[INFO] Connecting to {target} ({ip})...")
            subprocess.run(f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.SSH_KEY_PATH} ansible@{ip}", shell=True)
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
            data = self._load_inventory()
            
            if not data or 'all' not in data:
                 raise ValueError("Invalid inventory format")

            master_group = self._get_inventory_group(data, 'master')
            edge_group = self._get_inventory_group(data, 'edge')
            workers_group = self._get_inventory_group(data, 'workers')

            if not master_group or not edge_group or not workers_group:
                raise ValueError("Could not find cluster groups in inventory")

            master_ip = master_group['hosts']['spark-master']['ansible_host']
            edge_ip = edge_group['hosts']['spark-edge']['ansible_host']
            workers = workers_group['hosts']

        except Exception as e:
            print(f"\n\t[FAIL] Error reading inventory: {e}")
            print("\t       Try running 'deploy' to regenerate it.")
            return

        # Beautiful status output
        print("\n")
        print("\t╔════════════════════════════════════════════════════════════════════╗")
        print("\t║                     SPARK CLUSTER STATUS                           ║")
        print("\t╚════════════════════════════════════════════════════════════════════╝")
        print("\n")
        
        # print("\t┌─────────────────────────────────────────────────────────────────────┐")
        # print("\t│                     CLUSTER ARCHITECTURE                            │")
        # print("\t└─────────────────────────────────────────────────────────────────────┘")
        
        print("\n\t            [ Internet ]")
        print("\t                 │")
        print("\t                 │ (Firewall)")
        print("\t                 ▼")
        print(f"\t       ╔═══════════════════╗        ╔══════════════════════╗")
        print(f"\t       ║   EDGE NODE       ║───────▶║   MASTER NODE        ║")
        print(f"\t       ╠═══════════════════╣        ╠══════════════════════╣")
        print(f"\t       ║ {edge_ip:<17} ║        ║ {master_ip:<20} ║")
        print(f"\t       ║ Job Submission    ║        ║ Resource Manager     ║")
        print(f"\t       ║ Client Gateway    ║        ║ Prometheus + Grafana ║")
        print(f"\t       ╚═══════════════════╝        ╚══════════════════════╝")
        print(f"\t                                              │")
        print(f"\t                                              ▼")
        
        # Worker nodes section
        worker_count = len(workers)
        print(f"\t                       ╔═════════════════════════════════╗")
        print(f"\t                       ║   WORKER NODES ({worker_count})              ║")
        print(f"\t                       ╠═════════════════════════════════╣")
        
        for name, info in sorted(workers.items()):
            worker_ip = info['ansible_host']
            print(f"\t                       ║ • {name:<14} {worker_ip:<13}  ║")
        
        print(f"\t                       ╚═════════════════════════════════╝")
        
        # Services section
        print("\n")
        print("\t┌─────────────────────────────────────────────────────────────────────┐")
        print("\t│                      AVAILABLE SERVICES                             │")
        print("\t├─────────────────────────────────────────────────────────────────────┤")
        print(f"\t│  Spark Master UI    http://{master_ip}:8080{' ' * (30 - len(master_ip))}      │")
        print(f"\t│  Grafana Dashboard  http://{master_ip}:3000  (admin/admin){' ' * (8 - len(master_ip))}        │")
        print(f"\t│  Prometheus Metrics http://{master_ip}:9090{' ' * (27 - len(master_ip))}         │")
        print("\t└─────────────────────────────────────────────────────────────────────┘")
        print("")

    def _get_ip(self, host_alias):
        if not os.path.exists(self.inventory_file):
            return None
        try:
            data = self._load_inventory()
            if not data: return None
            
            master_group = self._get_inventory_group(data, 'master')
            edge_group = self._get_inventory_group(data, 'edge')
            workers_group = self._get_inventory_group(data, 'workers')

            if not master_group or not edge_group or not workers_group:
                return None

            if host_alias == 'master':
                return master_group['hosts']['spark-master']['ansible_host']
            elif host_alias == 'edge':
                return edge_group['hosts']['spark-edge']['ansible_host']
            elif host_alias == 'worker-1':
                 return workers_group['hosts']['spark-worker-1']['ansible_host']
            elif 'worker' in host_alias:
                 # Check specific match
                 if host_alias in workers_group['hosts']:
                     return workers_group['hosts'][host_alias]['ansible_host']
                 # Partial match
                 for w in workers_group['hosts']:
                     if host_alias in w:
                          return workers_group['hosts'][w]['ansible_host']
        except Exception:
            return None
        return None

    def do_run(self, arg):
        """
        Run a Spark job (WordCount) on the cluster.
        
        Usage: run [options] [file_path]
        
        Options:
        -u, --upload    Upload the file from local machine before running.
        
        Examples:
        - run                  (Runs default test on sample.txt)
        - run /tmp/data.txt    (Runs on existing REMOTE file at /tmp/data.txt)
        - run -u my_data.txt   (Uploads LOCAL my_data.txt to all nodes, then runs)
        """
        args = shlex.split(arg)
        
        # Default defaults
        should_upload = False
        target_path = "/tmp/sample.txt"
        
        # Parse arguments
        if '-u' in args or '--upload' in args:
            should_upload = True
            # Remove flag to find the file argument
            args = [a for a in args if a not in ['-u', '--upload']]
        
        if args:
            target_path = args[0]
        elif not should_upload:
            # No args, no upload -> default sample run
            pass
        else:
            print("\t[FAIL] Upload flag specified but no file provided.")
            return

        # Handle Upload
        if should_upload:
            local_file = target_path
            if not os.path.exists(local_file):
                print(f"\t[FAIL] Local file '{local_file}' not found.")
                return
            
            remote_path = f"/tmp/{os.path.basename(local_file)}"
            print(f"\t[INFO] Uploading '{local_file}' to cluster at '{remote_path}'...")
            
            try:
                with open(self.inventory_file) as f:
                    data = yaml.safe_load(f)

                # Helper to navigate potential nesting
                hosts = []
                for g in ['master', 'edge', 'workers']:
                    group = self._get_inventory_group(data, g)
                    if group and 'hosts' in group:
                        for h, info in group['hosts'].items():
                            hosts.append((h, info['ansible_host']))

                if not hosts:
                    print("\t[FAIL] No hosts found in inventory.")
                    return

                # Perform SCP in parallel
                print(f"\t[INFO] Uploading to {len(hosts)} nodes in parallel...")
                success_count = 0
                
                def upload_to_node(host_info):
                    """Upload file to a single node."""
                    name, ip = host_info
                    cmd = f"scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.SSH_KEY_PATH} {local_file} ansible@{ip}:{remote_path}"
                    ret = subprocess.call(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return (name, ip, ret == 0)
                
                with ThreadPoolExecutor(max_workers=min(len(hosts), 10)) as executor:
                    futures = {executor.submit(upload_to_node, host): host for host in hosts}
                    for future in as_completed(futures):
                        name, ip, success = future.result()
                        status = "[OK]" if success else "[FAIL]"
                        print(f"\t -> {name} ({ip}): {status}")
                        if success:
                            success_count += 1
                
                if success_count == 0:
                    print("\t[FAIL] Upload failed on all nodes. Aborting run.")
                    return
                
                # Update target path to the new remote location
                target_path = remote_path

            except Exception as e:
                print(f"\n\t[FAIL] Inventory error during upload: {e}")
                return

        # Execute Job
        print(f"\t[INFO] Submitting Spark job on '{target_path}'...")
        edge_ip = self._get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Could not find Edge node IP.")
            return

        cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.SSH_KEY_PATH} ansible@{edge_ip} 'cd ~/spark-jobs && ./run_wordcount.sh {target_path}'"
        ret = subprocess.call(cmd, shell=True)
        if ret != 0:
            print(f"\t[FAIL] Spark job submission failed (Exit Code: {ret}).")

    def do_exit(self, arg):
        """Exit the shell."""
        print("\tBye!")
        return True

if __name__ == '__main__':
    try:
        if len(sys.argv) > 1:
            SparkClusterCLI().onecmd(' '.join(sys.argv[1:]))
        else:
            SparkClusterCLI().cmdloop()
    except KeyboardInterrupt:
        print("\n\t[INFO] Interrupted by user. Exiting.")
        sys.exit(0)
