import io
from src.core.logging import get_logger

logger = get_logger(__name__)

class PDFParser:
    """
    Extracts text from PDF binary content.
    Uses pypdf if available.
    """
    
    @staticmethod
    def parse_pdf(pdf_bytes: bytes) -> str:
        text_content = []
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
            
            full_text = "\n".join(text_content)
            logger.info("pdf_parsed_success", length=len(full_text))
            return full_text

        except ImportError:
            logger.warning("pypdf_missing_skipping_pdf")
            return "[ERROR: pypdf not installed. Cannot parse PDF.]"
        except Exception as e:
            logger.error("pdf_parsing_error", error=str(e))
            return ""
