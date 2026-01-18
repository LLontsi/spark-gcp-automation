#!/usr/bin/env python3
"""
Spark Cluster Management CLI - Entry Point

This is the main entry point for the Spark Cluster Manager.
Run this file to start the interactive CLI.

Usage:
    python3 run_cli.py
    ./run_cli.py  (if executable)
"""

from src.cli import SparkClusterCLI


def main():
    """Initialize and start the CLI."""
    try:
        SparkClusterCLI().cmdloop()
    except KeyboardInterrupt:
        print("\n\n\tInterrupted. Exiting...")
    except Exception as e:
        print(f"\n\t[ERROR] Unexpected error: {e}")
        raise


if __name__ == '__main__':
    main()
