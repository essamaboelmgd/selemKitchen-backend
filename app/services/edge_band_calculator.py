"""
Service for calculating edge band breakdown
"""
from typing import List, Dict, Optional
from app.models.units import Part, EdgeDistribution
from app.models.edge_band import EdgeDetail, EdgeBandPart, EdgeType
from app.models.settings import SettingsModel

def calculate_edge_breakdown_for_part(
    part: Part,
    settings: SettingsModel,
    edge_type: EdgeType = EdgeType.PVC
) -> EdgeBandPart:
    """
    حساب تفاصيل الشريط لقطعة واحدة
    
    Returns:
        EdgeBandPart with detailed edge information
    """
    # استخدام edge_overlap_cm من settings مباشرة
    edge_overlap_cm = settings.edge_overlap_cm
    
    # تحديد توزيع الشريط
    if part.edge_distribution is None:
        edge_dist = EdgeDistribution()
    else:
        edge_dist = part.edge_distribution
    
    edges = []
    total_edge_cm = 0.0
    
    # حساب كل حافة
    if edge_dist.top:
        length_cm = part.width_cm + edge_overlap_cm
        length_m = length_cm / 100.0
        edges.append(EdgeDetail(
            edge="top",
            length_mm=length_cm * 10,  # Convert to mm for consistency
            length_m=length_m,
            edge_type=edge_type,
            has_edge=True
        ))
        total_edge_cm += length_cm
    
    if edge_dist.bottom:
        length_cm = part.width_cm + edge_overlap_cm
        length_m = length_cm / 100.0
        edges.append(EdgeDetail(
            edge="bottom",
            length_mm=length_cm * 10,  # Convert to mm for consistency
            length_m=length_m,
            edge_type=edge_type,
            has_edge=True
        ))
        total_edge_cm += length_cm
    
    if edge_dist.left:
        length_cm = part.height_cm + edge_overlap_cm
        length_m = length_cm / 100.0
        edges.append(EdgeDetail(
            edge="left",
            length_mm=length_cm * 10,  # Convert to mm for consistency
            length_m=length_m,
            edge_type=edge_type,
            has_edge=True
        ))
        total_edge_cm += length_cm
    
    if edge_dist.right:
        length_cm = part.height_cm + edge_overlap_cm
        length_m = length_cm / 100.0
        edges.append(EdgeDetail(
            edge="right",
            length_mm=length_cm * 10,  # Convert to mm for consistency
            length_m=length_m,
            edge_type=edge_type,
            has_edge=True
        ))
        total_edge_cm += length_cm
    
    # إضافة حواف بدون شريط (للتوثيق فقط - لا تُضاف للـ total)
    if not edge_dist.top:
        edges.append(EdgeDetail(
            edge="top",
            length_mm=part.width_cm * 10,  # Convert to mm for consistency
            length_m=part.width_cm / 100.0,
            edge_type=edge_type,
            has_edge=False
        ))
    
    if not edge_dist.bottom:
        edges.append(EdgeDetail(
            edge="bottom",
            length_mm=part.width_cm * 10,  # Convert to mm for consistency
            length_m=part.width_cm / 100.0,
            edge_type=edge_type,
            has_edge=False
        ))
    
    if not edge_dist.left:
        edges.append(EdgeDetail(
            edge="left",
            length_mm=part.height_cm * 10,  # Convert to mm for consistency
            length_m=part.height_cm / 100.0,
            edge_type=edge_type,
            has_edge=False
        ))
    
    if not edge_dist.right:
        edges.append(EdgeDetail(
            edge="right",
            length_mm=part.height_cm * 10,  # Convert to mm for consistency
            length_m=part.height_cm / 100.0,
            edge_type=edge_type,
            has_edge=False
        ))
    
    # إجمالي متر الشريط للقطعة (مع الكمية)
    total_edge_m = (total_edge_cm / 100.0) * part.qty
    
    return EdgeBandPart(
        part_name=part.name,
        qty=part.qty,
        edges=edges,
        total_edge_m=round(total_edge_m, 3),
        edge_type=edge_type
    )

def calculate_edge_breakdown(
    parts: List[Part],
    settings: SettingsModel,
    edge_type: EdgeType = EdgeType.PVC
) -> List[EdgeBandPart]:
    """
    حساب تفاصيل الشريط لجميع القطع
    
    Returns:
        List of EdgeBandPart objects
    """
    edge_breakdown = []
    
    for part in parts:
        edge_part = calculate_edge_breakdown_for_part(part, settings, edge_type)
        edge_breakdown.append(edge_part)
    
    return edge_breakdown

def calculate_total_edge_meters(edge_breakdown: List[EdgeBandPart]) -> float:
    """حساب إجمالي متر الشريط"""
    return sum(part.total_edge_m for part in edge_breakdown)

def calculate_edge_cost(
    edge_breakdown: List[EdgeBandPart],
    settings: SettingsModel
) -> Dict[str, float]:
    """
    حساب تكلفة الشريط حسب النوع
    
    Returns:
        Dict with cost breakdown by edge type
    """
    cost_breakdown = {}
    total_cost = 0.0
    
    # حساب التكلفة لكل نوع شريط
    for edge_type in EdgeType:
        type_parts = [p for p in edge_breakdown if p.edge_type == edge_type]
        if not type_parts:
            continue
        
        total_meters = sum(p.total_edge_m for p in type_parts)
        
        # البحث عن سعر الشريط في settings
        material_key = f"edge_band_{edge_type.value}_per_meter"
        if material_key in settings.materials:
            price = settings.materials[material_key].price_per_meter
            if price:
                cost = total_meters * price
                cost_breakdown[edge_type.value] = round(cost, 2)
                total_cost += cost
        else:
            # Fallback: استخدام السعر العام للشريط
            if "edge_band_per_meter" in settings.materials:
                price = settings.materials["edge_band_per_meter"].price_per_meter
                if price:
                    cost = total_meters * price
                    cost_breakdown[edge_type.value] = round(cost, 2)
                    total_cost += cost
    
    return {
        "breakdown": cost_breakdown,
        "total": round(total_cost, 2)
    }