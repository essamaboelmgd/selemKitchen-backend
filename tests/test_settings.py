import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_database
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Test client
client = TestClient(app)

@pytest.fixture
async def test_db():
    """Setup test database"""
    # Use a test database
    test_mongodb_url = os.getenv("TEST_MONGODB_URL", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
    test_db_name = "test_kitchen_db"
    
    # Connect to test database
    test_client = AsyncIOMotorClient(test_mongodb_url)
    test_database = test_client[test_db_name]
    
    yield test_database
    
    # Cleanup: drop test database
    await test_client.drop_database(test_db_name)
    test_client.close()

@pytest.mark.asyncio
async def test_get_settings_default():
    """Test getting default settings when none exist"""
    response = client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    
    assert "assembly_method" in data
    assert "handle_type" in data
    assert "handle_recess_height_mm" in data
    assert "default_board_thickness_mm" in data
    assert "materials" in data
    assert data["assembly_method"] == "bolt"
    assert data["handle_type"] == "built-in"
    assert data["handle_recess_height_mm"] == 30
    assert data["default_board_thickness_mm"] == 16

@pytest.mark.asyncio
async def test_update_settings():
    """Test updating settings"""
    # Update settings
    update_data = {
        "assembly_method": "screw",
        "handle_type": "external",
        "handle_recess_height_mm": 40,
        "default_board_thickness_mm": 18
    }
    
    response = client.put("/settings", json=update_data)
    assert response.status_code == 200
    data = response.json()
    
    assert data["assembly_method"] == "screw"
    assert data["handle_type"] == "external"
    assert data["handle_recess_height_mm"] == 40
    assert data["default_board_thickness_mm"] == 18
    assert "last_updated" in data

@pytest.mark.asyncio
async def test_update_settings_partial():
    """Test partial update of settings"""
    # First, set some initial values
    initial_data = {
        "assembly_method": "screw",
        "handle_type": "external"
    }
    client.put("/settings", json=initial_data)
    
    # Update only one field
    update_data = {
        "handle_recess_height_mm": 50
    }
    
    response = client.put("/settings", json=update_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check that only the updated field changed
    assert data["handle_recess_height_mm"] == 50
    # Other fields should remain
    assert data["assembly_method"] == "screw"
    assert data["handle_type"] == "external"

@pytest.mark.asyncio
async def test_update_settings_materials():
    """Test updating materials prices"""
    update_data = {
        "materials": {
            "plywood_sheet": {
                "price_per_sheet": 3000,
                "sheet_size_m2": 2.4
            },
            "edge_band_per_meter": {
                "price_per_meter": 15
            }
        }
    }
    
    response = client.put("/settings", json=update_data)
    assert response.status_code == 200
    data = response.json()
    
    assert "materials" in data
    assert "plywood_sheet" in data["materials"]
    assert data["materials"]["plywood_sheet"]["price_per_sheet"] == 3000
    assert "edge_band_per_meter" in data["materials"]
    assert data["materials"]["edge_band_per_meter"]["price_per_meter"] == 15

@pytest.mark.asyncio
async def test_get_settings_after_update():
    """Test getting settings after update"""
    # Update settings
    update_data = {
        "assembly_method": "glue",
        "handle_type": "push"
    }
    client.put("/settings", json=update_data)
    
    # Get settings
    response = client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    
    assert data["assembly_method"] == "glue"
    assert data["handle_type"] == "push"

@pytest.mark.asyncio
async def test_update_settings_empty():
    """Test updating with empty data (should return current settings)"""
    # First set some values
    client.put("/settings", json={"assembly_method": "bolt"})
    
    # Try to update with empty data
    response = client.put("/settings", json={})
    assert response.status_code == 200
    data = response.json()
    
    # Should return current settings
    assert "assembly_method" in data
    assert data["assembly_method"] == "bolt"

