"""
Configuration settings for the DevOps Agent
"""

import os
from pathlib import Path

# Server Configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# Client Configuration
CLIENT_HOST = os.getenv("CLIENT_HOST", "localhost")
CLIENT_PORT = int(os.getenv("CLIENT_PORT", "8000"))

# Authentication Configuration
AUTH_TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", "devops-agent-secret-key-2025")
SSH_KEYS_DIR = Path(os.getenv("SSH_KEYS_DIR", "~/.ssh")).expanduser()
AUTHORIZED_KEYS_FILE = SSH_KEYS_DIR / "authorized_keys"

# Sandbox Configuration
SANDBOX_ROOT = Path(os.getenv("SANDBOX_ROOT", "./sandbox"))
SANDBOX_ROOT.mkdir(exist_ok=True)

# Resource Limits
MAX_EXECUTION_TIME = int(os.getenv("MAX_EXECUTION_TIME", "30"))  # seconds
MAX_OUTPUT_SIZE = int(os.getenv("MAX_OUTPUT_SIZE", "1048576"))  # 1MB
MAX_PROCESSES = int(os.getenv("MAX_PROCESSES", "10"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "devops_agent.log")

# Available DevOps Tools (simulated/safe versions)
AVAILABLE_TOOLS = [
    "git", "curl", "wget", "ssh", "scp", "rsync", 
    "docker", "kubectl", "terraform", "ansible",
    "grep", "awk", "sed", "find", "cat", "ls", "pwd"
]

# Blocked Commands (for security)
BLOCKED_COMMANDS = [
    "rm", "rmdir", "delete", "format", "fdisk",
    "mkfs", "mount", "umount", "reboot", "shutdown",
    "systemctl", "service", "kill", "killall"
]
