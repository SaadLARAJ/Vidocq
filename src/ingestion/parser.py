from unstructured.partition.html import partition_html
from unstructured.cleaners.core import clean, replace_unicode_quotes
from src.core.logging import get_logger
from src.core.exceptions import ParsingError

logger = get_logger(__name__)

class ContentParser:
    """Parses and cleans raw content (HTML, etc.) into text."""
    
    @staticmethod
    def parse_html(html_content: str) -> str:
        """
        Extract clean text from HTML.
        """
        try:
            # 1. BeautifulSoup Pre-cleaning (Strip structure)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            cleaned_html = str(soup)

            # 2. Unstructured Partitioning
            elements = partition_html(text=cleaned_html)
            text = "\n\n".join([str(el) for el in elements])
            
            # Cleaning pipeline
            cleaned_text = clean(
                text,
                bullets=True,
                extra_whitespace=True,
                dashes=True,
                trailing_punctuation=True
            )
            cleaned_text = replace_unicode_quotes(cleaned_text)
            
            return cleaned_text
        except Exception as e:
            logger.error("parsing_failed", error=str(e))
            raise ParsingError(f"Failed to parse HTML content: {e}")
