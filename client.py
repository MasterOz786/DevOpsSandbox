"""
Terminal client for the DevOps Agent
"""

import json
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any

import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich import box

from models import AuthMethod, AuthRequest, CommandRequest
from config import CLIENT_HOST, CLIENT_PORT

class DevOpsTerminalClient:
    """Terminal client for interacting with the DevOps Agent"""
    
    def __init__(self, host: str = CLIENT_HOST, port: int = CLIENT_PORT):
        self.console = Console()
        self.base_url = f"http://{host}:{port}"
        self.session_id: Optional[str] = None
        self.username: Optional[str] = None
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[Any, Any]]:
        """Make HTTP request to the server"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]Request failed: {e}[/red]")
            return None
        except json.JSONDecodeError as e:
            self.console.print(f"[red]Invalid JSON response: {e}[/red]")
            return None
    
    def display_welcome(self):
        """Display welcome message"""
        welcome_text = """
# 🚀 DevOps Terminal Agent

Welcome to the **DevOps Terminal Agent** - a sandboxed environment for safe DevOps operations!

## Features:
- 🔐 **Secure Authentication** (SSH Keys or API Tokens)
- 📦 **Sandboxed Execution** Environment
- 🛡️ **Safe Simulation** of DevOps Commands
- 📊 **Comprehensive Logging** and Audit Trail
- 🔧 **Popular DevOps Tools** (git, docker, kubectl, terraform, etc.)

## Available Commands:
- `git` - Version control operations
- `docker` - Container management
- `kubectl` - Kubernetes operations
- `terraform` - Infrastructure as Code
- `curl` - HTTP requests
- `ansible` - Configuration management
- And many more standard CLI tools!

