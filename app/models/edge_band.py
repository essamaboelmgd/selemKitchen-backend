from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum

class EdgeType(str, Enum):
    """نوع الشريط"""
    WOOD = "wood"  # خشبي
    PVC = "pvc"  # PVC

class EdgeDetail(BaseModel):
    """تفاصيل حافة واحدة"""
    edge: str = Field(description="اسم الحافة (top, bottom, left, right)")
    length_mm: float = Field(description="طول الحافة بالمليمتر")
    length_m: float = Field(description="طول الحافة بالمتر")
    edge_type: EdgeType = Field(default=EdgeType.PVC, description="نوع الشريط")
    has_edge: bool = Field(description="هل الحافة تحتاج شريط")

class EdgeBandPart(BaseModel):
    """تفاصيل الشريط لقطعة واحدة"""
    part_name: str = Field(description="اسم القطعة")
    qty: int = Field(description="الكمية")
    edges: List[EdgeDetail] = Field(description="قائمة الحواف")
    total_edge_m: float = Field(description="إجمالي متر الشريط للقطعة (مع الكمية)")
    edge_type: EdgeType = Field(default=EdgeType.PVC, description="نوع الشريط المستخدم")

class EdgeBreakdownResponse(BaseModel):
    """نتيجة توزيع الشريط"""
    unit_id: str = Field(description="معرف الوحدة")
    parts: List[EdgeBandPart] = Field(description="قائمة القطع مع تفاصيل الشريط")
    total_edge_m: float = Field(description="إجمالي متر الشريط للوحدة")
    total_cost: Optional[float] = Field(default=None, description="التكلفة الإجمالية للشريط")
    cost_breakdown: Optional[Dict[str, float]] = Field(
        default=None,
        description="تفاصيل التكلفة حسب نوع الشريط"
    )

