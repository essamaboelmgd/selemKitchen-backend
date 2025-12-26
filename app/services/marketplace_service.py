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

    async def get_items(self, status: Optional[ItemStatus] = ItemStatus.AVAILABLE, search_query: str = None, skip: int = 0, limit: int = 20) -> List[MarketplaceItemDocument]:
        query = {}
        if status:
            query["status"] = status
            
        if search_query:
            # Case-insensitive search on title or description
            regex = {"$regex": search_query, "$options": "i"}
            query["$or"] = [
                {"title": regex},
                {"description": regex}
            ]
            
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

    async def get_items_by_owner(self, seller_id: str, skip: int = 0, limit: int = 20) -> List[MarketplaceItemDocument]:
        """Get all items listed by a specific seller (owner) regardless of status"""
        query = {"seller_id": seller_id}
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        items = []
        async for doc in cursor:
            items.append(MarketplaceItemDocument(**doc))
        return items

    async def get_items_by_seller(self, seller_id: str, skip: int = 0, limit: int = 20) -> List[MarketplaceItemDocument]:
        # Get items sold by this seller
        query = {"seller_id": seller_id, "status": {"$in": [ItemStatus.SOLD, ItemStatus.PENDING]}}
        cursor = self.collection.find(query).skip(skip).limit(limit).sort("updated_at", -1)
        items = []
        async for doc in cursor:
            items.append(MarketplaceItemDocument(**doc))
        return items

    async def get_item_by_id(self, item_id: str) -> Optional[MarketplaceItemDocument]:
        doc = await self.collection.find_one({"_id": item_id})
        if doc:
            # Fetch seller phone
            seller = await self.db.users.find_one({"_id": doc["seller_id"]})
            item_doc = MarketplaceItemDocument(**doc)
            
            # We need to manually inject seller phone/name into the response logic
            # Since MarketplaceItemDocument doesn't have seller_phone (it's DB model),
            # we handle this mapping in the Router usually, OR we extend the logic here.
            # To keep it clean, let's return the doc, and let the Router fetch details?
            # NO, better to handle it here if we change the return type or just attach it.
            # But the method returns MarketplaceItemDocument which matches DB schema.
            # I will modify the router to fetch seller details or modify this method to return a dict/enriched object.
            
            # Actually, the Router `get_item` uses `service.get_item_by_id`.
            # And expects `MarketplaceItemResponse`.
            # Let's modify the Router `get_item` to fetch seller info.
            return item_doc
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

    async def buy_item(self, item_id: str, buyer_id: str, quantity: int = 1) -> MarketplaceItemDocument:
        item = await self.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        if item.status != ItemStatus.AVAILABLE:
            raise HTTPException(status_code=400, detail="Item is not available for sale")
            
        if item.quantity < quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock. Available: {item.quantity}")

        if item.seller_id == buyer_id:
            raise HTTPException(status_code=400, detail="Cannot buy your own item")

        # atomic update to decrement quantity
        update_result = await self.collection.update_one(
            {"_id": item_id, "status": ItemStatus.AVAILABLE, "quantity": {"$gte": quantity}},
            {
                "$inc": {"quantity": -quantity},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if update_result.modified_count == 0:
             raise HTTPException(status_code=409, detail="Item stock changed or item no longer available")
        
        # Create a new "Sold/Pending" item record to represent this transaction
        # This preserves the original listing while creating a record for the sale
        sold_item_doc = MarketplaceItemDocument(
            _id=str(uuid4()),
            seller_id=item.seller_id,
            buyer_id=buyer_id,
            title=item.title,
            description=item.description,
            price=item.price * quantity, # Total price for this transaction
            quantity=quantity,
            unit=item.unit,
            images=item.images,
            status=ItemStatus.PENDING,
            location=item.location,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await self.collection.insert_one(sold_item_doc.model_dump(by_alias=True))
             
        return sold_item_doc

    async def accept_order(self, item_id: str, seller_id: str) -> MarketplaceItemDocument:
        item = await self.get_item_by_id(item_id)
        if not item or item.seller_id != seller_id:
             raise HTTPException(status_code=404, detail="Item not found or unauthorized")
        
        if item.status != ItemStatus.PENDING:
             raise HTTPException(status_code=400, detail="Item is not pending approval")

        await self.collection.update_one(
            {"_id": item_id},
            {"$set": {"status": ItemStatus.SOLD, "updated_at": datetime.utcnow()}}
        )
        return await self.get_item_by_id(item_id)

    async def deny_order(self, item_id: str, seller_id: str) -> MarketplaceItemDocument:
        item = await self.get_item_by_id(item_id)
        if not item or item.seller_id != seller_id:
             raise HTTPException(status_code=404, detail="Item not found or unauthorized")
        
        if item.status != ItemStatus.PENDING:
             raise HTTPException(status_code=400, detail="Item is not pending approval")

        await self.collection.update_one(
            {"_id": item_id},
            {"$set": {"status": ItemStatus.AVAILABLE, "buyer_id": None, "updated_at": datetime.utcnow()}}
        )
        return await self.get_item_by_id(item_id)

    async def get_buyer_details(self, item_id: str, seller_id: str) -> dict:
        item = await self.get_item_by_id(item_id)
        if not item or item.seller_id != seller_id:
             raise HTTPException(status_code=404, detail="Item not found or unauthorized")
             
        if item.status != ItemStatus.SOLD:
             raise HTTPException(status_code=400, detail="Can only view buyer details for accepted orders")
             
        # Fetch buyer info from users collection
        buyer = await self.db.users.find_one({"_id": item.buyer_id})
        if not buyer:
             return {"name": "Unknown", "phone": "Unknown"}
             
        return {
            "name": buyer.get("full_name"),
            "phone": buyer.get("phone"),
            "email": buyer.get("email")
        }

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
    db = get_database()
    return MarketplaceService(db)
