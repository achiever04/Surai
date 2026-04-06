"""
User model for authentication and authorization
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
from app.core.timezone import utc_now

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=False)
    hashed_password = Column(String(200), nullable=False)
    
    # Role-based access control
    role = Column(String(20), default="operator")  # admin, operator, auditor
    
    # Status
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_login = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Metadata
    created_by = Column(String(50), nullable=True)
    
    def __repr__(self):
        return f""
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        role_permissions = {
            "admin": ["read", "write", "delete", "manage_users", "view_audit"],
            "operator": ["read", "write", "view_detections", "manage_watchlist"],
            "auditor": ["read", "view_audit", "view_blockchain"]
        }
        return permission in role_permissions.get(self.role, [])