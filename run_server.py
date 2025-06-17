#!/usr/bin/env python3
"""
DevOps Agent Server Launcher
"""

import uvicorn
from config import SERVER_HOST, SERVER_PORT
from logger import logger

def main():
    """Launch the DevOps Agent server"""
    logger.info("Starting DevOps Agent Server", host=SERVER_HOST, port=SERVER_PORT)
    
    try:
        uvicorn.run(
            "server:app",
            host=SERVER_HOST,
            port=SERVER_PORT,
            reload=False,  # Set to True for development
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server startup failed", error=str(e))
        raise

if __name__ == "__main__":
    main()
