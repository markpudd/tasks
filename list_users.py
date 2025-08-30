#!/usr/bin/env python3
"""
Script to list all users in the Task Manager application
"""
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from task_manager.core.auth import UserManager

def list_users():
    user_manager = UserManager()
    
    print("=== Task Manager - User List ===")
    print()
    
    users = user_manager.get_all_users()
    
    if not users:
        print("No users found.")
        return
    
    print(f"Found {len(users)} user(s):")
    print()
    
    for i, user in enumerate(users, 1):
        status = "Active" if user.is_active else "Inactive"
        print(f"{i}. Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Full Name: {user.full_name or 'Not provided'}")
        print(f"   Status: {status}")
        print(f"   Created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if user.last_login:
            print(f"   Last Login: {user.last_login.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"   Last Login: Never")
        print(f"   ID: {user.id}")
        print()

if __name__ == "__main__":
    list_users()