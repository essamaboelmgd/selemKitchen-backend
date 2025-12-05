import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.units import UnitType
from app.database import get_database
from motor.motor_asyncio import AsyncIOMotorClient
import os

client = TestClient(app)

@pytest.fixture
def cleanup_units():
    """Cleanup units after test"""
    yield
    # Cleanup will be done in each test

@pytest.mark.asyncio
async def test_calculate_ground_unit():
    """Test calculating a ground unit"""
    request_data = {
        "type": "ground",
        "width_cm": 80,
        "height_cm": 72,
        "depth_cm": 30,
        "shelf_count": 2,
        "options": {}
    }
    
    response = client.post("/units/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "unit_id" in data
    assert data["type"] == "ground"
    assert data["width_cm"] == 80
    assert data["height_cm"] == 72
    assert data["depth_cm"] == 30
    assert data["shelf_count"] == 2
    
    # Check parts
    assert "parts" in data
    assert isinstance(data["parts"], list)
    assert len(data["parts"]) > 0
    
    # Check for expected parts
    part_names = [part["name"] for part in data["parts"]]
    assert "side_panel" in part_names
    assert "top_panel" in part_names
    assert "bottom_panel" in part_names
    assert "back_panel" in part_names
    
    # Check shelves
    shelf_parts = [p for p in data["parts"] if p["name"].startswith("shelf")]
    assert len(shelf_parts) == 2
    
    # Check totals
    assert "total_edge_band_m" in data
    assert data["total_edge_band_m"] > 0
    assert "total_area_m2" in data
    assert data["total_area_m2"] > 0
    assert "material_usage" in data

@pytest.mark.asyncio
async def test_calculate_wall_unit():
    """Test calculating a wall unit"""
    request_data = {
        "type": "wall",
        "width_cm": 60,
        "height_cm": 50,
        "depth_cm": 25,
        "shelf_count": 1,
        "options": {}
    }
    
    response = client.post("/units/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    assert data["type"] == "wall"
    assert data["width_cm"] == 60
    assert data["height_cm"] == 50
    assert data["depth_cm"] == 25
    assert data["shelf_count"] == 1
    
    # Check parts
    assert len(data["parts"]) > 0
    shelf_parts = [p for p in data["parts"] if p["name"].startswith("shelf")]
    assert len(shelf_parts) == 1

@pytest.mark.asyncio
async def test_calculate_double_door_unit():
    """Test calculating a double door unit"""
    request_data = {
        "type": "double_door",
        "width_cm": 100,
        "height_cm": 80,
        "depth_cm": 35,
        "shelf_count": 3,
        "options": {}
    }
    
    response = client.post("/units/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    assert data["type"] == "double_door"
    assert data["width_cm"] == 100
    assert data["shelf_count"] == 3
    
    # Check shelves
    shelf_parts = [p for p in data["parts"] if p["name"].startswith("shelf")]
    assert len(shelf_parts) == 3

@pytest.mark.asyncio
async def test_calculate_unit_with_options():
    """Test calculating unit with custom options"""
    request_data = {
        "type": "ground",
        "width_cm": 80,
        "height_cm": 72,
        "depth_cm": 30,
        "shelf_count": 2,
        "options": {
            "board_thickness_cm": 1.8,
            "back_clearance_cm": 0.5
        }
    }
    
    response = client.post("/units/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Verify parts were calculated with custom options
    assert len(data["parts"]) > 0
    # The top/bottom panels should be narrower due to thicker sides
    top_panel = next((p for p in data["parts"] if p["name"] == "top_panel"), None)
    assert top_panel is not None
    # Width should be less than unit width due to side thickness
    assert top_panel["width_cm"] < 80

@pytest.mark.asyncio
async def test_calculate_unit_invalid_dimensions():
    """Test calculating unit with invalid dimensions"""
    request_data = {
        "type": "ground",
        "width_cm": -10,  # Invalid
        "height_cm": 72,
        "depth_cm": 30,
        "shelf_count": 2
    }
    
    response = client.post("/units/calculate", json=request_data)
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_get_unit_by_id():
    """Test getting a unit by ID"""
    # First create a unit
    request_data = {
        "type": "ground",
        "width_cm": 80,
        "height_cm": 72,
        "depth_cm": 30,
        "shelf_count": 2
    }
    
    create_response = client.post("/units/calculate", json=request_data)
    assert create_response.status_code == 200
    unit_id = create_response.json()["unit_id"]
    assert unit_id is not None
    
    # Get the unit
    get_response = client.get(f"/units/{unit_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    
    assert data["unit_id"] == unit_id
    assert data["type"] == "ground"
    assert data["width_cm"] == 80
    assert len(data["parts"]) > 0

@pytest.mark.asyncio
async def test_get_unit_not_found():
    """Test getting a non-existent unit"""
    response = client.get("/units/nonexistent_id")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_estimate_unit_cost():
    """Test estimating unit cost"""
    # First set some material prices
    settings_update = {
        "materials": {
            "plywood_sheet": {
                "price_per_sheet": 2500,
                "sheet_size_m2": 2.4
            },
            "edge_band_per_meter": {
                "price_per_meter": 10
            }
        }
    }
    client.put("/settings", json=settings_update)
    
    # Estimate unit cost
    request_data = {
        "type": "ground",
        "width_cm": 80,
        "height_cm": 72,
        "depth_cm": 30,
        "shelf_count": 2
    }
    
    response = client.post("/units/estimate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "cost_breakdown" in data
    assert "total_cost" in data
    assert data["total_cost"] >= 0
    
    # Check that cost breakdown has expected keys
    if "plywood" in data["cost_breakdown"]:
        assert data["cost_breakdown"]["plywood"] >= 0
    if "edge_band" in data["cost_breakdown"]:
        assert data["cost_breakdown"]["edge_band"] >= 0

@pytest.mark.asyncio
async def test_estimate_unit_cost_no_prices():
    """Test estimating cost when no material prices are set"""
    # Clear material prices
    settings_update = {
        "materials": {}
    }
    client.put("/settings", json=settings_update)
    
    request_data = {
        "type": "ground",
        "width_cm": 80,
        "height_cm": 72,
        "depth_cm": 30,
        "shelf_count": 2
    }
    
    response = client.post("/units/estimate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Should still return structure, but costs may be 0
    assert "cost_breakdown" in data
    assert "total_cost" in data

@pytest.mark.asyncio
async def test_calculate_unit_parts_structure():
    """Test that calculated parts have correct structure"""
    request_data = {
        "type": "ground",
        "width_cm": 80,
        "height_cm": 72,
        "depth_cm": 30,
        "shelf_count": 2
    }
    
    response = client.post("/units/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check each part structure
    for part in data["parts"]:
        assert "name" in part
        assert "width_cm" in part
        assert "height_cm" in part
        assert "qty" in part
        assert part["width_cm"] > 0
        assert part["height_cm"] > 0
        assert part["qty"] > 0
        
        # Check optional fields if present
        if "edge_band_m" in part:
            assert part["edge_band_m"] >= 0
        if "area_m2" in part:
            assert part["area_m2"] >= 0

@pytest.mark.asyncio
async def test_calculate_sink_ground_unit():
    """Test calculating a sink ground unit"""
    request_data = {
        "type": "sink_ground",
        "width_cm": 60,
        "height_cm": 72,
        "depth_cm": 32,  # Slightly deeper for sink
        "shelf_count": 2,  # Should be reduced by 1 in calculation
        "options": {}
    }
    
    response = client.post("/units/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "unit_id" in data
    assert data["type"] == "sink_ground"
    assert data["width_cm"] == 60
    assert data["height_cm"] == 72
    assert data["depth_cm"] == 32
    assert data["shelf_count"] == 2
    
    # Check parts
    assert "parts" in data
    assert isinstance(data["parts"], list)
    assert len(data["parts"]) > 0
    
    # Check for expected parts with sink-specific names
    part_names = [part["name"] for part in data["parts"]]
    assert "side_panel" in part_names
    assert "top_panel_sink" in part_names  # Sink-specific naming
    assert "bottom_panel" in part_names
    assert "back_panel_sink" in part_names  # Sink-specific naming
    
    # Check shelves - should be reduced by 1 for sink units
    shelf_parts = [p for p in data["parts"] if p["name"].startswith("shelf")]
    # With shelf_count=2, sink units should have 1 shelf (2-1=1)
    assert len(shelf_parts) == 1
    
    # Check that areas are positive (no negative areas due to cutouts)
    for part in data["parts"]:
        assert part["area_m2"] >= 0
    
    # Check totals
    assert "total_edge_band_m" in data
    assert data["total_edge_band_m"] > 0
    assert "total_area_m2" in data
    assert data["total_area_m2"] > 0
    assert "material_usage" in data

@pytest.mark.asyncio
async def test_calculate_sink_ground_unit_with_custom_cutouts():
    """Test calculating a sink ground unit with custom cutout sizes"""
    request_data = {
        "type": "sink_ground",
        "width_cm": 60,
        "height_cm": 72,
        "depth_cm": 32,
        "shelf_count": 3,
        "options": {
            "sink_cutout_width_cm": 40,
            "sink_cutout_depth_cm": 30,
            "plumbing_cutout_width_cm": 15,
            "plumbing_cutout_height_cm": 8
        }
    }
    
    response = client.post("/units/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check shelves - should have 2 shelves (3-1=2)
    shelf_parts = [p for p in data["parts"] if p["name"].startswith("shelf")]
    assert len(shelf_parts) == 2
    
    # Check that the unit type is correctly identified
    assert data["type"] == "sink_ground"
    
    # Check that areas are positive
    for part in data["parts"]:
        assert part["area_m2"] >= 0

@pytest.mark.asyncio
async def test_calculate_sink_ground_unit_with_shelf():
    """Test calculating a sink ground unit with a shelf"""
    request_data = {
        "type": "sink_ground",
        "width_cm": 60,
        "height_cm": 72,
        "depth_cm": 32,
        "shelf_count": 3,
        "options": {}
    }
    
    response = client.post("/units/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check shelves - should have 2 shelves (3-1=2)
    shelf_parts = [p for p in data["parts"] if p["name"].startswith("shelf")]
    assert len(shelf_parts) == 2
    
    # Check that the unit type is correctly identified
    assert data["type"] == "sink_ground"
    
    # Check that all part areas are non-negative
    for part in data["parts"]:
        if "area_m2" in part:
            assert part["area_m2"] >= 0
        if "area_m2" in part and part["name"] == "top_panel_sink":
            # Top panel should have a smaller area due to sink cutout
            assert part["area_m2"] > 0