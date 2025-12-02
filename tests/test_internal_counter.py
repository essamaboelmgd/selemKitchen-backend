import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def create_test_unit():
    """Create a test unit for internal counter tests"""
    request_data = {
        "type": "ground",
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2
    }
    
    response = client.post("/units/calculate", json=request_data)
    assert response.status_code == 200
    unit_id = response.json()["unit_id"]
    
    yield unit_id
    
    # Cleanup (optional - MongoDB will handle it)

@pytest.mark.asyncio
async def test_calculate_internal_counter_base_only(create_test_unit):
    """Test calculating internal counter with base only"""
    unit_id = create_test_unit
    
    request_data = {
        "options": {
            "add_base": True,
            "add_mirror": False,
            "add_internal_shelf": False,
            "drawer_count": 0
        }
    }
    
    response = client.post(f"/units/{unit_id}/internal-counter/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert data["unit_id"] == unit_id
    assert "parts" in data
    assert len(data["parts"]) > 0
    
    # Check for base part
    base_parts = [p for p in data["parts"] if p["name"] == "internal_base"]
    assert len(base_parts) == 1
    
    base_part = base_parts[0]
    assert base_part["type"] == "base"
    assert base_part["width_mm"] > 0
    assert base_part["height_mm"] > 0
    assert base_part["qty"] == 1
    assert "cutting_dimensions" in base_part
    
    # Check totals
    assert "total_edge_band_m" in data
    assert "total_area_m2" in data
    assert "material_usage" in data

@pytest.mark.asyncio
async def test_calculate_internal_counter_with_mirror(create_test_unit):
    """Test calculating internal counter with mirror"""
    unit_id = create_test_unit
    
    request_data = {
        "options": {
            "add_base": True,
            "add_mirror": True,
            "add_internal_shelf": False,
            "drawer_count": 0
        }
    }
    
    response = client.post(f"/units/{unit_id}/internal-counter/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check for mirror part
    mirror_parts = [p for p in data["parts"] if p["name"] == "mirror_front"]
    assert len(mirror_parts) == 1
    
    mirror_part = mirror_parts[0]
    assert mirror_part["type"] == "mirror"
    assert mirror_part["edge_band_m"] == 0  # Mirror doesn't need edge band

@pytest.mark.asyncio
async def test_calculate_internal_counter_with_shelf(create_test_unit):
    """Test calculating internal counter with internal shelf"""
    unit_id = create_test_unit
    
    request_data = {
        "options": {
            "add_base": True,
            "add_mirror": False,
            "add_internal_shelf": True,
            "drawer_count": 0
        }
    }
    
    response = client.post(f"/units/{unit_id}/internal-counter/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check for internal shelf
    shelf_parts = [p for p in data["parts"] if p["name"] == "internal_shelf"]
    assert len(shelf_parts) == 1
    
    shelf_part = shelf_parts[0]
    assert shelf_part["type"] == "shelf"
    assert shelf_part["edge_band_m"] > 0

@pytest.mark.asyncio
async def test_calculate_internal_counter_with_drawers(create_test_unit):
    """Test calculating internal counter with drawers"""
    unit_id = create_test_unit
    
    request_data = {
        "options": {
            "add_base": True,
            "add_mirror": False,
            "add_internal_shelf": False,
            "drawer_count": 2
        }
    }
    
    response = client.post(f"/units/{unit_id}/internal-counter/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check for drawer parts
    drawer_parts = [p for p in data["parts"] if "drawer" in p["name"]]
    assert len(drawer_parts) > 0
    
    # Each drawer should have: bottom, side_left, side_right, back
    drawer_1_parts = [p for p in drawer_parts if "drawer_1" in p["name"]]
    assert len(drawer_1_parts) == 4  # bottom, side_left, side_right, back
    
    # Check drawer bottom
    drawer_bottom = next((p for p in drawer_1_parts if p["name"] == "drawer_1_bottom"), None)
    assert drawer_bottom is not None
    assert drawer_bottom["type"] == "drawer"
    assert drawer_bottom["width_mm"] > 0
    assert drawer_bottom["height_mm"] > 0

@pytest.mark.asyncio
async def test_calculate_internal_counter_all_options(create_test_unit):
    """Test calculating internal counter with all options"""
    unit_id = create_test_unit
    
    request_data = {
        "options": {
            "add_base": True,
            "add_mirror": True,
            "add_internal_shelf": True,
            "drawer_count": 1,
            "back_clearance_mm": 5,
            "expansion_gap_mm": 3
        }
    }
    
    response = client.post(f"/units/{unit_id}/internal-counter/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Should have all types of parts
    part_types = [p["type"] for p in data["parts"]]
    assert "base" in part_types
    assert "mirror" in part_types
    assert "shelf" in part_types
    assert "drawer" in part_types
    
    # Check totals
    assert data["total_edge_band_m"] > 0
    assert data["total_area_m2"] > 0

@pytest.mark.asyncio
async def test_calculate_internal_counter_default_options(create_test_unit):
    """Test calculating internal counter with default options"""
    unit_id = create_test_unit
    
    # Send request without options (should use defaults)
    request_data = {}
    
    response = client.post(f"/units/{unit_id}/internal-counter/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Default should have base only
    assert len(data["parts"]) > 0
    base_parts = [p for p in data["parts"] if p["name"] == "internal_base"]
    assert len(base_parts) == 1

@pytest.mark.asyncio
async def test_calculate_internal_counter_unit_not_found():
    """Test calculating internal counter for non-existent unit"""
    request_data = {
        "options": {
            "add_base": True
        }
    }
    
    response = client.post("/units/nonexistent_id/internal-counter/calculate", json=request_data)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_calculate_internal_counter_parts_structure(create_test_unit):
    """Test that internal counter parts have correct structure"""
    unit_id = create_test_unit
    
    request_data = {
        "options": {
            "add_base": True,
            "drawer_count": 1
        }
    }
    
    response = client.post(f"/units/{unit_id}/internal-counter/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check each part structure
    for part in data["parts"]:
        assert "name" in part
        assert "type" in part
        assert "width_mm" in part
        assert "height_mm" in part
        assert "qty" in part
        assert part["width_mm"] > 0
        assert part["height_mm"] > 0
        assert part["qty"] > 0
        
        # Check optional fields
        if "cutting_dimensions" in part and part["cutting_dimensions"]:
            assert isinstance(part["cutting_dimensions"], dict)
        if "edge_band_m" in part:
            assert part["edge_band_m"] >= 0
        if "area_m2" in part:
            assert part["area_m2"] >= 0

@pytest.mark.asyncio
async def test_calculate_internal_counter_multiple_drawers(create_test_unit):
    """Test calculating internal counter with multiple drawers"""
    unit_id = create_test_unit
    
    request_data = {
        "options": {
            "add_base": True,
            "drawer_count": 3
        }
    }
    
    response = client.post(f"/units/{unit_id}/internal-counter/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Should have 3 drawers, each with 4 parts
    drawer_parts = [p for p in data["parts"] if "drawer" in p["name"]]
    assert len(drawer_parts) == 3 * 4  # 3 drawers × 4 parts each
    
    # Check drawer numbering
    drawer_1_parts = [p for p in drawer_parts if "drawer_1" in p["name"]]
    drawer_2_parts = [p for p in drawer_parts if "drawer_2" in p["name"]]
    drawer_3_parts = [p for p in drawer_parts if "drawer_3" in p["name"]]
    
    assert len(drawer_1_parts) == 4
    assert len(drawer_2_parts) == 4
    assert len(drawer_3_parts) == 4

@pytest.mark.asyncio
async def test_calculate_internal_counter_custom_clearance(create_test_unit):
    """Test calculating internal counter with custom clearance values"""
    unit_id = create_test_unit
    
    request_data = {
        "options": {
            "add_base": True,
            "back_clearance_mm": 10,
            "expansion_gap_mm": 5
        }
    }
    
    response = client.post(f"/units/{unit_id}/internal-counter/calculate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Parts should be calculated with custom clearances
    assert len(data["parts"]) > 0
    # The dimensions should reflect the custom clearances
    base_part = next((p for p in data["parts"] if p["name"] == "internal_base"), None)
    assert base_part is not None
    # Width and depth should account for clearances
    assert base_part["width_mm"] < 800  # Less than unit width due to clearances

