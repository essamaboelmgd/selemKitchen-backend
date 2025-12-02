from fastapi import APIRouter, HTTPException, status
from app.database import get_database
from app.models.settings import SettingsModel, SettingsUpdate
from datetime import datetime
from typing import Dict, Any
from bson import ObjectId

router = APIRouter()

SETTINGS_ID = "global"

async def get_settings_from_db() -> Dict[str, Any]:
    """Get settings from MongoDB"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    settings_collection = db.settings
    settings_doc = await settings_collection.find_one({"_id": SETTINGS_ID})
    
    if settings_doc is None:
        # Create default settings if not exists
        default_settings = SettingsModel().model_dump()
        default_settings["_id"] = SETTINGS_ID
        default_settings["last_updated"] = datetime.utcnow()
        await settings_collection.insert_one(default_settings)
        return default_settings
    
    # Convert ObjectId to string if present
    if "_id" in settings_doc and isinstance(settings_doc["_id"], ObjectId):
        settings_doc["_id"] = str(settings_doc["_id"])
    
    return settings_doc

@router.get("", response_model=SettingsModel)
async def get_settings():
    """
    جلب الإعدادات الحالية
    
    Returns the current application settings including:
    - assembly_method: طريقة التجميع
    - handle_type: نوع المقبض
    - handle_recess_height_mm: ارتفاع قطاع المقبض
    - default_board_thickness_mm: سمك الافتراضي للألواح
    - materials: أسعار الخامات
    """
    try:
        settings_doc = await get_settings_from_db()
        # Remove _id from response
        settings_doc.pop("_id", None)
        return SettingsModel(**settings_doc)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving settings: {str(e)}"
        )

@router.put("", response_model=SettingsModel)
async def update_settings(settings_update: SettingsUpdate):
    """
    تحديث الإعدادات
    
    Updates application settings. Only provided fields will be updated.
    """
    try:
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        settings_collection = db.settings
        
        # Get current settings
        current_settings = await get_settings_from_db()
        
        # Prepare update data (only non-None fields)
        update_data = settings_update.model_dump(exclude_unset=True)
        
        if not update_data:
            # No fields to update, return current settings
            current_settings.pop("_id", None)
            return SettingsModel(**current_settings)
        
        # Add last_updated timestamp
        update_data["last_updated"] = datetime.utcnow()
        
        # Update settings
        result = await settings_collection.update_one(
            {"_id": SETTINGS_ID},
            {"$set": update_data},
            upsert=True
        )
        
        # Get updated settings
        updated_settings = await get_settings_from_db()
        updated_settings.pop("_id", None)
        
        return SettingsModel(**updated_settings)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating settings: {str(e)}"
        )

