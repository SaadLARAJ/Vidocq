from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.core.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="ShadowMap",
    version="4.0.0",
    description="Advanced OSINT Knowledge Graph Platform."
)

# CORS
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routes
# Include Routes
app.include_router(router)

@app.get("/")
async def root():
    return {"message": "ShadowMap API is Online", "docs": "/docs", "war_room_data": "/graph/geo"}

@app.on_event("startup")
async def startup_event():
    logger.info("application_startup")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("application_shutdown")
