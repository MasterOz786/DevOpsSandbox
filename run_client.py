#!/usr/bin/env python3
"""
DevOps Agent Client Launcher
"""

import sys
import argparse
from client import DevOpsTerminalClient
from config import CLIENT_HOST, CLIENT_PORT

def main():
    """Launch the DevOps Agent client"""
    parser = argparse.ArgumentParser(description="DevOps Agent Terminal Client")
    parser.add_argument("--host", default=CLIENT_HOST, 
                       help=f"Server host (default: {CLIENT_HOST})")
    parser.add_argument("--port", type=int, default=CLIENT_PORT, 
                       help=f"Server port (default: {CLIENT_PORT})")
    
    args = parser.parse_args()
    
    try:
        client = DevOpsTerminalClient(host=args.host, port=args.port)
        client.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
        sys.exit(0)
    except Exception as e:
        print(f"\nClient error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
