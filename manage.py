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
        """
        args = shlex.split(arg)
        if not args:
            print("\t[FAIL] Usage: scale <num_workers>")
            return
        
        try:
            target_workers = int(args[0])
        except ValueError:
            print("\t[FAIL] Worker count must be a number")
            return
        
        if target_workers < 1:
            print("\t[FAIL] Must have at least 1 worker")
            return
        
        if target_workers > self.MAX_WORKERS:
            print(f"\t[WARN] Limiting to {self.MAX_WORKERS} workers (free trial safety)")
            target_workers = self.MAX_WORKERS
        
        # Check if cluster exists
        if not os.path.exists(self.inventory_file):
            print("\t[FAIL] No cluster found. Deploy first with 'deploy'")
            return
        
        # Get current worker count
        current_workers = self._get_current_worker_count()
        if current_workers is None:
            print("\t[WARN] Could not determine current worker count")
            current_workers = "?"
        
        print(f"\t[INFO] Current workers: {current_workers}")
        print(f"\t[INFO] Target workers:  {target_workers}")
        
        if current_workers == target_workers:
            print("\t[INFO] Cluster already at target size. Nothing to do.")
            return
        
        action = "Scaling up" if (isinstance(current_workers, int) and target_workers > current_workers) else "Scaling"
        print(f"\t[INFO] {action} to {target_workers} workers...")
        
        # Trigger deployment with new worker count
        self.do_deploy(f"-w {target_workers}")
        
        # Verify
        print("\t[INFO] Verifying new worker count...")
        import time
        time.sleep(2)  # Give workers time to register
        new_count = self._get_current_worker_count()
        if new_count == target_workers:
            print(f"\t[SUCCESS] Cluster scaled to {target_workers} workers!")
        else:
            print(f"\t[WARN] Expected {target_workers} workers, found {new_count}")
            print("\t       Check 'status' for details")

    def _get_current_worker_count(self):
        """Helper to count workers in inventory."""
        if not os.path.exists(self.inventory_file):
            return None
        try:
            data = self._load_inventory()
            if not data:
                return None
            workers_group = self._get_inventory_group(data, 'workers')
            if not workers_group or 'hosts' not in workers_group:
                return None
            return len(workers_group['hosts'])
        except Exception:
            return None

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
        print(f"\t│  HDFS NameNode UI   http://{master_ip}:9870{' ' * (30 - len(master_ip))}      │")
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

    def _get_internal_ip(self, host_alias):
        """Get internal IP for VPC communication (HDFS, Spark, etc)."""
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
                return master_group['hosts']['spark-master'].get('internal_ip')
            elif host_alias == 'edge':
                return edge_group['hosts']['spark-edge'].get('internal_ip')
            elif host_alias == 'worker-1':
                 return workers_group['hosts']['spark-worker-1'].get('internal_ip')
            elif 'worker' in host_alias:
                 if host_alias in workers_group['hosts']:
                     return workers_group['hosts'][host_alias].get('internal_ip')
                 for w in workers_group['hosts']:
                     if host_alias in w:
                          return workers_group['hosts'][w].get('internal_ip')
        except Exception:
            return None
        return None

    def do_run(self, arg):
        """
        Run a Spark job on the cluster.
        
        Usage: run [TARGET] [ARGUMENTS...]
        
        Examples:
        - run                                    # Show examples menu
        - run wordcount                          # Built-in WordCount example
        - run pi 1000                            # Calculate Pi with 1000 iterations
        - run code.py                            # Run script (no arguments)
        - run code.py arg1 arg2                  # Run script with arguments
        - run code.py /user/spark/data/file.csv  # Pass HDFS path as argument
        - run wrapper.sh --arg1 v1 --arg2 v2     # Execute custom wrapper script
        
        Note: Use 'upload' command to upload data files to HDFS first.
        """
        args = shlex.split(arg)
        
        # No args? Show examples menu
        if not args:
            self._show_examples_menu()
            return
        
        target = args[0]
        
        # Check for built-in examples (keywords)
        if target in ['wordcount', 'pi', 'examples']:
            self._run_builtin_example(target, args[1:])
            return
        
        # Detect file type
        if not os.path.exists(target):
            print(f"\t[FAIL] File not found: {target}")
            print(f"\t       Try 'run examples' to see built-in options")
            return
        
        # Route based on file extension
        if target.endswith('.sh'):
            self._run_wrapper_script(target, args[1:])
        elif target.endswith('.py'):
            self._run_pyspark_script(target, args[1:])
        else:
            print(f"\t[FAIL] Unsupported file type: {target}")
            print(f"\t       Supported: .py (PySpark), .sh (Wrapper scripts)")

    def _show_examples_menu(self):
        """Display available built-in examples."""
        print("\n\t╔═══════════════════════════════════════════════════════════╗")
        print("\t║               Built-in Spark Examples                    ║")
        print("\t╚═══════════════════════════════════════════════════════════╝")
        print("\t")
        print("\t  1. wordcount              - Classic word frequency counter")
        print("\t                               (Uses sample data in HDFS)")
        print("\t")
        print("\t  2. pi [iterations]        - Monte Carlo Pi estimation")
        print("\t                               (Default: 1000 iterations)")
        print("\t")
        print("\t  3. examples               - Show this menu")
        print("\t")
        print("\t╔═══════════════════════════════════════════════════════════╗")
        print("\t║  Usage: run <example_name> [args]                         ║")
        print("\t║                                                           ║")
        print("\t║  Example: run wordcount                                   ║")
        print("\t║           run pi 10000                                    ║")
        print("\t╚═══════════════════════════════════════════════════════════╝")
        print()

    def _run_builtin_example(self, example, args):
        """Execute built-in example jobs."""
        if example == 'examples':
            self._show_examples_menu()
        elif example == 'wordcount':
            print("\t[INFO] Running built-in WordCount example...")
            self._run_default_wordcount()
        elif example == 'pi':
            iterations = args[0] if args else "1000"
            print(f"\t[INFO] Running Monte Carlo Pi estimation ({iterations} iterations)...")
            self._run_pi_example(iterations)

    def _run_pi_example(self, iterations):
        """Run Monte Carlo Pi estimation example."""
        edge_ip = self._get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Edge node IP not found.")
            return
        
        master_internal_ip = self._get_internal_ip('master')
        if not master_internal_ip:
            print("\t[FAIL] Could not determine master internal IP.")
            return
        
        # Create Pi estimation script inline
        pi_script = f'''
from pyspark.sql import SparkSession
import sys
import random

spark = SparkSession.builder.appName("MonteCarloPi").getOrCreate()
sc = spark.sparkContext

iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 1000

def sample(_):
    x, y = random.random(), random.random()
    return 1 if x*x + y*y <= 1 else 0

count = sc.parallelize(range(iterations)).map(sample).reduce(lambda a, b: a + b)
pi_estimate = 4.0 * count / iterations

print(f"\\nπ ≈ {{pi_estimate}}")
print(f"Error: {{abs(pi_estimate - 3.14159265359):.6f}}\\n")

spark.stop()
'''
        
        # Write script to remote
        cmd = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.SSH_KEY_PATH} ansible@{edge_ip} 'cat > /tmp/pi_example.py << \"EOFSCRIPT\"\n{pi_script}\nEOFSCRIPT'"
        subprocess.call(cmd, shell=True)
        
        # Run it
        run_cmd = f"/home/ansible/spark-jobs/submit_job.sh /tmp/pi_example.py {iterations}"
        subprocess.call(f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.SSH_KEY_PATH} ansible@{edge_ip} '{run_cmd}'", shell=True)

    def _run_wrapper_script(self, script_path, remaining_args):
        """Upload and execute a custom .sh wrapper script."""
        edge_ip = self._get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Edge node IP not found.")
            return
        
        print(f"\t[INFO] Uploading wrapper script '{os.path.basename(script_path)}'...")
        script_name = os.path.basename(script_path)
        remote_path = f"/home/ansible/spark-jobs/user-scripts/{script_name}"
        
        # Upload
        subprocess.call(f"ssh -o StrictHostKeyChecking=no -i {self.SSH_KEY_PATH} ansible@{edge_ip} 'mkdir -p /home/ansible/spark-jobs/user-scripts'", shell=True, stdout=subprocess.DEVNULL)
        subprocess.call(f"scp -q -o StrictHostKeyChecking=no -i {self.SSH_KEY_PATH} {script_path} ansible@{edge_ip}:{remote_path}", shell=True)
        
        # Make executable
        subprocess.call(f"ssh -o StrictHostKeyChecking=no -i {self.SSH_KEY_PATH} ansible@{edge_ip} 'chmod +x {remote_path}'", shell=True, stdout=subprocess.DEVNULL)
        
        # Execute with all arguments
        print(f"\t[INFO] Executing wrapper script...")
        args_str = " ".join([shlex.quote(a) for a in remaining_args])
        ret = subprocess.call(f"ssh -o StrictHostKeyChecking=no -i {self.SSH_KEY_PATH} ansible@{edge_ip} '{remote_path} {args_str}'", shell=True)
        
        if ret != 0:
            print(f"\t[FAIL] Wrapper script failed (Exit Code: {ret}).")

    def _run_pyspark_script(self, script_path, remaining_args):
        """
        Simple PySpark script execution.
        
        Uploads the script and passes all arguments directly to it.
        No auto-upload, no smart detection - user controls everything.
        """
        edge_ip = self._get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Edge node IP not found.")
            return
        
        # Upload script
        print(f"\t[INFO] Uploading script '{os.path.basename(script_path)}'...")
        script_name = os.path.basename(script_path)
        remote_script_dir = "spark-jobs/user-scripts"
        remote_script_path = f"{remote_script_dir}/{script_name}"
        
        subprocess.call(f"ssh -o StrictHostKeyChecking=no -i {self.SSH_KEY_PATH} ansible@{edge_ip} 'mkdir -p {remote_script_dir}'", shell=True, stdout=subprocess.DEVNULL)
        subprocess.call(f"scp -q -o StrictHostKeyChecking=no -i {self.SSH_KEY_PATH} {script_path} ansible@{edge_ip}:{remote_script_path}", shell=True)
        
        # Pass all arguments directly to script (no processing)
        args_str = " ".join([shlex.quote(a) for a in remaining_args])
        
        # Submit job
        print(f"\t[INFO] Submitting job...")
        submit_wrapper = "/home/ansible/spark-jobs/submit_job.sh"
        cmd = f"ssh -o StrictHostKeyChecking=no -i {self.SSH_KEY_PATH} ansible@{edge_ip} '{submit_wrapper} {remote_script_path} {args_str}'"
        
        ret = subprocess.call(cmd, shell=True)
        if ret != 0:
            print(f"\t[FAIL] Job submission failed (Exit Code: {ret}).")

    def _run_default_wordcount(self):
        """Helper to run the default wordcount test (legacy behavior)."""
        edge_ip = self._get_ip('edge')
        if not edge_ip: return
        
        # Use default HDFS sample with INTERNAL IP
        master_internal_ip = self._get_internal_ip('master')
        if not master_internal_ip:
            print("\t[FAIL] Could not determine master internal IP.")
            return
        target_path = f"hdfs://{master_internal_ip}:9000/user/spark/data/sample.txt"
        
        run_cmd = f"/home/ansible/spark-jobs/run_wordcount.sh '{target_path}'"
        subprocess.call(f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.SSH_KEY_PATH} ansible@{edge_ip} \"{run_cmd}\"", shell=True)

    def do_upload(self, arg):
        """
        Upload a local file to HDFS.
        
        Usage: upload <local_file> [hdfs_path]
        
        Examples:
        - upload data.csv                          (uploads to /user/spark/data/uploads/)
        - upload data.csv /user/spark/custom/      (uploads to custom HDFS path)
        """
        args = shlex.split(arg)
        if not args:
            print("\t[FAIL] Please specify a file to upload.")
            print("\tUsage: upload <local_file> [hdfs_path]")
            return
        
        local_file = args[0]
        if not os.path.exists(local_file):
            print(f"\t[FAIL] Local file not found: {local_file}")
            return
        
        # Default HDFS upload path
        hdfs_path = args[1] if len(args) > 1 else "/user/spark/data/uploads/"
        filename = os.path.basename(local_file)
        
        edge_ip = self._get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Could not find edge node IP.")
            return
        
        print(f"\t[INFO] Uploading {local_file} to HDFS...")
        print(f"\t       Target: {hdfs_path}")
        
        # Step 1: SCP file to edge node
        tmp_path = f"/tmp/{filename}"
        scp_cmd = f"scp -i {self.SSH_KEY_PATH} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no {local_file} ansible@{edge_ip}:{tmp_path}"
        
        ret = subprocess.call(scp_cmd, shell=True)
        if ret != 0:
            print(f"\t[FAIL] Failed to upload file to edge node.")
            return
        
        # Step 2: Put file into HDFS from edge node
        hdfs_cmd = f"ssh -i {self.SSH_KEY_PATH} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ansible@{edge_ip} '/opt/hadoop/current/bin/hdfs dfs -put -f {tmp_path} {hdfs_path}'"
        
        ret = subprocess.call(hdfs_cmd, shell=True)
        if ret != 0:
            print(f"\t[FAIL] Failed to put file into HDFS.")
            return
        
        # Step 3: Clean up tmp file
        cleanup_cmd = f"ssh -i {self.SSH_KEY_PATH} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ansible@{edge_ip} 'rm -f {tmp_path}'"
        subprocess.call(cleanup_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print(f"\t[SUCCESS] File uploaded to HDFS: {hdfs_path}{filename}")

    def do_download(self, arg):
        """
        Download a file/directory from HDFS to local machine.
        
        Usage: download <hdfs_path> [local_path]
        
        Examples:
        - download /user/spark/results/job-123             (downloads to ./results/)
        - download /user/spark/results/job-123 ./my-data/  (downloads to custom local path)
        """
        args = shlex.split(arg)
        if not args:
            print("\t[FAIL] Please specify an HDFS path to download.")
            print("\tUsage: download <hdfs_path> [local_path]")
            return
        
        hdfs_path = args[0]
        local_path = args[1] if len(args) > 1 else "./results/"
        
        # Create local directory if it doesn't exist
        os.makedirs(local_path, exist_ok=True)
        
        edge_ip = self._get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Could not find edge node IP.")
            return
        
        print(f"\t[INFO] Downloading from HDFS...")
        print(f"\t       Source: {hdfs_path}")
        print(f"\t       Destination: {local_path}")
        
        # Step 1: Get from HDFS to edge node tmp
        basename = os.path.basename(hdfs_path.rstrip('/'))
        tmp_path = f"/tmp/{basename}"
        
        hdfs_cmd = f"ssh -i {self.SSH_KEY_PATH} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ansible@{edge_ip} '/opt/hadoop/current/bin/hdfs dfs -get {hdfs_path} {tmp_path}'"
        
        ret = subprocess.call(hdfs_cmd, shell=True)
        if ret != 0:
            print(f"\t[FAIL] Failed to get file from HDFS.")
            return
        
        # Step 2: SCP from edge to local
        scp_cmd = f"scp -i {self.SSH_KEY_PATH} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -r ansible@{edge_ip}:{tmp_path} {local_path}"
        
        ret = subprocess.call(scp_cmd, shell=True)
        if ret != 0:
            print(f"\t[FAIL] Failed to download file from edge node.")
            return
        
        # Step 3: Clean up tmp
        cleanup_cmd = f"ssh -i {self.SSH_KEY_PATH} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ansible@{edge_ip} 'rm -rf {tmp_path}'"
        subprocess.call(cleanup_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print(f"\t[SUCCESS] Downloaded to: {local_path}{basename}")

    def do_hdfs(self, arg):
        """
        HDFS Management Shell.
        
        Usage: 
        - hdfs              (Enter interactive HDFS shell with aliases like ls, put, get)
        - hdfs <command>    (Execute single HDFS command, e.g., hdfs ls /)
        """
        edge_ip = self._get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Could not find edge node IP.")
            return

        # Interactive Mode
        if not arg or arg.strip() == "":
            print("\t[INFO] Entering interactive HDFS shell...")
            print("\t       Aliases: ls, put, get, rm, cat, mkdir, du, df")
            print("\t       Type 'exit' or Ctrl+D to quit.")
            
            # Create remote .hdfs_rc file
            # WE USE ABSOLUTE PATHS because non-login shells might not have HADOOP_HOME in PATH
            rc_content = r"""
