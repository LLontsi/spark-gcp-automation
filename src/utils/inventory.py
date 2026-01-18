"""Inventory management utilities"""

import os
import yaml
from typing import Optional, Dict, Any
from src.config import config


class InventoryManager:
    """
    Helper for reading and parsing Ansible inventory.
    
    Provides methods to extract host IPs and other inventory data
    without duplicating YAML parsing logic.
    """
    
    def __init__(self, inventory_path: Optional[str] = None):
        """
        Initialize inventory manager.
        
        Args:
            inventory_path: Path to inventory file (uses config default if None)
        """
        self.inventory_path = inventory_path or config.INVENTORY_FILE
    
    def load(self) -> Optional[Dict[str, Any]]:
        """
        Load inventory YAML file.
        
        Returns:
            dict: Parsed inventory data, or None if file doesn't exist
        """
        if not os.path.exists(self.inventory_path):
            return None
        
        try:
            with open(self.inventory_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"\t[WARN] Failed to load inventory: {e}")
            return None
    
    def get_group(self, data: Dict[str, Any], group_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific group from inventory data.
        
        Args:
            data: Loaded inventory data
            group_name: Name of the group (e.g., 'master', 'workers', 'edge')
            
        Returns:
            dict: Group data, or None if not found
        """
        if not data or 'all' not in data or 'children' not in data['all']:
            return None
        
        spark_cluster = data['all']['children'].get('spark_cluster', {})
        if 'children' not in spark_cluster:
            return None
        
        return spark_cluster['children'].get(group_name)
    
    def get_ip(self, host_alias: str) -> Optional[str]:
        """
        Get external IP for a host alias.
        
        Args:
            host_alias: Host alias ('master', 'edge', 'worker-1', etc.)
            
        Returns:
            str: External IP address, or None if not found
        """
        data = self.load()
        if not data:
            return None
        
        # Try to find in master group
        if host_alias == 'master':
            master_group = self.get_group(data, 'master')
            if master_group and 'hosts' in master_group:
                for host_data in master_group['hosts'].values():
                    return host_data.get('ansible_host')
        
        # Try to find in edge group
        elif host_alias == 'edge':
            edge_group = self.get_group(data, 'edge')
            if edge_group and 'hosts' in edge_group:
                for host_data in edge_group['hosts'].values():
                    return host_data.get('ansible_host')
        
        # Try to find in workers group
        elif host_alias.startswith('worker'):
            workers_group = self.get_group(data, 'workers')
            if workers_group and 'hosts' in workers_group:
                # Try exact match first
                if host_alias in workers_group['hosts']:
                    return workers_group['hosts'][host_alias].get('ansible_host')
                # Try spark-worker-N format
                full_alias = f"spark-{host_alias}"
                if full_alias in workers_group['hosts']:
                    return workers_group['hosts'][full_alias].get('ansible_host')
        
        return None
    
    def get_internal_ip(self, host_alias: str) -> Optional[str]:
        """
        Get internal IP for a host alias.
        
        Args:
            host_alias: Host alias ('master', 'edge', 'worker-1', etc.)
            
        Returns:
            str: Internal IP address, or None if not found
        """
        data = self.load()
        if not data:
            return None
        
        # Try to find in master group
        if host_alias == 'master':
            master_group = self.get_group(data, 'master')
            if master_group and 'hosts' in master_group:
                for host_data in master_group['hosts'].values():
                    return host_data.get('internal_ip')
        
        # Try to find in edge group
        elif host_alias == 'edge':
            edge_group = self.get_group(data, 'edge')
            if edge_group and 'hosts' in edge_group:
                for host_data in edge_group['hosts'].values():
                    return host_data.get('internal_ip')
        
        # Try to find in workers group
        elif host_alias.startswith('worker'):
            workers_group = self.get_group(data, 'workers')
            if workers_group and 'hosts' in workers_group:
                # Try exact match first
                if host_alias in workers_group['hosts']:
                    return workers_group['hosts'][host_alias].get('internal_ip')
                # Try spark-worker-N format
                full_alias = f"spark-{host_alias}"
                if full_alias in workers_group['hosts']:
                    return workers_group['hosts'][full_alias].get('internal_ip')
        
        return None
    
    def count_workers(self) -> Optional[int]:
        """
        Count number of workers in inventory.
        
        Returns:
            int: Number of workers, or None if inventory doesn't exist
        """
        data = self.load()
        if not data:
            return None
        
        workers_group = self.get_group(data, 'workers')
        if not workers_group or 'hosts' not in workers_group:
            return None
        
        return len(workers_group['hosts'])


# Singleton instance
inventory = InventoryManager()
