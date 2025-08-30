#!/usr/bin/env python3
"""
Task Manager Web UI - Entry Point Script

This script starts the web-based user interface for the task manager application.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from task_manager.web.app import app, socketio, load_config

if __name__ == "__main__":
    print("Starting Task Manager Web UI...")
    print("Loading configuration...")
    load_config()
    print("Web UI will be available at: http://localhost:5001")
    print("Press Ctrl+C to stop the server")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)