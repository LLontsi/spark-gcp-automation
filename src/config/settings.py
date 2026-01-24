"""Centralized configuration management for Spark cluster automation"""

import os


class Config:
    """
    Configuration singleton for all cluster operations.
    
    Centralizes paths, ports, and cluster settings to avoid
    hardcoding values throughout the codebase.
    """
    
    # ===== Paths =====
    SSH_KEY_PATH = os.path.expanduser("~/.ssh/gcp_spark")
    INVENTORY_FILE = "ansible/inventory/hosts.yml"
    TERRAFORM_DIR = "terraform"
    ANSIBLE_DIR = "ansible"
    
    # ===== Cluster Defaults =====
    DEFAULT_WORKERS = 2
    MAX_WORKERS = 4
    DEFAULT_REGION = "europe-west1"
    
    # ===== HDFS Configuration =====
    HDFS_PORT = 9000
    HDFS_NAMENODE_HTTP_PORT = 9870
    HDFS_DATANODE_HTTP_PORT = 9864
    HDFS_DEFAULT_REPLICATION = 2
    
    # ===== Spark Configuration =====
    SPARK_MASTER_PORT = 7077
    SPARK_MASTER_UI_PORT = 8080
    SPARK_WORKER_UI_PORT = 8081
    SPARK_HISTORY_PORT = 18080
    
    # ===== Remote Paths (on cluster nodes) =====
    HADOOP_BIN = "/opt/hadoop/current/bin/hdfs"
    SPARK_HOME = "/opt/spark/current"
    SPARK_SUBMIT_WRAPPER = "/home/ansible/spark-jobs/submit_job.sh"
    REMOTE_SCRIPT_DIR = "/home/ansible/spark-jobs/user-scripts"
    
    # ===== HDFS Paths =====
    HDFS_USER_BASE = "/user/spark"
    HDFS_DATA_DIR = "/user/spark/data"
    HDFS_UPLOADS_DIR = "/user/spark/data/uploads"
    HDFS_RESULTS_DIR = "/user/spark/results"
    
    # ===== SSH Configuration =====
    SSH_OPTS = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    SSH_USER = "ansible"
    
    # ===== Timeouts =====
    DEPLOY_TIMEOUT = 1800  # 30 minutes
    JOB_TIMEOUT = 3600     # 1 hour
    
    @classmethod
    def get_hdfs_url(cls, internal_ip):
        """
        Construct full HDFS NameNode URL.
        
        Args:
            internal_ip: Internal IP of the master node
            
        Returns:
            str: Full HDFS URL (e.g., 'hdfs://10.0.0.10:9000')
        """
        return f"hdfs://{internal_ip}:{cls.HDFS_PORT}"
    
    @classmethod
    def get_spark_master_url(cls, internal_ip):
        """
        Construct Spark master URL.
        
        Args:
            internal_ip: Internal IP of the master node
            
        Returns:
            str: Spark master URL (e.g., 'spark://10.0.0.10:7077')
        """
        return f"spark://{internal_ip}:{cls.SPARK_MASTER_PORT}"
    
    @classmethod
    def get_hdfs_path(cls, path):
        """
        Ensure HDFS path starts with base directory.
        
        Args:
            path: Relative or absolute HDFS path
            
        Returns:
            str: Absolute HDFS path
        """
        if path.startswith('/'):
            return path
        return f"{cls.HDFS_USER_BASE}/{path}"


# Singleton instance
config = Config()
