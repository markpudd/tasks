#!/usr/bin/env python3
"""
Script to create new users for the Task Manager application
"""
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from task_manager.core.auth import UserManager

def create_user():
    user_manager = UserManager()
    
    print("=== Task Manager - Create New User ===")
    print()
    
    username = input("Enter username: ").strip()
    if not username:
        print("Username is required!")
        return
    
    if user_manager.get_user(username):
        print(f"User '{username}' already exists!")
        return
    
    email = input("Enter email: ").strip()
    if not email:
        print("Email is required!")
        return
    
    if user_manager.get_user_by_email(email):
        print(f"Email '{email}' is already in use!")
        return
    
    password = input("Enter password (min 6 chars): ").strip()
    if len(password) < 6:
        print("Password must be at least 6 characters long!")
        return
    
    full_name = input("Enter full name (optional): ").strip()
    
    # Create the user
    user = user_manager.create_user(username, email, password, full_name if full_name else None)
    
    if user:
        print()
        print("✅ User created successfully!")
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Full Name: {user.full_name or 'Not provided'}")
        print(f"User ID: {user.id}")
    else:
        print("❌ Failed to create user!")

if __name__ == "__main__":
    create_user()