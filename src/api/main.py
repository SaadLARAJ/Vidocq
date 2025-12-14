from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.api.routes import router
from src.core.logging import get_logger
import os

logger = get_logger(__name__)

app = FastAPI(
    title="Vidocq - ShadowMap Intelligence",
    version="6.0.0",
    description="Autonomous OSINT Investigation Agent - Powered by AI"
)

# CORS - Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routes
app.include_router(router)

# Serve Frontend (Vidocq UI)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/ui", StaticFiles(directory=frontend_path, html=True), name="frontend")

@app.get("/")
async def root():
    return {
        "name": "Vidocq",
        "version": "6.0.0",
        "description": "Autonomous OSINT Investigation Agent",
        "ui": {
            "dashboard": "/ui/dashboard.html",
            "graph": "/ui/graph.html",
            "legacy": "/ui/index.html"
        },
        "docs": "/docs",
        "endpoints": {
            "investigate": "/investigate/{entity}",
            "analyze": "/graph/analyze",
            "discover": "/discover/v2",
            "risk": "/risk/score",
            "watchlist": "/watchlist"
        }
    }

@app.on_event("startup")
async def startup_event():
    logger.info("vidocq_startup", version="6.0.0")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("vidocq_shutdown")

