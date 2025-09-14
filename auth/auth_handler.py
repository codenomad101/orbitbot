import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from typing import Optional, Dict, Any
import os
from fastapi import HTTPException, status
import json
from pathlib import Path

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# User data file path
USER_DATA_FILE = Path("data/users.json")

class AuthHandler:
    def __init__(self):
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        self.access_token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
        self.ensure_user_data_file()
    
    def ensure_user_data_file(self):
        """Ensure the user data file exists with default admin user"""
        USER_DATA_FILE.parent.mkdir(exist_ok=True)
        
        if not USER_DATA_FILE.exists():
            # Create default admin user
            default_users = {
                "admin": {
                    "username": "admin",
                    "email": "admin@example.com",
                    "hashed_password": self.get_password_hash("admin123"),
                    "role": "admin",
                    "is_active": True,
                    "created_at": datetime.now().isoformat()
                }
            }
            
            with open(USER_DATA_FILE, "w") as f:
                json.dump(default_users, f, indent=2)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return payload
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def load_users(self) -> Dict[str, Dict]:
        """Load users from file"""
        try:
            with open(USER_DATA_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_users(self, users: Dict[str, Dict]):
        """Save users to file"""
        with open(USER_DATA_FILE, "w") as f:
            json.dump(users, f, indent=2)
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate a user"""
        users = self.load_users()
        user = users.get(username)
        
        if not user or not user.get("is_active", True):
            return None
        
        if not self.verify_password(password, user["hashed_password"]):
            return None
        
        return user
    
    def create_user(self, username: str, email: str, password: str, role: str = "user") -> bool:
        """Create a new user"""
        users = self.load_users()
        
        if username in users:
            return False  # User already exists
        
        hashed_password = self.get_password_hash(password)
        new_user = {
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "role": role,
            "is_active": True,
            "created_at": datetime.now().isoformat()
        }
        
        users[username] = new_user
        self.save_users(users)
        return True
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        users = self.load_users()
        return users.get(username)
    
    def update_user_role(self, username: str, role: str) -> bool:
        """Update user role (admin only)"""
        users = self.load_users()
        if username not in users:
            return False
        
        users[username]["role"] = role
        self.save_users(users)
        return True
    
    def deactivate_user(self, username: str) -> bool:
        """Deactivate a user (admin only)"""
        users = self.load_users()
        if username not in users:
            return False
        
        users[username]["is_active"] = False
        self.save_users(users)
        return True

# Global auth handler instance
auth_handler = AuthHandler()

