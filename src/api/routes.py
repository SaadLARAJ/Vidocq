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
import hashlib
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

logger = get_logger(__name__)
router = APIRouter()

# --- GEO MAPPING CONFIGURATION ---
# 1. Static Cache (Fastest)
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
    "AUSTRALIA": {"lat": -25.2744, "lng": 133.7751},
    "HYDERABAD": {"lat": 17.3850, "lng": 78.4867},
    "PARIS": {"lat": 48.8566, "lng": 2.3522},
    "SHENZHEN": {"lat": 22.5431, "lng": 114.0579},
    "BANGALORE": {"lat": 12.9716, "lng": 77.5946},
    "TOKYO": {"lat": 35.6762, "lng": 139.6503},
    "BEIJING": {"lat": 39.9042, "lng": 116.4074},
    "MOSCOW": {"lat": 55.7558, "lng": 37.6173},
    "LONDON": {"lat": 51.5074, "lng": -0.1278},
    "NEW YORK": {"lat": 40.7128, "lng": -74.0060},
    "CALIFORNIA": {"lat": 36.7783, "lng": -119.4179},
    "SAFRAN": {"lat": 48.8566, "lng": 2.3522}, # Default HQ
}

DEFAULT_COORDS = {"lat": 37.0902, "lng": -95.7129} # USA

# Initialize Geocoder
geolocator = Nominatim(user_agent="shadowmap_agent")

def get_coordinates(location_name: str) -> Dict[str, float]:
    """
    Resolve coordinates with 3-tier strategy:
    1. Static Cache (Instant)
    2. Geopy/OSM (Online)
    3. Deterministic Fallback (Offline/Fail-safe)
    """
    clean_name = location_name.upper().strip()
    
    # Tier 1: Static Cache
    if clean_name in GEO_MAPPING:
        return GEO_MAPPING[clean_name]
    
    # Tier 2: Online Geocoding
    try:
        location = geolocator.geocode(clean_name, timeout=2)
        if location:
            coords = {"lat": location.latitude, "lng": location.longitude}
            # Update cache for this session
            GEO_MAPPING[clean_name] = coords
            return coords
    except Exception as e:
        logger.warning("geocoding_failed", location=clean_name, error=str(e))

    # Tier 3: Deterministic Fallback (Hash-based)
    # Ensures the same entity always appears at the same "random" spot
    # Use a hash of the name to generate a consistent lat/lng
    hash_val = int(hashlib.md5(clean_name.encode()).hexdigest(), 16)
    
    # Generate lat between -60 and 70 (avoid poles)
    lat = (hash_val % 13000) / 100.0 - 60.0
    # Generate lng between -180 and 180
    lng = ((hash_val // 13000) % 36000) / 100.0 - 180.0
    
    return {"lat": lat, "lng": lng}

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
    MATCH (supplier)-[r2:LOCATED_IN|OPERATES_IN|MANUFACTURES_IN]->(country:Entity)
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
                location = record["location"] if record["location"] else "UNKNOWN"
                relation = record["relation"]
                
                # Resolve Coordinates
                supplier_coords = get_coordinates(location)
                
                # Try to find buyer location (default to Paris/Safran if unknown)
                # Ideally we would query the buyer's location too, but for now:
                if "SAFRAN" in buyer.upper():
                    buyer_coords = GEO_MAPPING["SAFRAN"]
                else:
                    buyer_coords = get_coordinates(buyer) # Try to geocode the buyer name itself
                
                # Determine Risk
                risk = "HIGH" if "DEPENDS" in relation or "OPPOSES" in relation else "MEDIUM"
                
                flows.append({
                    "buyer": buyer,
                    "supplier": supplier,
                    "from": supplier_coords,
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
