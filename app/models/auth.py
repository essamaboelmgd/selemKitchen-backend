from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
import re

class UserRole(str, Enum):
    """نوع المستخدم"""
    ADMIN = "admin"  # مدير النظام
    USER = "user"    # مستخدم عادي

class DeviceInfo(BaseModel):
    """معلومات الجهاز"""
    device_id: str = Field(description="معرف الجهاز")
    device_name: Optional[str] = Field(default="", description="اسم الجهاز")
    ip_address: Optional[str] = Field(default="", description="عنوان IP")
    last_login: datetime = Field(description="آخر تسجيل دخول")
    is_active: bool = Field(default=True, description="هل الجهاز مفعل")

class SubscriptionPlan(BaseModel):
    """خطة الاشتراك"""
    max_units_per_month: int = Field(default=3, description="الحد الأقصى للوحدات شهرياً")
    max_devices: int = Field(default=1, description="الحد الأقصى للأجهزة")
    validity_days: Optional[int] = Field(default=None, description="مدة الصلاحية بالأيام")
    is_unlimited_units: bool = Field(default=False, description="عدد غير محدود من الوحدات")
    is_unlimited_devices: bool = Field(default=False, description="عدد غير محدود من الأجهزة")

class UserCreateRequest(BaseModel):
    """طلب إنشاء مستخدم جديد"""
    phone: str = Field(description="رقم الهاتف")
    password: str = Field(min_length=8, description="كلمة المرور")
    full_name: str = Field(description="الاسم الكامل")
    role: UserRole = Field(default=UserRole.USER, description="نوع المستخدم")
    
    @validator('phone')
    def validate_phone(cls, v):
        # Remove any spaces, dashes, or parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        # Check if it's a valid Egyptian phone number (11 digits starting with 01)
        if not re.match(r'^01[0-9]{9}$', cleaned):
            raise ValueError('رقم الهاتف غير صحيح')
        return cleaned

class UserLoginRequest(BaseModel):
    """طلب تسجيل دخول"""
    phone: str = Field(description="رقم الهاتف")
    password: str = Field(description="كلمة المرور")
    device_id: str = Field(description="معرف الجهاز")
    device_name: Optional[str] = Field(default="", description="اسم الجهاز")
    
    @validator('phone')
    def validate_phone(cls, v):
        # Remove any spaces, dashes, or parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        # Check if it's a valid Egyptian phone number (11 digits starting with 01)
        if not re.match(r'^01[0-9]{9}$', cleaned):
            raise ValueError('رقم الهاتف غير صحيح')
        return cleaned

class UserResponse(BaseModel):
    """نموذج المستخدم"""
    user_id: str
    phone: str
    full_name: str
    role: UserRole
    subscription: SubscriptionPlan
    devices: List[DeviceInfo] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

class UserDocument(BaseModel):
    """نموذج المستخدم المحفوظ في MongoDB"""
    id: str = Field(alias="_id")
    
    class Config:
        # Allow population by field name
        populate_by_name = True
        # Extra fields from MongoDB will be ignored
        extra = "ignore"
    phone: str
    hashed_password: str
    full_name: str
    role: UserRole
    subscription: SubscriptionPlan
    devices: List[DeviceInfo] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

class Token(BaseModel):
    """نموذج التوكن"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration
    user_id: str
    role: UserRole

class TokenData(BaseModel):
    """بيانات التوكن"""
    user_id: Optional[str] = None
    role: Optional[UserRole] = None