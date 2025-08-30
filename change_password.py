#!/usr/bin/env python3
"""
Script to change password for existing users
"""
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from task_manager.core.auth import UserManager

def change_password():
    user_manager = UserManager()
    
    print("=== Task Manager - Change Password ===")
    print()
    
    username = input("Enter username: ").strip()
    if not username:
        print("Username is required!")
        return
    
    user = user_manager.get_user(username)
    if not user:
        print(f"User '{username}' not found!")
        return
    
    old_password = input("Enter current password: ").strip()
    new_password = input("Enter new password (min 6 chars): ").strip()
    
    if len(new_password) < 6:
        print("New password must be at least 6 characters long!")
        return
    
    confirm_password = input("Confirm new password: ").strip()
    if new_password != confirm_password:
        print("Passwords don't match!")
        return
    
    # Change the password
    if user_manager.change_password(username, old_password, new_password):
        print()
        print("✅ Password changed successfully!")
        print(f"Username: {username}")
        print("You can now login with your new password.")
    else:
        print("❌ Failed to change password! Check your current password.")

if __name__ == "__main__":
    change_password()