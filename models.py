"""
Data models for the DevOps Agent
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class AuthMethod(str, Enum):
    SSH_KEY = "ssh_key"
    API_TOKEN = "api_token"

class CommandStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class AuthRequest(BaseModel):
    method: AuthMethod
    credentials: str  # SSH key content or API token
    username: Optional[str] = None

class AuthResponse(BaseModel):
    success: bool
    session_id: Optional[str] = None
    message: str
    expires_at: Optional[datetime] = None

class CommandRequest(BaseModel):
    session_id: str
    command: str
    args: List[str] = []
    environment: Dict[str, str] = {}
    working_directory: Optional[str] = None
    timeout: Optional[int] = None

class CommandResponse(BaseModel):
    command_id: str
    status: CommandStatus
    stdout: str
    stderr: str
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None
    timestamp: datetime
    resource_usage: Dict[str, Any] = {}

class SandboxInfo(BaseModel):
    session_id: str
    working_directory: str
    environment_variables: Dict[str, str]
    available_tools: List[str]
    resource_limits: Dict[str, Any]
    created_at: datetime

class SessionInfo(BaseModel):
    session_id: str
    username: str
    auth_method: AuthMethod
    created_at: datetime
    last_activity: datetime
    commands_executed: int
    sandbox_info: SandboxInfo
