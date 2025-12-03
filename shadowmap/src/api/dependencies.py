from src.storage.graph import GraphStore
from src.storage.vector import VectorStore
from src.storage.postgres import AuditStore
from src.pipeline.extractor import Extractor
from src.pipeline.resolver import EntityResolver

# Singleton instances
_graph_store = None
_vector_store = None
_audit_store = None
_extractor = None
_resolver = None

def get_graph_store() -> GraphStore:
    global _graph_store
    if _graph_store is None:
        _graph_store = GraphStore()
    return _graph_store

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

def get_audit_store() -> AuditStore:
    global _audit_store
    if _audit_store is None:
        _audit_store = AuditStore()
    return _audit_store

def get_extractor() -> Extractor:
    global _extractor
    if _extractor is None:
        _extractor = Extractor()
    return _extractor

def get_resolver() -> EntityResolver:
    global _resolver
    if _resolver is None:
        _resolver = EntityResolver()
    return _resolver
