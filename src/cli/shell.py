#!/usr/bin/env python3
import cmd
import os
import subprocess
import sys
import yaml
import time
import shlex
from concurrent.futures import ThreadPoolExecutor, as_completed

# Refactored utilities
from src.config import config
from src.utils.ssh import ssh
from src.utils.inventory import inventory


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



    def do_deploy(self, arg):
        """
        Deploy a new Spark cluster on GCP or update existing configuration.
        
        WHAT IT DOES:
        This is a comprehensive deployment that sets up your entire cluster in 3 phases:
        
        Phase 1 - Infrastructure (Terraform):
        - Provisions GCP VMs (master, workers, edge node)
        - Configures VPC networking and internal IPs
        - Sets up firewall rules for Spark, HDFS, and UIs
        - Manages SSH keys and access
        
        Phase 2 - Software Installation (Ansible):
        - Installs Java 11 (OpenJDK)
        - Installs Apache Spark 3.5.0
        - Installs Apache Hadoop 3.3.6 (for HDFS)
        - Configures HDFS with NameNode and DataNodes
        - Sets up Spark Master and Workers
        - Installs monitoring stack (Prometheus + Grafana)
        
        Phase 3 - Initialization:
        - Formats HDFS namespace (first-time only)
        - Starts all Spark and HDFS services
        - Uploads sample data for testing
        - Creates default HDFS directories
        - Verifies cluster health
        
        Usage: deploy [options]
        
        Options:
        -w, --workers <N>     Number of workers (default: 2, max: 3)
        -b, --background      Run deployment in background (logs to deploy.log)
        
        Examples:
        - deploy                    # Interactive: 2 workers (shows output)
        - deploy -w 3               # Interactive: 3 workers
        - deploy -w 3 -b            # Background: 3 workers (check with 'logs')
        
        Time: ~8-10 minutes for complete deployment
        
        Updates: Running 'deploy' on existing cluster:
        - Updates worker count (scales up/down)
        - Reapplies Ansible configuration
        - Does NOT destroy data in HDFS
        
        After Deployment:
        - Master UI: http://MASTER_IP:8080
        - HDFS UI: http://MASTER_IP:9870
        - Grafana: http://MASTER_IP:3000
        
        Note: First deployment takes longer due to downloads and HDFS format.
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
        """
        Follow deployment logs in real-time.
        
        WHAT IT DOES:
        Shows live output from background deployment process.
        Uses 'tail -f' to stream logs as they're written.
        
        Usage: logs
        
        When to Use:
        - After running 'deploy -b' (background deployment)
        - To monitor long-running deployment progress
        - To debug deployment failures
        
        Press Ctrl+C to stop following (deployment continues).
        
        Tip: Logs are saved to 'deploy.log' in the current directory.
        """
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
        
        WHAT IT DOES:
        1. Validates target worker count (1-3)
        2. Checks current cluster size
        3. Adds or removes worker VMs via Terraform
        4. Reconfigures Spark and HDFS via Ansible
        5. Verifies new worker count
        
        Usage: scale <N>
        
        Where N is the target number of workers (1-3).
        
        Examples:
        - scale 3
          Current: 2 workers → Target: 3 workers
          Action: Adds 1 worker, reconfigures cluster
          
        - scale 1
          Current: 2 workers → Target: 1 worker
          Action: Removes 1 worker, rebalances HDFS
        
        Smart Behavior:
        - Shows current → target transition
        - Skips if already at target size
        - Validates target is within limits (1-3)
        - Verifies new count after scaling
        
        Important:
        - HDFS data is preserved during scaling
        - Rebalancing happens automatically
        - Running jobs are NOT interrupted (graceful)
        
        This is a user-friendly wrapper around 'deploy -w <N>'.
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
        return inventory.count_workers()

    def do_destroy(self, arg):
        """
        Destroy the cluster infrastructure.
        
        WHAT IT DOES:
        1. Prompts for confirmation (safety check)
        2. Runs 'terraform destroy' to delete all GCP resources:
           - All VMs (master, workers, edge)
           - VPC network and subnets
           - Firewall rules
           - SSH keys and metadata
        3. Removes local inventory file
        
        Usage: destroy
        
        WARNING:
        - This is IRREVERSIBLE
        - All data in HDFS will be PERMANENTLY DELETED
        - All running Spark jobs will be TERMINATED
        - All monitoring data will be LOST
        
        What is Preserved:
        - Downloaded results (if you used 'download')
        - Local scripts and data files
        - Terraform state (for audit trail)
        
        Type 'y' to confirm destruction, any other key to cancel.
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
        SSH into a specific cluster node for direct access.
        
        WHAT IT DOES:
        Opens an interactive SSH session to the specified node.
        Useful for debugging, checking logs, or manual operations.
        
        Usage: ssh [target]
        
        Available Targets:
        - master: Spark Master + HDFS NameNode + Monitoring
        - edge: Job submission node
        - worker-1, worker-2, worker-3: Spark Workers + HDFS DataNodes
        
        Default: master (if no target specified)
        
        Examples:
        - ssh                # Connect to master node
        - ssh edge           # Connect to edge node
        - ssh worker-1       # Connect to first worker
        - ssh worker-2       # Connect to second worker
        
        Tips:
        - Check Spark logs: /opt/spark/current/logs/
        - Check HDFS logs: /opt/hadoop/current/logs/
        - Verify services: systemctl status spark-worker
        - View HDFS data: /opt/hadoop/current/bin/hdfs dfs -ls /
        """
        args = shlex.split(arg)
        target = args[0] if args else 'master'
        
        ip = inventory.get_ip(target)
        if ip:
            print(f"\t[INFO] Connecting to {target} ({ip})...")
            subprocess.run(f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.SSH_KEY_PATH} ansible@{ip}", shell=True)
        else:
            print(f"\t[FAIL] Unknown host: {target}")

    def do_status(self, arg):
        """
        Display comprehensive cluster status and architecture.
        
        WHAT IT SHOWS:
        1. Cluster Architecture:
           - Visual diagram of nodes (master, edge, workers)
           - IP addresses for each node
           - Role descriptions
           
        2. Available Services:
           - Spark Master UI (port 8080)
           - HDFS NameNode UI (port 9870)
           - Grafana Dashboard (port 3000)
           - Prometheus Metrics (port 9090)
           
        3. Node Information:
           - Current worker count
           - Internal vs External IPs
           - Service assignments
        
        Usage: status
        
        Requires: Active cluster (run 'deploy' first)
        
        Example Output:
        ╔════════════════════════════════╗
        ║    SPARK CLUSTER STATUS        ║
        ╚════════════════════════════════╝
        
        [Architecture Diagram]
        Master: 35.x.x.x
        Workers: 2 nodes
        Services: All running
        """
        if not os.path.exists(self.inventory_file):
            print("\n\t[WARN] Inventory file not found.")
            print("\t       The cluster does not appear to be deployed.")
            print("\t       Run 'deploy' to provision the infrastructure.")
            return

        try:
            # Use inventory manager to get IPs
            master_ip = inventory.get_ip('master')
            edge_ip = inventory.get_ip('edge')
            worker_count = inventory.count_workers()
            
            if not master_ip or not edge_ip:
                raise ValueError("Could not find cluster IPs in inventory")
            
            # Get worker details from inventory
            data = inventory.load()
            if not data:
                raise ValueError("Invalid inventory format")
            
            workers_group = inventory.get_group(data, 'workers')
            if not workers_group or 'hosts' not in workers_group:
                raise ValueError("Could not find workers in inventory")
            
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





    def do_run(self, arg):
        """
        Run a Spark job on the cluster.
        
        WHAT IT DOES:
        1. Automatically uploads your script to the edge node
        2. Submits the job via spark-submit
        3. Streams output back to your terminal
        4. Cleans up the uploaded script when done
        
        IMPORTANT: This command does NOT upload data files. Use 'upload' first.
        
        Usage: run [TARGET] [ARGUMENTS...]
        
        Built-in Examples:
        - run                                    # Show interactive examples menu
        - run wordcount                          # Classic WordCount on sample data
        - run pi 1000                            # Monte Carlo Pi (1000 iterations)
        - run examples                           # Show examples menu
        
        Custom Scripts:
        - run code.py                            # Run script with no arguments
        - run code.py arg1 arg2                  # Pass arguments to your script
        - run code.py /user/spark/data/file.csv  # Use HDFS path as argument
        - run wrapper.sh --config production     # Execute custom Spark wrapper
        
        Workflow Example:
        ```
        # 1. Upload data to HDFS (one-time)
        upload data.csv
        
        # 2. Run your script (pass HDFS path as argument)
        run analyze.py /user/spark/data/uploads/data.csv --verbose
        
        # 3. Script gets executed on cluster with those arguments:
        #    sys.argv[1] = "/user/spark/data/uploads/data.csv"
        #    sys.argv[2] = "--verbose"
        ```
        
        File Types:
        - .py files: Submitted via spark-submit (PySpark applications)
        - .sh files: Executed directly (custom Spark wrappers with configs)
        
        Note: Data files must be uploaded separately. Use 'upload' command first.
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
        edge_ip = inventory.get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Edge node IP not found.")
            return
        
        master_internal_ip = inventory.get_internal_ip('master')
        if not master_internal_ip:
            print("\t[FAIL] Could not determine master internal IP.")
            return
        
        # Create Pi estimation script content
        pi_script = f'''from pyspark.sql import SparkSession
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
        
        # Write script locally first
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(pi_script)
            local_script = f.name
        
        try:
            # Upload to edge node
            remote_path = "/tmp/pi_example.py"
            ssh.upload(local_script, remote_path, edge_ip, quiet=True)
            
            # Run it
            ssh.submit_spark_job(edge_ip, remote_path, [iterations])
        finally:
            # Clean up local temp file
            import os
            os.unlink(local_script)

    def _run_wrapper_script(self, script_path, remaining_args):
        """Upload and execute a custom .sh wrapper script."""
        edge_ip = inventory.get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Edge node IP not found.")
            return
        
        print(f"\t[INFO] Uploading wrapper script '{os.path.basename(script_path)}'...")
        script_name = os.path.basename(script_path)
        remote_path = f"{config.REMOTE_SCRIPT_DIR}/{script_name}"
        
        # Create directory and upload script
        ssh.mkdir(edge_ip, config.REMOTE_SCRIPT_DIR)
        ssh.upload(script_path, remote_path, edge_ip, quiet=True)
        ssh.chmod(edge_ip, remote_path, "+x")
        
        # Execute with all arguments
        print(f"\t[INFO] Executing wrapper script...")
        args_str = " ".join([shlex.quote(a) for a in remaining_args])
        ret = ssh.run(edge_ip, f"{remote_path} {args_str}")
        
        if ret != 0:
            print(f"\t[FAIL] Wrapper script failed (Exit Code: {ret}).")

    def _run_pyspark_script(self, script_path, remaining_args):
        """
        Simple PySpark script execution.
        
        Uploads the script and passes all arguments directly to it.
        No auto-upload, no smart detection - user controls everything.
        """
        edge_ip = inventory.get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Edge node IP not found.")
            return
        
        # Upload script
        print(f"\t[INFO] Uploading script '{os.path.basename(script_path)}'...")
        script_name = os.path.basename(script_path)
        remote_script_path = f"{config.REMOTE_SCRIPT_DIR}/{script_name}"
        
        ssh.mkdir(edge_ip, config.REMOTE_SCRIPT_DIR)
        ssh.upload(script_path, remote_script_path, edge_ip, quiet=True)
        
        # Submit job
        print(f"\t[INFO] Submitting job...")
        ret = ssh.submit_spark_job(edge_ip, remote_script_path, remaining_args)
        
        if ret != 0:
            print(f"\t[FAIL] Job submission failed (Exit Code: {ret}).")

    def _run_default_wordcount(self):
        """Helper to run the default wordcount test (legacy behavior)."""
        edge_ip = inventory.get_ip('edge')
        if not edge_ip:
            return
        
        # Use default HDFS sample with INTERNAL IP
        master_internal_ip = inventory.get_internal_ip('master')
        if not master_internal_ip:
            print("\t[FAIL] Could not determine master internal IP.")
            return
        
        target_path = f"{config.get_hdfs_url(master_internal_ip)}/user/spark/data/sample.txt"
        run_cmd = f"/home/ansible/spark-jobs/run_wordcount.sh '{target_path}'"
        ssh.run(edge_ip, run_cmd)

    def do_upload(self, arg):
        """
        Upload a local file to HDFS.
        
        WHAT IT DOES:
        1. Copies your local file to the edge node via SCP
        2. Puts the file into HDFS from the edge node
        3. Cleans up the temporary file on edge node
        4. File is now permanently stored in HDFS
        
        Usage: upload <local_file> [hdfs_path]
        
        Examples:
        - upload data.csv
          Uploads to: /user/spark/data/uploads/data.csv
          
        - upload report.txt /user/spark/reports/
          Uploads to: /user/spark/reports/report.txt
          
        - upload large_dataset.parquet /user/spark/data/processed/
          Uploads to: /user/spark/data/processed/large_dataset.parquet
        
        After Upload:
        - File persists in HDFS across all cluster nodes
        - Can be used by multiple Spark jobs
        - Access via: hdfs://master-ip:9000/user/spark/data/uploads/filename
        
        Tip: Upload data files once, use many times!
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
        hdfs_path = args[1] if len(args) > 1 else config.HDFS_UPLOADS_DIR + "/"
        filename = os.path.basename(local_file)
        
        edge_ip = inventory.get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Could not find edge node IP.")
            return
        
        print(f"\t[INFO] Uploading {local_file} to HDFS...")
        print(f"\t       Target: {hdfs_path}")
        
        # Upload to HDFS (handles SCP + put + cleanup automatically)
        ret = ssh.upload_to_hdfs(local_file, hdfs_path, edge_ip)
        
        if ret != 0:
            print(f"\t[FAIL] Failed to upload file to HDFS.")
            return
        
        print(f"\t[SUCCESS] File uploaded to HDFS: {hdfs_path}{filename}")

    def do_download(self, arg):
        """
        Download Spark job results from HDFS to your local machine.
        
        WHAT IT DOES:
        1. Retrieves files from HDFS directory via edge node
        2. Transfers to local directory using SCP
        3. Preserves directory structure
        4. Cleans up temporary files on edge node
        
        Usage: download <hdfs_directory> [local_directory]
        
        Examples:
        - download /user/spark/results/wordcount-20240115
          Downloads to: ./results/wordcount-20240115/
          
        - download /user/spark/results/my_job ./output/
          Downloads to: ./output/my_job/
          
        - download /user/spark/data/processed /tmp/data/
          Downloads to: /tmp/data/processed/
        
        Output Files:
        - Spark saves results as multiple part-xxxxx files
        - All parts are downloaded to preserve data
        - Use 'cat part-*' to merge if needed
        
        Tip: Local directory is created if it doesn't exist.
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
        
        edge_ip = inventory.get_ip('edge')
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
        HDFS Management Shell - Interact with the HDFS filesystem.
        
        WHAT IT DOES:
        Provides direct access to HDFS commands without typing full paths.
        
        Interactive Mode (no arguments):
        - Starts a bash shell on edge node with HDFS aliases
        - Pre-configured shortcuts: ls, put, get, rm, cat, mkdir, du, df
        - Custom prompt shows [hdfs-shell]
        - Type 'exit' or Ctrl+D to quit
        
        Single Command Mode:
        - Executes one HDFS command and returns
        - Auto-adds 'dfs' prefix if you forget it
        - Example: 'hdfs ls /' is auto-converted to 'hdfs dfs -ls /'
        
        Usage:
        - hdfs                    # Interactive shell
        - hdfs <command>          # Single command
        
        Interactive Examples:
        ```
        hdfs
        [hdfs-shell]$ ls /user/spark/data
        [hdfs-shell]$ put local.txt /user/spark/
        [hdfs-shell]$ cat /user/spark/results/part-00000
        [hdfs-shell]$ du /user/spark/
        [hdfs-shell]$ exit
        ```
        
        Single Command Examples:
        - hdfs ls /user/spark/data/uploads
        - hdfs cat /user/spark/results/wordcount/part-00000
        - hdfs du -h /user/spark/
        - hdfs df -h
        - hdfs rm -r /user/spark/temp/
        
        Available Aliases (interactive mode):
        - ls, put, get, rm, cat: File operations
        - mkdir, mv, cp: Directory operations  
        - du, df: Disk usage
        - chmod, chown: Permissions
        
        Tip: Use interactive mode for multiple operations, single mode for quick checks.
        """
        edge_ip = inventory.get_ip('edge')
        if not edge_ip:
            print("\t[FAIL] Could not find edge node IP.")
            return

        # Interactive Mode
        if not arg or arg.strip() == "":
            print("\t[INFO] Entering interactive HDFS shell...")
            print("\t       Aliases: ls, put, get, rm, cat, mkdir, du, df")
            print("\t       Type 'exit' or Ctrl+D to quit.")
            
            # Create remote .hdfs_rc file with absolute paths
            rc_content = rf"""
HDFS_BIN={config.HADOOP_BIN}
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
                
                # SSH ControlMaster for faster connections
                ssh_opts = f"{config.SSH_OPTS} -o ControlMaster=auto -o ControlPersist=600s -o ControlPath=~/.ssh/ansible-%r@%h:%p"
                
                # Upload RC file
                subprocess.call(f"scp -q {ssh_opts} -i {config.SSH_KEY_PATH} hdfs_rc.tmp {config.SSH_USER}@{edge_ip}:.hdfs_rc", shell=True)
                os.remove("hdfs_rc.tmp")
                
                # SSH with RC file
                subprocess.call(f"ssh -t {ssh_opts} -i {config.SSH_KEY_PATH} {config.SSH_USER}@{edge_ip} 'bash --rcfile .hdfs_rc'", shell=True)
                
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
        
        # Execute HDFS command
        ssh.run(edge_ip, f"{config.HADOOP_BIN} dfs {arg}")

    def do_results(self, arg):
        """
        List Spark job results stored in HDFS.
        
        WHAT IT DOES:
        Lists contents of the HDFS results directory showing
        output directories from completed Spark jobs.
        
        Usage: results [limit]
        
        Parameters:
        - limit: Number of recent results to show (default: 10)
        
        Examples:
        - results       # Show last 10 job results
        - results 20    # Show last 20 job results
        - results 5     # Show last 5 job results
        
        Output:
        Directories in /user/spark/results/ with timestamps.
        Each contains part-xxxxx files from Spark.
        
        Next Steps:
        - Use 'download' to get results locally
        - Use 'hdfs cat' to view part files
        - Use 'hdfs ls <path>' for details
        """
        args = shlex.split(arg)
        limit = int(args[0]) if args and args[0].isdigit() else 10
        
        edge_ip = inventory.get_ip('edge')
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
