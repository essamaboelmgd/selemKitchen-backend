"""
Service for calculating internal counter parts
"""
from typing import List, Dict, Any
from app.models.units import UnitType
from app.models.internal_counter import InternalCounterPart, InternalCounterOptions
from app.models.settings import SettingsModel
from app.services.unit_calculator import calculate_piece_edge_meters
from app.models.units import Part, EdgeDistribution

# Constants
DEFAULT_INTERNAL_BACK_CLEARANCE_MM = 3  # المسافة الخلفية للقطع الداخلية
DEFAULT_EXPANSION_GAP_MM = 3  # مسافة التمدد
DEFAULT_DRAWER_SIDE_HEIGHT_MM = 100  # ارتفاع جانب الدرج الافتراضي
DEFAULT_DRAWER_FRONT_HEIGHT_MM = 150  # ارتفاع واجهة الدرج

def calculate_internal_counter_parts(
    unit_type: UnitType,
    unit_width_mm: float,
    unit_height_mm: float,
    unit_depth_mm: float,
    settings: SettingsModel,
    options: InternalCounterOptions
) -> List[InternalCounterPart]:
    """
    حساب القطع الداخلية للكونتر
    
    Returns:
        List of InternalCounterPart objects
    """
    parts = []
    board_thickness_mm = settings.default_board_thickness_mm
    # استخدام back_clearance من settings إذا لم يُحدد في options
    back_clearance = options.back_clearance_mm or settings.back_clearance_mm
    expansion_gap = options.expansion_gap_mm or DEFAULT_EXPANSION_GAP_MM
    
    # حساب الأبعاد الداخلية المتاحة
    internal_width = unit_width_mm - (2 * board_thickness_mm) - (2 * expansion_gap)
    internal_depth = unit_depth_mm - back_clearance - expansion_gap
    internal_height = unit_height_mm - (2 * board_thickness_mm) - expansion_gap
    
    # 1. القاعدة الداخلية (Internal Base)
    if options.add_base:
        base_part = InternalCounterPart(
            name="internal_base",
            type="base",
            width_mm=internal_width,
            height_mm=internal_depth,
            qty=1,
            cutting_dimensions={
                "width": internal_width,
                "depth": internal_depth,
                "thickness": board_thickness_mm
            }
        )
        base_part.area_m2 = (base_part.width_mm * base_part.height_mm) / 1_000_000
        
        # حساب متر الشريط للقاعدة
        base_part_for_edge = Part(
            name="internal_base",
            width_mm=base_part.width_mm,
            height_mm=base_part.height_mm,
            qty=1,
            edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=True)
        )
        base_part.edge_band_m = calculate_piece_edge_meters(base_part_for_edge)
        parts.append(base_part)
    
    # 2. المرآة الأمامية (Mirror Front)
    if options.add_mirror:
        mirror_part = InternalCounterPart(
            name="mirror_front",
            type="mirror",
            width_mm=internal_width,
            height_mm=internal_height,
            qty=1,
            cutting_dimensions={
                "width": internal_width,
                "height": internal_height,
                "thickness": 3  # سمك المرآة عادة 3-5 مم
            }
        )
        mirror_part.area_m2 = (mirror_part.width_mm * mirror_part.height_mm) / 1_000_000
        mirror_part.edge_band_m = 0  # المرآة لا تحتاج شريط
        parts.append(mirror_part)
    
    # 3. الرف الداخلي (Internal Shelf)
    if options.add_internal_shelf:
        shelf_part = InternalCounterPart(
            name="internal_shelf",
            type="shelf",
            width_mm=internal_width,
            height_mm=internal_depth,
            qty=1,
            cutting_dimensions={
                "width": internal_width,
                "depth": internal_depth,
                "thickness": board_thickness_mm
            }
        )
        shelf_part.area_m2 = (shelf_part.width_mm * shelf_part.height_mm) / 1_000_000
        
        # حساب متر الشريط للرف
        shelf_part_for_edge = Part(
            name="internal_shelf",
            width_mm=shelf_part.width_mm,
            height_mm=shelf_part.height_mm,
            qty=1,
            edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=False)
        )
        shelf_part.edge_band_m = calculate_piece_edge_meters(shelf_part_for_edge)
        parts.append(shelf_part)
    
    # 4. الأدراج (Drawers)
    if options.drawer_count > 0:
        drawer_height = (internal_height - (options.drawer_count - 1) * expansion_gap) / options.drawer_count
        
        for i in range(options.drawer_count):
            drawer_num = i + 1
            
            # قاع الدرج (Drawer Bottom)
            drawer_bottom = InternalCounterPart(
                name=f"drawer_{drawer_num}_bottom",
                type="drawer",
                width_mm=internal_width - (2 * expansion_gap),
                height_mm=internal_depth - (2 * expansion_gap),
                qty=1,
                cutting_dimensions={
                    "width": internal_width - (2 * expansion_gap),
                    "depth": internal_depth - (2 * expansion_gap),
                    "thickness": board_thickness_mm
                }
            )
            drawer_bottom.area_m2 = (drawer_bottom.width_mm * drawer_bottom.height_mm) / 1_000_000
            
            # حساب متر الشريط لقاع الدرج
            drawer_bottom_for_edge = Part(
                name=f"drawer_{drawer_num}_bottom",
                width_mm=drawer_bottom.width_mm,
                height_mm=drawer_bottom.height_mm,
                qty=1,
                edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=False)
            )
            drawer_bottom.edge_band_m = calculate_piece_edge_meters(drawer_bottom_for_edge)
            parts.append(drawer_bottom)
            
            # جوانب الدرج (Drawer Sides) - 2 قطعة
            drawer_side_height = drawer_height - (2 * expansion_gap)
            drawer_side_depth = internal_depth - expansion_gap
            
            # الجانب الأيسر
            drawer_side_left = InternalCounterPart(
                name=f"drawer_{drawer_num}_side_left",
                type="drawer",
                width_mm=drawer_side_depth,
                height_mm=drawer_side_height,
                qty=1,
                cutting_dimensions={
                    "width": drawer_side_depth,
                    "height": drawer_side_height,
                    "thickness": board_thickness_mm
                }
            )
            drawer_side_left.area_m2 = (drawer_side_left.width_mm * drawer_side_left.height_mm) / 1_000_000
            
            drawer_side_left_for_edge = Part(
                name=f"drawer_{drawer_num}_side_left",
                width_mm=drawer_side_left.width_mm,
                height_mm=drawer_side_left.height_mm,
                qty=1,
                edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=True)
            )
            drawer_side_left.edge_band_m = calculate_piece_edge_meters(drawer_side_left_for_edge)
            parts.append(drawer_side_left)
            
            # الجانب الأيمن
            drawer_side_right = InternalCounterPart(
                name=f"drawer_{drawer_num}_side_right",
                type="drawer",
                width_mm=drawer_side_depth,
                height_mm=drawer_side_height,
                qty=1,
                cutting_dimensions={
                    "width": drawer_side_depth,
                    "height": drawer_side_height,
                    "thickness": board_thickness_mm
                }
            )
            drawer_side_right.area_m2 = (drawer_side_right.width_mm * drawer_side_right.height_mm) / 1_000_000
            
            drawer_side_right_for_edge = Part(
                name=f"drawer_{drawer_num}_side_right",
                width_mm=drawer_side_right.width_mm,
                height_mm=drawer_side_right.height_mm,
                qty=1,
                edge_distribution=EdgeDistribution(top=True, left=True, right=True, bottom=True)
            )
            drawer_side_right.edge_band_m = calculate_piece_edge_meters(drawer_side_right_for_edge)
            parts.append(drawer_side_right)
            
            # الخلفية (Drawer Back)
            drawer_back = InternalCounterPart(
                name=f"drawer_{drawer_num}_back",
                type="drawer",
                width_mm=internal_width - (2 * expansion_gap),
                height_mm=drawer_side_height,
                qty=1,
                cutting_dimensions={
                    "width": internal_width - (2 * expansion_gap),
                    "height": drawer_side_height,
                    "thickness": board_thickness_mm
                }
            )
            drawer_back.area_m2 = (drawer_back.width_mm * drawer_back.height_mm) / 1_000_000
            drawer_back.edge_band_m = 0  # الخلفية عادة بدون شريط
            parts.append(drawer_back)
    
    return parts

