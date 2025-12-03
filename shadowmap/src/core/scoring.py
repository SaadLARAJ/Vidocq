import math
from src.config import settings

class ConfidenceCalculator:
    """
    Moteur de calcul de confiance déterministe.
    Formule V4: C = min(0.99, (S × M) × (1 + log₁₀(N)/10))
    
    S = Source reliability (0-1)
    M = Method confidence (0-1)  
    N = Corroboration count (>= 1)
    """

    @staticmethod
    def compute(
        source_domain: str, 
        method: str, 
        corroboration_count: int = 1
    ) -> float:
        """
        Calcule le score de confiance d'une affirmation.
        
        Args:
            source_domain: Domaine de la source (ex: 'reuters.com')
            method: Méthode d'extraction (ex: 'gpt-4o')
            corroboration_count: Nombre de sources corroborant l'affirmation
            
        Returns:
            float: Score de confiance entre 0.0 et 0.99
        """
        s = settings.SOURCE_WEIGHTS.get(
            source_domain, 
            settings.SOURCE_WEIGHTS["DEFAULT"]
        )
        m = settings.METHOD_WEIGHTS.get(method, 0.5)
        
        base_score = s * m
        
        # Protection mathématique : count >= 1
        safe_count = max(1, corroboration_count)
        boost = 1.0 + (math.log10(safe_count) / 10.0)
        
        return min(0.99, base_score * boost)
