from typing import List, Optional
from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.marketplace import (
    MarketplaceItemCreate,
    MarketplaceItemUpdate,
    MarketplaceItemDocument,
    ItemStatus,
    MarketplaceItemResponse
)
from app.database import get_database

class MarketplaceService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.marketplace_items

    async def create_item(self, user_id: str, item_data: MarketplaceItemCreate) -> MarketplaceItemDocument:
        item_dict = item_data.model_dump()
        item_doc = MarketplaceItemDocument(
            _id=str(uuid4()),
            seller_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status=ItemStatus.AVAILABLE,
            **item_dict
        )
        
        await self.collection.insert_one(item_doc.model_dump(by_alias=True))
        return item_doc

    async def get_items(self, status: Optional[ItemStatus] = ItemStatus.AVAILABLE, skip: int = 0, limit: int = 20) -> List[MarketplaceItemDocument]:
        query = {}
        if status:
            query["status"] = status
            
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        items = []
        async for doc in cursor:
            items.append(MarketplaceItemDocument(**doc))
        return items

    async def get_items_by_buyer(self, buyer_id: str, skip: int = 0, limit: int = 20) -> List[MarketplaceItemDocument]:
        query = {"buyer_id": buyer_id, "status": ItemStatus.SOLD}
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("updated_at", -1)
        items = []
        async for doc in cursor:
            items.append(MarketplaceItemDocument(**doc))
        return items

    async def get_item_by_id(self, item_id: str) -> Optional[MarketplaceItemDocument]:
        doc = await self.collection.find_one({"_id": item_id})
        if doc:
            return MarketplaceItemDocument(**doc)
        return None

    async def update_item(self, item_id: str, user_id: str, update_data: MarketplaceItemUpdate) -> Optional[MarketplaceItemDocument]:
        item = await self.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        if item.seller_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this item")

        update_dict = update_data.model_dump(exclude_unset=True)
        if update_dict:
            update_dict["updated_at"] = datetime.utcnow()
            await self.collection.update_one(
                {"_id": item_id},
                {"$set": update_dict}
            )
            return await self.get_item_by_id(item_id)
        return item

    async def buy_item(self, item_id: str, buyer_id: str) -> MarketplaceItemDocument:
        item = await self.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        if item.status != ItemStatus.AVAILABLE:
            raise HTTPException(status_code=400, detail="Item is not available for sale")
            
        if item.seller_id == buyer_id:
            raise HTTPException(status_code=400, detail="Cannot buy your own item")

        update_result = await self.collection.update_one(
            {"_id": item_id, "status": ItemStatus.AVAILABLE}, # Atomic check
            {
                "$set": {
                    "status": ItemStatus.SOLD,
                    "buyer_id": buyer_id,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if update_result.modified_count == 0:
             raise HTTPException(status_code=409, detail="Item was just sold to someone else")
             
        return await self.get_item_by_id(item_id)

    async def delete_item(self, item_id: str, user_id: str) -> bool:
        item = await self.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        if item.seller_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this item")
            
        result = await self.collection.delete_one({"_id": item_id})
        return result.deleted_count > 0

# Helper to get service instance
async def get_marketplace_service() -> MarketplaceService:
    db = await get_database()
    return MarketplaceService(db)
