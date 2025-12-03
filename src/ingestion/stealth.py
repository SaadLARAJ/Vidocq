import time
import random
import requests
from fake_useragent import UserAgent
from src.config import settings
from src.core.logging import get_logger
from src.core.exceptions import SourceUnreachableError

logger = get_logger(__name__)

class StealthSession:
    """
    OpSec-compliant HTTP session wrapper.
    Enforces:
    - Random User-Agent rotation
    - Jitter (random sleep) between requests
    - No naked requests (always uses session with headers)
    """
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self._rotate_ua()
        
    def _rotate_ua(self):
        """Rotate User-Agent header."""
        new_ua = self.ua.random
        self.session.headers.update({
            "User-Agent": new_ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
        logger.debug("user_agent_rotated", user_agent=new_ua)

    def _apply_jitter(self):
        """Sleep for a random duration between JITTER_MIN and JITTER_MAX."""
        sleep_time = random.uniform(settings.JITTER_MIN, settings.JITTER_MAX)
        logger.debug("applying_jitter", duration=sleep_time)
        time.sleep(sleep_time)

    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Execute a GET request with OpSec protections.
        """
        self._apply_jitter()
        self._rotate_ua()
        
        try:
            response = self.session.get(url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.warning("request_failed", url=url, error=str(e))
            raise SourceUnreachableError(f"Failed to fetch {url}: {e}")

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
