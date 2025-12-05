import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_generate_summary_basic():
    """Test generating a basic summary"""
    request_data = {
        "type": "ground",
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2,
        "include_internal_counter": False
    }
    
    response = client.post("/summaries/generate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "summary_id" in data
    assert "unit_id" in data
    assert data["type"] == "ground"
    assert "unit_dimensions" in data
    assert data["unit_dimensions"]["width_mm"] == 800
    assert data["unit_dimensions"]["height_mm"] == 720
    assert data["unit_dimensions"]["depth_mm"] == 300
    assert data["shelf_count"] == 2
    
    # Check items
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0
    
    # Check totals
    assert "totals" in data
    assert "total_area_m2" in data["totals"]
    assert "total_edge_band_m" in data["totals"]
    assert "total_parts" in data["totals"]
    assert "total_qty" in data["totals"]
    
    # Check material usage
    assert "material_usage" in data
    assert "costs" in data
    assert "generated_at" in data

@pytest.mark.asyncio
async def test_generate_summary_with_internal_counter():
    """Test generating summary with internal counter"""
    request_data = {
        "type": "ground",
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2,
        "include_internal_counter": True,
        "internal_counter_options": {
            "add_base": True,
            "add_mirror": False,
            "add_internal_shelf": True,
            "drawer_count": 1
        }
    }
    
    response = client.post("/summaries/generate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Should have more items with internal counter
    assert len(data["items"]) > 5  # More than basic parts
    
    # Check for internal parts
    part_names = [item["part_name"] for item in data["items"]]
    assert any("internal" in name for name in part_names) or any("drawer" in name for name in part_names)

@pytest.mark.asyncio
async def test_generate_summary_with_costs():
    """Test generating summary with cost calculation"""
    # Set material prices
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
    
    request_data = {
        "type": "ground",
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2
    }
    
    response = client.post("/summaries/generate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check costs
    assert "costs" in data
    if data["costs"].get("material_cost"):
        assert data["costs"]["material_cost"] >= 0
    if data["costs"].get("edge_band_cost"):
        assert data["costs"]["edge_band_cost"] >= 0
    if data["costs"].get("total_cost"):
        assert data["costs"]["total_cost"] >= 0

@pytest.mark.asyncio
async def test_generate_summary_different_unit_types():
    """Test generating summaries for different unit types"""
    unit_types = ["ground", "wall", "double_door"]
    
    for unit_type in unit_types:
        request_data = {
            "type": unit_type,
            "width_mm": 600,
            "height_mm": 500,
            "depth_mm": 250,
            "shelf_count": 1
        }
        
        response = client.post("/summaries/generate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        
        assert data["type"] == unit_type
        assert len(data["items"]) > 0

@pytest.mark.asyncio
async def test_get_summary_by_unit_id():
    """Test getting summary by unit ID"""
    # First generate a summary
    request_data = {
        "type": "ground",
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2
    }
    
    generate_response = client.post("/summaries/generate", json=request_data)
    assert generate_response.status_code == 200
    unit_id = generate_response.json()["unit_id"]
    
    # Get the summary
    get_response = client.get(f"/summaries/{unit_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    
    assert data["unit_id"] == unit_id
    assert data["type"] == "ground"
    assert len(data["items"]) > 0
    assert "totals" in data
    assert "costs" in data

@pytest.mark.asyncio
async def test_get_summary_not_found():
    """Test getting summary for non-existent unit"""
    response = client.get("/summaries/nonexistent_unit_id")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_summary_items_structure():
    """Test that summary items have correct structure"""
    request_data = {
        "type": "ground",
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2
    }
    
    response = client.post("/summaries/generate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check each item structure
    for item in data["items"]:
        assert "part_name" in item
        assert "width_mm" in item
        assert "height_mm" in item
        assert "qty" in item
        assert item["width_mm"] > 0
        assert item["height_mm"] > 0
        assert item["qty"] > 0
        
        # Optional fields
        if "area_m2" in item and item["area_m2"]:
            assert item["area_m2"] >= 0
        if "edge_band_m" in item and item["edge_band_m"]:
            assert item["edge_band_m"] >= 0

@pytest.mark.asyncio
async def test_summary_totals_calculation():
    """Test that summary totals are calculated correctly"""
    request_data = {
        "type": "ground",
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2
    }
    
    response = client.post("/summaries/generate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check totals
    totals = data["totals"]
    assert totals["total_parts"] == len(data["items"])
    assert totals["total_qty"] == sum(item["qty"] for item in data["items"])
    assert totals["total_area_m2"] > 0
    assert totals["total_edge_band_m"] > 0

@pytest.mark.asyncio
async def test_summary_with_options():
    """Test generating summary with custom options"""
    request_data = {
        "type": "ground",
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2,
        "options": {
            "board_thickness_mm": 18,
            "back_clearance_mm": 5
        }
    }
    
    response = client.post("/summaries/generate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Should have calculated with custom options
    assert len(data["items"]) > 0
    assert data["totals"]["total_area_m2"] > 0

@pytest.mark.asyncio
async def test_summary_material_usage():
    """Test that material usage is calculated correctly"""
    request_data = {
        "type": "ground",
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2
    }
    
    response = client.post("/summaries/generate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    # Check material usage
    material_usage = data["material_usage"]
    assert "ألواح الخشب" in material_usage
    assert "شريط الحافة" in material_usage
    assert "المساحة الإجمالية" in material_usage
    
    assert material_usage["ألواح الخشب"] >= 0
    assert material_usage["شريط الحافة"] >= 0
    assert material_usage["المساحة الإجمالية"] > 0

@pytest.mark.asyncio
async def test_summary_invalid_dimensions():
    """Test generating summary with invalid dimensions"""
    request_data = {
        "type": "ground",
        "width_mm": -100,  # Invalid
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2
    }
    
    response = client.post("/summaries/generate", json=request_data)
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_summary_generated_at_timestamp():
    """Test that generated_at timestamp is included"""
    request_data = {
        "type": "ground",
        "width_mm": 800,
        "height_mm": 720,
        "depth_mm": 300,
        "shelf_count": 2
    }
    
    response = client.post("/summaries/generate", json=request_data)
    assert response.status_code == 200
    data = response.json()
    
    assert "generated_at" in data
    assert data["generated_at"] is not None

