from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect_to_mongo, close_mongo_connection
from app.routers import settings, units, summaries

app = FastAPI(
    title="Kitchen Cabinet Calculator API",
    description="API for calculating kitchen cabinet dimensions and costs",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(settings.router, prefix="/settings", tags=["Settings"])
app.include_router(units.router, prefix="/units", tags=["Units"])
app.include_router(summaries.router, prefix="/summaries", tags=["Summaries"])

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

