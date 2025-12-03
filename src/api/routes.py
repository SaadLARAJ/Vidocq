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

logger = get_logger(__name__)
router = APIRouter()

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
