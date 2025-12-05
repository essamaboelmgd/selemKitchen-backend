"""
Service for handling authentication and authorization
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import secrets
from app.models.auth import (
    UserCreateRequest, UserLoginRequest, UserDocument, 
    Token, TokenData, UserRole, SubscriptionPlan, DeviceInfo
)
from app.database import get_database
from fastapi import HTTPException, status
import jwt
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours (1 day)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def create_user(request: UserCreateRequest) -> UserDocument:
    """Create a new user"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    # Check if user already exists
    existing_user = await db.users.find_one({"phone": request.phone})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this phone number already exists"
        )
    
    # Hash password
    hashed_password = get_password_hash(request.password)
    
    # Create default subscription based on role
    if request.role == UserRole.ADMIN:
        subscription = SubscriptionPlan(
            max_units_per_month=1000,
            max_devices=5,
            is_unlimited_units=True,
            is_unlimited_devices=True
        )
    else:
        subscription = SubscriptionPlan(
            max_units_per_month=3,
            max_devices=1
        )
    
    # Create user document
    user_id = f"user_{secrets.token_hex(8).upper()}"
    user_doc = UserDocument(
        id=user_id,
        phone=request.phone,
        hashed_password=hashed_password,
        full_name=request.full_name,
        role=request.role,
        subscription=subscription,
        devices=[],
        created_at=datetime.utcnow()
    )
    
    # Save to database
    user_dict = user_doc.model_dump()
    user_dict['_id'] = user_dict.pop('id')
    await db.users.insert_one(user_dict)
    
    return user_doc

async def authenticate_user(phone: str, password: str, device_id: str, device_name: str = "", ip_address: str = "") -> Optional[Dict[str, Any]]:
    """Authenticate a user and return token and user data"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    # Find user
    user_doc = await db.users.find_one({"phone": phone})
    if not user_doc:
        return None
    
    user = UserDocument(**user_doc)
    
    # Verify password
    if not verify_password(password, user.hashed_password):
        return None
    
    # Check device limit for non-admin users
    if user.role != UserRole.ADMIN:
        active_devices = [d for d in user.devices if d.is_active]
        if len(active_devices) >= user.subscription.max_devices and not user.subscription.is_unlimited_devices:
            # Check if this device already exists
            existing_device = next((d for d in user.devices if d.device_id == device_id), None)
            if not existing_device:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"You have reached the maximum number of devices ({user.subscription.max_devices})"
                )
    
    # Update or add device
    device_exists = False
    updated_devices = []
    for device in user.devices:
        if device.device_id == device_id:
            # Update existing device
            device.last_login = datetime.utcnow()
            device.is_active = True
            device.device_name = device_name or device.device_name
            device.ip_address = ip_address or device.ip_address
            device_exists = True
        updated_devices.append(device)
    
    if not device_exists:
        # Add new device
        new_device = DeviceInfo(
            device_id=device_id,
            device_name=device_name,
            ip_address=ip_address,
            last_login=datetime.utcnow(),
            is_active=True
        )
        updated_devices.append(new_device)
    
    # Update user devices
    await db.users.update_one(
        {"_id": user.id},
        {"$set": {"devices": [d.model_dump() for d in updated_devices], "updated_at": datetime.utcnow()}}
    )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    return {
        "token": Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            role=user.role
        ),
        "user": user
    }

async def get_user_by_id(user_id: str) -> Optional[UserDocument]:
    """Get user by ID"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        return None
    
    return UserDocument(**user_doc)

async def update_user_subscription(user_id: str, subscription: SubscriptionPlan) -> bool:
    """Update user subscription (admin only)"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"subscription": subscription.model_dump(), "updated_at": datetime.utcnow()}}
    )
    
    return result.modified_count > 0

async def deactivate_device(user_id: str, device_id: str) -> bool:
    """Deactivate a user device (admin only)"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        return False
    
    user = UserDocument(**user_doc)
    updated_devices = []
    device_found = False
    
    for device in user.devices:
        if device.device_id == device_id:
            device.is_active = False
            device_found = True
        updated_devices.append(device)
    
    if not device_found:
        return False
    
    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"devices": [d.model_dump() for d in updated_devices], "updated_at": datetime.utcnow()}}
    )
    
    return result.modified_count > 0

async def get_user_units_count(user_id: str, period_days: int = 30) -> int:
    """Get the number of units created by user in the specified period"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    # Calculate date range
    from_date = datetime.utcnow() - timedelta(days=period_days)
    
    # Count units created by user in the period
    count = await db.units.count_documents({
        "created_by": user_id,
        "created_at": {"$gte": from_date}
    })
    
    return count