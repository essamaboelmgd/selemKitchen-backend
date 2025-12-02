from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.units import UnitType

class SummaryItem(BaseModel):
    """عنصر في الملخص - قطعة واحدة"""
    part_name: str = Field(description="اسم القطعة")
    description: Optional[str] = Field(default=None, description="وصف القطعة")
    width_mm: float = Field(description="العرض بالمليمتر")
    height_mm: float = Field(description="الارتفاع بالمليمتر")
    depth_mm: Optional[float] = Field(default=None, description="العمق بالمليمتر")
    qty: int = Field(description="الكمية")
    area_m2: Optional[float] = Field(default=None, description="المساحة بالمتر المربع")
    edge_band_m: Optional[float] = Field(default=None, description="متر الشريط للقطعة")

class SummaryRequest(BaseModel):
    """طلب توليد الملخص"""
    type: UnitType = Field(description="نوع الوحدة")
    width_mm: float = Field(gt=0, description="عرض الوحدة بالمليمتر")
    height_mm: float = Field(gt=0, description="ارتفاع الوحدة بالمليمتر")
    depth_mm: float = Field(gt=0, description="عمق الوحدة بالمليمتر")
    shelf_count: int = Field(ge=0, description="عدد الرفوف")
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="خيارات إضافية"
    )
    include_internal_counter: bool = Field(
        default=False,
        description="هل يتضمن القطع الداخلية"
    )
    internal_counter_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="خيارات القطع الداخلية"
    )

class SummaryResponse(BaseModel):
    """نتيجة الملخص"""
    summary_id: Optional[str] = Field(default=None, description="معرف الملخص")
    unit_id: Optional[str] = Field(default=None, description="معرف الوحدة")
    type: UnitType = Field(description="نوع الوحدة")
    unit_dimensions: Dict[str, float] = Field(
        description="أبعاد الوحدة (width_mm, height_mm, depth_mm)"
    )
    shelf_count: int = Field(description="عدد الرفوف")
    items: List[SummaryItem] = Field(description="قائمة القطع في الملخص")
    totals: Dict[str, float] = Field(
        description="الإجماليات (total_area_m2, total_edge_band_m, etc.)"
    )
    material_usage: Dict[str, float] = Field(
        description="استخدام المواد"
    )
    costs: Dict[str, float] = Field(
        description="التكاليف (material_cost, edge_band_cost, total_cost)"
    )
    generated_at: datetime = Field(description="تاريخ توليد الملخص")

