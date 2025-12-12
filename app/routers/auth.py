from fastapi import APIRouter, HTTPException, status, Depends, Request, Header
from typing import List
import uuid
from datetime import datetime
from app.models.auth import (
    UserCreateRequest, UserLoginRequest, UserResponse, 
    Token, SubscriptionPlan, UserRole, UserDocument
)
from app.services.auth_service import (
    create_user, authenticate_user, get_user_by_id, 
    update_user_subscription, deactivate_device, get_user_units_count
)
from app.services.auth_service import TokenData
import jwt
from app.services.auth_service import SECRET_KEY, ALGORITHM
from app.database import get_database

router = APIRouter()

async def get_current_user_from_token(token: str) -> TokenData:
    """Get current user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, role=role)
    except jwt.PyJWTError:
        raise credentials_exception
    return token_data

async def get_admin_user(token: str) -> TokenData:
    """Get admin user from token"""
    token_data = await get_current_user_from_token(token)
    if token_data.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return token_data

async def get_current_user(authorization: str = Header(None)) -> UserResponse:
    """Dependency to get current user from token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header", 
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = authorization[len("Bearer "):]
    token_data = await get_current_user_from_token(token)
    
    user = await get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return UserResponse(
        user_id=user.id,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        subscription=user.subscription,
        devices=user.devices,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: UserCreateRequest):
    """
    تسجيل مستخدم جديد
    
    Parameters:
    - request: بيانات المستخدم (رقم الهاتف، كلمة المرور، الاسم، النوع)
    
    Returns:
    - UserResponse: تفاصيل المستخدم المنشأ
    """
    try:
        user = await create_user(request)
        
        return UserResponse(
            user_id=user.id,
            phone=user.phone,
            full_name=user.full_name,
            role=user.role,
            subscription=user.subscription,
            devices=user.devices,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login_user(request: UserLoginRequest, req: Request):
    """
    تسجيل دخول المستخدم
    
    Parameters:
    - request: بيانات تسجيل الدخول (رقم الهاتف، كلمة المرور، معرف الجهاز)
    
    Returns:
    - Token: توكن الوصول
    """
    try:
        # Get IP address
        ip_address = req.client.host if req.client else ""
        
        auth_result = await authenticate_user(
            request.phone, 
            request.password, 
            request.device_id,
            request.device_name,
            ip_address
        )
        
        if not auth_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect phone number or password"
            )
        
        return auth_result["token"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error logging in: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(authorization: str = Header(None)):
    """
    جلب تفاصيل المستخدم الحالي
    
    Returns:
    - UserResponse: تفاصيل المستخدم
    """
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = authorization[len("Bearer "):]
        token_data = await get_current_user_from_token(token)
        
        user = await get_user_by_id(token_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            user_id=user.id,
            phone=user.phone,
            full_name=user.full_name,
            role=user.role,
            subscription=user.subscription,
            devices=user.devices,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user: {str(e)}"
        )

@router.get("/users", response_model=List[UserResponse])
async def list_users(authorization: str = Header(None)):
    """
    جلب قائمة بجميع المستخدمين (مدير النظام فقط)
    
    Returns:
    - List[UserResponse]: قائمة بجميع المستخدمين
    """
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = authorization[len("Bearer "):]
        token_data = await get_current_user_from_token(token)
        
        # Only admin users can list all users
        if token_data.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can list users"
            )
        
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        users_cursor = db.users.find({})
        users = []
        
        async for user_doc in users_cursor:
            # Convert ObjectId to string
            if "_id" in user_doc:
                user_doc["id"] = str(user_doc["_id"])
                del user_doc["_id"]
            
            # Create UserDocument and then UserResponse
            user_document = UserDocument(**user_doc)
            users.append(UserResponse(
                user_id=user_document.id,
                phone=user_document.phone,
                full_name=user_document.full_name,
                role=user_document.role,
                subscription=user_document.subscription,
                devices=user_document.devices,
                created_at=user_document.created_at,
                updated_at=user_document.updated_at
            ))
        
        return users
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing users: {str(e)}"
        )

@router.put("/users/{user_id}/subscription", response_model=bool)
async def update_user_subscription_plan(
    user_id: str, 
    subscription: SubscriptionPlan,
    authorization: str = Header(None)
):
    """
    تحديث خطة اشتراك المستخدم (مدير النظام فقط)
    
    Parameters:
    - user_id: معرف المستخدم
    - subscription: بيانات خطة الاشتراك الجديدة
    
    Returns:
    - bool: نتيجة العملية
    """
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = authorization[len("Bearer "):]
        await get_admin_user(token)
        
        result = await update_user_subscription(user_id, subscription)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating subscription: {str(e)}"
        )

@router.delete("/users/{user_id}/devices/{device_id}", response_model=bool)
async def deactivate_user_device(
    user_id: str, 
    device_id: str,
    authorization: str = Header(None)
):
    """
    تعطيل جهاز مستخدم (مدير النظام فقط)
    
    Parameters:
    - user_id: معرف المستخدم
    - device_id: معرف الجهاز
    
    Returns:
    - bool: نتيجة العملية
    """
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = authorization[len("Bearer "):]
        await get_admin_user(token)
        
        result = await deactivate_device(user_id, device_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or device not found"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deactivating device: {str(e)}"
        )

@router.get("/users/{user_id}/units/count", response_model=int)
async def get_user_units_count_endpoint(
    user_id: str,
    period_days: int = 30,
    authorization: str = Header(None)
):
    """
    جلب عدد الوحدات التي أنشأها المستخدم خلال فترة معينة
    
    Parameters:
    - user_id: معرف المستخدم
    - period_days: عدد الأيام (الافتراضي: 30 يوم)
    
    Returns:
    - int: عدد الوحدات
    """
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = authorization[len("Bearer "):]
        token_data = await get_current_user_from_token(token)
        
        # Check if user is requesting their own data or is admin
        if token_data.user_id != user_id and token_data.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this user's data"
            )
        
        count = await get_user_units_count(user_id, period_days)
        return count
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving units count: {str(e)}"
        )


@router.get("/users/{user_id}/subscription-status")
async def get_user_subscription_status(
    user_id: str,
    authorization: str = Header(None)
):
    """
    جلب حالة اشتراك المستخدم وعدد الوحدات المتاحة
    
    Parameters:
    - user_id: معرف المستخدم
    - authorization: Header - توكن المستخدم
    
    Returns:
    - dict: حالة الاشتراك وعدد الوحدات المتاحة
    """
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = authorization[len("Bearer "):]
        token_data = await get_current_user_from_token(token)
        
        # Check if user is requesting their own data or is admin
        if token_data.user_id != user_id and token_data.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this user's data"
            )
        
        # Get user data
        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user's current unit count for the month
        current_units_count = await get_user_units_count(user_id, 30)
        
        # Calculate remaining units
        if user.subscription.is_unlimited_units:
            remaining_units = "unlimited"
        else:
            remaining_units = max(0, user.subscription.max_units_per_month - current_units_count)
        
        return {
            "subscription": {
                "max_units_per_month": user.subscription.max_units_per_month,
                "is_unlimited_units": user.subscription.is_unlimited_units,
                "current_units_used": current_units_count,
                "remaining_units": remaining_units
            },
            "can_create_units": user.subscription.is_unlimited_units or current_units_count < user.subscription.max_units_per_month
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving subscription status: {str(e)}"
        )
