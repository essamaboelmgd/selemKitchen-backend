# Kitchen Cabinet Calculator API

Backend API for calculating kitchen cabinet dimensions and costs using FastAPI and MongoDB.

## Features

- FastAPI for high-performance API
- MongoDB for data storage
- Docker support for easy deployment
- Settings management for application configuration
- Unit calculation with automatic parts generation
- Cost estimation based on material prices

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── database.py          # MongoDB connection
│   ├── models/              # Pydantic models
│   │   ├── settings.py
│   │   └── units.py
│   ├── services/            # Business logic
│   │   └── unit_calculator.py
│   └── routers/             # API routes
│       ├── settings.py
│       └── units.py
├── tests/                   # Unit tests
│   ├── test_settings.py
│   └── test_units.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Setup

### Using Docker (Recommended)

1. Build and run with Docker Compose:
```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`

### Manual Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (create `.env` file):
```
MONGODB_URL=mongodb://admin:admin123@localhost:27017/?authSource=admin
DATABASE_NAME=kitchen_db
```

3. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

### Settings

- `GET /settings` - Get current application settings
- `PUT /settings` - Update application settings

### Units

- `POST /units/calculate` - Calculate unit parts and dimensions
- `GET /units/{unit_id}` - Get saved unit details
- `POST /units/estimate` - Estimate unit cost with material prices
- `POST /units/{unit_id}/internal-counter/calculate` - Calculate internal counter parts (drawers, mirrors, shelves)
- `GET /units/{unit_id}/edge-breakdown` - Get detailed edge band distribution breakdown

### Summaries

- `POST /summaries/generate` - Generate comprehensive unit summary with all calculations
- `GET /summaries/{unit_id}` - Get saved unit summary

### Health Check

- `GET /` - API information
- `GET /health` - Health check endpoint

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Running Tests

```bash
pytest
```

## API Examples

### Calculate Unit

```bash
POST /units/calculate
{
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2,
  "options": {
    "board_thickness_mm": 16,
    "back_clearance_mm": 3
  }
}
```

### Estimate Unit Cost

```bash
POST /units/estimate
{
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2
}
```

### Calculate Internal Counter Parts

```bash
POST /units/{unit_id}/internal-counter/calculate
{
  "options": {
    "add_base": true,
    "add_mirror": true,
    "add_internal_shelf": false,
    "drawer_count": 2,
    "back_clearance_mm": 3,
    "expansion_gap_mm": 3
  }
}
```

### Get Edge Band Breakdown

```bash
GET /units/{unit_id}/edge-breakdown?edge_type=pvc
```

Returns detailed edge band distribution for all parts:
- Edge details (top, bottom, left, right)
- Length in mm and meters
- Edge type (wood/PVC)
- Total edge meters per part
- Cost breakdown

### Generate Unit Summary

```bash
POST /summaries/generate
{
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2,
  "include_internal_counter": true,
  "internal_counter_options": {
    "add_base": true,
    "add_mirror": false,
    "drawer_count": 1
  }
}
```

Returns comprehensive summary:
- List of all parts with dimensions and quantities
- Total area and edge band meters
- Material usage
- Cost breakdown
- Optional internal counter parts

## Data Schemas

### Settings Schema

The settings collection stores global application configuration:

```json
{
  "assembly_method": "bolt",
  "handle_type": "built-in",
  "handle_recess_height_mm": 30,
  "default_board_thickness_mm": 16,
  "edge_overlap_mm": 2,
  "materials": {
    "plywood_sheet": {
      "price_per_sheet": 2500,
      "sheet_size_m2": 2.4
    },
    "edge_band_per_meter": {
      "price_per_meter": 10
    }
  },
  "last_updated": "2025-01-21T..."
}
```

### Unit Schema

The units collection stores calculated unit data:

```json
{
  "_id": "unit_ABC123",
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2,
  "parts_calculated": [
    {
      "name": "side_panel",
      "width_mm": 300,
      "height_mm": 720,
      "qty": 2,
      "edge_band_m": 2.04,
      "area_m2": 0.432
    }
  ],
  "edge_band_m": 5.6,
  "total_area_m2": 1.2,
  "material_usage": {
    "plywood_sheets": 0.5,
    "edge_m": 5.6
  },
  "price_estimate": 3400,
  "created_at": "2025-01-21T..."
}
```

### Summary Schema

The unit_summaries collection stores comprehensive unit summaries:

```json
{
  "_id": "summary_ABC123",
  "unit_id": "unit_ABC123",
  "type": "ground",
  "width_mm": 800,
  "height_mm": 720,
  "depth_mm": 300,
  "shelf_count": 2,
  "items": [
    {
      "part_name": "side_panel",
      "description": "side_panel - 300mm × 720mm",
      "width_mm": 300,
      "height_mm": 720,
      "qty": 2,
      "area_m2": 0.432,
      "edge_band_m": 2.04
    }
  ],
  "totals": {
    "total_area_m2": 1.2,
    "total_edge_band_m": 5.6,
    "total_parts": 6,
    "total_qty": 8
  },
  "material_usage": {
    "plywood_sheets": 0.5,
    "edge_m": 5.6,
    "total_area_m2": 1.2
  },
  "costs": {
    "material_cost": 1250,
    "edge_band_cost": 56,
    "total_cost": 1306
  },
  "generated_at": "2025-01-21T..."
}
```

