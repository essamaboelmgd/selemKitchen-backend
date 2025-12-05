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
    handle_recess_height_cm: int = Field(default=3, description="ارتفاع قطاع المقبض بالسنتيمتر")
    default_board_thickness_cm: int = Field(default=1.6, description="سمك الافتراضي للألواح بالسنتيمتر")
    back_panel_thickness_cm: int = Field(default=0.3, description="سمك لوح الظهر بالسنتيمتر")
    edge_overlap_cm: int = Field(default=0.2, description="مسافة التداخل للشريط بالسنتيمتر (للمفاصل)")
    back_clearance_cm: int = Field(default=0.3, description="مسافة الفراغ من الخلف للرفوف (سم)")
    top_clearance_cm: int = Field(default=0.5, description="المسافة العلوية للظهر (سم)")
    bottom_clearance_cm: int = Field(default=0.5, description="المسافة السفلية للظهر (سم)")
    side_overlap_cm: int = Field(default=0, description="تداخل الجوانب مع الظهر (سم)")
    sheet_size_m2: float = Field(default=2.4, description="حجم اللوح بالمتر المربع")
    materials: Dict[str, MaterialPrice] = Field(
        default_factory=lambda: {
            "plywood_sheet": MaterialPrice(
                price_per_sheet=400,  # Changed from 2500 SAR to 400 EGP
                sheet_size_m2=2.4
            ),
            "edge_band_per_meter": MaterialPrice(
                price_per_meter=20  # Changed from 10 SAR to 20 EGP
            )
        },
        description="أسعار الخامات"
    )
    edge_types: Dict[str, str] = Field(
        default_factory=lambda: {"pvc": "PVC", "wood": "خشبي", "no_edge": "بدون شريط"},
        description="أنواع الحواف المتاحة"
    )
    default_unit_depth_by_type: Dict[str, int] = Field(
        default_factory=lambda: {"ground": 30, "wall": 25, "tall": 35, "sink_ground": 32},
        description="العمق الافتراضي حسب نوع الوحدة (سم)"
    )
    last_updated: Optional[datetime] = Field(default=None, description="تاريخ آخر تحديث")

    model_config = {
        "json_schema_extra": {
            "example": {
                "assembly_method": "bolt",
                "handle_type": "built-in",
                "handle_recess_height_cm": 3,
                "default_board_thickness_cm": 1.6,
                "back_panel_thickness_cm": 0.3,
                "edge_overlap_cm": 0.2,
                "back_clearance_cm": 0.3,
                "top_clearance_cm": 0.5,
                "bottom_clearance_cm": 0.5,
                "side_overlap_cm": 0,
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
                    "ground": 30,
                    "wall": 25,
                    "tall": 35,
                    "sink_ground": 32
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
    handle_recess_height_cm: Optional[int] = Field(default=None, description="ارتفاع قطاع المقبض بالسنتيمتر")
    default_board_thickness_cm: Optional[int] = Field(default=None, description="سمك الافتراضي للألواح بالسنتيمتر")
    
    # الحقول المتعلقة بالقياسات
    back_panel_thickness_cm: Optional[int] = Field(default=None, description="سمك لوح الظهر بالسنتيمتر")
    edge_overlap_cm: Optional[int] = Field(default=None, description="مسافة التداخل للشريط بالسنتيمتر (للمفاصل)")
    back_clearance_cm: Optional[int] = Field(default=None, description="مسافة الفراغ من الخلف للرفوف (سم)")
    top_clearance_cm: Optional[int] = Field(default=None, description="المسافة العلوية للظهر (سم)")
    bottom_clearance_cm: Optional[int] = Field(default=None, description="المسافة السفلية للظهر (سم)")
    side_overlap_cm: Optional[int] = Field(default=None, description="تداخل الجوانب مع الظهر (سم)")
    sheet_size_m2: Optional[float] = Field(default=None, description="حجم اللوح بالمتر المربع")
    
    # الحقول المعقدة
    materials: Optional[Dict[str, MaterialPrice]] = Field(default=None, description="أسعار الخامات")
    edge_types: Optional[Dict[str, str]] = Field(default=None, description="أنواع الحواف المتاحة")
    default_unit_depth_by_type: Optional[Dict[str, int]] = Field(default=None, description="العمق الافتراضي حسب نوع الوحدة (سم)")
    
    # ملاحظة: last_updated لا يُحدّث يدوياً، يتم تحديثه تلقائياً في الـ router