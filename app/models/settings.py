from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime

class MaterialPrice(BaseModel):
    price_per_sheet: Optional[float] = None
    sheet_size_m2: Optional[float] = None
    price_per_meter: Optional[float] = None
    price_per_unit: Optional[float] = None

class SettingsModel(BaseModel):
    """Pydantic model for Settings"""
    assembly_method: str = Field(default="bolt", description="طريقة التجميع")
    handle_type: str = Field(default="built-in", description="نوع المقبض")
    handle_recess_height_mm: int = Field(default=30, description="ارتفاع قطاع المقبض بالمليمتر")
    default_board_thickness_mm: int = Field(default=16, description="سمك الافتراضي للألواح بالمليمتر")
    back_panel_thickness_mm: int = Field(default=3, description="سمك لوح الظهر بالمليمتر")
    edge_overlap_mm: int = Field(default=2, description="مسافة التداخل للشريط بالمليمتر (للمفاصل)")
    back_clearance_mm: int = Field(default=3, description="مسافة الفراغ من الخلف للرفوف (مم)")
    top_clearance_mm: int = Field(default=5, description="المسافة العلوية للظهر (مم)")
    bottom_clearance_mm: int = Field(default=5, description="المسافة السفلية للظهر (مم)")
    side_overlap_mm: int = Field(default=0, description="تداخل الجوانب مع الظهر (مم)")
    sheet_size_m2: float = Field(default=2.4, description="حجم اللوح بالمتر المربع")
    materials: Dict[str, MaterialPrice] = Field(
        default_factory=dict,
        description="أسعار الخامات"
    )
    edge_types: Dict[str, str] = Field(
        default_factory=lambda: {"pvc": "PVC", "wood": "خشبي", "no_edge": "بدون شريط"},
        description="أنواع الحواف المتاحة"
    )
    default_unit_depth_by_type: Dict[str, int] = Field(
        default_factory=lambda: {"ground": 300, "wall": 250, "tall": 350},
        description="العمق الافتراضي حسب نوع الوحدة (مم)"
    )
    last_updated: Optional[datetime] = Field(default=None, description="تاريخ آخر تحديث")

    model_config = {
        "json_schema_extra": {
            "example": {
                "assembly_method": "bolt",
                "handle_type": "built-in",
                "handle_recess_height_mm": 30,
                "default_board_thickness_mm": 16,
                "back_panel_thickness_mm": 3,
                "edge_overlap_mm": 2,
                "back_clearance_mm": 3,
                "top_clearance_mm": 5,
                "bottom_clearance_mm": 5,
                "side_overlap_mm": 0,
                "sheet_size_m2": 2.4,
                "materials": {
                    "plywood_sheet": {
                        "price_per_sheet": 2500,
                        "sheet_size_m2": 2.4
                    },
                    "edge_band_per_meter": {
                        "price_per_meter": 10
                    }
                },
                "edge_types": {
                    "pvc": "PVC",
                    "wood": "خشبي",
                    "no_edge": "بدون شريط"
                },
                "default_unit_depth_by_type": {
                    "ground": 300,
                    "wall": 250,
                    "tall": 350
                }
            }
        }
    }

class SettingsUpdate(BaseModel):
    """
    Model for updating settings
    
    جميع الحقول Optional للسماح بالتحديث الجزئي.
    كل حقل يجب أن يطابق نوع البيانات في SettingsModel.
    """
    # الحقول الأساسية
    assembly_method: Optional[str] = Field(default=None, description="طريقة التجميع")
    handle_type: Optional[str] = Field(default=None, description="نوع المقبض")
    handle_recess_height_mm: Optional[int] = Field(default=None, description="ارتفاع قطاع المقبض بالمليمتر")
    default_board_thickness_mm: Optional[int] = Field(default=None, description="سمك الافتراضي للألواح بالمليمتر")
    
    # الحقول المتعلقة بالقياسات
    back_panel_thickness_mm: Optional[int] = Field(default=None, description="سمك لوح الظهر بالمليمتر")
    edge_overlap_mm: Optional[int] = Field(default=None, description="مسافة التداخل للشريط بالمليمتر (للمفاصل)")
    back_clearance_mm: Optional[int] = Field(default=None, description="مسافة الفراغ من الخلف للرفوف (مم)")
    top_clearance_mm: Optional[int] = Field(default=None, description="المسافة العلوية للظهر (مم)")
    bottom_clearance_mm: Optional[int] = Field(default=None, description="المسافة السفلية للظهر (مم)")
    side_overlap_mm: Optional[int] = Field(default=None, description="تداخل الجوانب مع الظهر (مم)")
    sheet_size_m2: Optional[float] = Field(default=None, description="حجم اللوح بالمتر المربع")
    
    # الحقول المعقدة
    materials: Optional[Dict[str, MaterialPrice]] = Field(default=None, description="أسعار الخامات")
    edge_types: Optional[Dict[str, str]] = Field(default=None, description="أنواع الحواف المتاحة")
    default_unit_depth_by_type: Optional[Dict[str, int]] = Field(default=None, description="العمق الافتراضي حسب نوع الوحدة (مم)")
    
    # ملاحظة: last_updated لا يُحدّث يدوياً، يتم تحديثه تلقائياً في الـ router

