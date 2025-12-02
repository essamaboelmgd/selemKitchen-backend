from fastapi import APIRouter, HTTPException, status
from app.database import get_database
from app.models.units import (
    UnitCalculateRequest,
    UnitCalculateResponse,
    UnitEstimateRequest,
    UnitEstimateResponse,
    UnitType
)
from app.models.internal_counter import (
    InternalCounterRequest,
    InternalCounterResponse,
    InternalCounterOptions
)
from app.models.settings import SettingsModel
from app.routers.settings import get_settings_from_db
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
from app.services.edge_band_calculator import (
    calculate_edge_breakdown,
    calculate_total_edge_meters,
    calculate_edge_cost
)
from app.models.edge_band import EdgeBreakdownResponse, EdgeType
from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId
import uuid

router = APIRouter()

async def get_settings_model() -> SettingsModel:
    """Get settings as SettingsModel"""
    settings_doc = await get_settings_from_db()
    settings_doc.pop("_id", None)
    return SettingsModel(**settings_doc)

@router.post("/calculate", response_model=UnitCalculateResponse)
async def calculate_unit(request: UnitCalculateRequest):
    """
    حساب مقاسات الوحدة وقطعها
    
    يقبل بيانات الوحدة (النوع، الأبعاد، عدد الرفوف) ويحسب:
    - جميع القطع (الجوانب، القاعدة، العلوية، الرفوف، الظهر)
    - متر الشريط المطلوب
    - المساحة الإجمالية
    - استخدام المواد
    """
    try:
        # جلب الإعدادات
        settings = await get_settings_model()
        
        # حساب القطع
        parts = calculate_unit_parts(
            unit_type=request.type,
            width_mm=request.width_mm,
            height_mm=request.height_mm,
            depth_mm=request.depth_mm,
            shelf_count=request.shelf_count,
            settings=settings,
            options=request.options or {}
        )
        
        # حساب الإجماليات
        total_edge_band_m = calculate_total_edge_band(parts)
        total_area_m2 = calculate_total_area(parts)
        
        # حساب استخدام المواد (يستخدم settings مباشرة)
        material_usage = calculate_material_usage(
            total_area_m2=total_area_m2,
            edge_band_m=total_edge_band_m,
            settings=settings
        )
        
        # حفظ في MongoDB (اختياري)
        unit_id = None
        db = get_database()
        if db is not None:
            unit_id = f"unit_{uuid.uuid4().hex[:8].upper()}"
            unit_doc = {
                "_id": unit_id,
                "type": request.type.value,
                "width_mm": request.width_mm,
                "height_mm": request.height_mm,
                "depth_mm": request.depth_mm,
                "shelf_count": request.shelf_count,
                "parts_calculated": [part.model_dump() for part in parts],
                "edge_band_m": total_edge_band_m,
                "total_area_m2": total_area_m2,
                "material_usage": material_usage,
                "created_at": datetime.utcnow()
            }
            await db.units.insert_one(unit_doc)
        
        return UnitCalculateResponse(
            unit_id=unit_id,
            type=request.type,
            width_mm=request.width_mm,
            height_mm=request.height_mm,
            depth_mm=request.depth_mm,
            shelf_count=request.shelf_count,
            parts=parts,
            total_edge_band_m=round(total_edge_band_m, 2),
            total_area_m2=round(total_area_m2, 4),
            material_usage=material_usage
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating unit: {str(e)}"
        )

