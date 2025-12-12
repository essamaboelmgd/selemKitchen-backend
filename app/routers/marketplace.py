from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from typing import List, Optional
from app.services.marketplace_service import MarketplaceService, get_marketplace_service
from app.models.marketplace import (
    MarketplaceItemCreate,
    MarketplaceItemUpdate,
    MarketplaceItemResponse,
    ItemStatus
)
from app.routers.auth import get_current_user
from app.models.auth import UserResponse

router = APIRouter()

@router.post("/items", response_model=MarketplaceItemResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(
    item_data: MarketplaceItemCreate,
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Create a new marketplace listing.
    """
    item = await service.create_item(user_id=current_user.user_id, item_data=item_data)
    
    # Map to response (can add seller info resolution here if needed, keeping simple for now)
    return MarketplaceItemResponse(
        item_id=item.id,
        seller_id=item.seller_id,
        seller_name=current_user.full_name, # Optimization: we know the seller is the current user
        **item.model_dump()
    )

@router.get("/items", response_model=List[MarketplaceItemResponse])
async def list_items(
    status: ItemStatus = Query(ItemStatus.AVAILABLE, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    List marketplace items.
    """
    items = await service.get_items(status=status, skip=skip, limit=limit)
    
    # We might want to fetch seller names here in a real app (e.g. via aggregation or separate queries)
    # For now returning without resolving names for other sellers to keep it efficient/simple as per scope
    return [
        MarketplaceItemResponse(
            item_id=item.id,
            seller_id=item.seller_id,
            # seller_name=... # Would require fetching user details
            **item.model_dump()
        ) for item in items
    ]

@router.get("/my-orders", response_model=List[MarketplaceItemResponse])
async def get_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Get items bought by the current user.
    """
    items = await service.get_items_by_buyer(buyer_id=current_user.user_id, skip=skip, limit=limit)
    return [
        MarketplaceItemResponse(
            item_id=item.id,
            seller_id=item.seller_id,
            **item.model_dump()
        ) for item in items
    ]

@router.get("/items/{item_id}", response_model=MarketplaceItemResponse)
async def get_item(
    item_id: str = Path(..., description="Item ID"),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Get a specific marketplace item.
    """
    item = await service.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    return MarketplaceItemResponse(
        item_id=item.id,
        **item.model_dump()
    )

@router.put("/items/{item_id}", response_model=MarketplaceItemResponse)
async def update_listing(
    update_data: MarketplaceItemUpdate,
    item_id: str = Path(..., description="Item ID"),
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Update a listing (Seller only).
    """
    item = await service.update_item(item_id=item_id, user_id=current_user.user_id, update_data=update_data)
    return MarketplaceItemResponse(
        item_id=item.id,
        **item.model_dump()
    )

@router.post("/items/{item_id}/buy", response_model=MarketplaceItemResponse)
async def buy_item(
    item_id: str = Path(..., description="Item ID"),
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Buy an item.
    """
    item = await service.buy_item(item_id=item_id, buyer_id=current_user.user_id)
    return MarketplaceItemResponse(
        item_id=item.id,
        **item.model_dump()
    )

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(
    item_id: str = Path(..., description="Item ID"),
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Delete a listing (Seller only).
    """
    await service.delete_item(item_id=item_id, user_id=current_user.user_id)
    return None
