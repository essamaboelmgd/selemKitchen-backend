from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from enum import Enum

class AssemblyMethod(str, Enum):
    """طريقة التجميع"""
    FULL_SIDES_BACK_ROUTED = "full_sides_back_routed"  # جانبين كاملين (ظهر مفحار)
    FULL_BASE_BACK_ROUTED = "full_base_back_routed"  # أرضية كاملة ظهر مفحار
    BASE_FULL_TOP_SIDES_BACK_ROUTED = "base_full_top_sides_back_routed"  # ارضي (قاعدة كاملة) +علوي(جانبين كاملين) ظهر مفحار
    FULL_SIDES_BACK_FLUSH = "full_sides_back_flush"  # جانبين كاملين (ظهر لطش)
    FULL_BASE_BACK_FLUSH = "full_base_back_flush"  # أرضية كاملة (ظهر لطش)
    BASE_FULL_TOP_SIDES_BACK_FLUSH = "base_full_top_sides_back_flush"  # ارضي (قاعدة كاملة) +علوي(جانبين كاملين) ظهر لطش

class HandleType(str, Enum):
    """نوع المقبض"""
    BUILT_IN = "built_in"  # مقبض بيلت ان
    REGULAR = "regular"  # مقبض عادي
    HIDDEN_CL_CHASSIS = "hidden_cl_chassis"  # مقبض ارضي مخفي ( C-L ) علوي شاسية
    HIDDEN_CL_DROP = "hidden_cl_drop"  # مقبض ارضي مخفي ( C-L ) علوي ساقط

class EdgeBandingType(str, Enum):
    """نوع الشريط"""
    NONE = "-"  # بدون
    I = "I"  # شريط طول
    L = "L"  # شريط ( طول + عرض )
    L_M_RIGHT = "LM-يمين"  # شريط ( طول + عرض ) مفحار يمين (using slug safe value? usually enum values are sent as string)
    C = "C"  # شريط ( طول + 2 عرض )
    U = "U"  # شريط ( 2 طول + عرض )
    O = "O"  # شريط داير
    SLASH = "\\"  # شريط عرض
    II = "II"  # شريط 2 طول
    DOUBLE_SLASH = "\\\\"  # شريط 2 عرض
    IM = "IM"  # شريط طول + مفحار عكس
    CM = "CM"  # شريط ( طول + 2 عرض ) + مفحار عكس
    UM_RIGHT = "UM-يمين"  # شريط ( 2 طول + عرض ) + مفحار يمين
    IIM = "IIM"  # شريط 2 طول + مفحار مع الطول
    SLASH_M = "\\M"  # شريط عرض + مفحار عكس
    DOUBLE_SLASH_M = "\\\\M"  # شريط 2 عرض + مفحار مع العرض
    OM = "OM"  # شريط داير + مفحار مع الطول
    DR = "DR"  # شريط طول + مفحار درج بلوم
    LL = "LL"  # وحدة زاوية حرف L
    LS = "LS"  # وحدة ركنة مشطوفة
    LLM = "LLM" # وحدة زاوية حرف L + مفحار
    LSM = "LSM" # وحدة ركنة مشطوفة + مفحار

class MaterialInfo(BaseModel):
    """معلومات الخامة"""
    price_per_sheet: Optional[float] = None
    sheet_size_m2: Optional[float] = None
    price_per_meter: Optional[float] = None
    description: Optional[str] = None

