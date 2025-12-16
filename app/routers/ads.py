from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.services.ads_service import AdsService, get_ads_service
from app.models.ads import AdCreate, AdResponse, AdLocation
from app.routers.auth import get_current_user
from app.models.auth import UserResponse, UserRole

router = APIRouter()

@router.post("/", response_model=AdResponse, status_code=status.HTTP_201_CREATED)
async def create_ad(
    ad_data: AdCreate,
    current_user: UserResponse = Depends(get_current_user),
    service: AdsService = Depends(get_ads_service)
):
    """Create a new ad (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    ad = await service.create_ad(ad_data)
    return AdResponse(ad_id=ad.id, **ad.model_dump(exclude={'id'}))

@router.get("/", response_model=List[AdResponse])
async def get_ads(
    location: Optional[AdLocation] = Query(None, description="Filter by location"),
    service: AdsService = Depends(get_ads_service)
):
    """Get active ads (Public)"""
    ads = await service.get_ads(location=location, active_only=True)
    return [AdResponse(ad_id=ad.id, **ad.model_dump(exclude={'id'})) for ad in ads]

@router.get("/admin", response_model=List[AdResponse])
async def get_all_ads_admin(
    current_user: UserResponse = Depends(get_current_user),
    service: AdsService = Depends(get_ads_service)
):
    """Get all ads including inactive (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    ads = await service.get_all_ads()
    return [AdResponse(ad_id=ad.id, **ad.model_dump(exclude={'id'})) for ad in ads]

@router.delete("/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ad(
    ad_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: AdsService = Depends(get_ads_service)
):
    """Delete an ad (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    success = await service.delete_ad(ad_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ad not found")
    return None

@router.put("/{ad_id}/toggle", response_model=AdResponse)
async def toggle_ad(
    ad_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: AdsService = Depends(get_ads_service)
):
    """Toggle active status (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    ad = await service.toggle_ad_status(ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
        
    return AdResponse(ad_id=ad.id, **ad.model_dump(exclude={'id'}))
