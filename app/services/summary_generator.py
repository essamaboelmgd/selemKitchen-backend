"""
Service for generating unit summaries
"""
from typing import List, Dict, Optional
from datetime import datetime
from app.models.units import UnitType, Part
from app.models.summary import SummaryItem
from app.models.settings import SettingsModel
from app.models.internal_counter import InternalCounterOptions, InternalCounterPart
from app.services.unit_calculator import (
    calculate_unit_parts,
    calculate_total_edge_band,
    calculate_total_area,
    calculate_material_usage
)
from app.services.internal_counter_calculator import (
    calculate_internal_counter_parts,
    calculate_internal_total_edge_band,
    calculate_internal_total_area,
    calculate_internal_material_usage
)
from app.services.edge_band_calculator import calculate_edge_cost

def part_to_summary_item(part: Part) -> SummaryItem:
    """تحويل Part إلى SummaryItem"""
    return SummaryItem(
        part_name=part.name,
        description=f"{part.name} - {part.width_mm}mm × {part.height_mm}mm",
        width_mm=part.width_mm,
        height_mm=part.height_mm,
        depth_mm=part.depth_mm,
        qty=part.qty,
        area_m2=part.area_m2,
        edge_band_m=part.edge_band_m
    )

def internal_part_to_summary_item(part: InternalCounterPart) -> SummaryItem:
    """تحويل InternalCounterPart إلى SummaryItem"""
    return SummaryItem(
        part_name=part.name,
        description=f"{part.type} - {part.name}",
        width_mm=part.width_mm,
        height_mm=part.height_mm,
        depth_mm=part.depth_mm,
        qty=part.qty,
        area_m2=part.area_m2,
        edge_band_m=part.edge_band_m
    )

def generate_summary(
    unit_type: UnitType,
    width_mm: float,
    height_mm: float,
    depth_mm: float,
    shelf_count: int,
    settings: SettingsModel,
    options: Dict = None,
    include_internal_counter: bool = False,
    internal_counter_options: Dict = None
) -> Dict:
    """
    توليد ملخص شامل للوحدة
    
    Returns:
        Dict containing summary data
    """
    if options is None:
        options = {}
    
    # حساب القطع الأساسية
    parts = calculate_unit_parts(
        unit_type=unit_type,
        width_mm=width_mm,
        height_mm=height_mm,
        depth_mm=depth_mm,
        shelf_count=shelf_count,
        settings=settings,
        options=options
    )
    
    # حساب الإجماليات الأساسية
    total_edge_band_m = calculate_total_edge_band(parts)
    total_area_m2 = calculate_total_area(parts)
    
    # حساب استخدام المواد (يستخدم settings مباشرة)
    material_usage = calculate_material_usage(
        total_area_m2=total_area_m2,
        edge_band_m=total_edge_band_m,
        settings=settings
    )
    
    # تحويل القطع إلى SummaryItems
    summary_items = [part_to_summary_item(part) for part in parts]
    
    # حساب القطع الداخلية إذا طُلب
    internal_edge_band_m = 0.0
    internal_area_m2 = 0.0
    internal_material_usage = {}
    
    if include_internal_counter:
        internal_options_obj = InternalCounterOptions()
        if internal_counter_options:
            internal_options_obj = InternalCounterOptions(**internal_counter_options)
        
        internal_parts = calculate_internal_counter_parts(
            unit_type=unit_type,
            unit_width_mm=width_mm,
            unit_height_mm=height_mm,
            unit_depth_mm=depth_mm,
            settings=settings,
            options=internal_options_obj
        )
        
        internal_edge_band_m = calculate_internal_total_edge_band(internal_parts)
        internal_area_m2 = calculate_internal_total_area(internal_parts)
        
        # حساب استخدام المواد للقطع الداخلية (يستخدم settings مباشرة)
        internal_material_usage = calculate_internal_material_usage(
            total_area_m2=internal_area_m2,
            edge_band_m=internal_edge_band_m,
            settings=settings
        )
        
        # إضافة القطع الداخلية إلى الملخص
        internal_items = [internal_part_to_summary_item(part) for part in internal_parts]
        summary_items.extend(internal_items)
        
        # تحديث الإجماليات
        total_edge_band_m += internal_edge_band_m
        total_area_m2 += internal_area_m2
        
        # دمج استخدام المواد
        material_usage["ألواح الخشب"] = round(
            material_usage.get("ألواح الخشب", 0) + 
            internal_material_usage.get("ألواح الخشب", 0), 2
        )
        material_usage["شريط الحافة"] = round(
            material_usage.get("شريط الحافة", 0) + 
            internal_material_usage.get("شريط الحافة", 0), 2
        )
    
    # حساب التكاليف
    costs = {}
    
    # تكلفة الألواح
    if "plywood_sheet" in settings.materials:
        plywood_price = settings.materials["plywood_sheet"].price_per_sheet
        if plywood_price:
            plywood_cost = material_usage["ألواح الخشب"] * plywood_price
            costs["material_cost"] = round(plywood_cost, 2)
    
    # تكلفة الشريط
    if "edge_band_per_meter" in settings.materials:
        edge_price = settings.materials["edge_band_per_meter"].price_per_meter
        if edge_price:
            edge_cost = total_edge_band_m * edge_price
            costs["edge_band_cost"] = round(edge_cost, 2)
    
    # التكلفة الإجمالية
    costs["total_cost"] = round(
        costs.get("material_cost", 0) + costs.get("edge_band_cost", 0), 2
    )
    
    # إعداد الإجماليات
    totals = {
        "total_area_m2": round(total_area_m2, 4),
        "total_edge_band_m": round(total_edge_band_m, 2),
        "total_parts": len(summary_items),
        "total_qty": sum(item.qty for item in summary_items)
    }
    
    return {
        "items": summary_items,
        "totals": totals,
        "material_usage": material_usage,
        "costs": costs
    }

