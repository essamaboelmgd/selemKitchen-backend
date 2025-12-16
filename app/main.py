from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import connect_to_mongo, close_mongo_connection
from app.routers import settings, units, summaries, projects, auth, dashboard, marketplace, cart, ads
import os

app = FastAPI(
    title="Kitchen Cabinet Calculator API",
    description="API for calculating kitchen cabinet dimensions and costs",
    version="1.0.0"
)

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

# Mount uploads directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(settings.router, prefix="/settings", tags=["Settings"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(units.router, prefix="/units", tags=["Units"])
app.include_router(marketplace.router, prefix="/marketplace", tags=["Marketplace"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(cart.router, prefix="/cart", tags=["Cart"])
app.include_router(ads.router, prefix="/ads", tags=["Ads"])

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

@app.get("/")
async def root():
    return {"message": "Kitchen Cabinet Calculator API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}