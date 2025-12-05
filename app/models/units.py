from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any
from datetime import datetime
from enum import Enum

class UnitType(str, Enum):
    """نوع الوحدة"""
    GROUND = "ground"  # أرضي
    WALL = "wall"  # علوي
    DOUBLE_DOOR = "double_door"  # ضلفتين
    SINK_GROUND = "sink_ground"  # أرضي بحوض

class EdgeDistribution(BaseModel):
    """توزيع الشريط على الحواف"""
    top: bool = Field(default=True, description="أعلى")
    left: bool = Field(default=True, description="شمال")
    right: bool = Field(default=True, description="يمين")
    bottom: bool = Field(default=True, description="أسفل")

class Part(BaseModel):
    """قطعة من الوحدة"""
    name: str = Field(description="اسم القطعة")
    width_cm: float = Field(description="العرض بالسنتيمتر")
    height_cm: float = Field(description="الارتفاع بالسنتيمتر")
    depth_cm: Optional[float] = Field(default=None, description="العمق بالسنتيمتر (للقطع ثلاثية الأبعاد)")
    qty: int = Field(description="الكمية")
    edge_distribution: Optional[EdgeDistribution] = Field(default=None, description="توزيع الشريط")
    area_m2: Optional[float] = Field(default=None, description="المساحة بالمتر المربع")
    edge_band_m: Optional[float] = Field(default=None, description="متر الشريط المطلوب")

class UnitCalculateRequest(BaseModel):
    """طلب حساب الوحدة"""
    type: UnitType = Field(description="نوع الوحدة: ground, wall, double_door, sink_ground")
    width_cm: float = Field(gt=0, description="عرض الوحدة بالسنتيمتر")
    height_cm: float = Field(gt=0, description="ارتفاع الوحدة بالسنتيمتر")
    depth_cm: float = Field(gt=0, description="عمق الوحدة بالسنتيمتر")
    shelf_count: int = Field(ge=0, description="عدد الرفوف")
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="خيارات إضافية (board_thickness_cm, back_clearance_cm, etc.)"
    )

class UnitCalculateResponse(BaseModel):
    """نتيجة حساب الوحدة"""
    unit_id: Optional[str] = Field(default=None, description="معرف الوحدة إذا تم الحفظ")
    type: UnitType
    width_cm: float
    height_cm: float
    depth_cm: float
    shelf_count: int
    parts: List[Part] = Field(description="قائمة القطع المحسوبة")
    total_edge_band_m: float = Field(description="إجمالي متر الشريط")
    total_area_m2: float = Field(description="إجمالي المساحة بالمتر المربع")
    material_usage: Dict[str, float] = Field(
        default_factory=dict,
        description="استخدام المواد (ألواح الخشب, شريط الحافة, etc.)"
    )
    cost_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="تفاصيل التكلفة لكل مادة"
    )
    total_cost: float = Field(default=0.0, description="التكلفة الإجمالية")

class UnitEstimateRequest(BaseModel):
    """طلب تقدير تكلفة الوحدة"""
    type: UnitType = Field(description="نوع الوحدة: ground, wall, double_door, sink_ground")
    width_cm: float = Field(gt=0)
    height_cm: float = Field(gt=0)
    depth_cm: float = Field(gt=0)
    shelf_count: int = Field(ge=0)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class UnitEstimateResponse(BaseModel):
    """نتيجة تقدير التكلفة"""
    unit_id: Optional[str] = None
    type: UnitType
    width_cm: float
    height_cm: float
    depth_cm: float
    shelf_count: int
    parts: List[Part]
    total_edge_band_m: float
    total_area_m2: float
    material_usage: Dict[str, float]
    cost_breakdown: Dict[str, float] = Field(
        description="تفاصيل التكلفة لكل مادة"
    )
    total_cost: float = Field(description="التكلفة الإجمالية")

class UnitDocument(BaseModel):
    """نموذج الوحدة المحفوظة في MongoDB"""
    id: Optional[str] = None
    type: UnitType
    width_cm: float
    height_cm: float
    depth_cm: float
    shelf_count: int
    parts_calculated: List[Dict]
    edge_band_m: float
    total_area_m2: float
    material_usage: Dict[str, float]
    price_estimate: Optional[float] = None
    project_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
