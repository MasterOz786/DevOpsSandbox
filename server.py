"""
FastAPI server for the DevOps Agent
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn

from models import (
    AuthRequest, AuthResponse, CommandRequest, CommandResponse,
    SandboxInfo, SessionInfo, CommandStatus
)
from auth import auth_manager
from sandbox import sandbox_manager
from logger import logger
from config import SERVER_HOST, SERVER_PORT

app = FastAPI(
    title="DevOps Terminal Agent",
    description="A sandboxed environment for safe DevOps operations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_current_session(session_id: str):
    """Dependency to validate session"""
    session = auth_manager.validate_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "DevOps Terminal Agent API",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.post("/auth/login", response_model=AuthResponse)
async def login(auth_request: AuthRequest):
    """Authenticate user and create session"""
    try:
        response = auth_manager.authenticate(auth_request)
        
        if response.success and response.session_id:
            # Create sandbox for the new session
            session = auth_manager.validate_session(response.session_id)
            if session:
                sandbox_manager.create_sandbox(response.session_id, session["username"])
        
        return response
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(status_code=500, detail="Authentication failed")

@app.post("/auth/logout")
async def logout(session_id: str):
    """Logout user and cleanup session"""
    try:
        success = auth_manager.logout(session_id)
        if success:
            sandbox_manager.cleanup_sandbox(session_id)
        
        return {"success": success, "message": "Logged out successfully"}
    except Exception as e:
        logger.error("Logout error", error=str(e))
        raise HTTPException(status_code=500, detail="Logout failed")

@app.get("/session/info", response_model=SessionInfo)
async def get_session_info(session_id: str, session: dict = Depends(get_current_session)):
    """Get current session information"""
    try:
        sandbox = sandbox_manager.get_sandbox(session_id)
        if not sandbox:
            raise HTTPException(status_code=404, detail="Sandbox not found")
        
        return SessionInfo(
            session_id=session_id,
            username=session["username"],
            auth_method=session["auth_method"],
            created_at=session["created_at"],
            last_activity=session["last_activity"],
            commands_executed=len(sandbox_manager.get_command_history(session_id)),
            sandbox_info=sandbox
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Session info error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get session info")

@app.get("/sandbox/info", response_model=SandboxInfo)
async def get_sandbox_info(session_id: str, session: dict = Depends(get_current_session)):
    """Get sandbox information"""
    sandbox = sandbox_manager.get_sandbox(session_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    return sandbox

@app.post("/commands/execute", response_model=CommandResponse)
async def execute_command(
    session_id: str,
    command_request: CommandRequest,
    session: dict = Depends(get_current_session)
):
    """Execute a command in the sandbox"""
    try:
        # Ensure the session_id matches
        if command_request.session_id != session_id:
            raise HTTPException(status_code=400, detail="Session ID mismatch")
        
        response = sandbox_manager.execute_command(session_id, command_request)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Command execution error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Command execution failed")

@app.get("/commands/history", response_model=List[CommandResponse])
async def get_command_history(
    session_id: str,
    limit: int = 50,
    session: dict = Depends(get_current_session)
):
    """Get command execution history"""
    try:
        history = sandbox_manager.get_command_history(session_id, limit)
        return history
    except Exception as e:
        logger.error("History retrieval error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get command history")

@app.get("/admin/sessions")
async def get_active_sessions(session_id: str, session: dict = Depends(get_current_session)):
    """Get all active sessions (admin only)"""
    # Simple admin check - in production, implement proper role-based access
    if session["username"] not in ["admin", "root"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        sessions = auth_manager.get_active_sessions()
        return {"active_sessions": sessions}
    except Exception as e:
        logger.error("Admin sessions error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get sessions")

@app.get("/admin/logs")
async def get_logs(
    session_id: str,
    limit: int = 100,
    session: dict = Depends(get_current_session)
):
    """Get system logs (admin only)"""
    if session["username"] not in ["admin", "root"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        logs = logger.get_recent_logs(limit)
        return {"logs": logs}
    except Exception as e:
        logger.error("Admin logs error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get logs")

@app.on_event("startup")
async def startup_event():
    """Initialize the server"""
    logger.info("DevOps Agent server starting up")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    logger.info("DevOps Agent server shutting down")
    
    # Cleanup all active sandboxes
    for session_id in list(sandbox_manager.active_sandboxes.keys()):
        sandbox_manager.cleanup_sandbox(session_id)

def create_app():
    """Create and configure the FastAPI app"""
    return app

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
        log_level="info"
    )