Ready to get started? Let's authenticate you first! 🎯
        """
        
        self.console.print(Panel(
            Markdown(welcome_text),
            title="🎯 DevOps Agent",
            border_style="blue",
            padding=(1, 2)
        ))
    
    def authenticate(self) -> bool:
        """Handle user authentication"""
        self.console.print("\n[bold blue]🔐 Authentication Required[/bold blue]")
        
        # Choose authentication method
        auth_methods = {
            "1": ("SSH Key", AuthMethod.SSH_KEY),
            "2": ("API Token", AuthMethod.API_TOKEN)
        }
        
        self.console.print("\nAvailable authentication methods:")
        for key, (name, _) in auth_methods.items():
            self.console.print(f"  {key}. {name}")
        
        choice = Prompt.ask(
            "\nSelect authentication method",
            choices=list(auth_methods.keys()),
            default="2"
        )
        
        method_name, auth_method = auth_methods[choice]
        
        if auth_method == AuthMethod.SSH_KEY:
            credentials = Prompt.ask(
                "\n[yellow]Enter your SSH public key[/yellow]",
                password=False
            )
        else:
            # Show available demo tokens
            self.console.print("\n[dim]Demo API tokens available:[/dim]")
            self.console.print("[dim]  admin, devops, user[/dim]")
            credentials = Prompt.ask(
                "\n[yellow]Enter your API token[/yellow]",
                password=True
            )
        
        username = Prompt.ask(
            "[yellow]Enter username (optional)[/yellow]",
            default=""
        )
        
        # Make authentication request
        auth_request = AuthRequest(
            method=auth_method,
            credentials=credentials,
            username=username if username else None
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Authenticating...", total=None)
            
            response = self._make_request(
                "POST",
                "/auth/login",
                json=auth_request.dict()
            )
            
            progress.remove_task(task)
        
        if response and response.get("success"):
            self.session_id = response.get("session_id")
            self.username = username or "user"
            
            self.console.print(f"\n[green]✅ {response.get('message')}[/green]")
            self.console.print(f"[dim]Session expires: {response.get('expires_at', 'Unknown')}[/dim]")
            return True
        else:
            error_msg = response.get("message", "Authentication failed") if response else "Connection failed"
            self.console.print(f"\n[red]❌ {error_msg}[/red]")
            return False
    
    def display_sandbox_info(self):
        """Display sandbox environment information"""
        if not self.session_id:
            return
        
        response = self._make_request(
            "GET",
            "/sandbox/info",
            params={"session_id": self.session_id}
        )
        
        if response:
            self.console.print("\n[bold green]📦 Sandbox Environment[/bold green]")
            
            table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Working Directory", response.get("working_directory", "Unknown"))
            table.add_row("Session ID", response.get("session_id", "Unknown"))
            table.add_row("Created At", response.get("created_at", "Unknown"))
            
            # Resource limits
            limits = response.get("resource_limits", {})
            table.add_row("Max Execution Time", f"{limits.get('max_execution_time', 'Unknown')}s")
            table.add_row("Max Memory", limits.get("max_memory", "Unknown"))
            table.add_row("Max CPU", limits.get("max_cpu", "Unknown"))
            
            self.console.print(table)
            
            # Available tools
            tools = response.get("available_tools", [])
            if tools:
                self.console.print(f"\n[bold blue]🔧 Available Tools:[/bold blue]")
                tools_text = ", ".join(tools)
                self.console.print(f"[dim]{tools_text}[/dim]")
    
    def execute_command_interactive(self):
        """Interactive command execution"""
        if not self.session_id:
            self.console.print("[red]Not authenticated![/red]")
            return
        
        while True:
            self.console.print(f"\n[bold green]{self.username}@devops-agent[/bold green]:[blue]~[/blue]$ ", end="")
            
            command_input = Prompt.ask("", console=self.console).strip()
            
            if not command_input:
                continue
            
            if command_input.lower() in ["exit", "quit", "logout"]:
                break
            
            if command_input.lower() == "help":
                self.show_help()
                continue
            
            if command_input.lower() == "history":
                self.show_command_history()
                continue
            
            if command_input.lower() == "sandbox":
                self.display_sandbox_info()
                continue
            
            # Parse command and arguments
            parts = command_input.split()
            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            # Confirm execution for potentially dangerous commands
            if command.lower() in ["rm", "delete", "format", "reboot"]:
                if not Confirm.ask(f"[yellow]⚠️  Execute potentially dangerous command '{command_input}'?[/yellow]"):
                    continue
            
            # Execute command
            self.execute_command(command, args)
    
    def execute_command(self, command: str, args: list):
        """Execute a single command"""
        if not self.session_id:
            return
        
        command_request = CommandRequest(
            session_id=self.session_id,
            command=command,
            args=args
        )
        
        self.console.print(f"\n[dim]Executing: {command} {' '.join(args)}[/dim]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Running command...", total=None)
            
            response = self._make_request(
                "POST",
                "/commands/execute",
                params={"session_id": self.session_id},
                json=command_request.dict()
            )
            
            progress.remove_task(task)
        
        if response:
            status = response.get("status", "unknown")
            exit_code = response.get("exit_code", -1)
            execution_time = response.get("execution_time", 0)
            
            # Display command result
            if status == "completed":
                status_color = "green"
                status_icon = "✅"
            else:
                status_color = "red"
                status_icon = "❌"
            
            self.console.print(f"\n[{status_color}]{status_icon} Command {status}[/{status_color}] "
                             f"(exit code: {exit_code}, time: {execution_time:.2f}s)")
            
            # Display output
            stdout = response.get("stdout", "")
            stderr = response.get("stderr", "")
            
            if stdout:
                self.console.print(Panel(
                    stdout,
                    title="📤 Output",
                    border_style="green",
                    expand=False
                ))
            
            if stderr:
                self.console.print(Panel(
                    stderr,
                    title="⚠️ Error Output",
                    border_style="red",
                    expand=False
                ))
            
            # Resource usage
            resource_usage = response.get("resource_usage", {})
            if resource_usage:
                self.console.print(f"[dim]Resources: CPU: {resource_usage.get('cpu_time', 'N/A')}, "
                                 f"Memory: {resource_usage.get('memory_peak', 'N/A')}, "
                                 f"Disk I/O: {resource_usage.get('disk_io', 'N/A')}[/dim]")
    
    def show_command_history(self):
        """Display command execution history"""
        if not self.session_id:
            return
        
        response = self._make_request(
            "GET",
            "/commands/history",
            params={"session_id": self.session_id, "limit": 20}
        )
        
        if response:
            self.console.print("\n[bold blue]📜 Command History[/bold blue]")
            
            if not response:
                self.console.print("[dim]No commands executed yet.[/dim]")
                return
            
            table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Command", style="white")
            table.add_column("Status", style="green")
            table.add_column("Exit Code", style="yellow", width=10)
            table.add_column("Time", style="blue", width=8)
            table.add_column("Timestamp", style="dim", width=20)
            
            for i, cmd in enumerate(response[-10:], 1):  # Show last 10 commands
                status = cmd.get("status", "unknown")
                status_color = "green" if status == "completed" else "red"
                
                # Reconstruct command
                command_text = cmd.get("command_id", "").split("_")[-1] if cmd.get("command_id") else "unknown"
                
                table.add_row(
                    str(i),
                    f"{command_text}",
                    f"[{status_color}]{status}[/{status_color}]",
                    str(cmd.get("exit_code", -1)),
                    f"{cmd.get('execution_time', 0):.2f}s",
                    cmd.get("timestamp", "")[:19] if cmd.get("timestamp") else ""
                )
            
            self.console.print(table)
    
    def show_help(self):
        """Display help information"""
        help_text = """
# 🔧 DevOps Agent Help

## Available Commands:
- **DevOps Tools**: `git`, `docker`, `kubectl`, `terraform`, `ansible`, `curl`
- **File Operations**: `ls`, `pwd`, `cat`, `grep`, `find`
- **System**: `help`, `history`, `sandbox`, `exit`

## Usage Examples:
```bash
git status                    # Check git repository status
docker ps                     # List running containers
kubectl get pods             # List Kubernetes pods
terraform plan               # Show infrastructure changes
curl https://api.github.com  # Make HTTP request
