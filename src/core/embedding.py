"""
Embedding Generation Module.
Handles text-to-vector conversion using Gemini or local SentenceTransformers.
"""
import time
from typing import List, Optional
import google.generativeai as genai
from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

# Singleton for local model
_local_model = None

def get_local_model():
    """Lazy load local model to avoid startup overhead."""
    global _local_model
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            # 768 dimensions to match Gemini text-embedding-004
            logger.info("loading_local_embedding_model")
            _local_model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
        except ImportError:
            logger.error("sentence_transformers_not_installed")
            return None
        except Exception as e:
            logger.error("local_model_load_error", error=str(e))
            return None
    return _local_model

def embed_text(text: str) -> List[float]:
    """
    Generate embedding vector for text.
    Priority:
    1. Gemini API (text-embedding-004)
    2. Local SentenceTransformer (paraphrase-multilingual-mpnet-base-v2)
    3. Zero vector fallback (768 dim)
    """
    if not text:
        return [0.0] * 768

    # 1. Try Gemini
    if settings.GEMINI_API_KEY:
        try:
            # text-embedding-004 output dimension is 768
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            vector = result['embedding']
            if len(vector) == 768:
                return vector
            else:
                logger.warning("gemini_dim_mismatch", expected=768, actual=len(vector))
        except Exception as e:
            logger.warning("gemini_embedding_failed", error=str(e))

    # 2. Try Local Model
    local = get_local_model()
    if local:
        try:
            vector = local.encode(text).tolist()
            if len(vector) == 768:
                return vector
        except Exception as e:
            logger.error("local_embedding_failed", error=str(e))

    # 3. Fallback
    logger.warning("using_fallback_embedding", text=text[:50])
    return [0.0] * 768
