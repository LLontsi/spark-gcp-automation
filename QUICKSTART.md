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
├── src/                # All source code
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
hdfs ls /           # Browse HDFS
download /path      # Download results
status              # Check cluster status
destroy             # Tear down cluster
```

Type `help` in the CLI for full command list!
