from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any
from src.api.dependencies import get_graph_store, get_vector_store, get_extractor, get_resolver
from src.storage.graph import GraphStore
from src.storage.vector import VectorStore
from src.pipeline.extractor import Extractor
from src.pipeline.resolver import EntityResolver
from src.ingestion.tasks import ingest_url
from src.core.logging import get_logger
import random

logger = get_logger(__name__)
router = APIRouter()

# --- GEO MAPPING CONFIGURATION ---
GEO_MAPPING = {
    "CHINA": {"lat": 35.8617, "lng": 104.1954},
    "INDIA": {"lat": 20.5937, "lng": 78.9629},
    "USA": {"lat": 37.0902, "lng": -95.7129},
    "TAIWAN": {"lat": 23.6978, "lng": 120.9605},
    "VIETNAM": {"lat": 14.0583, "lng": 108.2772},
    "FRANCE": {"lat": 46.2276, "lng": 2.2137},
    "GERMANY": {"lat": 51.1657, "lng": 10.4515},
    "JAPAN": {"lat": 36.2048, "lng": 138.2529},
    "SOUTH KOREA": {"lat": 35.9078, "lng": 127.7669},
    "UK": {"lat": 55.3781, "lng": -3.4360},
    "BRAZIL": {"lat": -14.2350, "lng": -51.9253},
    "CANADA": {"lat": 56.1304, "lng": -106.3468},
    "MEXICO": {"lat": 23.6345, "lng": -102.5528},
    "RUSSIA": {"lat": 61.5240, "lng": 105.3188},
    "AUSTRALIA": {"lat": -25.2744, "lng": 133.7751}
}

DEFAULT_COORDS = {"lat": 37.0902, "lng": -95.7129} # USA

class IngestRequest(BaseModel):
    url: HttpUrl
    source_domain: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

@router.post("/ingest")
async def ingest_endpoint(request: IngestRequest):
    """
    Trigger ingestion for a URL.
    """
    logger.info("ingest_request_received", url=str(request.url))
    
    # Trigger Celery task
    task = ingest_url.delay(str(request.url), request.source_domain)
    
    return {"task_id": task.id, "status": "processing"}

@router.post("/search")
async def search_endpoint(
    request: SearchRequest,
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Semantic search for entities.
    """
    # TODO: Generate embedding for query using OpenAI/Cohere
    # vector = embed(request.query)
    query_vector = [0.1] * 1536 
    
    results = vector_store.search_similar(query_vector, limit=request.limit)
    return {"results": results}

@router.get("/status")
async def status_endpoint():
    return {"status": "ok", "version": "4.0.0"}

@router.get("/graph/geo")
async def get_geo_graph(graph_store: GraphStore = Depends(get_graph_store)):
    """
    Fetch geospatial supply chain flows from Neo4j.
    """
    query = """
    MATCH (buyer:ORGANIZATION)-[r1]->(supplier:ORGANIZATION)
    MATCH (supplier)-[r2:LOCATED_IN|OPERATES_IN]->(country:COUNTRY)
    RETURN buyer.name as buyer, supplier.name as supplier, country.name as location, type(r1) as relation
    LIMIT 100
    """
    
    try:
        flows = []
        with graph_store.driver.session() as session:
            result = session.run(query)
            
            for record in result:
                buyer = record["buyer"]
                supplier = record["supplier"]
                location = record["location"].upper() if record["location"] else "UNKNOWN"
                relation = record["relation"]
                
                # Resolve Coordinates
                # Supplier Location (from query)
                supplier_coords = GEO_MAPPING.get(location, DEFAULT_COORDS)
                
                # Buyer Location (Default to USA as per requirements since not in query)
                buyer_coords = DEFAULT_COORDS
                
                # Determine Risk
                # Simple logic: DEPENDS_ON = HIGH, others = MEDIUM/LOW
                risk = "HIGH" if "DEPENDS" in relation else "MEDIUM"
                
                flows.append({
                    "buyer": buyer,
                    "supplier": supplier,
                    "from": supplier_coords, # Supplier -> Buyer flow
                    "to": buyer_coords,
                    "risk": risk
                })
        
        return {
            "count": len(flows),
            "flows": flows
        }

    except Exception as e:
        logger.error("geo_graph_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
