from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.models.units import Part, UnitType

class InternalCounterPart(BaseModel):
    """قطعة داخلية من الكونتر"""
    name: str = Field(description="اسم القطعة (مثل: drawer_bottom, mirror_front, internal_shelf)")
    type: str = Field(description="نوع القطعة (drawer, mirror, shelf, base)")
    width_mm: float = Field(description="العرض بالمليمتر")
    height_mm: float = Field(description="الارتفاع بالمليمتر")
    depth_mm: Optional[float] = Field(default=None, description="العمق بالمليمتر")
    qty: int = Field(description="الكمية")
    cutting_dimensions: Optional[Dict[str, float]] = Field(
        default=None,
        description="مقاسات القص التفصيلية"
    )
    area_m2: Optional[float] = Field(default=None, description="المساحة بالمتر المربع")
    edge_band_m: Optional[float] = Field(default=None, description="متر الشريط المطلوب")

class InternalCounterOptions(BaseModel):
    """خيارات القطع الداخلية"""
    add_mirror: bool = Field(default=False, description="إضافة مرآة أمامية")
    add_base: bool = Field(default=True, description="إضافة قاعدة داخلية")
    add_internal_shelf: bool = Field(default=False, description="إضافة رف داخلي")
    drawer_count: int = Field(default=0, ge=0, description="عدد الأدراج")
    back_clearance_mm: Optional[float] = Field(default=None, description="المسافة الخلفية (مم)")
    expansion_gap_mm: Optional[float] = Field(default=3, description="مسافة التمدد (مم)")

class InternalCounterRequest(BaseModel):
    """طلب حساب القطع الداخلية"""
    options: Optional[InternalCounterOptions] = Field(
        default_factory=InternalCounterOptions,
        description="خيارات القطع الداخلية"
    )

class InternalCounterResponse(BaseModel):
    """نتيجة حساب القطع الداخلية"""
    unit_id: str = Field(description="معرف الوحدة")
    unit_type: UnitType = Field(description="نوع الوحدة")
    parts: List[InternalCounterPart] = Field(description="قائمة القطع الداخلية")
    total_edge_band_m: float = Field(description="إجمالي متر الشريط")
    total_area_m2: float = Field(description="إجمالي المساحة بالمتر المربع")
    material_usage: Dict[str, float] = Field(
        default_factory=dict,
        description="استخدام المواد"
    )

