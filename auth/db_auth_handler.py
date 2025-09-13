import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from typing import Optional, Dict, Any
import os
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from database.config import get_db
from database.services import UserService, LogService
from database.models import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

class DatabaseAuthHandler:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.log_service = LogService(db)
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        self.access_token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    
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
        # Ensure subject is a string
        if "sub" in to_encode:
            to_encode["sub"] = str(to_encode["sub"])
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id_str: str = payload.get("sub")
            if user_id_str is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Convert string user_id back to int for database lookup
            payload["sub"] = int(user_id_str)
            return payload
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user"""
        user = self.user_service.get_user_by_username(username)
        
        if not user or not user.is_active:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        self.user_service.update_last_login(user.id)
        
        # Log login
        self.log_service.create_log(
            action="login",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id
        )
        
        return user
    
    def create_user(self, username: str, email: str, password: str, role: str = "user") -> bool:
        """Create a new user"""
        hashed_password = self.get_password_hash(password)
        user = self.user_service.create_user(username, email, hashed_password, role)
        
        if user:
            # Log user creation
            self.log_service.create_log(
                action="user_created",
                user_id=user.id,
                resource_type="user",
                resource_id=user.id,
                details={"username": username, "email": email, "role": role}
            )
            return True
        return False
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.user_service.get_user_by_username(username)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.user_service.get_user_by_id(user_id)
    
    def update_user_role(self, user_id: int, role: str) -> bool:
        """Update user role (admin only)"""
        success = self.user_service.update_user_role(user_id, role)
        
        if success:
            # Log role update
            self.log_service.create_log(
                action="role_updated",
                user_id=user_id,
                resource_type="user",
                resource_id=user_id,
                details={"new_role": role}
            )
        
        return success
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user (admin only)"""
        success = self.user_service.deactivate_user(user_id)
        
        if success:
            # Log user deactivation
            self.log_service.create_log(
                action="user_deactivated",
                user_id=user_id,
                resource_type="user",
                resource_id=user_id
            )
        
        return success
    
    def get_all_users(self) -> list:
        """Get all users"""
        return self.user_service.get_all_users()
    
    def create_default_admin(self):
        """Create default admin user if it doesn't exist"""
        admin_user = self.user_service.get_user_by_username("admin")
        
        if not admin_user:
            success = self.create_user("admin", "admin@example.com", "admin123", "admin")
            if success:
                print("✅ Default admin user created successfully")
                print("   Username: admin")
                print("   Password: admin123")
                print("   ⚠️  Please change the default password after first login!")
            else:
                print("❌ Failed to create default admin user")
        else:
            print("ℹ️  Admin user already exists")

def get_auth_handler(db: Session = Depends(get_db)) -> DatabaseAuthHandler:
    """Get database auth handler instance"""
    return DatabaseAuthHandler(db)