class SettingsModel(BaseModel):
    """نموذج إعدادات التقطيع والتجميع"""
    
    # طريقة التجميع
    assembly_method: AssemblyMethod = Field(
        default=AssemblyMethod.FULL_SIDES_BACK_ROUTED,
        description="طريقة التجميع"
    )
    
    # نوع المقبض
    handle_type: HandleType = Field(
        default=HandleType.BUILT_IN,
        description="نوع المقبض"
    )

    # كود الشريط (Edge Banding Option)
    edge_banding_type: EdgeBandingType = Field(
        default=EdgeBandingType.NONE,
        description="كود الشريط"
    )
    
    # ارتفاع قطاع المقبض (بيلت ان \ C &L)
    handle_profile_height: float = Field(
        default=3.5,
        description="ارتفاع قطاع المقبض (بيلت ان \\ C &L) بالسنتيمتر"
    )
    
    # مقبض الشاسية (الوحدات العلوية) / سقوط الضلفة
    chassis_handle_drop: float = Field(
        default=2.0,
        description="مقبض الشاسية (الوحدات العلوية) / سقوط الضلفة بالسنتيمتر"
    )
    
    # سمك لوح الكونتر
    counter_thickness: float = Field(
        default=1.8,
        description="سمك لوح الكونتر بالسنتيمتر"
    )
    
    # عرض المراية
    mirror_width: float = Field(
        default=8.0,
        description="عرض المراية بالسنتيمتر"
    )
    
    # تخصيم الظهر
    back_deduction: float = Field(
        default=2.0,
        description="تخصيم الظهر بالسنتيمتر"
    )
    
    # عمق المفحار
    router_depth: float = Field(
        default=0.9,
        description="عمق المفحار بالسنتيمتر"
    )
    
    # بعد المفحار
    router_distance: float = Field(
        default=2.0,
        description="بعد المفحار بالسنتيمتر"
    )
    
    # سمك المفحار
    router_thickness: float = Field(
        default=0.5,
        description="سمك المفحار بالسنتيمتر"
    )
    
    # تخصيم عرض الضلفة بدون الشريط
    door_width_deduction_no_edge: float = Field(
        default=0.4,
        description="تخصيم عرض الضلفة بدون الشريط بالسنتيمتر"
    )
    
    # تخصيم الرف من العمق
    shelf_depth_deduction: float = Field(
        default=5.0,
        description="تخصيم الرف من العمق بالسنتيمتر"
    )
    
    # تخصيم ارتفاع الضلفة الارضي بدون الشريط
    ground_door_height_deduction_no_edge: float = Field(
        default=1.0,
        description="تخصيم ارتفاع الضلفة الارضي بدون الشريط بالسنتيمتر"
    )
    
    # هدر مكنة لصق الشريط لكل مقاس
    edge_banding_waste_per_size: float = Field(
        default=6.0,
        description="هدر مكنة لصق الشريط لكل مقاس بالسنتيمتر"
    )
    
    # أسعار الخامات
    materials: Dict[str, MaterialInfo] = Field(
        default_factory=dict,
        description="أسعار الخامات"
    )

    # تاريخ آخر تحديث
    last_updated: Optional[datetime] = Field(
        default=None,
        description="تاريخ آخر تحديث"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "assembly_method": "full_sides_back_routed",
                "handle_type": "built_in",
                "handle_profile_height": 3.5,
                "chassis_handle_drop": 2.0,
                "counter_thickness": 1.8,
                "mirror_width": 8.0,
                "back_deduction": 2.0,
                "router_depth": 0.9,
                "router_distance": 2.0,
                "router_thickness": 0.5,
                "door_width_deduction_no_edge": 0.4,
                "shelf_depth_deduction": 5.0,
                "ground_door_height_deduction_no_edge": 1.0,
                "edge_banding_waste_per_size": 6.0,
                "materials": {
                    "plywood_sheet": {
                        "price_per_sheet": 1200,
                        "sheet_size_m2": 2.98
                    },
                    "edge_band_per_meter": {
                        "price_per_meter": 5
                    }
                }
            }
        }
    }

class SettingsUpdate(BaseModel):
    """
    نموذج تحديث الإعدادات
    جميع الحقول Optional للسماح بالتحديث الجزئي
    """
    assembly_method: Optional[AssemblyMethod] = Field(default=None, description="طريقة التجميع")
    handle_type: Optional[HandleType] = Field(default=None, description="نوع المقبض")
    edge_banding_type: Optional[EdgeBandingType] = Field(default=None, description="كود الشريط")
    handle_profile_height: Optional[float] = Field(default=None, description="ارتفاع قطاع المقبض")
    chassis_handle_drop: Optional[float] = Field(default=None, description="مقبض الشاسية / سقوط الضلفة")
    counter_thickness: Optional[float] = Field(default=None, description="سمك لوح الكونتر")
    mirror_width: Optional[float] = Field(default=None, description="عرض المراية")
    back_deduction: Optional[float] = Field(default=None, description="تخصيم الظهر")
    router_depth: Optional[float] = Field(default=None, description="عمق المفحار")
    router_distance: Optional[float] = Field(default=None, description="بعد المفحار")
    router_thickness: Optional[float] = Field(default=None, description="سمك المفحار")
    door_width_deduction_no_edge: Optional[float] = Field(default=None, description="تخصيم عرض الضلفة بدون الشريط")
    shelf_depth_deduction: Optional[float] = Field(default=None, description="تخصيم الرف من العمق")
    ground_door_height_deduction_no_edge: Optional[float] = Field(default=None, description="تخصيم ارتفاع الضلفة الارضي بدون الشريط")
    edge_banding_waste_per_size: Optional[float] = Field(default=None, description="هدر مكنة لصق الشريط لكل مقاس")
    materials: Optional[Dict[str, MaterialInfo]] = Field(default=None, description="أسعار الخامات")