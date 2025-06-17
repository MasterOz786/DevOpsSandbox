#!/usr/bin/env python3
"""
DevOps Terminal Agent - Main Entry Point
Provides options to run server or client components
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_server():
    """Launch the FastAPI server"""
    print("🚀 Starting DevOps Agent Server...")
    subprocess.run([sys.executable, "run_server.py"])

def run_client():
    """Launch the terminal client"""
    print("🖥️  Starting DevOps Agent Client...")
    subprocess.run([sys.executable, "run_client.py"])

def main():
    parser = argparse.ArgumentParser(description="DevOps Terminal Agent")
    parser.add_argument("mode", choices=["server", "client"], 
                       help="Run mode: server or client")
    parser.add_argument("--host", default="localhost", 
                       help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, 
                       help="Server port (default: 8000)")
    
    args = parser.parse_args()
    
    if args.mode == "server":
        run_server()
    elif args.mode == "client":
        run_client()

if __name__ == "__main__":
    main()
