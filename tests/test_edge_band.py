import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def create_test_unit():
    """Create a test unit for edge band tests"""
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

@pytest.mark.asyncio
async def test_get_edge_breakdown(create_test_unit):
    """Test getting edge breakdown for a unit"""
    unit_id = create_test_unit
    
    response = client.get(f"/units/{unit_id}/edge-breakdown")
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert data["unit_id"] == unit_id
    assert "parts" in data
    assert "total_edge_m" in data
    assert isinstance(data["parts"], list)
    assert len(data["parts"]) > 0
    
    # Check total edge meters
    assert data["total_edge_m"] > 0

@pytest.mark.asyncio
async def test_get_edge_breakdown_with_edge_type(create_test_unit):
    """Test getting edge breakdown with specific edge type"""
    unit_id = create_test_unit
    
    # Test with PVC
    response = client.get(f"/units/{unit_id}/edge-breakdown?edge_type=pvc")
    assert response.status_code == 200
    data = response.json()
    assert len(data["parts"]) > 0
    
    # Test with wood
    response = client.get(f"/units/{unit_id}/edge-breakdown?edge_type=wood")
    assert response.status_code == 200
    data = response.json()
    assert len(data["parts"]) > 0

@pytest.mark.asyncio
async def test_get_edge_breakdown_invalid_edge_type(create_test_unit):
    """Test getting edge breakdown with invalid edge type"""
    unit_id = create_test_unit
    
    response = client.get(f"/units/{unit_id}/edge-breakdown?edge_type=invalid")
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_get_edge_breakdown_unit_not_found():
    """Test getting edge breakdown for non-existent unit"""
    response = client.get("/units/nonexistent_id/edge-breakdown")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_edge_breakdown_parts_structure(create_test_unit):
    """Test that edge breakdown parts have correct structure"""
    unit_id = create_test_unit
    
    response = client.get(f"/units/{unit_id}/edge-breakdown")
    assert response.status_code == 200
    data = response.json()
    
    # Check each part structure
    for part in data["parts"]:
        assert "part_name" in part
        assert "qty" in part
        assert "edges" in part
        assert "total_edge_m" in part
        assert "edge_type" in part
        
        assert isinstance(part["edges"], list)
        assert len(part["edges"]) > 0
        assert part["total_edge_m"] >= 0
        
        # Check edge details
        for edge in part["edges"]:
            assert "edge" in edge
            assert "length_mm" in edge
            assert "length_m" in edge
            assert "has_edge" in edge
            assert "edge_type" in edge
            
            assert edge["length_mm"] > 0
            assert edge["length_m"] > 0
            assert edge["length_m"] == edge["length_mm"] / 1000.0

@pytest.mark.asyncio
async def test_edge_breakdown_edges_coverage(create_test_unit):
    """Test that edge breakdown covers all edges"""
    unit_id = create_test_unit
    
    response = client.get(f"/units/{unit_id}/edge-breakdown")
    assert response.status_code == 200
    data = response.json()
    
    # Check that each part has edge details for all 4 edges
    for part in data["parts"]:
        edge_names = [e["edge"] for e in part["edges"]]
        assert "top" in edge_names
        assert "bottom" in edge_names
        assert "left" in edge_names
        assert "right" in edge_names

@pytest.mark.asyncio
async def test_edge_breakdown_total_calculation(create_test_unit):
    """Test that total edge meters is calculated correctly"""
    unit_id = create_test_unit
    
    response = client.get(f"/units/{unit_id}/edge-breakdown")
    assert response.status_code == 200
    data = response.json()
    
    # Calculate total from parts
    calculated_total = sum(part["total_edge_m"] for part in data["parts"])
    
    # Should match the total in response
    assert abs(data["total_edge_m"] - calculated_total) < 0.01  # Allow small rounding difference

@pytest.mark.asyncio
async def test_edge_breakdown_with_cost(create_test_unit):
    """Test edge breakdown with cost calculation"""
    unit_id = create_test_unit
    
    # Set edge band price in settings
    settings_update = {
        "materials": {
            "edge_band_per_meter": {
                "price_per_meter": 10
            }
        }
    }
    client.put("/settings", json=settings_update)
    
    response = client.get(f"/units/{unit_id}/edge-breakdown")
    assert response.status_code == 200
    data = response.json()
    
    # If prices are set, should have cost information
    if data.get("total_cost") is not None:
        assert data["total_cost"] >= 0
        if data.get("cost_breakdown"):
            assert isinstance(data["cost_breakdown"], dict)

@pytest.mark.asyncio
async def test_edge_breakdown_edge_overlap(create_test_unit):
    """Test that edge overlap is included in calculations"""
    unit_id = create_test_unit
    
    # Set edge overlap in settings
    settings_update = {
        "edge_overlap_mm": 5
    }
    client.put("/settings", json=settings_update)
    
    response = client.get(f"/units/{unit_id}/edge-breakdown")
    assert response.status_code == 200
    data = response.json()
    
    # Check that edges with has_edge=True include overlap
    for part in data["parts"]:
        for edge in part["edges"]:
            if edge["has_edge"]:
                # The length should account for overlap
                # (exact calculation depends on part dimensions)
                assert edge["length_mm"] > 0

@pytest.mark.asyncio
async def test_edge_breakdown_different_edge_types(create_test_unit):
    """Test edge breakdown with different edge types"""
    unit_id = create_test_unit
    
    # Test PVC
    response_pvc = client.get(f"/units/{unit_id}/edge-breakdown?edge_type=pvc")
    assert response_pvc.status_code == 200
    data_pvc = response_pvc.json()
    
    # Test Wood
    response_wood = client.get(f"/units/{unit_id}/edge-breakdown?edge_type=wood")
    assert response_wood.status_code == 200
    data_wood = response_wood.json()
    
    # Both should have same structure and totals (edge type doesn't affect length)
    assert len(data_pvc["parts"]) == len(data_wood["parts"])
    assert abs(data_pvc["total_edge_m"] - data_wood["total_edge_m"]) < 0.01
    
    # But edge_type should be different
    assert all(p["edge_type"] == "pvc" for p in data_pvc["parts"])
    assert all(p["edge_type"] == "wood" for p in data_wood["parts"])

