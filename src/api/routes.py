from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Path, Query
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional
from src.api.dependencies import get_graph_store, get_vector_store, get_extractor, get_resolver
from src.storage.graph import GraphStore
from src.storage.vector import VectorStore
from src.pipeline.extractor import Extractor
from src.pipeline.resolver import EntityResolver
from src.ingestion.tasks import ingest_url, launch_discovery_task
from src.core.logging import get_logger
import random
import hashlib
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import threading
from src.core.embedding import embed_text

logger = get_logger(__name__)
router = APIRouter()

# --- GEO MAPPING CONFIGURATION ---
# 1. Static Cache (Fastest)
geo_lock = threading.Lock()
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
            with geo_lock:
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
    # Generate embedding for query
    query_vector = embed_text(request.query) 
    
    results = vector_store.search_similar(query_vector, limit=request.limit)
    return {"results": results}

@router.get("/status")
async def status_endpoint():
    return {"status": "ok", "version": "5.0.0-investigator"}


@router.get("/sources")
async def get_data_sources():
    """
    List all available data sources and their status.
    Demonstrates production-ready architecture to investors.
    """
    from src.core.sources import data_sources
    from src.ingestion.connectors import MultiSourceSearch
    
    # Get enabled sources
    multi_search = MultiSourceSearch()
    enabled = multi_search.get_enabled_sources()
    
    return {
        "mode": "PRODUCTION" if data_sources.ENABLE_PREMIUM_SOURCES else "DEMO",
        "demo_source": "DuckDuckGo" if not data_sources.ENABLE_PREMIUM_SOURCES else None,
        "premium_sources": {
            "search_engines": {
                "SerpApi": {"enabled": data_sources.USE_SERPAPI, "cost": "$50/month"},
                "BrightData": {"enabled": data_sources.USE_BRIGHTDATA, "cost": "$500+/month"}
            },
            "corporate_registries": {
                "OpenCorporates": {"enabled": data_sources.USE_OPENCORPORATES, "cost": "$500/month"},
                "GLEIF": {"enabled": data_sources.USE_GLEIF, "cost": "FREE"},
                "CompaniesHouse": {"enabled": data_sources.USE_COMPANIES_HOUSE, "cost": "FREE"}
            },
            "investigation_databases": {
                "OCCRP_Aleph": {"enabled": data_sources.USE_OCCRP_ALEPH, "cost": "FREE"},
                "OpenSanctions": {"enabled": data_sources.USE_OPENSANCTIONS, "cost": "FREE"}
            },
            "knowledge_graphs": {
                "Wikidata": {"enabled": data_sources.USE_WIKIDATA, "cost": "FREE"}
            }
        },
        "enabled_sources": enabled,
        "upgrade_instructions": "Set ENABLE_PREMIUM_SOURCES=true in .env and add API keys"
    }


# === BRAIN ENDPOINTS (Cognitive Intelligence) ===

@router.get("/brain/analyze/{target}")
async def brain_analyze(
    target: str = Path(..., description="Target to analyze (person, company, or state)")
):
    """
    Run the Vidocq Brain analysis on a target.
    
    This will:
    1. CLASSIFY the target (Person / Company / State)
    2. CONSULT memory (What do we already know?)
    3. GENERATE investigation plan
    4. PREDICT dangers based on patterns
    
    Does NOT launch scrapers - just analyzes existing knowledge + plans.
    """
    from src.brain import VidocqBrain
    
    try:
        brain = VidocqBrain()
        result = await brain.analyze(target)
        return result
        
    except Exception as e:
        logger.error("brain_analysis_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/report/{target}")
async def brain_report(
    target: str = Path(..., description="Target for geo-sourced report")
):
    """
    Generate a geo-sourced intelligence report.
    
    The report structures information by SOURCE ORIGIN:
    - What WESTERN sources say (US, EU)
    - What HOSTILE sources say (RU, CN)
    - Where narratives DIVERGE (information warfare)
    
    Requires existing data in the graph.
    """
    from src.brain import GeoSourcedReporter
    
    try:
        reporter = GeoSourcedReporter()
        report = await reporter.generate_report(target)
        markdown = reporter.export_to_markdown(report)
        
        return {
            "status": "success",
            "target": target,
            "target_type": report.target_type,
            "confidence": report.confidence_score,
            "source_breakdown": report.source_breakdown,
            "alerts_count": len(report.alerts),
            "report_markdown": markdown,
            "report_data": report.model_dump()
        }
        
    except Exception as e:
        logger.error("brain_report_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/classify/{target}")
async def brain_classify(
    target: str = Path(..., description="Target to classify")
):
    """
    Quick classification of a target.
    Returns: COMPANY, PERSON, or STATE with confidence score.
    """
    from src.brain import VidocqBrain
    
    try:
        brain = VidocqBrain()
        profile = await brain.classify_target(target)
        
        return {
            "target": target,
            "type": profile.target_type.value,
            "confidence": profile.confidence,
            "indicators": profile.detected_indicators,
            "country": profile.probable_country,
            "sector": profile.probable_sector,
            "investigation_strategy": profile.search_strategy[:5],
            "priority_sources": profile.priority_sources[:5]
        }
        
    except Exception as e:
        logger.error("brain_classify_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/ghost-scan/{target}")
async def brain_ghost_scan(
    target: str = Path(..., description="Target to scan for suspicious absences")
):
    """
    🔍 NEGATIVE SPACE ANALYSIS (Ghost Detector)
    
    Detects what's MISSING - the most suspicious signal.
    
    Checks for:
    - No LinkedIn profile
    - No pre-2020 digital traces (synthetic identity risk)
    - Claimed expertise without publications
    - No identifiable photos
    - Suspiciously clean profile
    
    Returns a "void score" and list of anomalies.
    """
    from src.brain import NegativeSpaceAnalyzer, VidocqBrain
    
    try:
        # First classify the target
        brain = VidocqBrain()
        profile = await brain.classify_target(target)
        
        # Run negative space analysis
        analyzer = NegativeSpaceAnalyzer()
        report = await analyzer.analyze(
            target=target,
            target_type=profile.target_type.value,
            existing_data=profile.memory_context
        )
        
        return {
            "status": "success",
            "target": target,
            "target_type": profile.target_type.value,
            "suspicion_level": report.overall_suspicion.value,
            "void_score": report.void_score,
            "profile_completeness": report.profile_completeness,
            "historical_depth_years": report.historical_depth,
            "anomalies": [
                {
                    "type": a.anomaly_type,
                    "severity": a.severity.value,
                    "description": a.description,
                    "expected": a.expected,
                    "found": a.found,
                    "hint": a.investigation_hint
                }
                for a in report.anomalies
            ],
            "summary": report.summary,
            "recommendation": report.recommendation
        }
        
    except Exception as e:
        logger.error("ghost_scan_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain/wargame/{trigger}")
