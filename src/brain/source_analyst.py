"""
VIDOCQ BRAIN - Source Intelligence Module
Classifies sources by geographic origin and detects information warfare.
"""

from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from urllib.parse import urlparse
import re

from src.core.logging import get_logger

logger = get_logger(__name__)


class SourceOrigin(str, Enum):
    """Geographic classification of information sources"""
    WESTERN = "WESTERN"       # US, EU, UK, etc.
    HOSTILE = "HOSTILE"       # CN, RU, IR, etc.
    LOCAL = "LOCAL"           # Target country specific
    NEUTRAL = "NEUTRAL"       # International orgs, etc.
    UNKNOWN = "UNKNOWN"


class SourceAnalysis(BaseModel):
    """Analysis result for a source"""
    url: str
    domain: str
    tld: str
    origin: SourceOrigin
    confidence: float = Field(ge=0, le=1)
    language_detected: Optional[str] = None
    bias_indicators: List[str] = []
    trust_score: float = Field(ge=0, le=1, default=0.5)


class SourceIntelligence:
    """
    Analyzes sources by geographic origin.
    
    This allows reports to say:
    "Western sources claim X, but Russian sources claim Y"
    
    Essential for detecting information warfare and propaganda.
    """
    
    def __init__(self):
        # TLD to country mapping
        self.tld_countries = {
            # Western (Five Eyes + EU)
            ".com": "US", ".us": "US", ".gov": "US",
            ".uk": "UK", ".co.uk": "UK",
            ".fr": "FR", ".de": "DE", ".it": "IT", ".es": "ES",
            ".eu": "EU", ".nl": "NL", ".be": "BE", ".ch": "CH",
            ".ca": "CA", ".au": "AU", ".nz": "NZ",
            ".jp": "JP", ".kr": "KR",
            
            # Hostile/Adversarial
            ".ru": "RU", ".su": "RU",
            ".cn": "CN", ".hk": "HK",
            ".ir": "IR",
            ".by": "BY", ".kp": "KP",
            
            # Neutral
            ".org": "INTL", ".int": "INTL",
            ".edu": "ACADEMIC",
        }
        
        # Country to bloc mapping
        self.country_blocs = {
            "WESTERN": ["US", "UK", "FR", "DE", "IT", "ES", "EU", "NL", "BE", 
                       "CH", "CA", "AU", "NZ", "JP", "KR"],
            "HOSTILE": ["RU", "CN", "IR", "BY", "KP"],
            "NEUTRAL": ["INTL", "ACADEMIC"]
        }
        
        # Known state media / propaganda outlets
        self.state_media = {
            "rt.com": ("RU", "state_media"),
            "sputniknews.com": ("RU", "state_media"),
            "tass.com": ("RU", "state_media"),
            "xinhuanet.com": ("CN", "state_media"),
            "chinadaily.com.cn": ("CN", "state_media"),
            "globaltimes.cn": ("CN", "state_media"),
            "presstv.ir": ("IR", "state_media"),
            "aljazeera.com": ("QA", "state_media"),
            "bbc.com": ("UK", "public_media"),
            "bbc.co.uk": ("UK", "public_media"),
            "france24.com": ("FR", "public_media"),
            "dw.com": ("DE", "public_media"),
            "voanews.com": ("US", "state_funded"),
            "rferl.org": ("US", "state_funded"),
        }
        
        # High-trust sources
        self.trusted_sources = {
            "reuters.com": 0.9,
            "apnews.com": 0.9,
            "ft.com": 0.85,
            "wsj.com": 0.8,
            "nytimes.com": 0.8,
            "theguardian.com": 0.75,
            "lemonde.fr": 0.8,
            "spiegel.de": 0.8,
            "opensanctions.org": 0.95,
            "icij.org": 0.95,
            "occrp.org": 0.9,
        }
    
    def analyze_source(self, url: str, content: Optional[str] = None) -> SourceAnalysis:
        """
        Analyze a source URL to determine its geographic origin and reliability.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            
            # Get TLD
            tld = self._extract_tld(domain)
            
            # Determine country
            country = self._get_country(domain, tld)
            
            # Determine bloc
            origin = self._get_origin(domain, country)
            
            # Get trust score
            trust_score = self._get_trust_score(domain)
            
            # Get bias indicators
            bias_indicators = self._get_bias_indicators(domain)
            
            # Detect language if content provided
            language = None
            if content:
                language = self._detect_language(content)
            
            return SourceAnalysis(
                url=url,
                domain=domain,
                tld=tld,
                origin=origin,
                confidence=0.8 if country != "UNKNOWN" else 0.3,
                language_detected=language,
                bias_indicators=bias_indicators,
                trust_score=trust_score
            )
            
        except Exception as e:
            logger.warning("source_analysis_failed", url=url, error=str(e))
            return SourceAnalysis(
                url=url,
                domain="unknown",
                tld="unknown",
                origin=SourceOrigin.UNKNOWN,
                confidence=0.0
            )
    
    def _extract_tld(self, domain: str) -> str:
        """Extract TLD from domain"""
        parts = domain.split(".")
        if len(parts) >= 2:
            # Handle .co.uk style TLDs
            if parts[-2] in ["co", "com", "org", "gov"] and len(parts) >= 3:
                return f".{parts[-2]}.{parts[-1]}"
            return f".{parts[-1]}"
        return ".unknown"
    
    def _get_country(self, domain: str, tld: str) -> str:
        """Determine source country"""
        # First check known domains
        if domain in self.state_media:
            return self.state_media[domain][0]
        
        # Then check TLD
        return self.tld_countries.get(tld, "UNKNOWN")
    
    def _get_origin(self, domain: str, country: str) -> SourceOrigin:
        """Determine geographic bloc"""
        # Check known state media first
        if domain in self.state_media:
            country = self.state_media[domain][0]
        
        for bloc, countries in self.country_blocs.items():
            if country in countries:
                if bloc == "WESTERN":
                    return SourceOrigin.WESTERN
                elif bloc == "HOSTILE":
                    return SourceOrigin.HOSTILE
                elif bloc == "NEUTRAL":
                    return SourceOrigin.NEUTRAL
        
        return SourceOrigin.UNKNOWN
    
    def _get_trust_score(self, domain: str) -> float:
        """Get trust score for domain"""
        # Known trusted sources
        if domain in self.trusted_sources:
            return self.trusted_sources[domain]
        
        # State media gets lower trust
        if domain in self.state_media:
            media_type = self.state_media[domain][1]
            if media_type == "state_media":
                return 0.3
            elif media_type == "state_funded":
                return 0.5
            else:
                return 0.6
        
        # Default trust
        return 0.5
    
    def _get_bias_indicators(self, domain: str) -> List[str]:
        """Get bias/reliability indicators for source"""
        indicators = []
        
        if domain in self.state_media:
            country, media_type = self.state_media[domain]
            indicators.append(f"{media_type.upper()}")
            indicators.append(f"COUNTRY:{country}")
        
        if domain in self.trusted_sources:
            indicators.append("HIGH_CREDIBILITY")
        
        return indicators
    
    def _detect_language(self, content: str) -> Optional[str]:
        """Simple language detection from content"""
        # Very basic detection based on common words
        content_lower = content.lower()[:5000]
        
        lang_patterns = {
            "en": ["the", "and", "is", "are", "was", "were"],
            "fr": ["le", "la", "les", "est", "sont", "pour"],
            "de": ["der", "die", "das", "ist", "und", "für"],
            "ru": ["и", "в", "на", "что", "это"],
            "zh": ["的", "是", "了", "在", "有"],
        }
        
        scores = {}
        for lang, patterns in lang_patterns.items():
            scores[lang] = sum(1 for p in patterns if f" {p} " in content_lower)
        
        if max(scores.values()) > 2:
            return max(scores, key=scores.get)
        
        return None
    
    def cluster_by_origin(
        self, 
        sources: List[str]
    ) -> Dict[SourceOrigin, List[SourceAnalysis]]:
        """
        Cluster multiple sources by their geographic origin.
        Returns grouped sources for comparative analysis.
        """
        clusters = {origin: [] for origin in SourceOrigin}
        
        for url in sources:
            analysis = self.analyze_source(url)
            clusters[analysis.origin].append(analysis)
        
        return clusters
    
    def generate_source_report(
        self,
        clusters: Dict[SourceOrigin, List[SourceAnalysis]]
    ) -> str:
        """
        Generate a summary of source distribution.
        """
        lines = ["## Source Intelligence Analysis\n"]
        
        total = sum(len(v) for v in clusters.values())
        
        for origin in [SourceOrigin.WESTERN, SourceOrigin.HOSTILE, 
                       SourceOrigin.NEUTRAL, SourceOrigin.UNKNOWN]:
            sources = clusters.get(origin, [])
            if sources:
                pct = len(sources) / total * 100 if total > 0 else 0
                lines.append(f"### {origin.value} Sources ({len(sources)} - {pct:.0f}%)")
                
                for s in sources[:5]:  # Show top 5
                    trust = "🟢" if s.trust_score > 0.7 else "🟡" if s.trust_score > 0.4 else "🔴"
                    lines.append(f"- {trust} {s.domain} (trust: {s.trust_score:.1f})")
                
                if len(sources) > 5:
                    lines.append(f"- ... and {len(sources) - 5} more")
                lines.append("")
        
        return "\n".join(lines)
