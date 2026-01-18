# Spark GCP Automation - Quick Start

## Running the CLI

```bash
# Option 1: Direct execution (recommended)
python3 run_cli.py

# Option 2: If executable
./run_cli.py
```

## Project Structure

```
spark-gcp-automation/
├── run_cli.py          # Main entry point (START HERE)
├── src/                # All source code (modular architecture)
│   ├── cli/
│   │   └── shell.py    # CLI implementation
│   ├── config/
│   │   └── settings.py # Configuration management
│   └── utils/
│       ├── ssh.py      # SSH operations
│       └── inventory.py # Inventory management
├── terraform/          # Infrastructure as Code
├── ansible/            # Configuration management
└── README.md           # Full documentation
```

## Common Commands

Once in the CLI:

```
deploy -w 2         # Deploy cluster with 2 workers
upload data.csv     # Upload data to HDFS
run script.py arg1  # Run Spark job
hdfs           # Browse HDFS (interactive shell)
download /path      # Download results
status              # Check cluster status
destroy             # Tear down cluster
```

## Verbosity Control

Control output verbosity for cleaner logs:

```
set verbose on      # Default: Show all logs (SSH, Spark, HDFS)
set verbose off     # Quiet: Only show results and errors
set                 # View current settings
```

**Quiet mode hides:**
- SSH warnings ("Permanently added...")
- Spark INFO/WARN logs
- HDFS command noise
- Upload/download progress messages

**Perfect for:** Production use, cleaner output, when you know what you're doing

## Examples

### Deploy and Run a Job
```bash
python3 run_cli.py

# Deploy cluster
(spark-cluster) deploy -w 2

# Check status
(spark-cluster) status

# Run built-in example
(spark-cluster) run wordcount

# Upload your data
(spark-cluster) upload mydata.csv

# Run your script
(spark-cluster) run myscript.py /user/spark/data/uploads/mydata.csv

# Download results
(spark-cluster) download /user/spark/results/job-xyz

# Clean up
(spark-cluster) destroy
```

### Using Quiet Mode
```bash
# Switch to quiet mode for cleaner output
(spark-cluster) set verbose off

# Run job (only shows results, no Spark logs)
(spark-cluster) run pi 10000
π ≈ 3.1416
Error: 0.000007

# Switch back if needed
(spark-cluster) set verbose on
```

## Get Help

```
help                # List all commands
help <command>      # Detailed help for specific command
help set            # See all available settings
```

Type `help` in the CLI for the full command list!
