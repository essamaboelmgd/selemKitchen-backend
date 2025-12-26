from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ItemStatus(str, Enum):
    """حالة المنتج"""
    AVAILABLE = "available"  # متاح للبيع
    PENDING = "pending"     # في انتظار الموافقة
    SOLD = "sold"           # تم البيع
    RESERVED = "reserved"   # محجوز

class MarketplaceItemCreate(BaseModel):
    """طلب إضافة منتج جديد"""
    title: str = Field(..., min_length=3, description="عنوان المنتج")
    description: str = Field(..., description="وصف المنتج")
    price: float = Field(..., gt=0, description="السعر")
    quantity: int = Field(default=1, gt=0, description="الكمية المتاحة")
    unit: str = Field(default="item", description="وحدة القياس (مثلا: قطعة، متر، لوح)")
    images: List[str] = Field(default_factory=list, description="روابط صور المنتج")
    location: Optional[str] = Field(default="", description="المعيشة / العنوان")
    
    @validator('images')
    def validate_images_count(cls, v):
        if len(v) > 3:
            raise ValueError('لا يمكن إضافة أكثر من 3 صور للمنتج')
        return v

class MarketplaceItemUpdate(BaseModel):
    """طلب تحديث منتج"""
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    unit: Optional[str] = None
    images: Optional[List[str]] = None
    status: Optional[ItemStatus] = None
    location: Optional[str] = None
    
    @validator('images')
    def validate_images_count(cls, v):
        if v is not None and len(v) > 3:
            raise ValueError('لا يمكن إضافة أكثر من 3 صور للمنتج')
        return v

class MarketplaceItemResponse(BaseModel):
    """عرض بيانات المنتج"""
    item_id: str
    seller_id: str
    seller_name: Optional[str] = None # To display seller name
    seller_phone: Optional[str] = None # To display seller phone
    title: str
    description: str
    price: float
    quantity: int
    unit: str
    images: List[str]
    status: ItemStatus
    location: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

class MarketplaceItemDocument(BaseModel):
    """نموذج المنتج في قاعدة البيانات"""
    id: str = Field(alias="_id")
    seller_id: str
    buyer_id: Optional[str] = None
    title: str
    description: str
    price: float
    quantity: int
    unit: str
    images: List[str] = Field(default_factory=list)
    status: ItemStatus = ItemStatus.AVAILABLE
    location: Optional[str] = ""
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        extra = "ignore"
