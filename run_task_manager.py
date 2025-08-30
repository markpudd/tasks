#!/usr/bin/env python3
"""
Task Manager - Entry Point Script

This script provides an easy way to run the task manager application
without needing to install it as a package.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from task_manager.cli.main_cli import main

if __name__ == "__main__":
    main()