async def brain_wargame(
    trigger: str = Path(..., description="Entity to simulate failure (e.g., 'Taiwan', 'TSMC')"),
    scenario: str = Query(
        default="EMBARGO",
        description="Scenario type: EMBARGO, SUPPLIER_FAILURE, CONFLICT, SANCTION, CYBER_ATTACK"
    )
):
    """
    💥 SUPPLY CHAIN WARGAMING (Digital Twin of Chaos)
    
    Simulates catastrophic scenarios: "What happens if X fails?"
    
    Examples:
    - /brain/wargame/Taiwan?scenario=EMBARGO → Shows TSMC dependencies
    - /brain/wargame/Gazprom?scenario=SANCTION → Shows energy cascade
    
    Returns affected entities, cascade depth, and mitigation options.
    """
    from src.brain import SupplyChainWargamer, ScenarioType
    
    try:
        # Parse scenario type
        try:
            scenario_type = ScenarioType(scenario.upper())
        except ValueError:
            scenario_type = ScenarioType.EMBARGO
        
        wargamer = SupplyChainWargamer()
        result = await wargamer.simulate(
            trigger_entity=trigger,
            scenario_type=scenario_type
        )
        
        return {
            "status": "success",
            "scenario_id": result.scenario_id,
            "trigger": trigger,
            "scenario_type": result.scenario_type.value,
            "simulation_date": result.simulation_date.isoformat(),
            "impact_summary": {
                "total_affected": result.total_affected,
                "cascade_depth": result.cascade_depth,
                "estimated_recovery_days": result.estimated_recovery_days,
                "critical_nodes": result.critical_nodes
            },
            "affected_entities": [
                {
                    "name": e.entity_name,
                    "type": e.entity_type,
                    "impact_level": e.impact_level.value,
                    "delay_days": e.impact_delay_days,
                    "dependency_chain": e.dependency_chain,
                    "mitigations": e.mitigation_options
                }
                for e in result.affected_entities[:20]  # Top 20
            ],
            "recommendations": result.recommended_actions,
            "summary": result.summary
        }
        
    except Exception as e:
        logger.error("wargame_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brain/contradiction-check")
