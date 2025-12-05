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
    
    # تحويل من cm إلى m
    width_m = part.width_cm / 100.0
    height_m = part.height_cm / 100.0
    
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
    width_cm: float,
    height_cm: float,
    depth_cm: float,
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
    board_thickness_cm = options.get(
        "board_thickness_cm",
        settings.default_board_thickness_cm
    )
    back_clearance_cm = options.get(
        "back_clearance_cm",
        settings.back_clearance_cm
    )
    top_clearance_cm = options.get(
        "top_clearance_cm",
        settings.top_clearance_cm
    )
    bottom_clearance_cm = options.get(
        "bottom_clearance_cm",
        settings.bottom_clearance_cm
    )
    side_overlap_cm = options.get(
        "side_overlap_cm",
        settings.side_overlap_cm
    )
    back_panel_thickness_cm = options.get(
        "back_panel_thickness_cm",
        settings.back_panel_thickness_cm
    )
    
    parts = []
    
    # 1. الجوانب (Side Panels)
    # ارتفاع الجانب = ارتفاع الوحدة
    # عمق الجانب = عمق الوحدة
    side_panel = Part(
        name="side_panel",
        width_cm=depth_cm,  # العرض = العمق
        height_cm=height_cm,
        qty=2,
        edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=True)
    )
    side_panel.area_m2 = (side_panel.width_cm * side_panel.height_cm * side_panel.qty) / 10_000
    side_panel.edge_band_m = calculate_piece_edge_meters(side_panel)
    parts.append(side_panel)
    
    # 2. القاعدة والعلوية (Top/Bottom Panels)
    # عرض = عرض الوحدة - (2 * سمك الجانب)
    top_bottom_width = width_cm - (2 * board_thickness_cm)
    
    # القاعدة (Bottom)
    bottom_panel = Part(
        name="bottom_panel",
        width_cm=top_bottom_width,
        height_cm=depth_cm,  # الارتفاع = العمق
        qty=1,
        edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=True)
    )
    bottom_panel.area_m2 = (bottom_panel.width_cm * bottom_panel.height_cm * bottom_panel.qty) / 10_000
    bottom_panel.edge_band_m = calculate_piece_edge_meters(bottom_panel)
    parts.append(bottom_panel)
    
    # العلوية (Top) - Special handling for sink units
    if unit_type == UnitType.SINK_GROUND:
        # For sink units, the top panel has a sink cutout (50x40 cm centered)
        # Extract sink cutout dimensions from options or use defaults
        sink_cutout_width_cm = options.get("sink_cutout_width_cm", 50)  # 50 cm default
        sink_cutout_depth_cm = options.get("sink_cutout_depth_cm", 40)  # 40 cm default
        
        top_panel = Part(
            name="top_panel_sink",
            width_cm=top_bottom_width,
            height_cm=depth_cm,
            qty=1,
            edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=True)
        )
        
        # Calculate area considering the sink cutout
        # Total area minus cutout area (but ensure cutout doesn't exceed panel area)
        total_top_area = top_bottom_width * depth_cm
        # Limit cutout to panel dimensions to prevent negative areas
        actual_cutout_width = min(sink_cutout_width_cm, top_bottom_width)
        actual_cutout_depth = min(sink_cutout_depth_cm, depth_cm)
        sink_cutout_area = actual_cutout_width * actual_cutout_depth
        top_panel_area = max(0, total_top_area - sink_cutout_area)  # Ensure non-negative area
        top_panel.area_m2 = (top_panel_area * top_panel.qty) / 10_000
    else:
        top_panel = Part(
            name="top_panel",
            width_cm=top_bottom_width,
            height_cm=depth_cm,
            qty=1,
            edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=True)
        )
        top_panel.area_m2 = (top_panel.width_cm * top_panel.height_cm * top_panel.qty) / 10_000
    
    top_panel.edge_band_m = calculate_piece_edge_meters(top_panel)
    parts.append(top_panel)
    
    # 3. الرفوف (Shelves) - Special handling for sink units
    # عرض الرف = عرض القاعدة/العلوية
    # عمق الرف = عمق الوحدة - المسافة الخلفية
    shelf_width = top_bottom_width
    shelf_depth = depth_cm - back_clearance_cm
    
    # For sink units, reduce shelves by 1 or make bottom shelf half-depth
    if unit_type == UnitType.SINK_GROUND:
        # Reduce shelf count by 1 for sink units (remove bottom shelf)
        effective_shelf_count = max(0, shelf_count - 1)
        for i in range(effective_shelf_count):
            shelf_num = i + 1
            shelf = Part(
                name=f"shelf_{shelf_num}",
                width_cm=shelf_width,
                height_cm=shelf_depth,  # الارتفاع = العمق
                qty=1,
                edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=False)  # لا شريط من الأسفل
            )
            shelf.area_m2 = (shelf.width_cm * shelf.height_cm * shelf.qty) / 10_000
            shelf.edge_band_m = calculate_piece_edge_meters(shelf)
            parts.append(shelf)
    else:
        # Regular units - all shelves full depth
        for i in range(shelf_count):
            shelf = Part(
                name=f"shelf_{i+1}",
                width_cm=shelf_width,
                height_cm=shelf_depth,  # الارتفاع = العمق
                qty=1,
                edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=False)  # لا شريط من الأسفل
            )
            shelf.area_m2 = (shelf.width_cm * shelf.height_cm * shelf.qty) / 10_000
            shelf.edge_band_m = calculate_piece_edge_meters(shelf)
            parts.append(shelf)
    
    # 4. الظهر (Back Panel) - Special handling for sink units
    # عرض = عرض الوحدة - (2 * تداخل الجوانب)
    # ارتفاع = ارتفاع الوحدة - المسافة العلوية - المسافة السفلية
    # سمك الظهر يأتي من settings.back_panel_thickness_cm
    back_width = width_cm - (2 * side_overlap_cm)
    back_height = height_cm - top_clearance_cm - bottom_clearance_cm
    
    if unit_type == UnitType.SINK_GROUND:
        # For sink units, back panel has plumbing cutout (20x10 cm at bottom center)
        # Extract plumbing cutout dimensions from options or use defaults
        plumbing_cutout_width_cm = options.get("plumbing_cutout_width_cm", 20)  # 20 cm default
        plumbing_cutout_height_cm = options.get("plumbing_cutout_height_cm", 10)  # 10 cm default
        
        back_panel = Part(
            name="back_panel_sink",
            width_cm=back_width,
            height_cm=back_height,
            depth_cm=back_panel_thickness_cm,  # استخدام سمك الظهر من settings
            qty=1,
            edge_distribution=EdgeDistribution(top=False, left=False, right=False, bottom=False)  # الظهر عادة بدون شريط
        )
        
        # Calculate area considering the plumbing cutout
        # Total area minus cutout area (but ensure cutout doesn't exceed panel area)
        total_back_area = back_width * back_height
        # Limit cutout to panel dimensions to prevent negative areas
        actual_plumbing_width = min(plumbing_cutout_width_cm, back_width)
        actual_plumbing_height = min(plumbing_cutout_height_cm, back_height)
        plumbing_cutout_area = actual_plumbing_width * actual_plumbing_height
        back_panel_area = max(0, total_back_area - plumbing_cutout_area)  # Ensure non-negative area
        back_panel.area_m2 = (back_panel_area * back_panel.qty) / 10_000
    else:
        back_panel = Part(
            name="back_panel",
            width_cm=back_width,
            height_cm=back_height,
            depth_cm=back_panel_thickness_cm,  # استخدام سمك الظهر من settings
            qty=1,
            edge_distribution=EdgeDistribution(top=False, left=False, right=False, bottom=False)  # الظهر عادة بدون شريط
        )
        back_panel.area_m2 = (back_panel.width_cm * back_panel.height_cm * back_panel.qty) / 10_000
    
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
        "ألواح الخشب": round(plywood_sheets, 2),
        "شريط الحافة": round(edge_band_m, 2),
        "المساحة الإجمالية": round(total_area_m2, 4)
    }