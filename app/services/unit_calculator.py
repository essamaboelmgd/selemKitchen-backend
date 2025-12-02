"""
Service for calculating unit parts and dimensions
"""
from typing import List, Dict, Any
from app.models.units import Part, UnitType, EdgeDistribution
from app.models.settings import SettingsModel

# Note: These constants are deprecated - all values should come from settings
# They are kept only for backward compatibility
# All calculations now use settings directly

def calculate_piece_edge_meters(part: Part, settings: SettingsModel = None) -> float:
    """
    حساب متر الشريط المطلوب لقطعة واحدة
    
    الحساب: محيط القطعة حسب توزيع الشريط
    ملاحظة: هذه الدالة بسيطة ولا تحتاج settings، لكن تم إضافة المعامل للتوافق
    """
    if part.edge_distribution is None:
        # Default: جميع الحواف
        edge_dist = EdgeDistribution()
    else:
        edge_dist = part.edge_distribution
    
    edge_length_m = 0.0
    
    # تحويل من mm إلى m
    width_m = part.width_mm / 1000.0
    height_m = part.height_mm / 1000.0
    
    # حساب محيط الحواف المطلوبة
    if edge_dist.top:
        edge_length_m += width_m
    if edge_dist.bottom:
        edge_length_m += width_m
    if edge_dist.left:
        edge_length_m += height_m
    if edge_dist.right:
        edge_length_m += height_m
    
    # ضرب في الكمية
    return edge_length_m * part.qty

def calculate_unit_parts(
    unit_type: UnitType,
    width_mm: float,
    height_mm: float,
    depth_mm: float,
    shelf_count: int,
    settings: SettingsModel,
    options: Dict[str, Any] = None
) -> List[Part]:
    """
    حساب جميع قطع الوحدة
    
    Returns:
        List of Part objects with calculated dimensions
    """
    if options is None:
        options = {}
    
    # استخراج القيم من options أو استخدام القيم من settings مباشرة
    # جميع القيم تأتي من settings كقيم افتراضية
    board_thickness_mm = options.get(
        "board_thickness_mm",
        settings.default_board_thickness_mm
    )
    back_clearance_mm = options.get(
        "back_clearance_mm",
        settings.back_clearance_mm
    )
    top_clearance_mm = options.get(
        "top_clearance_mm",
        settings.top_clearance_mm
    )
    bottom_clearance_mm = options.get(
        "bottom_clearance_mm",
        settings.bottom_clearance_mm
    )
    side_overlap_mm = options.get(
        "side_overlap_mm",
        settings.side_overlap_mm
    )
    back_panel_thickness_mm = options.get(
        "back_panel_thickness_mm",
        settings.back_panel_thickness_mm
    )
    
    parts = []
    
    # 1. الجوانب (Side Panels)
    # ارتفاع الجانب = ارتفاع الوحدة
    # عمق الجانب = عمق الوحدة
    side_panel = Part(
        name="side_panel",
        width_mm=depth_mm,  # العرض = العمق
        height_mm=height_mm,
        qty=2,
        edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=True)
    )
    side_panel.area_m2 = (side_panel.width_mm * side_panel.height_mm * side_panel.qty) / 1_000_000
    side_panel.edge_band_m = calculate_piece_edge_meters(side_panel)
    parts.append(side_panel)
    
    # 2. القاعدة والعلوية (Top/Bottom Panels)
    # عرض = عرض الوحدة - (2 * سمك الجانب)
    top_bottom_width = width_mm - (2 * board_thickness_mm)
    
    # القاعدة (Bottom)
    bottom_panel = Part(
        name="bottom_panel",
        width_mm=top_bottom_width,
        height_mm=depth_mm,  # الارتفاع = العمق
        qty=1,
        edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=True)
    )
    bottom_panel.area_m2 = (bottom_panel.width_mm * bottom_panel.height_mm * bottom_panel.qty) / 1_000_000
    bottom_panel.edge_band_m = calculate_piece_edge_meters(bottom_panel)
    parts.append(bottom_panel)
    
    # العلوية (Top)
    top_panel = Part(
        name="top_panel",
        width_mm=top_bottom_width,
        height_mm=depth_mm,
        qty=1,
        edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=True)
    )
    top_panel.area_m2 = (top_panel.width_mm * top_panel.height_mm * top_panel.qty) / 1_000_000
    top_panel.edge_band_m = calculate_piece_edge_meters(top_panel)
    parts.append(top_panel)
    
    # 3. الرفوف (Shelves)
    # عرض الرف = عرض القاعدة/العلوية
    # عمق الرف = عمق الوحدة - المسافة الخلفية
    shelf_width = top_bottom_width
    shelf_depth = depth_mm - back_clearance_mm
    
    for i in range(shelf_count):
        shelf = Part(
            name=f"shelf_{i+1}",
            width_mm=shelf_width,
            height_mm=shelf_depth,  # الارتفاع = العمق
            qty=1,
            edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=False)  # لا شريط من الأسفل
        )
        shelf.area_m2 = (shelf.width_mm * shelf.height_mm * shelf.qty) / 1_000_000
        shelf.edge_band_m = calculate_piece_edge_meters(shelf)
        parts.append(shelf)
    
    # 4. الظهر (Back Panel)
    # عرض = عرض الوحدة - (2 * تداخل الجوانب)
    # ارتفاع = ارتفاع الوحدة - المسافة العلوية - المسافة السفلية
    # سمك الظهر يأتي من settings.back_panel_thickness_mm
    back_width = width_mm - (2 * side_overlap_mm)
    back_height = height_mm - top_clearance_mm - bottom_clearance_mm
    
    back_panel = Part(
        name="back_panel",
        width_mm=back_width,
        height_mm=back_height,
        depth_mm=back_panel_thickness_mm,  # استخدام سمك الظهر من settings
        qty=1,
        edge_distribution=EdgeDistribution(top=False, left=False, right=False, bottom=False)  # الظهر عادة بدون شريط
    )
    back_panel.area_m2 = (back_panel.width_mm * back_panel.height_mm * back_panel.qty) / 1_000_000
    back_panel.edge_band_m = calculate_piece_edge_meters(back_panel)
    parts.append(back_panel)
    
    return parts

def calculate_total_edge_band(parts: List[Part]) -> float:
    """حساب إجمالي متر الشريط"""
    return sum(part.edge_band_m or 0 for part in parts)

def calculate_total_area(parts: List[Part]) -> float:
    """حساب إجمالي المساحة بالمتر المربع"""
    return sum(part.area_m2 or 0 for part in parts)

def calculate_material_usage(
    total_area_m2: float,
    edge_band_m: float,
    settings: SettingsModel
) -> Dict[str, float]:
    """
    حساب استخدام المواد
    
    يستخدم sheet_size_m2 من settings
    
    Returns:
        Dict with material usage (plywood_sheets, edge_m, etc.)
    """
    # استخدام sheet_size_m2 من settings
    sheet_size_m2 = settings.sheet_size_m2
    # Fallback من materials إذا كان موجود
    if settings.materials and "plywood_sheet" in settings.materials:
        sheet_size = settings.materials["plywood_sheet"].sheet_size_m2
        if sheet_size:
            sheet_size_m2 = sheet_size
    
    # حساب عدد الألواح المطلوبة (تقريبي)
    plywood_sheets = (total_area_m2 / sheet_size_m2) if sheet_size_m2 > 0 else 0
    
    return {
        "plywood_sheets": round(plywood_sheets, 2),
        "edge_m": round(edge_band_m, 2),
        "total_area_m2": round(total_area_m2, 4)
    }

