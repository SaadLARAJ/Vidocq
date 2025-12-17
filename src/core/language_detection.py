"""
VIDOCQ - LLM-based Language Detection
Accurate language detection using Gemini LLM.

Replaces simple heuristics with proper multilingual detection.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import google.generativeai as genai

from src.core.logging import get_logger
from src.config import settings

logger = get_logger(__name__)


class LanguageDetectionResult(BaseModel):
    """Result of language detection"""
    primary_language: str = Field(description="Primary language code (ISO 639-1)")
    primary_language_name: str = Field(description="Full language name")
    confidence: float = Field(ge=0, le=1, description="Detection confidence")
    secondary_languages: List[str] = Field(default=[], description="Other languages detected")
    is_multilingual: bool = Field(default=False, description="Contains multiple languages")
    script: Optional[str] = Field(default=None, description="Writing script (Latin, Cyrillic, etc.)")
    

class LanguageDetector:
    """
    LLM-based language detection for accurate multilingual content analysis.
    
    Uses Gemini to analyze text and determine:
    1. Primary language
    2. Secondary languages (for mixed-language content)
    3. Writing script
    4. Confidence level
    """
    
    # Fallback patterns for when LLM is unavailable
    SCRIPT_PATTERNS = {
        "cyrillic": "абвгдежзийклмнопрстуфхцчшщъыьэюя",
        "chinese": "的是不了在人有我他这中大来上国和",
        "arabic": "ابتثجحخدذرزسشصضطظعغفقكلمنهوي",
        "japanese_hiragana": "あいうえおかきくけこさしすせそ",
        "japanese_katakana": "アイウエオカキクケコサシスセソ",
        "korean": "가나다라마바사아자차카타파하",
        "greek": "αβγδεζηθικλμνξοπρστυφχψω",
    }
    
    # Language hints from common words
    LANGUAGE_HINTS = {
        "fr": ["le", "la", "les", "de", "du", "des", "en", "est", "sont", "pour", "avec"],
        "de": ["der", "die", "das", "und", "ist", "von", "mit", "für", "auf", "ein"],
        "es": ["el", "la", "los", "las", "de", "del", "en", "es", "para", "con"],
        "it": ["il", "la", "di", "che", "in", "per", "con", "una", "sono", "questo"],
        "pt": ["o", "a", "os", "as", "de", "do", "da", "em", "para", "com"],
        "ru": ["и", "в", "на", "с", "что", "не", "это", "как", "по", "из"],
        "zh": ["的", "是", "在", "有", "和", "了", "不", "这", "中", "人"],
        "ja": ["の", "は", "に", "を", "が", "と", "で", "た", "です", "ます"],
        "ar": ["في", "من", "على", "إلى", "عن", "مع", "هذا", "التي", "الذي"],
    }
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = None
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as e:
                logger.warning("language_detector_llm_init_failed", error=str(e))
    
    async def detect(self, text: str) -> LanguageDetectionResult:
        """
        Detect language of text using LLM.
        
        Falls back to heuristics if LLM unavailable.
        """
        if not text or len(text.strip()) < 10:
            return LanguageDetectionResult(
                primary_language="und",
                primary_language_name="Undetermined",
                confidence=0.0
            )
        
        # Try LLM detection first
        if self.model:
            try:
                return await self._detect_with_llm(text)
            except Exception as e:
                logger.warning("llm_language_detection_failed", error=str(e))
        
        # Fallback to heuristics
        return self._detect_with_heuristics(text)
    
    async def _detect_with_llm(self, text: str) -> LanguageDetectionResult:
        """Use Gemini LLM for accurate language detection."""
        
        # Take a sample if text is too long
        sample = text[:2000] if len(text) > 2000 else text
        
        prompt = f"""Analyze this text and detect the language(s).

TEXT:
{sample}

