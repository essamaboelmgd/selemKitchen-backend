from fastapi import APIRouter, HTTPException, status
from app.database import get_database
from app.models.summary import SummaryRequest, SummaryResponse, SummaryItem
from app.models.settings import SettingsModel
from app.routers.settings import get_settings_from_db
from app.services.summary_generator import generate_summary
from datetime import datetime
from typing import Dict, Any
from bson import ObjectId
import uuid

router = APIRouter()

async def get_settings_model() -> SettingsModel:
    """Get settings as SettingsModel"""
    settings_doc = await get_settings_from_db()
    settings_doc.pop("_id", None)
    return SettingsModel(**settings_doc)

@router.post("/generate", response_model=SummaryResponse)
async def generate_unit_summary(request: SummaryRequest):
    """
    توليد ملخص شامل للوحدة
    
    يقبل مواصفات الوحدة ويولد ملخص يتضمن:
    - قائمة القطع مع الأبعاد والكميات
    - إجمالي المساحة ومتر الشريط
    - استخدام المواد
    - التكاليف الإجمالية
    - إمكانية تضمين القطع الداخلية
    """
    try:
        # جلب الإعدادات
        settings = await get_settings_model()
        
        # توليد الملخص
        summary_data = generate_summary(
            unit_type=request.type,
            width_mm=request.width_mm,
            height_mm=request.height_mm,
            depth_mm=request.depth_mm,
            shelf_count=request.shelf_count,
            settings=settings,
            options=request.options or {},
            include_internal_counter=request.include_internal_counter,
            internal_counter_options=request.internal_counter_options
        )
        
        # حفظ الوحدة أولاً
        unit_id = None
        summary_id = None
        db = get_database()
        
        if db:
            # إنشاء أو تحديث الوحدة
            unit_id = f"unit_{uuid.uuid4().hex[:8].upper()}"
            summary_id = f"summary_{uuid.uuid4().hex[:8].upper()}"
            
            # حفظ الوحدة
            unit_doc = {
                "_id": unit_id,
                "type": request.type.value,
                "width_mm": request.width_mm,
                "height_mm": request.height_mm,
                "depth_mm": request.depth_mm,
                "shelf_count": request.shelf_count,
                "parts_calculated": [item.model_dump() for item in summary_data["items"]],
                "edge_band_m": summary_data["totals"]["total_edge_band_m"],
                "total_area_m2": summary_data["totals"]["total_area_m2"],
                "material_usage": summary_data["material_usage"],
                "created_at": datetime.utcnow()
            }
            await db.units.insert_one(unit_doc)
            
            # حفظ الملخص
            summary_doc = {
                "_id": summary_id,
                "unit_id": unit_id,
                "type": request.type.value,
                "width_mm": request.width_mm,
                "height_mm": request.height_mm,
                "depth_mm": request.depth_mm,
                "shelf_count": request.shelf_count,
                "items": [item.model_dump() for item in summary_data["items"]],
                "totals": summary_data["totals"],
                "material_usage": summary_data["material_usage"],
                "costs": summary_data["costs"],
                "generated_at": datetime.utcnow()
            }
            await db.unit_summaries.insert_one(summary_doc)
        
        return SummaryResponse(
            summary_id=summary_id,
            unit_id=unit_id,
            type=request.type,
            unit_dimensions={
                "width_mm": request.width_mm,
                "height_mm": request.height_mm,
                "depth_mm": request.depth_mm
            },
            shelf_count=request.shelf_count,
            items=summary_data["items"],
            totals=summary_data["totals"],
            material_usage=summary_data["material_usage"],
            costs=summary_data["costs"],
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}"
        )

@router.get("/{unit_id}", response_model=SummaryResponse)
async def get_unit_summary(unit_id: str):
    """
    جلب ملخص الوحدة المحفوظ
    
    Returns the saved summary for a unit
    """
    try:
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # البحث عن الملخص
        summary_doc = await db.unit_summaries.find_one({"unit_id": unit_id})
        
        if summary_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Summary for unit {unit_id} not found"
            )
        
        # Convert ObjectId to string if present
        if "_id" in summary_doc and isinstance(summary_doc["_id"], ObjectId):
            summary_doc["_id"] = str(summary_doc["_id"])
        
        # Convert to response model
        from app.models.units import UnitType
        
        items = [SummaryItem(**item) for item in summary_doc.get("items", [])]
        
        return SummaryResponse(
            summary_id=str(summary_doc["_id"]),
            unit_id=summary_doc["unit_id"],
            type=UnitType(summary_doc["type"]),
            unit_dimensions={
                "width_mm": summary_doc["width_mm"],
                "height_mm": summary_doc["height_mm"],
                "depth_mm": summary_doc["depth_mm"]
            },
            shelf_count=summary_doc["shelf_count"],
            items=items,
            totals=summary_doc.get("totals", {}),
            material_usage=summary_doc.get("material_usage", {}),
            costs=summary_doc.get("costs", {}),
            generated_at=summary_doc.get("generated_at", datetime.utcnow())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving summary: {str(e)}"
        )