HDFS_BIN=/opt/hadoop/current/bin/hdfs
alias ls='$HDFS_BIN dfs -ls'
alias put='$HDFS_BIN dfs -put'
alias get='$HDFS_BIN dfs -get'
alias rm='$HDFS_BIN dfs -rm'
alias mkdir='$HDFS_BIN dfs -mkdir'
alias cat='$HDFS_BIN dfs -cat'
alias du='$HDFS_BIN dfs -du -h'
alias df='$HDFS_BIN dfs -df -h'
alias chown='$HDFS_BIN dfs -chown'
alias chmod='$HDFS_BIN dfs -chmod'
alias mv='$HDFS_BIN dfs -mv'
alias cp='$HDFS_BIN dfs -cp'
# Custom prompt
export PS1="\[\033[01;32m\][hdfs-shell]\[\033[00m\] \u@\h:\w$ "
"""
            try:
                with open("hdfs_rc.tmp", "w") as f:
                    f.write(rc_content)
                
                # Check for existing ControlMaster socket or just run fast SCP
                # We use -C (compression) and standard options
                ssh_opts = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPersist=600s -o ControlPath=~/.ssh/ansible-%r@%h:%p"
                
                subprocess.call(f"scp -q {ssh_opts} -i {self.SSH_KEY_PATH} hdfs_rc.tmp ansible@{edge_ip}:.hdfs_rc", shell=True)
                os.remove("hdfs_rc.tmp")
                
                # SSH with RC file
                subprocess.call(f"ssh -t {ssh_opts} -i {self.SSH_KEY_PATH} ansible@{edge_ip} 'bash --rcfile .hdfs_rc'", shell=True)
                
            except Exception as e:
                print(f"\t[FAIL] Error starting shell: {e}")
            return

        # Single Command Mode
        # Auto-fix: Prepend dash if command is a known HDFS op and missing it
        tokens = arg.split()
        cmd = tokens[0]
        known_ops = ['ls', 'du', 'df', 'put', 'get', 'rm', 'mkdir', 'cat', 'mv', 'cp', 'chmod', 'chown', 'tail', 'head', 'text', 'touchz']
        
        if cmd in known_ops:
            tokens[0] = f"-{cmd}"
            arg = " ".join(tokens)
            
        print(f"\t[EXEC] hdfs dfs {arg}")
        
        # Enable ControlMaster for speedier repeated commands
        ssh_opts = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPersist=600s -o ControlPath=~/.ssh/ansible-%r@%h:%p"
        
        hdfs_cmd = f"ssh -i {self.SSH_KEY_PATH} {ssh_opts} ansible@{edge_ip} '/opt/hadoop/current/bin/hdfs dfs {arg}'"
        subprocess.call(hdfs_cmd, shell=True)

    def do_results(self, arg):
        """
        List Spark job results stored in HDFS.
        
        Usage: results [limit]
        
        Examples:
        - results       (show last 10 jobs)
        - results 20    (show last 20 jobs)
        """
        args = shlex.split(arg)
        limit = int(args[0]) if args and args[0].isdigit() else 10
        
        edge_ip = self._get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Could not find edge node IP.")
            return
        
        print(f"\t[INFO] Fetching last {limit} job results from HDFS...")
        
        # List results directory
        hdfs_cmd = f"ssh -i {self.SSH_KEY_PATH} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ansible@{edge_ip} '/opt/hadoop/current/bin/hdfs dfs -ls /user/spark/results/ 2>/dev/null | tail -{limit}'"
        
        ret = subprocess.call(hdfs_cmd, shell=True)
        if ret != 0:
            print(f"\t[WARN] No results found or HDFS error.")

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