Return ONLY valid JSON:
{{
    "primary_language": "ISO 639-1 code (e.g., en, fr, ru, zh, ar)",
    "primary_language_name": "Full name (e.g., English, French)",
    "confidence": 0.0-1.0,
    "secondary_languages": ["list of other language codes if mixed"],
    "is_multilingual": true/false,
    "script": "Latin/Cyrillic/Chinese/Arabic/etc."
}}

Be precise. If multiple languages are present, list primary and secondary."""

        response = self.model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "max_output_tokens": 300}
        )
        
        import json
        text_response = response.text.strip()
        
        # Clean markdown code blocks
        if "```" in text_response:
            text_response = text_response.split("```")[1]
            if text_response.startswith("json"):
                text_response = text_response[4:]
        
        data = json.loads(text_response)
        
        return LanguageDetectionResult(
            primary_language=data.get("primary_language", "en"),
            primary_language_name=data.get("primary_language_name", "English"),
            confidence=data.get("confidence", 0.7),
            secondary_languages=data.get("secondary_languages", []),
            is_multilingual=data.get("is_multilingual", False),
            script=data.get("script")
        )
    
    def _detect_with_heuristics(self, text: str) -> LanguageDetectionResult:
        """Fallback heuristic-based detection."""
        
        text_lower = text.lower()
        
        # First, detect script
        script = self._detect_script(text)
        
        # Script-based language inference
        if script == "Cyrillic":
            return LanguageDetectionResult(
                primary_language="ru",
                primary_language_name="Russian",
                confidence=0.7,
                script=script
            )
        elif script == "Chinese":
            return LanguageDetectionResult(
                primary_language="zh",
                primary_language_name="Chinese",
                confidence=0.7,
                script=script
            )
        elif script == "Arabic":
            return LanguageDetectionResult(
                primary_language="ar",
                primary_language_name="Arabic",
                confidence=0.6,
                script=script
            )
        elif script in ("Japanese_Hiragana", "Japanese_Katakana"):
            return LanguageDetectionResult(
                primary_language="ja",
                primary_language_name="Japanese",
                confidence=0.7,
                script="Japanese"
            )
        elif script == "Korean":
            return LanguageDetectionResult(
                primary_language="ko",
                primary_language_name="Korean",
                confidence=0.7,
                script=script
            )
        
        # For Latin-script languages, use word frequency
        lang_scores = {}
        words = text_lower.split()
        
        for lang, hints in self.LANGUAGE_HINTS.items():
            if lang in ("ru", "zh", "ja", "ar"):  # Skip non-Latin
                continue
            score = sum(1 for word in words if word in hints)
            if score > 0:
                lang_scores[lang] = score
        
        if lang_scores:
            best_lang = max(lang_scores, key=lang_scores.get)
            lang_names = {
                "fr": "French", "de": "German", "es": "Spanish",
                "it": "Italian", "pt": "Portuguese"
            }
            return LanguageDetectionResult(
                primary_language=best_lang,
                primary_language_name=lang_names.get(best_lang, best_lang),
                confidence=min(0.7, lang_scores[best_lang] / 10),
                script="Latin"
            )
        
        # Default to English
        return LanguageDetectionResult(
            primary_language="en",
            primary_language_name="English",
            confidence=0.5,
            script="Latin"
        )
    
    def _detect_script(self, text: str) -> str:
        """Detect the writing script of text."""
        for script_name, chars in self.SCRIPT_PATTERNS.items():
            if any(c in text.lower() for c in chars):
                return script_name.replace("_", " ").title()
        return "Latin"
    
    def detect_sync(self, text: str) -> LanguageDetectionResult:
        """
        Synchronous language detection (heuristics only).
        Use `detect()` for async LLM-based detection.
        """
        return self._detect_with_heuristics(text)


# Singleton instance
LANGUAGE_DETECTOR = LanguageDetector()


async def detect_language(text: str) -> LanguageDetectionResult:
    """Convenience function for language detection."""
    return await LANGUAGE_DETECTOR.detect(text)


def detect_language_sync(text: str) -> LanguageDetectionResult:
    """Synchronous convenience function (heuristics only)."""
    return LANGUAGE_DETECTOR.detect_sync(text)
