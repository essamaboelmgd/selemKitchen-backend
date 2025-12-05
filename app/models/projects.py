from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from app.models.units import UnitDocument

class ProjectCreateRequest(BaseModel):
    """طلب إنشاء مشروع جديد"""
    name: str = Field(..., description="اسم المشروع")
    description: Optional[str] = Field(default="", description="وصف المشروع")
    client_name: Optional[str] = Field(default="", description="اسم العميل")

class ProjectUpdateRequest(BaseModel):
    """طلب تحديث مشروع"""
    name: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None

class ProjectResponse(BaseModel):
    """نموذج المشروع"""
    project_id: str
    name: str
    description: Optional[str] = ""
    client_name: Optional[str] = ""
    units: List[UnitDocument] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

class ProjectDocument(BaseModel):
    """نموذج المشروع المحفوظ في MongoDB"""
    _id: str
    name: str
    description: Optional[str] = ""
    client_name: Optional[str] = ""
    unit_ids: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None