"""SSH client abstraction layer"""

import subprocess
import shlex
from typing import Optional, List
from src.config import config


class SSHClient:
    """
    SSH client for executing commands on remote cluster nodes.
    
    Provides a clean interface for SSH operations, eliminating
    the need for repeated subprocess.call() with long argument strings.
    
    All SSH calls use the configured key and security options.
    """
    
    def __init__(self):
        self.ssh_key = config.SSH_KEY_PATH
        self.ssh_opts = config.SSH_OPTS
        self.ssh_user = config.SSH_USER
    
    def run(self, host: str, command: str, quiet: bool = False, check: bool = False) -> int:
        """
        Execute a command on a remote host via SSH.
        
        Args:
            host: Hostname or IP address
            command: Command to execute
            quiet: If True, suppress output (stdout/stderr to DEVNULL)
            check: If True, raise exception on non-zero exit code
            
        Returns:
            int: Exit code of the command
            
        Examples:
            >>> ssh = SSHClient()
            >>> ssh.run("10.0.0.10", "ls /tmp")
            >>> ssh.run("edge-node", "echo 'hello'", quiet=True)
        """
        cmd = f"ssh {self.ssh_opts} -i {self.ssh_key} {self.ssh_user}@{host} '{command}'"
        
        kwargs = {}
        if quiet:
            kwargs['stdout'] = subprocess.DEVNULL
            kwargs['stderr'] = subprocess.DEVNULL
        
        ret = subprocess.call(cmd, shell=True, **kwargs)
        
        if check and ret != 0:
            raise Exception(f"SSH command failed on {host}: {command}")
        
        return ret
    
    def upload(self, local_path: str, remote_path: str, host: str, quiet: bool = True) -> int:
        """
        Upload a file to a remote host via SCP.
        
        Args:
            local_path: Local file path
            remote_path: Remote destination path
            host: Hostname or IP address
            quiet: If True, suppress output
            
        Returns:
            int: Exit code
            
        Examples:
            >>> ssh = SSHClient()
            >>> ssh.upload("/tmp/script.py", "/home/ansible/script.py", "10.0.0.10")
        """
        quiet_flag = "-q" if quiet else ""
        cmd = f"scp {quiet_flag} {self.ssh_opts} -i {self.ssh_key} {local_path} {self.ssh_user}@{host}:{remote_path}"
        return subprocess.call(cmd, shell=True)
    
    def download(self, remote_path: str, local_path: str, host: str, quiet: bool = True) -> int:
        """
        Download a file from a remote host via SCP.
        
        Args:
            remote_path: Remote file path
            local_path: Local destination path
            host: Hostname or IP address
            quiet: If True, suppress output
            
        Returns:
            int: Exit code
        """
        quiet_flag = "-q" if quiet else ""
        cmd = f"scp {quiet_flag} {self.ssh_opts} -i {self.ssh_key} {self.ssh_user}@{host}:{remote_path} {local_path}"
        return subprocess.call(cmd, shell=True)
    
    def mkdir(self, host: str, directory: str) -> int:
        """
        Create a directory on remote host.
        
        Args:
            host: Hostname or IP address
            directory: Directory path to create
            
        Returns:
            int: Exit code
        """
        return self.run(host, f"mkdir -p {directory}", quiet=True)
    
    def chmod(self, host: str, path: str, mode: str = "+x") -> int:
        """
        Change file permissions on remote host.
        
        Args:
            host: Hostname or IP address
            path: File path
            mode: Permission mode (e.g., "+x", "755")
            
        Returns:
            int: Exit code
        """
        return self.run(host, f"chmod {mode} {path}", quiet=True)
    
    def hdfs_put(self, host: str, local_path: str, hdfs_path: str, force: bool = True) -> int:
        """
        Upload a file to HDFS via remote node.
        
        Args:
            host: Hostname or IP address (usually edge node)
            local_path: Local file path on remote host
            hdfs_path: HDFS destination path
            force: If True, overwrite existing files
            
        Returns:
            int: Exit code
        """
        force_flag = "-f" if force else ""
        return self.run(host, f"{config.HADOOP_BIN} dfs -put {force_flag} {local_path} {hdfs_path}", quiet=True)
    
    def hdfs_rm(self, host: str, hdfs_path: str, recursive: bool = True, force: bool = True) -> int:
        """
        Remove a file/directory from HDFS.
        
        Args:
            host: Hostname or IP address
            hdfs_path: HDFS path to remove
            recursive: If True, remove directories recursively
            force: If True, ignore non-existent files
            
        Returns:
            int: Exit code
        """
        r_flag = "-r" if recursive else ""
        f_flag = "-f" if force else ""
        return self.run(host, f"{config.HADOOP_BIN} dfs -rm {r_flag} {f_flag} {hdfs_path}", quiet=True)
    
    def upload_to_hdfs(self, local_file: str, hdfs_path: str, host: str) -> int:
        """
        Upload a local file to HDFS (handles temp transfer to remote host).
        
        This is a convenience method that:
        1. SCPs file to remote host's /tmp
        2. Puts it into HDFS
        3. Cleans up temp file
        
        Args:
            local_file: Local file path
            hdfs_path: HDFS destination path
            host: Remote host (usually edge node)
            
        Returns:
            int: Exit code (0 for success)
        """
        import os
        filename = os.path.basename(local_file)
        tmp_remote = f"/tmp/{filename}"
        
        # SCP to remote
        ret = self.upload(local_file, tmp_remote, host, quiet=True)
        if ret != 0:
            return ret
        
        # Put to HDFS
        ret = self.hdfs_put(host, tmp_remote, hdfs_path)
        
        # Cleanup temp
        self.run(host, f"rm -f {tmp_remote}", quiet=True)
        
        return ret
    
    def submit_spark_job(self, host: str, script_path: str, args: List[str]) -> int:
        """
        Submit a Spark job via submit_job.sh wrapper.
        
        Args:
            host: Edge node IP
            script_path: Remote path to script
            args: Arguments to pass to script
            
        Returns:
            int: Exit code
        """
        args_str = " ".join([shlex.quote(a) for a in args])
        cmd = f"{config.SPARK_SUBMIT_WRAPPER} {script_path} {args_str}"
        return self.run(host, cmd)


# Singleton instance
ssh = SSHClient()