@router.get("/{unit_id}", response_model=UnitCalculateResponse)
async def get_unit(unit_id: str):
    """
    جلب تفاصيل الوحدة المحفوظة
    
    Returns the saved unit calculation details
    """
    try:
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        unit_doc = await db.units.find_one({"_id": unit_id})
        
        if unit_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unit with id {unit_id} not found"
            )
        
        # Convert to response model
        from app.models.units import Part
        
        parts = [Part(**part) for part in unit_doc.get("parts_calculated", [])]
        
        return UnitCalculateResponse(
            unit_id=unit_id,
            type=UnitType(unit_doc["type"]),
            width_mm=unit_doc["width_mm"],
            height_mm=unit_doc["height_mm"],
            depth_mm=unit_doc["depth_mm"],
            shelf_count=unit_doc["shelf_count"],
            parts=parts,
            total_edge_band_m=unit_doc.get("edge_band_m", 0),
            total_area_m2=unit_doc.get("total_area_m2", 0),
            material_usage=unit_doc.get("material_usage", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving unit: {str(e)}"
        )

@router.post("/estimate", response_model=UnitEstimateResponse)
async def estimate_unit_cost(request: UnitEstimateRequest):
    """
    تقدير تكلفة الوحدة
    
    يحسب الوحدة ويعطي تقدير تكلفة مفصل اعتمادًا على أسعار المواد من الإعدادات
    """
    try:
        # جلب الإعدادات
        settings = await get_settings_model()
        
        # حساب القطع (نفس calculate_unit)
        parts = calculate_unit_parts(
            unit_type=request.type,
            width_mm=request.width_mm,
            height_mm=request.height_mm,
            depth_mm=request.depth_mm,
            shelf_count=request.shelf_count,
            settings=settings,
            options=request.options or {}
        )
        
        # حساب الإجماليات
        total_edge_band_m = calculate_total_edge_band(parts)
        total_area_m2 = calculate_total_area(parts)
        
        # حساب استخدام المواد (يستخدم settings مباشرة)
        material_usage = calculate_material_usage(
            total_area_m2=total_area_m2,
            edge_band_m=total_edge_band_m,
            settings=settings
        )
        
        # حساب التكلفة
        cost_breakdown = {}
        total_cost = 0.0
        
        # تكلفة الألواح
        if "plywood_sheet" in settings.materials:
            plywood_price = settings.materials["plywood_sheet"].price_per_sheet
            if plywood_price:
                plywood_cost = material_usage["plywood_sheets"] * plywood_price
                cost_breakdown["plywood"] = round(plywood_cost, 2)
                total_cost += plywood_cost
        
        # تكلفة الشريط
        if "edge_band_per_meter" in settings.materials:
            edge_price = settings.materials["edge_band_per_meter"].price_per_meter
            if edge_price:
                edge_cost = material_usage["edge_m"] * edge_price
                cost_breakdown["edge_band"] = round(edge_cost, 2)
                total_cost += edge_cost
        
        # حفظ في MongoDB
        unit_id = None
        db = get_database()
        if db is not None:
            unit_id = f"unit_{uuid.uuid4().hex[:8].upper()}"
            unit_doc = {
                "_id": unit_id,
                "type": request.type.value,
                "width_mm": request.width_mm,
                "height_mm": request.height_mm,
                "depth_mm": request.depth_mm,
                "shelf_count": request.shelf_count,
                "parts_calculated": [part.model_dump() for part in parts],
                "edge_band_m": total_edge_band_m,
                "total_area_m2": total_area_m2,
                "material_usage": material_usage,
                "price_estimate": total_cost,
                "created_at": datetime.utcnow()
            }
            await db.units.insert_one(unit_doc)
        
        return UnitEstimateResponse(
            unit_id=unit_id,
            type=request.type,
            width_mm=request.width_mm,
            height_mm=request.height_mm,
            depth_mm=request.depth_mm,
            shelf_count=request.shelf_count,
            parts=parts,
            total_edge_band_m=round(total_edge_band_m, 2),
            total_area_m2=round(total_area_m2, 4),
            material_usage=material_usage,
            cost_breakdown=cost_breakdown,
            total_cost=round(total_cost, 2)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error estimating unit cost: {str(e)}"
        )

@router.post("/{unit_id}/internal-counter/calculate", response_model=InternalCounterResponse)
async def calculate_internal_counter(unit_id: str, request: InternalCounterRequest):
    """
    حساب القطع الداخلية للكونتر
    
    يحسب القطع الداخلية مثل:
    - القاعدة الداخلية
    - المرآة الأمامية
    - الرف الداخلي
    - الأدراج (قاع، جوانب، خلفية)
    
    بناءً على أبعاد الوحدة المحفوظة وخيارات القطع الداخلية
    """
    try:
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # جلب بيانات الوحدة
        unit_doc = await db.units.find_one({"_id": unit_id})
        
        if unit_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unit with id {unit_id} not found"
            )
        
        # جلب الإعدادات
        settings = await get_settings_model()
        
        # استخراج بيانات الوحدة
        unit_type = UnitType(unit_doc["type"])
        unit_width_mm = unit_doc["width_mm"]
        unit_height_mm = unit_doc["height_mm"]
        unit_depth_mm = unit_doc["depth_mm"]
        
        # استخدام الخيارات من الطلب أو القيم الافتراضية
        options = request.options if request.options else InternalCounterOptions()
        
        # حساب القطع الداخلية
        internal_parts = calculate_internal_counter_parts(
            unit_type=unit_type,
            unit_width_mm=unit_width_mm,
            unit_height_mm=unit_height_mm,
            unit_depth_mm=unit_depth_mm,
            settings=settings,
            options=options
        )
        
        # حساب الإجماليات
        total_edge_band_m = calculate_internal_total_edge_band(internal_parts)
        total_area_m2 = calculate_internal_total_area(internal_parts)
        
        # حساب استخدام المواد (يستخدم settings مباشرة)
        material_usage = calculate_internal_material_usage(
            total_area_m2=total_area_m2,
            edge_band_m=total_edge_band_m,
            settings=settings
        )
        
        # حفظ القطع الداخلية في الوحدة (update)
        await db.units.update_one(
            {"_id": unit_id},
            {
                "$set": {
                    "internal_counter_parts": [part.model_dump() for part in internal_parts],
                    "internal_counter_edge_band_m": total_edge_band_m,
                    "internal_counter_total_area_m2": total_area_m2,
                    "internal_counter_material_usage": material_usage,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return InternalCounterResponse(
            unit_id=unit_id,
            unit_type=unit_type,
            parts=internal_parts,
            total_edge_band_m=round(total_edge_band_m, 2),
            total_area_m2=round(total_area_m2, 4),
            material_usage=material_usage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating internal counter: {str(e)}"
        )

@router.get("/{unit_id}/edge-breakdown", response_model=EdgeBreakdownResponse)
async def get_edge_breakdown(unit_id: str, edge_type: Optional[str] = None):
    """
    جلب تفاصيل توزيع الشريط للوحدة
    
    يعرض تفاصيل توزيع الشريط لكل قطعة في الوحدة:
    - الحواف التي تحتاج شريط (top, bottom, left, right)
    - طول كل حافة بالمليمتر والمتر
    - نوع الشريط (خشبي/PVC)
    - إجمالي متر الشريط لكل قطعة
    - التكلفة الإجمالية
    
    Parameters:
    - unit_id: معرف الوحدة
    - edge_type: نوع الشريط (wood/pvc) - اختياري
    """
    try:
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # جلب بيانات الوحدة
        unit_doc = await db.units.find_one({"_id": unit_id})
        
        if unit_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unit with id {unit_id} not found"
            )
        
        # جلب الإعدادات
        settings = await get_settings_model()
        
        # تحديد نوع الشريط
        selected_edge_type = EdgeType.PVC  # Default
        if edge_type:
            try:
                selected_edge_type = EdgeType(edge_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid edge_type: {edge_type}. Must be 'wood' or 'pvc'"
                )
        
        # تحويل parts من MongoDB إلى Part objects
        from app.models.units import Part
        
        parts_data = unit_doc.get("parts_calculated", [])
        parts = [Part(**part_data) for part_data in parts_data]
        
        # حساب توزيع الشريط
        edge_breakdown = calculate_edge_breakdown(parts, settings, selected_edge_type)
        
        # حساب الإجماليات
        total_edge_m = calculate_total_edge_meters(edge_breakdown)
        
        # حساب التكلفة
        cost_info = calculate_edge_cost(edge_breakdown, settings)
        
        return EdgeBreakdownResponse(
            unit_id=unit_id,
            parts=edge_breakdown,
            total_edge_m=round(total_edge_m, 3),
            total_cost=cost_info["total"] if cost_info["total"] > 0 else None,
            cost_breakdown=cost_info["breakdown"] if cost_info["breakdown"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating edge breakdown: {str(e)}"
        )

