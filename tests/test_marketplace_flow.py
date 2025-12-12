
import pytest
from httpx import AsyncClient
from app.main import app
from app.models.marketplace import ItemStatus

# Mock data
USER_1_PHONE = "01000000001"
USER_1_PASS = "password123"
USER_2_PHONE = "01000000002"
USER_2_PASS = "password123"

@pytest.mark.asyncio
async def test_marketplace_flow():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        
        # 1. Register User 1 (Seller)
        await ac.post("/auth/register", json={
            "phone": USER_1_PHONE,
            "password": USER_1_PASS,
            "full_name": "Seller User"
        })
        
        # Login User 1
        response = await ac.post("/auth/login", json={
            "phone": USER_1_PHONE,
            "password": USER_1_PASS,
            "device_id": "device1"
        })
        assert response.status_code == 200
        token_1 = response.json()["access_token"]
        headers_1 = {"Authorization": f"Bearer {token_1}"}

        # 2. Register User 2 (Buyer)
        await ac.post("/auth/register", json={
            "phone": USER_2_PHONE,
            "password": USER_2_PASS,
            "full_name": "Buyer User"
        })
        
        # Login User 2
        response = await ac.post("/auth/login", json={
            "phone": USER_2_PHONE,
            "password": USER_2_PASS,
            "device_id": "device2"
        })
        assert response.status_code == 200
        token_2 = response.json()["access_token"]
        headers_2 = {"Authorization": f"Bearer {token_2}"}

        # 3. Create Listing (User 1)
        item_data = {
            "title": "Wood Plank",
            "description": "High quality oak wood",
            "price": 100.0,
            "quantity": 5,
            "unit": "plank",
            "location": "Cairo"
        }
        response = await ac.post("/marketplace/items", json=item_data, headers=headers_1)
        assert response.status_code == 201
        item_id = response.json()["item_id"]
        assert response.json()["seller_id"] is not None
        assert response.json()["status"] == ItemStatus.AVAILABLE

        # 4. List Items (User 2)
        response = await ac.get("/marketplace/items", headers=headers_2)
        assert response.status_code == 200
        items = response.json()
        assert len(items) > 0
        assert items[0]["item_id"] == item_id

        # 5. Buy Item (User 2)
        response = await ac.post(f"/marketplace/items/{item_id}/buy", headers=headers_2)
        assert response.status_code == 200
        assert response.json()["status"] == ItemStatus.SOLD

        # 6. Verify Item Status (User 1)
        response = await ac.get(f"/marketplace/items/{item_id}", headers=headers_1)
        assert response.status_code == 200
        assert response.json()["status"] == ItemStatus.SOLD

        # 7. Try to buy again (should fail)
        response = await ac.post(f"/marketplace/items/{item_id}/buy", headers=headers_2)
        assert response.status_code == 400

        print("\nMarketplace Verification Successful!")
