from fastapi import APIRouter, Depends, Query, Path, HTTPException, status, UploadFile, File
from pydantic import BaseModel
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
import shutil
import uuid
import os

router = APIRouter()
UPLOAD_DIR = "uploads"

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Upload an image for a marketplace item.
    """
    # Create unique filename
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Check file size (10 MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB in bytes
    
    # Move cursor to end to get size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    # Reset cursor to start
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size too large. Maximum size is 10 MB."
        )
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Return URL (relative path that will be served by StaticFiles)
    # The frontend knows the base URL, so we can return /uploads/filename
    return {"url": f"/uploads/{filename}"}

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
    
    # Map to response
    return MarketplaceItemResponse(
        item_id=item.id,  # Map id to item_id
        seller_name=current_user.full_name,
        **item.model_dump(exclude={'id'}) # Exclude id so we don't pass it if it exists, relying on item_id key
    )

@router.get("/items", response_model=List[MarketplaceItemResponse])
async def list_items(
    q: Optional[str] = Query(None, description="Search term for title or description"),
    status: Optional[str] = Query('available', description="Filter by status (available, sold, reserved, My Orders)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    List marketplace items with search and filter.
    """
    # Handle "all" status from frontend by passing None to service if status is generic or empty
    status_enum = None
    if status and status != 'all':
        try:
             status_enum = ItemStatus(status)
        except ValueError:
             pass # Ignore invalid status or handle as None
             
    items = await service.get_items(status=status_enum, search_query=q, skip=skip, limit=limit)
    
    # We might want to fetch seller names here in a real app (e.g. via aggregation or separate queries)
    # For now returning without resolving names for other sellers to keep it efficient/simple as per scope
    return [
        MarketplaceItemResponse(
            item_id=item.id,
            # seller_name=... # Would require fetching user details
            **item.model_dump(exclude={'id'})
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
            **item.model_dump(exclude={'id'})
        ) for item in items
    ]

@router.get("/my-listings", response_model=List[MarketplaceItemResponse])
async def get_my_listings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Get all items listed by the current user (My Listings).
    """
    items = await service.get_items_by_owner(seller_id=current_user.user_id, skip=skip, limit=limit)
    return [
        MarketplaceItemResponse(
            item_id=item.id,
            seller_name=current_user.full_name, # Optimization: we know the seller is the current user
            **item.model_dump(exclude={'id'})
        ) for item in items
    ]

@router.get("/sales", response_model=List[MarketplaceItemResponse])
async def get_my_sales(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Get items sold by the current user.
    """
    items = await service.get_items_by_seller(seller_id=current_user.user_id, skip=skip, limit=limit)
    return [
        MarketplaceItemResponse(
            item_id=item.id,
            **item.model_dump(exclude={'id'})
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
        
    # Fetch seller details
    seller = await service.db.users.find_one({"_id": item.seller_id})
    seller_phone = seller.get("phone") if seller else None
    seller_name = seller.get("full_name") if seller else None
    
    return MarketplaceItemResponse(
        item_id=item.id,
        seller_phone=seller_phone,
        seller_name=seller_name,
        **item.model_dump(exclude={'id'})
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
        **item.model_dump(exclude={'id'})
    )

class BuyRequest(BaseModel):
    quantity: int = 1

@router.post("/items/{item_id}/buy", response_model=MarketplaceItemResponse)
async def buy_item(
    buy_request: BuyRequest,
    item_id: str = Path(..., description="Item ID"),
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Buy an item.
    """
    item = await service.buy_item(item_id=item_id, buyer_id=current_user.user_id, quantity=buy_request.quantity)
    return MarketplaceItemResponse(
        item_id=item.id,
        **item.model_dump(exclude={'id'})
    )

@router.post("/items/{item_id}/accept", response_model=MarketplaceItemResponse)
async def accept_order(
    item_id: str = Path(..., description="Item ID"),
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Accept a pending order (Seller only).
    """
    item = await service.accept_order(item_id=item_id, seller_id=current_user.user_id)
    return MarketplaceItemResponse(
        item_id=item.id,
        **item.model_dump(exclude={'id'})
    )

@router.post("/items/{item_id}/deny", response_model=MarketplaceItemResponse)
async def deny_order(
    item_id: str = Path(..., description="Item ID"),
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Deny a pending order (Seller only).
    """
    item = await service.deny_order(item_id=item_id, seller_id=current_user.user_id)
    return MarketplaceItemResponse(
        item_id=item.id,
        **item.model_dump(exclude={'id'})
    )

@router.get("/items/{item_id}/buyer-contact")
async def get_buyer_contact(
    item_id: str = Path(..., description="Item ID"),
    current_user: UserResponse = Depends(get_current_user),
    service: MarketplaceService = Depends(get_marketplace_service)
):
    """
    Get buyer contact details for an accepted order (Seller only).
    """
    return await service.get_buyer_details(item_id=item_id, seller_id=current_user.user_id)

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
