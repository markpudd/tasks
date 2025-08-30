import json
import os
import bcrypt
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    password_hash: str
    full_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    is_active: bool = True

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    @classmethod
    def create_user(cls, username: str, email: str, password: str, full_name: Optional[str] = None) -> "User":
        """Create a new user with hashed password"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        return cls(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        user_data = data.copy()
        user_data["created_at"] = datetime.fromisoformat(user_data["created_at"])
        if user_data["last_login"]:
            user_data["last_login"] = datetime.fromisoformat(user_data["last_login"])
        return cls(**user_data)
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Return user data without password hash"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active
        }

class UserManager:
    def __init__(self, storage_file: str = "users.json"):
        self.storage_file = storage_file
        self.users: Dict[str, User] = {}
        self.load_users()
        
        # Create default admin user if no users exist
        if not self.users:
            self._create_default_user()
    
    def load_users(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    users_data = json.load(f)
                    for user_data in users_data:
                        user = User.from_dict(user_data)
                        self.users[user.username] = user
            except Exception as e:
                print(f"Error loading users: {e}")
    
    def save_users(self):
        try:
            users_data = [user.to_dict() for user in self.users.values()]
            with open(self.storage_file, 'w') as f:
                json.dump(users_data, f, indent=2)
        except Exception as e:
            print(f"Error saving users: {e}")
    
    def _create_default_user(self):
        """Create a default admin user"""
        default_user = User.create_user(
            username="admin",
            email="admin@taskmanager.local",
            password="admin123",
            full_name="Administrator"
        )
        self.users[default_user.username] = default_user
        self.save_users()
        print("Created default user: admin / admin123")
    
    def create_user(self, username: str, email: str, password: str, full_name: Optional[str] = None) -> Optional[User]:
        """Create a new user"""
        if username in self.users:
            return None  # User already exists
        
        if self.get_user_by_email(email):
            return None  # Email already exists
        
        user = User.create_user(username, email, password, full_name)
        self.users[username] = user
        self.save_users()
        return user
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password"""
        user = self.users.get(username)
        if user and user.is_active and user.check_password(password):
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            self.save_users()
            return user
        return None
    
    def get_user(self, username: str) -> Optional[User]:
        """Get a user by username"""
        return self.users.get(username)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        for user in self.users.values():
            if user.email == email:
                return user
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID"""
        for user in self.users.values():
            if user.id == user_id:
                return user
        return None
    
    def update_user(self, username: str, **kwargs) -> Optional[User]:
        """Update user information"""
        user = self.users.get(username)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key) and key != 'password_hash':
                setattr(user, key, value)
        
        self.save_users()
        return user
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change user password"""
        user = self.users.get(username)
        if not user or not user.check_password(old_password):
            return False
        
        user.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        self.save_users()
        return True
    
    def deactivate_user(self, username: str) -> bool:
        """Deactivate a user account"""
        user = self.users.get(username)
        if not user:
            return False
        
        user.is_active = False
        self.save_users()
        return True
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        return list(self.users.values())