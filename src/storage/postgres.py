from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.core.models import SourceDocument, Claim
from src.core.logging import get_logger
from src.core.exceptions import StorageError

logger = get_logger(__name__)

class AuditStore:
    """
    PostgreSQL audit storage.
    """
    
    def __init__(self):
        self.engine = create_engine(settings.POSTGRES_DSN)
        self.Session = sessionmaker(bind=self.engine)

    def log_source_document(self, doc: SourceDocument):
        """Log ingested source document."""
        try:
            with self.Session() as session:
                session.execute(
                    text("""
                        INSERT INTO source_documents 
                        (id, url, source_domain, reliability_score, ingested_at, raw_content_hash)
                        VALUES (:id, :url, :source_domain, :reliability_score, :ingested_at, md5(:raw_content))
                        ON CONFLICT (id) DO NOTHING
                    """),
                    doc.model_dump(mode='json')
                )
                session.commit()
        except Exception as e:
            logger.error("audit_log_failed", error=str(e))
            raise StorageError(f"Failed to log source document: {e}")

    def log_claim(self, claim: Claim):
        """Log extracted claim for audit trail."""
        try:
            with self.Session() as session:
                session.execute(
                    text("""
                        INSERT INTO claims_audit 
                        (id, source_id, subject_id, relation_type, object_id, confidence_score, extraction_model, extracted_at)
                        VALUES (:id, :source_id, :subject_id, :relation_type, :object_id, :confidence_score, :extraction_model, :extracted_at)
                        ON CONFLICT (id) DO NOTHING
                    """),
                    claim.model_dump(mode='json')
                )
                session.commit()
        except Exception as e:
            logger.error("audit_log_failed", error=str(e))
            raise StorageError(f"Failed to log claim: {e}")