async def brain_contradiction_check(
    target: str = Query(..., description="Target being investigated"),
    claims: List[Dict[str, Any]] = None
):
    """
    ⚔️ CONTRADICTION DETECTOR (Narrative Warfare)
    
    Detects when Western and Eastern sources disagree.
    Shows the CONFLICT explicitly instead of averaging.
    
    "Reuters says WHITE, RT says BLACK" → "NARRATIVE WAR DETECTED"
    
    Request body should include claims with source_url and the claim text.
    """
    from src.brain import ContradictionDetector
    
    try:
        if not claims:
            claims = []
        
        source_urls = [c.get("source_url", "") for c in claims if c.get("source_url")]
        
        detector = ContradictionDetector()
        report = await detector.analyze(
            target=target,
            claims=claims,
            source_urls=source_urls
        )
        
        return {
            "status": "success",
            "target": target,
            "narrative_wars_detected": report.narrative_wars_detected,
            "overall_alignment": report.overall_narrative_alignment,
            "dominant_narrative": report.dominant_narrative,
            "conflicts": [
                {
                    "topic": c.topic,
                    "western_stance": c.western_stance.value,
                    "western_claim": c.western_claim,
                    "hostile_stance": c.hostile_stance.value,
                    "hostile_claim": c.hostile_claim,
                    "severity": c.conflict_severity,
                    "likely_truth": c.likely_truth,
                    "analysis": c.analysis
                }
                for c in report.conflicts
            ],
            "propaganda_indicators": report.propaganda_indicators,
            "recommendation": report.recommendation
        }
        
    except Exception as e:
        logger.error("contradiction_check_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === INVESTIGATION ENDPOINTS ===

@router.get("/investigate/{entity_name}")
async def investigate_entity(
    entity_name: str = Path(..., description="Name of entity to investigate"),
    depth: int = Query(default=2, ge=1, le=5, description="Investigation depth (1-5)")
):
    """
    Launch an autonomous investigation on any entity.
    The agent will:
    1. Profile the target (Corporation, Bank, Media, Government, etc.)
    2. Generate targeted search queries
    3. Scrape and extract information
    4. Build the knowledge graph
    
    Returns immediately with task_id. Use /graph/analyze to see results.
    """
    logger.info("investigation_launched", entity=entity_name, depth=depth)
    
    # Launch discovery task in background
    task = launch_discovery_task.delay(entity_name, depth=0)
    
    return {
        "status": "investigation_started",
        "target": entity_name,
        "max_depth": depth,
        "task_id": task.id,
        "next_steps": [
            "Wait 1-2 minutes for the agent to complete",
            "Check progress: GET /graph/stats",
            "View report: GET /graph/analyze"
        ]
    }


@router.get("/investigate/{entity_name}/preview")
async def preview_investigation(
    entity_name: str = Path(..., description="Name of entity to investigate")
):
    """
    Preview what the investigation agent would search for, without executing.
    Useful for understanding the agent's strategy.
    """
    from src.pipeline.discovery import DiscoveryEngine
    
    try:
        engine = DiscoveryEngine()
        queries = engine.generate_multilingual_queries(entity_name)
        
        return {
            "target": entity_name,
            "generated_queries": queries,
            "note": "Use GET /investigate/{entity} to actually run these searches"
        }
    except Exception as e:
        logger.error("preview_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/{entity_name}")
async def verify_entity(
    entity_name: str = Path(..., description="Entity name to verify"),
    entity_type: str = Query(default="ORGANIZATION", description="Entity type")
):
    """
    Verify an entity against trusted sources (Agent Critique).
    Checks Wikidata, OpenSanctions, and provides confidence assessment.
    """
    from src.pipeline.verification import VerificationAgent
    
    try:
        agent = VerificationAgent()
        result = agent.verify_entity(entity_name, entity_type)
        
        return {
            "entity": entity_name,
            "type": entity_type,
            "status": result.status.value,
            "confidence_adjustment": result.confidence_adjustment,
            "sources_checked": result.sources_checked,
            "matches_found": result.matches_found,
            "risk_flags": result.risk_flags,
            "notes": result.verification_notes
        }
    except Exception as e:
        logger.error("verification_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

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


@router.get("/graph/entities")
async def get_entities_with_relations(
    graph_store: GraphStore = Depends(get_graph_store),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type"),
    search: Optional[str] = Query(default=None, description="Search by name"),
    limit: int = Query(default=50, le=200)
):
    """
    Get entities with their relations, filtered by confidence level.
    Used by dashboard for real-time Neo4j queries.
    """
    # Build dynamic query based on filters
    where_clauses = []
    params = {"limit": limit, "min_confidence": min_confidence}
    
    if search:
        where_clauses.append("toLower(e.canonical_name) CONTAINS toLower($search)")
        params["search"] = search
    
    if entity_type:
        where_clauses.append("$entity_type IN labels(e)")
        params["entity_type"] = entity_type
    
    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    query = f"""
    MATCH (e:Entity)
    {where_clause}
    WITH e LIMIT $limit
    OPTIONAL MATCH (e)-[r]->(target:Entity)
    WHERE r.confidence_score IS NULL OR r.confidence_score >= $min_confidence
    RETURN 
        e.id as id,
        e.canonical_name as name,
        labels(e)[1] as type,
        e.country as country,
        e.confidence_score as confidence,
        collect(DISTINCT {{
            type: type(r),
            target: target.canonical_name,
            target_type: labels(target)[1],
            confidence: r.confidence_score,
            source_url: r.source_url
        }}) as relations
    """
    
    try:
        entities = []
        with graph_store.driver.session() as session:
            result = session.run(query, **params)
            
            for record in result:
                # Filter out null relations
                relations = [r for r in record["relations"] if r["target"] is not None]
                
                # Filter relations by confidence
                if min_confidence > 0:
                    relations = [r for r in relations if (r["confidence"] or 1.0) >= min_confidence]
                
                entity = {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"] or "Entity",
                    "country": record["country"],
                    "confidence": int((record["confidence"] or 0.8) * 100),
                    "risk_level": "HIGH" if record["country"] and record["country"].upper() in ["RUSSIA", "CHINA", "IRAN"] else "MEDIUM",
                    "relations": [
                        {
                            "type": r["type"],
                            "target": r["target"],
                            "confidence": int((r["confidence"] or 0.7) * 100),
                            "source_url": r["source_url"]
                        }
                        for r in relations[:5]  # Limit to 5 relations per entity
                    ]
                }
                entities.append(entity)
        
        return {
            "total": len(entities),
            "min_confidence_filter": int(min_confidence * 100),
            "entities": entities
        }
        
    except Exception as e:
        logger.error("entities_query_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === MAGIC SWITCH: VISIBILITY CONTROL (CIA/OTAN Style) ===

@router.get("/graph/visible")
async def get_visible_graph(
    show_all: bool = Query(default=False, description="Show quarantined data too"),
    graph_store: GraphStore = Depends(get_graph_store)
):
    """
    🎯 THE MAGIC SWITCH - Demo Killer Feature
    
    By default: Shows only CONFIRMED + UNVERIFIED (clean graph for demo)
    With show_all=true: Shows EVERYTHING including QUARANTINE (raw intelligence)
    
    For investor demo:
    1. First show clean graph (show_all=false)
    2. When asked "Do you miss weak signals?", click show_all=true
    3. Graph explodes with hidden data → "Nothing is ever deleted"
    """
    
    if show_all:
        # Show EVERYTHING (including quarantined)
        query = """
        MATCH (e:Entity)-[r]->(t:Entity)
        RETURN e.canonical_name as source,
               e.visibility_status as source_status,
               type(r) as relation,
               t.canonical_name as target,
               t.visibility_status as target_status,
               r.confidence_score as confidence,
               COALESCE(e.visibility_status, 'VISIBLE') as visibility
        LIMIT 500
        """
    else:
        # Show only VISIBLE (clean view for demo)
        query = """
        MATCH (e:Entity)-[r]->(t:Entity)
        WHERE (e.visibility IS NULL OR e.visibility = 'VISIBLE')
          AND (t.visibility IS NULL OR t.visibility = 'VISIBLE')
        RETURN e.canonical_name as source,
               COALESCE(e.visibility_status, 'UNVERIFIED') as source_status,
               type(r) as relation,
               t.canonical_name as target,
               COALESCE(t.visibility_status, 'UNVERIFIED') as target_status,
               r.confidence_score as confidence
        LIMIT 200
        """
    
    try:
        with graph_store.driver.session() as session:
            result = session.run(query)
            records = list(result)
            
            # Separate by visibility status for response
            confirmed = []
            unverified = []
            quarantined = []
            
            for record in records:
                entry = {
                    "source": record["source"],
                    "relation": record["relation"],
                    "target": record["target"],
                    "confidence": record.get("confidence", 0.5),
                    "status": record.get("source_status", "UNVERIFIED")
                }
                
                status = record.get("source_status", "VISIBLE")
                if status == "CONFIRMED":
                    confirmed.append(entry)
                elif status == "QUARANTINE":
                    quarantined.append(entry)
                else:
                    unverified.append(entry)
            
            return {
                "mode": "RAW_INTELLIGENCE" if show_all else "CLEAN_VIEW",
                "total": len(records),
                "breakdown": {
                    "confirmed": len(confirmed),
                    "unverified": len(unverified),
                    "quarantined": len(quarantined)
                },
                "message": "Raw Intelligence Never Dies" if show_all else "Showing actionable intelligence only",
                "data": {
                    "confirmed": confirmed,
                    "unverified": unverified,
                    "quarantined": quarantined if show_all else []
                }
            }
            
    except Exception as e:
        logger.error("visible_graph_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/stats/visibility")
async def get_visibility_stats(graph_store: GraphStore = Depends(get_graph_store)):
    """
    Get breakdown of data by visibility status.
    Shows how much is in each zone (Confirmed/Unverified/Quarantine).
    """
    query = """
    MATCH (e:Entity)
    RETURN COALESCE(e.visibility_status, 'UNVERIFIED') as status,
           count(*) as count
    """
    
    try:
        with graph_store.driver.session() as session:
            result = session.run(query)
            stats = {record["status"]: record["count"] for record in result}
            
            total = sum(stats.values())
            visible = stats.get("CONFIRMED", 0) + stats.get("UNVERIFIED", 0)
            hidden = stats.get("QUARANTINE", 0)
            
            return {
                "total_entities": total,
                "visible_entities": visible,
                "quarantined_entities": hidden,
                "breakdown": stats,
                "visibility_rate": f"{visible / max(total, 1) * 100:.1f}%",
                "note": "Quarantined data is hidden but preserved (CIA/OTAN principle)"
            }
            
    except Exception as e:
        logger.error("visibility_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === FEEDBACK & CONTINUOUS LEARNING ENDPOINTS ===

class FeedbackRequest(BaseModel):
    """Request model for analyst feedback"""
    source_entity: str
    target_entity: Optional[str] = None
    original_relation: Optional[str] = None
    feedback_type: str  # VALIDATE, CORRECT_RELATION, DELETE_RELATION, FLAG_NOISE
    correct_value: Optional[str] = None
    analyst_note: Optional[str] = None
    original_context: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    🎓 ANALYST FEEDBACK - Train the AI
    
    Submit corrections to improve the model:
    - VALIDATE: Confirm a relation is correct
    - CORRECT_RELATION: Fix wrong relation type
    - DELETE_RELATION: Remove false relation
    - FLAG_NOISE: Mark as irrelevant noise
    
    Each correction makes Vidocq smarter.
    """
    from src.core.feedback import FeedbackStore, FeedbackEntry, FeedbackType
    import uuid
    
    try:
        store = FeedbackStore()
        
        entry = FeedbackEntry(
            feedback_id=str(uuid.uuid4()),
            source_entity=feedback.source_entity,
            target_entity=feedback.target_entity,
            original_relation=feedback.original_relation,
            feedback_type=FeedbackType(feedback.feedback_type),
            correct_value=feedback.correct_value,
            analyst_note=feedback.analyst_note,
            original_context=feedback.original_context
        )
        
        result = await store.add_feedback(entry)
        
        return {
            "status": "success",
            "message": "Feedback recorded. Thank you for training the AI.",
            **result
        }
        
    except Exception as e:
        logger.error("feedback_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/stats")
async def get_feedback_stats():
    """
    📊 FEEDBACK STATISTICS
    
    Shows:
    - Total feedback collected
    - Breakdown by type
    - Progress toward training threshold
    """
    from src.core.feedback import FeedbackStore
    
    try:
        store = FeedbackStore()
        stats = store.get_stats()
        
        return {
            "status": "success",
            "learning_progress": stats,
            "message": f"Collected {stats['total_feedback']} corrections. "
                       f"{stats['progress_percent']:.1f}% toward training threshold."
        }
        
    except Exception as e:
        logger.error("feedback_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/export-training")
async def export_training_data():
    """
    📥 EXPORT TRAINING DATA
    
    Export all corrections as training examples for model fine-tuning.
    Format: JSONL suitable for Mistral/LLaMA fine-tuning.
    """
    from src.core.feedback import FeedbackStore
    
    try:
        store = FeedbackStore()
        examples = store.export_training_data()
        
        return {
            "status": "success",
            "training_examples": len(examples),
            "file_path": "data/feedback/training_data.jsonl",
            "examples_preview": [ex.model_dump() for ex in examples[:5]],
            "message": f"Exported {len(examples)} training examples."
        }
        
    except Exception as e:
        logger.error("export_training_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# === ECOSYSTEM LEARNING & CASCADE PREDICTION ===

class ReportRatingRequest(BaseModel):
    """Request to rate a report's quality (NOT for learning)"""
    target: str
    quality_score: float = 1.0  # 0.0 to 1.0
    precision_score: float = 1.0
    completeness_score: float = 1.0
    notes: Optional[str] = None


class RelationValidationRequest(BaseModel):
    """Request to validate a single relation (FOR learning)"""
    source_entity: str
    target_entity: str
    relation_type: str
    is_correct: bool = True
    corrected_type: Optional[str] = None
    original_context: Optional[str] = None
    analyst_note: Optional[str] = None


@router.post("/report/rate")
async def rate_report(request: ReportRatingRequest):
    """
    📊 RATE REPORT QUALITY (NOT for learning)
    
    This rates the overall quality of a report:
    - Quality score (0-1)
    - Precision score (0-1)
    - Completeness score (0-1)
    
    NOTE: This does NOT train the AI!
    To train, use /relation/validate for each relation.
    """
    from src.brain.ecosystem import ECOSYSTEM
    
    try:
        result = await ECOSYSTEM.rate_report(
            target=request.target,
            quality_score=request.quality_score,
            precision_score=request.precision_score,
            completeness_score=request.completeness_score,
            notes=request.notes
        )
        
        return {
            "status": "success",
            "message": f"Report rated. {result.relations_requiring_validation} relations need individual validation.",
            "rating": result.model_dump(),
            "next_step": "Use GET /relations/pending/{target} to see relations to validate"
        }
        
    except Exception as e:
        logger.error("report_rating_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relation/validate")
async def validate_relation(request: RelationValidationRequest):
    """
    🎓 VALIDATE SINGLE RELATION - This trains the AI!
    
    Each validation:
    1. Marks the relation as confirmed in Neo4j
    2. Stores as training example
    3. Makes Vidocq smarter
    
    The analyst must validate each relation individually.
    This is intentional - quality over quantity.
    """
    from src.brain.ecosystem import ECOSYSTEM
    
    try:
        result = await ECOSYSTEM.validate_relation(
            source_entity=request.source_entity,
            target_entity=request.target_entity,
            relation_type=request.relation_type,
            is_correct=request.is_correct,
            corrected_type=request.corrected_type,
            original_context=request.original_context,
            analyst_note=request.analyst_note
        )
        
        return {
            "status": "success",
            "message": "Relation validated! AI learned from this.",
            **result
        }
        
    except Exception as e:
        logger.error("relation_validation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relations/pending/{target}")
async def get_pending_relations(
    target: str = Path(..., description="Target entity to get pending relations for"),
    limit: int = Query(default=20, description="Max relations to return")
):
    """
    📋 GET RELATIONS TO VALIDATE
    
    Returns list of relations that need validation.
    The analyst reviews these and calls /relation/validate for each.
    """
    from src.brain.ecosystem import ECOSYSTEM
    
    try:
        relations = await ECOSYSTEM.get_relations_to_validate(target, limit)
        
        return {
            "status": "success",
            "target": target,
            "pending_count": len(relations),
            "relations": relations,
            "instruction": "For each relation, call POST /relation/validate"
        }
        
    except Exception as e:
        logger.error("pending_relations_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ecosystem/cascade/{trigger}")
async def predict_cascade(
    trigger: str = Path(..., description="Entity that triggers the event"),
    event: str = Query(default="STRIKE", description="Event type: STRIKE, BANKRUPTCY, SANCTION, etc."),
    max_depth: int = Query(default=3, description="Maximum cascade depth")
):
    """
    🌊 CASCADE PREDICTION - "What if X happens?"
    
    Predicts downstream impacts from events:
    - STRIKE: Grève
    - BANKRUPTCY: Faillite
    - SANCTION: Nouvelle sanction
    - PRODUCTION_STOP: Arrêt de production
    - SUPPLY_SHORTAGE: Pénurie
    
    Example: "If TSMC has a strike, who is affected?"
    """
    from src.brain.ecosystem import ECOSYSTEM, EventType
    
    try:
        # Parse event type
        try:
            event_type = EventType(event.upper())
        except ValueError:
            event_type = EventType.STRIKE
        
        prediction = await ECOSYSTEM.predict_cascade(
            trigger_entity=trigger,
            event_type=event_type,
            max_depth=max_depth
        )
        
        return {
            "status": "success",
            "trigger": trigger,
            "event": event_type.value,
            "prediction": {
                "total_affected": prediction.total_affected,
                "max_depth": prediction.max_cascade_depth,
                "direct_impacts": [
                    {
                        "entity": i.entity,
                        "impact_type": i.impact_type,
                        "severity": i.severity
                    }
                    for i in prediction.direct_impacts
                ],
                "cascade_impacts": [
                    {
                        "entity": i.entity,
                        "distance": i.distance,
                        "impact_type": i.impact_type,
                        "severity": i.severity
                    }
                    for i in prediction.cascade_impacts[:20]  # Limit output
                ],
                "critical_entities": prediction.critical_entities,
                "executive_summary": prediction.executive_summary
            }
        }
        
    except Exception as e:
        logger.error("cascade_prediction_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ecosystem/learn-status")
async def get_learning_status():
    """
    📊 LEARNING STATUS - How smart is Vidocq?
    
    Shows:
    - Total validated data
    - Training progress
    - Ecosystem coverage
    """
    try:
        from src.core.training import VidocqTrainer
        from src.storage.graph import GraphStore
        
        # Training readiness
        trainer = VidocqTrainer()
        readiness = trainer.check_readiness()
        
        # Graph coverage
        graph_store = GraphStore()
        with graph_store.driver.session() as session:
            # Total vs validated
            result = session.run("""
                MATCH (e:Entity)
                RETURN count(*) as total,
                       sum(CASE WHEN e.validated = true THEN 1 ELSE 0 END) as validated
            """)
            record = result.single()
            total_entities = record["total"] if record else 0
            validated_entities = record["validated"] if record else 0
            
            # Relations
            result = session.run("""
                MATCH ()-[r]->()
                RETURN count(*) as total,
                       sum(CASE WHEN r.validated = true THEN 1 ELSE 0 END) as validated
            """)
            record = result.single()
            total_relations = record["total"] if record else 0
            validated_relations = record["validated"] if record else 0
        
        coverage = validated_entities / max(total_entities, 1) * 100
        
        return {
            "status": "success",
            "training": readiness,
            "ecosystem_coverage": {
                "total_entities": total_entities,
                "validated_entities": validated_entities,
                "total_relations": total_relations,
                "validated_relations": validated_relations,
                "coverage_percent": f"{coverage:.1f}%"
            },
            "message": "Vidocq learns more with each validated report!"
        }
        
    except Exception as e:
        logger.error("learning_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# --- INTELLIGENCE ANALYST ENDPOINTS ---

@router.get("/graph/analyze")
async def analyze_graph():
    """
    Generate an AI-powered intelligence report from the knowledge graph.
    Uses the Graph Analyst to produce factual, unbiased analysis.
    """
    from src.pipeline.analyst import GraphAnalyst
    
    try:
        analyst = GraphAnalyst()
        result = analyst.generate_report()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))
        
        return result
        
    except Exception as e:
        logger.error("analysis_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/generate")
async def generate_report(
    title: str = Query(default="Intelligence Report", description="Report title")
):
    """
    Generate a professional intelligence report (HTML + Markdown).
    The HTML version can be printed to PDF from browser.
    """
    from src.pipeline.report import generate_pdf_report
    
    try:
        result = generate_pdf_report(title=title)
        
        if result["status"] == "empty":
            raise HTTPException(status_code=404, detail="No data in graph to analyze")
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Report generation failed"))
        
        return {
            "status": "success",
            "markdown_path": result["markdown_path"],
            "html_path": result["html_path"],
            "stats": result["stats"],
            "view_report": f"/report/view?path={result['html_path']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("report_generation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/view")
async def view_report(
    path: str = Query(..., description="Path to HTML report file")
):
    """
    Serve the generated HTML report for viewing/printing.
    """
    from fastapi.responses import HTMLResponse
    from pathlib import Path
    
    try:
        report_path = Path(path)
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        if not str(report_path).startswith("reports"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        with open(report_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("report_view_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/export")
async def export_graph_csv():
    """
    Export the knowledge graph as CSV for manual analysis.
    """
    from src.pipeline.analyst import GraphAnalyst
    from fastapi.responses import PlainTextResponse
    
    try:
        analyst = GraphAnalyst()
        csv_content = analyst.export_graph_csv()
        
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=shadowmap_export.csv"}
        )
        
    except Exception as e:
        logger.error("export_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/stats")
async def get_graph_stats(graph_store: GraphStore = Depends(get_graph_store)):
    """
    Get quick statistics about the knowledge graph.
    """
    query = """
    MATCH (e:Entity)
    WITH count(e) as entity_count
    MATCH ()-[r]->()
    RETURN entity_count, count(r) as relationship_count
    """
    
    try:
        with graph_store.driver.session() as session:
            result = session.run(query)
            record = result.single()
            
            if record:
                return {
                    "entities": record["entity_count"],
                    "relationships": record["relationship_count"]
                }
            else:
                return {"entities": 0, "relationships": 0}
                
    except Exception as e:
        logger.error("stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/visualization")
async def get_graph_visualization(
    graph_store: GraphStore = Depends(get_graph_store),
    limit: int = Query(default=100, le=500, description="Max nodes to return")
):
    """
    Get graph data formatted for Sigma.js visualization.
    Returns nodes and edges in a format ready for frontend rendering.
    """
    # Query entities and relationships
    query = """
    MATCH (e:Entity)
    WITH e LIMIT $limit
    OPTIONAL MATCH (e)-[r]->(target:Entity)
    RETURN 
        e.id as source_id,
        e.canonical_name as source_name,
        labels(e)[1] as source_type,
        type(r) as relation,
        r.confidence_score as confidence,
        r.source_url as source_url,
        target.id as target_id,
        target.canonical_name as target_name,
        labels(target)[1] as target_type
    """
    
    try:
        nodes = {}
        edges = []
        
        with graph_store.driver.session() as session:
            result = session.run(query, limit=limit)
            
            for record in result:
                # Add source node
                source_id = record["source_id"]
                if source_id and source_id not in nodes:
                    nodes[source_id] = {
                        "id": source_id,
                        "label": record["source_name"],
                        "type": record["source_type"] or "Entity",
                        "size": 10,
                        "color": get_node_color(record["source_type"])
                    }
                
                # Add target node and edge if relationship exists
                if record["target_id"]:
                    target_id = record["target_id"]
                    if target_id not in nodes:
                        nodes[target_id] = {
                            "id": target_id,
                            "label": record["target_name"],
                            "type": record["target_type"] or "Entity",
                            "size": 10,
                            "color": get_node_color(record["target_type"])
                        }
                    
                    edges.append({
                        "id": f"{source_id}-{record['relation']}-{target_id}",
                        "source": source_id,
                        "target": target_id,
                        "label": record["relation"],
                        "confidence": record["confidence"] or 0.5,
                        "source_url": record["source_url"],
                        "color": get_edge_color(record["confidence"])
                    })
        
        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        }
        
    except Exception as e:
        logger.error("visualization_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


def get_node_color(node_type: str) -> str:
    """Get color for node based on entity type."""
    colors = {
        "ORGANIZATION": "#3b82f6",  # Blue
        "PERSON": "#22c55e",        # Green
        "COUNTRY": "#f59e0b",       # Amber
        "CITY": "#8b5cf6",          # Purple
        "BANK": "#ec4899",          # Pink
        "SHELL_COMPANY": "#ef4444", # Red
        "MEDIA_OUTLET": "#06b6d4",  # Cyan
        "GOVERNMENT": "#f97316",    # Orange
    }
    return colors.get(node_type, "#6b7280")  # Default gray


def get_edge_color(confidence: float) -> str:
    """Get color for edge based on confidence score."""
    if confidence is None:
        return "#6b7280"
    if confidence >= 0.8:
        return "#22c55e"  # Green - high confidence
    if confidence >= 0.5:
        return "#f59e0b"  # Amber - medium confidence
    return "#ef4444"      # Red - low confidence


# ============================================================================
# RISK SCORING ENDPOINTS
# ============================================================================

class RiskScoreRequest(BaseModel):
    entity_name: str
    locations: Optional[List[str]] = None


@router.post("/risk/score")
async def score_entity_risk(
    request: RiskScoreRequest,
    graph_store: GraphStore = Depends(get_graph_store)
):
    """
    Calculate comprehensive risk score for an entity.
    Returns multi-dimensional risk analysis (concentration, geopolitical, sanctions, ESG).
    """
    try:
        from src.core.risk_scoring import get_risk_scorer
        
        scorer = get_risk_scorer(graph_store)
        
        # Query relationships from graph
        query = """
        MATCH (e:Entity {name: $name})-[r]->(target:Entity)
        RETURN type(r) as type, target.name as target, 
               target.id as target_id, labels(target) as labels
        """
        
        relationships = []
        try:
            with graph_store.driver.session() as session:
                result = session.run(query, name=request.entity_name)
                for record in result:
                    relationships.append({
                        "type": record["type"],
                        "target": record["target"],
                        "target_id": record["target_id"]
                    })
        except Exception as e:
            logger.warning("risk_query_failed", error=str(e))
        
        # Score entity
        score = scorer.score_entity(
            entity_id=request.entity_name,
            entity_name=request.entity_name,
            relationships=relationships,
            locations=request.locations or []
        )
        
        return {
            "entity": score.entity_name,
            "overall_score": round(score.overall_score, 1),
            "risk_level": score.risk_level.value,
            "breakdown": {
                "concentration": round(score.concentration_score, 1),
                "geopolitical": round(score.geopolitical_score, 1),
                "depth_visibility": round(score.depth_score, 1),
                "sanctions": round(score.sanctions_score, 1),
                "esg": round(score.esg_score, 1)
            },
            "risk_factors": score.risk_factors,
            "recommendations": score.recommendations
        }
        
    except Exception as e:
        logger.error("risk_scoring_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/supply-chain/{entity}")
async def score_supply_chain_risk(
    entity: str = Path(..., description="Root entity name"),
    graph_store: GraphStore = Depends(get_graph_store)
):
    """
    Score entire supply chain risk from a root entity.
    Returns aggregate risk and per-supplier breakdown.
    """
    try:
        from src.core.risk_scoring import get_risk_scorer
        
        scorer = get_risk_scorer(graph_store)
        result = scorer.score_supply_chain(entity)
        
        return result
        
    except Exception as e:
        logger.error("supply_chain_risk_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/geopolitical-map")
async def get_geopolitical_risk_map():
    """
    Get the geopolitical risk database.
    Returns risk scores for all known countries.
    """
    from src.core.risk_scoring import GEOPOLITICAL_RISK, RiskLevel
    
    # Categorize countries by risk level
    categorized = {
        "CRITICAL": [],
        "HIGH": [],
        "MEDIUM": [],
        "LOW": [],
        "MINIMAL": []
    }
    
    for country, score in GEOPOLITICAL_RISK.items():
        if country == "UNKNOWN":
            continue
        if score >= 80:
            categorized["CRITICAL"].append({"country": country, "score": score})
        elif score >= 60:
            categorized["HIGH"].append({"country": country, "score": score})
        elif score >= 40:
            categorized["MEDIUM"].append({"country": country, "score": score})
        elif score >= 20:
            categorized["LOW"].append({"country": country, "score": score})
        else:
            categorized["MINIMAL"].append({"country": country, "score": score})
    
    return {
        "risk_map": categorized,
        "total_countries": len(GEOPOLITICAL_RISK) - 1,
        "legend": {
            "CRITICAL": "Score >= 80 - Immediate risk",
            "HIGH": "Score 60-79 - Significant concerns",
            "MEDIUM": "Score 40-59 - Monitor closely",
            "LOW": "Score 20-39 - Standard vigilance",
            "MINIMAL": "Score < 20 - Low concern"
        }
    }


# ============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/cache/stats")
async def get_cache_statistics():
    """
    Get discovery cache statistics.
    Shows cache hit rates, stored entities, and TTL settings.
    """
    try:
        from src.storage.cache import get_discovery_cache
        
        cache = get_discovery_cache()
        return cache.get_stats()
        
    except Exception as e:
        logger.warning("cache_stats_error", error=str(e))
        return {"enabled": False, "error": str(e)}


@router.delete("/cache/clear")
async def clear_cache():
    """
    Clear the discovery cache.
    Use with caution - will cause re-scraping of all entities.
    """
    try:
        from src.storage.cache import get_discovery_cache
        
        cache = get_discovery_cache()
        if cache.enabled and cache.client:
            cache.client.flushdb()
            return {"status": "cleared", "message": "Discovery cache cleared"}
        
        return {"status": "disabled", "message": "Cache is not enabled"}
        
    except Exception as e:
        logger.error("cache_clear_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DISCOVERY V2 ENDPOINTS
# ============================================================================

class DiscoveryV2Request(BaseModel):
    entity: str
    use_cache: bool = True
    max_depth: int = 2


@router.post("/discover/v2")
async def discover_v2(request: DiscoveryV2Request):
    """
    Launch enhanced discovery (v2) with caching and parallel search.
    
    Improvements over v1:
    - Redis caching (avoids duplicate searches)
    - Parallel query execution (3x faster)
    - Smarter fallback strategies
    """
    logger.info("discovery_v2_request", entity=request.entity)
    
    try:
        from src.pipeline.discovery_v2 import DiscoveryEngineV2
        
        engine = DiscoveryEngineV2(use_cache=request.use_cache)
        result = engine.discover(request.entity, depth=0)
        
        return {
            "status": "completed",
            "entity": result.get("entity"),
            "urls_found": result.get("url_count", 0),
            "queries_used": result.get("queries_used", 0),
            "cached": result.get("cached", False),
            "urls": result.get("urls", [])[:10]  # Return first 10 URLs
        }
        
    except Exception as e:
        logger.error("discovery_v2_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover/v2/ingest")
async def discover_and_ingest_v2(request: DiscoveryV2Request):
    """
    Launch enhanced discovery and trigger ingestion for found URLs.
    This is the full pipeline: Discover → Ingest → Extract → Store.
    """
    logger.info("discovery_v2_ingest_request", entity=request.entity)
    
    try:
        from src.pipeline.discovery_v2 import DiscoveryEngineV2
        
        engine = DiscoveryEngineV2(use_cache=request.use_cache)
        result = engine.discover_and_ingest(request.entity, depth=0)
        
        return {
            "status": "ingestion_triggered",
            "entity": result.get("entity"),
            "urls_queued": result.get("url_count", 0),
            "cached": result.get("cached", False),
            "message": f"Ingestion tasks queued for {result.get('url_count', 0)} URLs"
        }
        
    except Exception as e:
        logger.error("discovery_v2_ingest_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DISCOVERY V3 ENDPOINTS (Multilingual Advanced Search)
# ============================================================================

class DiscoveryV3Request(BaseModel):
    entity: str
    use_cache: bool = True
    max_depth: int = 2
    aggressive: bool = True  # Use all languages and strategies
    max_urls: int = 50
    # Hybrid mode: provide a seed URL for controlled starting point
    seed_url: Optional[str] = None  # If provided, ingest this first then discover on extracted entities


@router.post("/discover/v3")
async def discover_v3(request: DiscoveryV3Request):
    """
    Launch advanced multilingual discovery (v3).
    
    Features:
    - Polyglot search (EN, FR, DE, ZH, RU, ES, AR)
    - Smart entity context detection
    - Multiple search strategies (suppliers, ownership, sanctions, leaks)
    - Source quality scoring
    - Noise domain filtering
    """
    logger.info("discovery_v3_request", entity=request.entity, aggressive=request.aggressive)
    
    try:
        from src.pipeline.discovery_v3 import DiscoveryEngineV3
        
        engine = DiscoveryEngineV3(
            use_cache=request.use_cache, 
            aggressive=request.aggressive
        )
        result = engine.discover(
            request.entity, 
            depth=0, 
            max_urls=request.max_urls
        )
        
        return {
            "status": "completed",
            "entity": result.get("entity"),
            "urls_found": len(result.get("urls", [])),
            "high_value_sources": result.get("high_value_sources", 0),
            "queries_executed": result.get("queries_executed", 0),
            "context": result.get("context", {}),
            "cached": result.get("cached", False),
            "urls": result.get("urls", [])[:20]  # Return first 20 URLs
        }
        
    except Exception as e:
        logger.error("discovery_v3_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover/v3/ingest")
async def discover_and_ingest_v3(request: DiscoveryV3Request):
    """
    Launch advanced multilingual discovery and trigger ingestion.
    
    MODES:
    - Standard: Search for entity → Ingest discovered URLs
    - Hybrid (seed_url provided): Ingest seed first → Extract entities → Discover on extracted entities
    
    The hybrid mode is more precise as YOU control the starting point.
    """
    logger.info("discovery_v3_ingest_request", entity=request.entity, seed_url=request.seed_url)
    
    try:
        from src.pipeline.discovery_v3 import DiscoveryEngineV3
        from src.ingestion.tasks import ingest_url
        from urllib.parse import urlparse
        
        queued_count = 0
        extracted_entities = []
        seed_result = None
        
        # =====================================================================
        # HYBRID MODE: If seed_url is provided, ingest it first
        # =====================================================================
        if request.seed_url:
            logger.info("hybrid_mode_seed_ingestion", url=request.seed_url)
            
            # Ingest the seed URL synchronously to extract entities
            try:
                from src.ingestion.stealth import StealthSession
                from src.ingestion.parser import ContentParser
                from src.ingestion.chunking import SemanticChunker
                from src.pipeline.extractor import extract_entities_and_claims
                
                # Fetch and parse seed
                with StealthSession() as session:
                    response = session.get(request.seed_url)
                    html_content = response.text
                
                clean_text = ContentParser.parse_html(html_content)
                
                # Chunk the text
                chunker = SemanticChunker()
                chunks = chunker.chunk(clean_text)
                
                # Extract from first chunk (for speed)
                if chunks:
                    result = extract_entities_and_claims(
                        chunks[0][:4000],  # Limit size
                        source_domain=urlparse(request.seed_url).netloc,
                        source_id="seed_extraction"
                    )
                    
                    # Get high-quality entity names for discovery
                    for entity in result.get("entities", []):
                        if entity.entity_type == "ORGANIZATION":
                            extracted_entities.append(entity.canonical_name)
                    
                    seed_result = {
                        "url": request.seed_url,
                        "entities_extracted": len(extracted_entities),
                        "entity_names": extracted_entities[:10]  # Limit
                    }
                    
                    logger.info("hybrid_seed_entities_extracted", 
                               count=len(extracted_entities), 
                               entities=extracted_entities[:5])
                
                # Queue the seed for full ingestion
                domain = urlparse(request.seed_url).netloc
                ingest_url.delay(request.seed_url, domain, depth=0, entity_name=request.entity)
                queued_count += 1
                
            except Exception as e:
                logger.warning("hybrid_seed_extraction_failed", error=str(e))
                # Fall back to standard mode
                extracted_entities = [request.entity]
        
        # =====================================================================
        # DISCOVERY: Run V3 on entity (or extracted entities in hybrid mode)
        # =====================================================================
        engine = DiscoveryEngineV3(
            use_cache=request.use_cache,
            aggressive=request.aggressive
        )
        
        # In hybrid mode, discover on extracted entities
        targets = extracted_entities if extracted_entities else [request.entity]
        all_urls = []
        
        for target in targets[:5]:  # Limit to 5 entities
            result = engine.discover(
                target, 
                depth=0,
                max_urls=request.max_urls // max(len(targets), 1)
            )
            all_urls.extend(result.get("urls", []))
        
        # Deduplicate URLs
        unique_urls = list(set(all_urls))
        
        # Queue ingestion for discovered URLs
        for url in unique_urls:
            try:
                domain = urlparse(url).netloc
                ingest_url.delay(url, domain, depth=1, entity_name=target)
                queued_count += 1
            except Exception as e:
                logger.warning("ingest_queue_error", url=url[:60], error=str(e))
        
        response = {
            "status": "ingestion_triggered",
            "mode": "hybrid" if request.seed_url else "standard",
            "entity": request.entity,
            "context_detected": result.get("context", {}),
            "urls_discovered": len(unique_urls),
            "urls_queued": queued_count,
            "message": f"Discovery complete. {queued_count} URLs queued for ingestion."
        }
        
        # Add hybrid mode details
        if seed_result:
            response["seed_result"] = seed_result
            response["discovery_targets"] = extracted_entities[:5]
        
        return response
        
    except Exception as e:
        logger.error("discovery_v3_ingest_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# SYSTEM HEALTH ENDPOINTS
# ============================================================================

@router.get("/health/full")
async def full_health_check(
    graph_store: GraphStore = Depends(get_graph_store),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """
    Comprehensive health check for all system components.
    """
    health = {
        "status": "healthy",
        "components": {}
    }
    
    # Check Neo4j
    try:
        with graph_store.driver.session() as session:
            session.run("RETURN 1")
        health["components"]["neo4j"] = {"status": "ok"}
    except Exception as e:
        health["components"]["neo4j"] = {"status": "error", "error": str(e)}
        health["status"] = "degraded"
    
    # Check Qdrant
    try:
        vector_store.client.get_collections()
        health["components"]["qdrant"] = {"status": "ok"}
    except Exception as e:
        health["components"]["qdrant"] = {"status": "error", "error": str(e)}
        health["status"] = "degraded"
    
    # Check Redis/Cache
    try:
        from src.storage.cache import get_discovery_cache
        cache = get_discovery_cache()
        if cache.enabled:
            cache.client.ping()
            health["components"]["redis"] = {"status": "ok"}
        else:
            health["components"]["redis"] = {"status": "disabled"}
    except Exception as e:
        health["components"]["redis"] = {"status": "error", "error": str(e)}
    
    # Check Gemini API
    try:
        if settings.GEMINI_API_KEY:
            health["components"]["gemini"] = {"status": "configured"}
        else:
            health["components"]["gemini"] = {"status": "not_configured"}
    except:
        health["components"]["gemini"] = {"status": "unknown"}
    
    return health


# ============================================================================
# WATCHLIST ENDPOINTS (Continuous Monitoring)
# ============================================================================

class WatchlistAddRequest(BaseModel):
    entity_name: str
    entity_type: str = "ORGANIZATION"
    alert_types: List[str] = ["news", "sanctions", "ownership_change", "scandal"]
    frequency: str = "daily"


@router.post("/watchlist/add")
async def add_to_watchlist(request: WatchlistAddRequest):
    """Add an entity to the watchlist for continuous monitoring."""
    try:
        from src.core.watchlist import get_watchlist_manager
        manager = get_watchlist_manager()
        
        entry = manager.add_entity(
            entity_name=request.entity_name,
            entity_type=request.entity_type,
            alert_types=request.alert_types,
            frequency=request.frequency
        )
        
        return {
            "status": "watching",
            "entity": entry.entity_name,
            "frequency": entry.frequency,
            "next_scan": entry.next_scan,
            "alert_types": entry.alert_types
        }
    except Exception as e:
        logger.error("watchlist_add_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watchlist/remove/{entity_name}")
async def remove_from_watchlist(entity_name: str):
    """Remove an entity from the watchlist."""
    try:
        from src.core.watchlist import get_watchlist_manager
        manager = get_watchlist_manager()
        
        removed = manager.remove_entity(entity_name)
        return {"removed": removed, "entity": entity_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist")
async def get_watchlist():
    """Get all entities currently being watched."""
    try:
        from src.core.watchlist import get_watchlist_manager
        manager = get_watchlist_manager()
        
        entries = manager.get_watchlist()
        return {
            "total": len(entries),
            "entities": [e.to_dict() for e in entries]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist/alerts")
async def get_watchlist_alerts(
    entity_name: str = None,
    unacknowledged_only: bool = False,
    limit: int = 100
):
    """Get alerts from the watchlist system."""
    try:
        from src.core.watchlist import get_watchlist_manager
        manager = get_watchlist_manager()
        
        alerts = manager.get_alerts(
            entity_name=entity_name,
            unacknowledged_only=unacknowledged_only,
            limit=limit
        )
        
        return {
            "total": len(alerts),
            "alerts": [a.to_dict() for a in alerts]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    try:
        from src.core.watchlist import get_watchlist_manager
        manager = get_watchlist_manager()
        
        success = manager.acknowledge_alert(alert_id)
        return {"acknowledged": success, "alert_id": alert_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist/stats")
async def get_watchlist_stats():
    """Get watchlist statistics."""
    try:
        from src.core.watchlist import get_watchlist_manager
        manager = get_watchlist_manager()
        return manager.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CROSS-CLIENT ALERTS (Anonymous Intelligence Sharing)
# ============================================================================

class FlagEntityRequest(BaseModel):
    entity_name: str
    flag_type: str = "RISK"
    severity: str = "MEDIUM"
    details: str = ""


@router.post("/alerts/flag")
async def flag_entity_for_network(request: FlagEntityRequest):
    """Flag an entity as risky (shared anonymously with other Vidocq users)."""
    try:
        from src.core.cross_client_alerts import get_cross_client_alerts
        system = get_cross_client_alerts()
        
        # Use a default client ID for now (would be from auth in production)
        client_id = "default_client"
        
        flag = system.flag_entity(
            client_id=client_id,
            entity_name=request.entity_name,
            flag_type=request.flag_type,
            severity=request.severity,
            details=request.details
        )
        
        return {
            "status": "flagged",
            "entity": request.entity_name,
            "flag_type": request.flag_type,
            "severity": request.severity,
            "message": "This flag is now shared anonymously with other Vidocq users"
        }
    except Exception as e:
        logger.error("flag_entity_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/check/{entity_name}")
async def check_entity_flags(entity_name: str):
    """Check if an entity has been flagged by other Vidocq users."""
    try:
        from src.core.cross_client_alerts import get_cross_client_alerts
        system = get_cross_client_alerts()
        
        flags = system.check_entity_flags(entity_name, exclude_client="default_client")
        
        return {
            "entity": entity_name,
            "has_flags": len(flags) > 0,
            "flag_count": len(flags),
            "flags": flags
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/network")
async def get_network_alerts():
    """Get all active flags for entities in your network."""
    try:
        from src.core.cross_client_alerts import get_cross_client_alerts
        system = get_cross_client_alerts()
        
        alerts = system.get_alerts_for_client("default_client")
        
        return {
            "total": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/stats")
async def get_cross_client_stats():
    """Get cross-client alert system statistics."""
    try:
        from src.core.cross_client_alerts import get_cross_client_alerts
        system = get_cross_client_alerts()
        return system.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# OWNERSHIP TRACING (Holdings Chain Detection)
# ============================================================================

@router.get("/brain/trace-ownership/{entity_name}")
async def trace_ownership_chain(
    entity_name: str,
    max_depth: int = 10,
    graph_store: GraphStore = Depends(get_graph_store)
):
    """
    Trace the ownership chain of an entity to find ultimate beneficial owners.
    Detects holding-in-holding-in-holding structures.
    """
    try:
        # Query to trace ownership chain
        query = """
        MATCH path = (target:Entity {name: $name})-[:OWNED_BY|SUBSIDIARY_OF|CONTROLLED_BY*1..10]->(owner)
        RETURN 
            [node in nodes(path) | {
                name: node.name, 
                type: labels(node)[0],
                country: node.country
            }] as chain,
            length(path) as depth
        ORDER BY depth DESC
        LIMIT 20
        """
        
        with graph_store.driver.session() as session:
            result = session.run(query, name=entity_name)
            chains = []
            
            for record in result:
                chain_data = record["chain"]
                chains.append({
                    "depth": record["depth"],
                    "chain": chain_data
                })
        
        # Analyze red flags
        red_flags = []
        all_countries = set()
        max_depth_found = 0
        
        for chain in chains:
            max_depth_found = max(max_depth_found, chain["depth"])
            for node in chain["chain"]:
                if node.get("country"):
                    all_countries.add(node["country"].upper())
        
        # Detect suspicious patterns
        tax_havens = {"CAYMAN ISLANDS", "BVI", "BRITISH VIRGIN ISLANDS", "LUXEMBOURG", 
                      "DELAWARE", "PANAMA", "BERMUDA", "JERSEY", "GUERNSEY", "ISLE OF MAN"}
        high_risk = {"RUSSIA", "CHINA", "IRAN", "NORTH KOREA", "BELARUS"}
        
        havens_found = all_countries & tax_havens
        risks_found = all_countries & high_risk
        
        if max_depth_found >= 5:
            red_flags.append(f"{max_depth_found} levels of holdings = intentional opacity")
        if havens_found:
            red_flags.append(f"Tax haven jurisdictions: {', '.join(havens_found)}")
        if risks_found:
            red_flags.append(f"High-risk countries: {', '.join(risks_found)}")
        
        # Calculate risk score
        risk_score = min(100, 20 * max_depth_found + 15 * len(havens_found) + 25 * len(risks_found))
        
        return {
            "target": entity_name,
            "ownership_chains": chains,
            "max_depth": max_depth_found,
            "countries_detected": list(all_countries),
            "red_flags": red_flags,
            "risk_score": risk_score,
            "recommendation": "Enhanced due diligence required" if risk_score > 50 else "Standard review"
        }
        
    except Exception as e:
        logger.error("ownership_trace_error", entity=entity_name, error=str(e))
        return {
            "target": entity_name,
            "ownership_chains": [],
            "error": str(e),
            "note": "No ownership data found or graph query failed"
        }


# ============================================================================
# UNIFIED INTELLIGENCE PIPELINE v2.0 - ALL MODULES INTEGRATED
# ============================================================================

class UnifiedInvestigationRequest(BaseModel):
    """Request for unified investigation pipeline"""
    target: str
    max_urls: int = 20
    

@router.post("/investigate/full")
async def investigate_full_pipeline(request: UnifiedInvestigationRequest):
    """
    🚀 UNIFIED INTELLIGENCE PIPELINE v2.0
    
    The MOST COMPLETE investigation endpoint. Uses ALL AI modules:
    
    ┌─────────────────────────────────────────────────────────────────┐
    │  1. PROVENANCE      → Chain of custody (audit trail)           │
    │  2. CLASSIFICATION  → VidocqBrain (CoT + few-shot)             │
    │  3. DISCOVERY       → DiscoveryV3 + Coverage Analysis          │
    │  4. INGESTION       → Fetch + Language Detection (LLM)         │
    │  5. EXTRACTION      → Extractor (with parent_context)          │
    │  6. ONTOLOGY        → Type inference + risk detection          │
    │  7. SCORING         → UnifiedScorer + Contradiction            │
    │  8. FUSION          → Bayesian multi-source fusion             │
    │  9. VERSIONING      → Temporal fact versioning                 │
    │ 10. STORAGE         → Neo4j + Qdrant                           │
    └─────────────────────────────────────────────────────────────────┘
    
    Use this instead of /discover/v3/ingest for a complete analysis.
    
    Returns comprehensive results with:
    - Bayesian probability for each claim
    - Narrative war detection
    - Coverage gap analysis
    - Entity risk assessment via ontology
    - Full audit trail (provenance)
    """
    logger.info("unified_pipeline_v2_request", target=request.target, max_urls=request.max_urls)
    
    try:
        from src.pipeline.unified_pipeline import investigate
        
        result = await investigate(request.target, max_urls=request.max_urls)
        
        return {
            "status": "complete",
            "pipeline_version": "2.0",
            "target": result.target,
            "duration_seconds": (result.completed_at - result.started_at).total_seconds() if result.completed_at else None,
            
            # Classification
            "classification": result.target_classification,
            
            # Discovery
            "discovery": {
                "urls_discovered": result.urls_discovered,
                "coverage_score": result.coverage_analysis.get("score"),
                "critical_gaps": result.critical_gaps
            },
            
            # Extraction
            "extraction": {
                "entities_extracted": result.entities_extracted,
                "claims_extracted": result.claims_extracted,
                "languages_detected": result.languages_detected,
                "parent_context": result.extraction_context
            },
            
            # Ontology (NEW)
            "ontology": {
                "entity_types": result.entity_types_inferred,
                "high_risk_entities": result.high_risk_entities
            },
            
            # Scoring
            "scoring": result.scoring_summary,
            
            # Contradiction (NEW)
            "contradiction": {
                "narrative_wars": result.contradiction_report.get("narrative_wars", 0),
                "contested_topics": result.contested_topics,
                "propaganda_indicators": result.contradiction_report.get("propaganda_indicators", [])
            },
            
            # Bayesian Fusion (NEW)
            "bayesian_fusion": result.bayesian_summary,
            
            # Temporal (NEW)
            "temporal": {
                "facts_versioned": result.facts_versioned
            },
            
            # Provenance / Audit (NEW)
            "provenance": {
                "custody_id": result.custody_id,
                "steps_count": len(result.provenance_export.get("audit_trail", [])),
                "audit_trail": result.provenance_export.get("audit_trail", [])[:5]  # First 5 steps
            },
            
            # Recommendations
            "recommendations": result.recommendations,
            
            # Next steps
            "next_steps": [
                f"GET /graph/analyze to see the full knowledge graph",
                f"GET /brain/report/{request.target} for geo-sourced report",
                f"GET /graph/visible?show_all=true to see quarantined data"
            ]
        }
        
    except Exception as e:
        logger.error("unified_pipeline_v2_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/investigate/full/{target}")
async def investigate_full_get(
    target: str = Path(..., description="Entity to investigate"),
    max_urls: int = Query(default=20, ge=1, le=50, description="Max URLs to process")
):
    """
    GET version of /investigate/full for easier testing.
    Same as POST but via URL path.
    """
    request = UnifiedInvestigationRequest(target=target, max_urls=max_urls)
    return await investigate_full_pipeline(request)