def calculate_internal_total_edge_band(parts: List[InternalCounterPart]) -> float:
    """حساب إجمالي متر الشريط للقطع الداخلية"""
    return sum(part.edge_band_m or 0 for part in parts)

def calculate_internal_total_area(parts: List[InternalCounterPart]) -> float:
    """حساب إجمالي المساحة للقطع الداخلية"""
    return sum(part.area_m2 or 0 for part in parts)

def calculate_internal_material_usage(
    total_area_m2: float,
    edge_band_m: float,
    settings: SettingsModel
) -> Dict[str, float]:
    """
    حساب استخدام المواد للقطع الداخلية
    
    يستخدم sheet_size_m2 من settings
    """
    # استخدام sheet_size_m2 من settings
    sheet_size_m2 = settings.sheet_size_m2
    # Fallback من materials إذا كان موجود
    if settings.materials and "plywood_sheet" in settings.materials:
        sheet_size = settings.materials["plywood_sheet"].sheet_size_m2
        if sheet_size:
            sheet_size_m2 = sheet_size
    
    plywood_sheets = (total_area_m2 / sheet_size_m2) if sheet_size_m2 > 0 else 0
    
    return {
        "plywood_sheets": round(plywood_sheets, 2),
        "edge_m": round(edge_band_m, 2),
        "total_area_m2": round(total_area_m2, 4)
    }

