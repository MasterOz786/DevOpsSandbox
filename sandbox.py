"""
Sandbox execution environment for the DevOps Agent
"""

import os
import subprocess
import shutil
import tempfile
import threading
import time
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import signal

from models import CommandRequest, CommandResponse, CommandStatus, SandboxInfo
from logger import logger
from config import (
    SANDBOX_ROOT, MAX_EXECUTION_TIME, MAX_OUTPUT_SIZE, 
    AVAILABLE_TOOLS, BLOCKED_COMMANDS
)

class SandboxManager:
    """Manages sandboxed execution of DevOps commands"""
    
    def __init__(self):
        self.active_sandboxes: Dict[str, SandboxInfo] = {}
        self.command_history: Dict[str, List[CommandResponse]] = {}
        
        # Ensure sandbox root exists
        SANDBOX_ROOT.mkdir(exist_ok=True)
    
    def create_sandbox(self, session_id: str, username: str) -> SandboxInfo:
        """Create a new sandbox environment for a session"""
        sandbox_dir = SANDBOX_ROOT / session_id
        sandbox_dir.mkdir(exist_ok=True)
        
        # Create basic directory structure
        (sandbox_dir / "home").mkdir(exist_ok=True)
        (sandbox_dir / "tmp").mkdir(exist_ok=True)
        (sandbox_dir / "workspace").mkdir(exist_ok=True)
        
        # Create a minimal environment
        env_vars = {
            "HOME": str(sandbox_dir / "home"),
            "TMPDIR": str(sandbox_dir / "tmp"),
            "USER": username,
            "PWD": str(sandbox_dir / "workspace"),
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "SHELL": "/bin/bash",
            "TERM": "xterm-256color"
        }
        
        sandbox_info = SandboxInfo(
            session_id=session_id,
            working_directory=str(sandbox_dir / "workspace"),
            environment_variables=env_vars,
            available_tools=AVAILABLE_TOOLS.copy(),
            resource_limits={
                "max_execution_time": MAX_EXECUTION_TIME,
                "max_output_size": MAX_OUTPUT_SIZE,
                "max_memory": "512MB",
                "max_cpu": "50%"
            },
            created_at=datetime.utcnow()
        )
        
        self.active_sandboxes[session_id] = sandbox_info
        self.command_history[session_id] = []
        
        logger.audit(
            "sandbox_created",
            session_id=session_id,
            sandbox_dir=str(sandbox_dir)
        )
        
        return sandbox_info
    
    def get_sandbox(self, session_id: str) -> Optional[SandboxInfo]:
        """Get sandbox info for a session"""
        return self.active_sandboxes.get(session_id)
    
    def _is_command_safe(self, command: str) -> Tuple[bool, str]:
        """Check if a command is safe to execute"""
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return False, "Empty command"
        
        base_command = cmd_parts[0].lower()
        
        # Check blocked commands
        if base_command in BLOCKED_COMMANDS:
            return False, f"Command '{base_command}' is blocked for security reasons"
        
        # Check if it's a known safe tool
        if base_command not in AVAILABLE_TOOLS:
            return False, f"Command '{base_command}' is not available in sandbox"
        
        # Additional safety checks
        dangerous_patterns = ['>', '>>', '|', '&', ';', '$(', '`']
        for pattern in dangerous_patterns:
            if pattern in command:
                return False, f"Command contains potentially dangerous pattern: {pattern}"
        
        return True, "Command is safe"
    
    def _simulate_devops_command(self, command: str, args: List[str]) -> Tuple[str, str, int]:
        """Simulate DevOps commands safely"""
        cmd_lower = command.lower()
        
        if cmd_lower == "git":
            if not args:
                return "git version 2.34.1", "", 0
            elif args[0] == "status":
                return "On branch main\nnothing to commit, working tree clean", "", 0
            elif args[0] == "clone":
                return f"Cloning into '{args[1] if len(args) > 1 else 'repository'}'...\nDone.", "", 0
            elif args[0] == "pull":
                return "Already up to date.", "", 0
            else:
                return f"Simulated: git {' '.join(args)}", "", 0
        
        elif cmd_lower == "docker":
            if not args:
                return "Docker version 20.10.17", "", 0
            elif args[0] == "ps":
                return "CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES", "", 0
            elif args[0] == "images":
                return "REPOSITORY    TAG       IMAGE ID       CREATED       SIZE", "", 0
            else:
                return f"Simulated: docker {' '.join(args)}", "", 0
        
        elif cmd_lower == "kubectl":
            if not args:
                return "kubectl controls the Kubernetes cluster manager.", "", 0
            elif args[0] == "get":
                return "No resources found in default namespace.", "", 0
            else:
                return f"Simulated: kubectl {' '.join(args)}", "", 0
        
        elif cmd_lower == "terraform":
            if not args:
                return "Terraform v1.0.0", "", 0
            elif args[0] == "plan":
                return "No changes. Infrastructure is up-to-date.", "", 0
            elif args[0] == "apply":
                return "Apply complete! Resources: 0 added, 0 changed, 0 destroyed.", "", 0
            else:
                return f"Simulated: terraform {' '.join(args)}", "", 0
        
        elif cmd_lower == "curl":
            url = args[0] if args else "http://example.com"
            return f"Simulated HTTP GET to {url}\nStatus: 200 OK\nContent: Sample response", "", 0
        
        elif cmd_lower in ["ls", "pwd", "cat", "grep", "find"]:
            # Use actual system commands for basic file operations (safe in isolated directory)
            return f"Simulated: {command} {' '.join(args)}", "", 0
        
        else:
            return f"Simulated: {command} {' '.join(args)}", "", 0
    
    def execute_command(self, session_id: str, request: CommandRequest) -> CommandResponse:
        """Execute a command in the sandbox"""
        command_id = f"cmd_{session_id}_{int(time.time())}"
        start_time = time.time()
        
        # Validate session has sandbox
        sandbox = self.get_sandbox(session_id)
        if not sandbox:
            return CommandResponse(
                command_id=command_id,
                status=CommandStatus.FAILED,
                stdout="",
                stderr="No sandbox found for session",
                exit_code=1,
                execution_time=0,
                timestamp=datetime.utcnow()
            )
        
        # Check command safety
        is_safe, safety_message = self._is_command_safe(request.command)
        if not is_safe:
            logger.audit(
                "unsafe_command_blocked",
                session_id=session_id,
                command=request.command,
                reason=safety_message
            )
            return CommandResponse(
                command_id=command_id,
                status=CommandStatus.FAILED,
                stdout="",
                stderr=f"Command blocked: {safety_message}",
                exit_code=1,
                execution_time=time.time() - start_time,
                timestamp=datetime.utcnow()
            )
        
        logger.audit(
            "command_execution_started",
            session_id=session_id,
            command_id=command_id,
            command=request.command,
            args=request.args
        )
        
        try:
            # Execute command in simulation mode
            stdout, stderr, exit_code = self._simulate_devops_command(
                request.command, 
                request.args
            )
            
            execution_time = time.time() - start_time
            status = CommandStatus.COMPLETED if exit_code == 0 else CommandStatus.FAILED
            
            response = CommandResponse(
                command_id=command_id,
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                resource_usage={
                    "cpu_time": execution_time,
                    "memory_peak": "< 1MB",
                    "disk_io": "minimal"
                }
            )
            
            # Store command history
            if session_id in self.command_history:
                self.command_history[session_id].append(response)
                # Keep only last 100 commands
                if len(self.command_history[session_id]) > 100:
                    self.command_history[session_id] = self.command_history[session_id][-100:]
            
            logger.audit(
                "command_execution_completed",
                session_id=session_id,
                command_id=command_id,
                status=status.value,
                exit_code=exit_code,
                execution_time=execution_time
            )
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_response = CommandResponse(
                command_id=command_id,
                status=CommandStatus.FAILED,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                exit_code=1,
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )
            
            logger.error(
                "command_execution_error",
                session_id=session_id,
                command_id=command_id,
                error=str(e)
            )
            
            return error_response
    
    def get_command_history(self, session_id: str, limit: int = 50) -> List[CommandResponse]:
        """Get command execution history for a session"""
        if session_id not in self.command_history:
            return []
        
        history = self.command_history[session_id]
        return history[-limit:] if limit > 0 else history
    
    def cleanup_sandbox(self, session_id: str) -> bool:
        """Clean up sandbox environment"""
        if session_id not in self.active_sandboxes:
            return False
        
        try:
            sandbox_dir = SANDBOX_ROOT / session_id
            if sandbox_dir.exists():
                shutil.rmtree(sandbox_dir)
            
            del self.active_sandboxes[session_id]
            if session_id in self.command_history:
                del self.command_history[session_id]
            
            logger.audit(
                "sandbox_cleaned_up",
                session_id=session_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "sandbox_cleanup_failed",
                session_id=session_id,
                error=str(e)
            )
            return False

# Global sandbox manager instance
sandbox_manager = SandboxManager()
