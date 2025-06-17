"""
Logging configuration and utilities for the DevOps Agent
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class StructuredLogger:
    """Custom logger that outputs both structured JSON and human-readable logs"""
    
    def __init__(self, name: str, log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Console handler for human-readable logs
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for structured JSON logs
        if log_file:
            file_handler = logging.FileHandler(log_file)
            self.logger.addHandler(file_handler)
        
        self.json_logs = []
    
    def log_structured(self, level: str, event: str, **kwargs):
        """Log a structured event with additional metadata"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.upper(),
            "event": event,
            **kwargs
        }
        
        # Store in memory for API access
        self.json_logs.append(log_entry)
        
        # Keep only last 1000 logs in memory
        if len(self.json_logs) > 1000:
            self.json_logs = self.json_logs[-1000:]
        
        # Log to file as JSON
        json_str = json.dumps(log_entry)
        getattr(self.logger, level.lower())(json_str)
        
        return log_entry
    
    def info(self, message: str, **kwargs):
        return self.log_structured("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        return self.log_structured("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        return self.log_structured("error", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        return self.log_structured("debug", message, **kwargs)
    
    def audit(self, event: str, session_id: str, **kwargs):
        """Log audit events for security and compliance"""
        return self.log_structured(
            "info", 
            f"AUDIT: {event}", 
            session_id=session_id,
            audit=True,
            **kwargs
        )
    
    def get_recent_logs(self, limit: int = 100) -> list:
        """Get recent structured logs"""
        return self.json_logs[-limit:] if limit > 0 else self.json_logs

# Global logger instance
logger = StructuredLogger("devops_agent", "devops_agent.log")
