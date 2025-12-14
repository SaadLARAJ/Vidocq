"""
VIDOCQ - Doctrine Française de Renseignement
Base de connaissances pour l'entraînement du modèle.

Ce fichier contient la "doctrine" - les règles de renseignement français
que le modèle doit apprendre AVANT les données utilisateur.

Sources:
- LPM (Loi de Programmation Militaire)
- DGSI/DGSE guidelines publiques
- Secteurs OIV/OSE
- Listes de sanctions (OFAC, EU)
"""

from typing import Dict, List, Any
from pydantic import BaseModel


class DoctrineExample(BaseModel):
    """Un exemple d'entraînement basé sur la doctrine"""
    input_text: str
    expected_output: Dict[str, Any]
    category: str  # CRITICAL_SECTOR, HOSTILE_ACTOR, SUPPLY_RISK, etc.
    source: str = "doctrine_fr"


class FrenchDoctrine:
    """
    La Doctrine Française de Renseignement Économique.
    
    Ces données servent à pré-entraîner le modèle AVANT
    les corrections utilisateur. Le modèle apprend:
    
    1. Quels secteurs sont critiques (OIV/OSE)
    2. Quels pays/entités sont hostiles
    3. Quelles relations sont suspectes
    4. Quelle terminologie utiliser
    """
    
    # ============================================
    # SECTEURS CRITIQUES (OIV - Opérateurs d'Importance Vitale)
    # ============================================
    
    CRITICAL_SECTORS = {
        "defense": {
            "keywords": ["armement", "défense", "militaire", "missile", "nucléaire", "sous-marin"],
            "companies": ["Thales", "Dassault", "Naval Group", "MBDA", "Safran", "Nexter"],
            "risk_level": "CRITICAL"
        },
        "nuclear": {
            "keywords": ["nucléaire", "uranium", "réacteur", "CEA", "Framatome"],
            "companies": ["EDF", "Orano", "Framatome", "CEA"],
            "risk_level": "CRITICAL"
        },
        "aerospace": {
            "keywords": ["aérospatial", "satellite", "lanceur", "Ariane"],
            "companies": ["Airbus", "ArianeGroup", "Thales Alenia Space"],
            "risk_level": "CRITICAL"
        },
        "telecom": {
            "keywords": ["télécommunications", "5G", "réseau", "câble sous-marin"],
            "companies": ["Orange", "Bouygues Telecom", "SFR", "Alcatel"],
            "risk_level": "HIGH"
        },
        "energy": {
            "keywords": ["énergie", "électricité", "gaz", "pétrole", "renouvelable"],
            "companies": ["EDF", "Engie", "TotalEnergies", "RTE"],
            "risk_level": "HIGH"
        },
        "health": {
            "keywords": ["santé", "pharmaceutique", "vaccin", "hôpital"],
            "companies": ["Sanofi", "Servier", "BioMérieux"],
            "risk_level": "HIGH"
        },
        "semiconductor": {
            "keywords": ["semiconducteur", "puce", "microprocesseur", "silicium"],
            "companies": ["STMicroelectronics", "Soitec", "Crolles"],
            "risk_level": "CRITICAL"
        }
    }
    
    # ============================================
    # ACTEURS HOSTILES (selon doctrine FR)
    # ============================================
    
    HOSTILE_ACTORS = {
        "russia": {
            "indicators": ["Kremlin", "FSB", "GRU", "Rosneft", "Gazprom", "Sberbank"],
            "state_media": ["RT", "Sputnik", "TASS", "RIA Novosti"],
            "oligarchs_patterns": ["sanctionné", "proche de Poutine", "yacht", "Londres"],
            "risk_level": "HIGH"
        },
        "china": {
            "indicators": ["PCC", "APL", "MSS", "Huawei", "ZTE", "CRRC"],
            "state_companies": ["COSCO", "China Mobile", "CNOOC", "Sinopec"],
            "belt_road": ["Nouvelle Route de la Soie", "BRI", "port stratégique"],
            "risk_level": "HIGH"
        },
        "iran": {
            "indicators": ["IRGC", "Pasdaran", "Hezbollah", "sanctions OFAC"],
            "companies": ["NIOC", "Bank Melli", "IRGC-linked"],
            "risk_level": "HIGH"
        },
        "north_korea": {
            "indicators": ["DPRK", "RGB", "Lazarus", "crypto theft"],
            "risk_level": "CRITICAL"
        }
    }
    
    # ============================================
    # JURIDICTIONS À RISQUE (Offshore)
    # ============================================
    
    RISKY_JURISDICTIONS = {
        "high_risk": [
            "British Virgin Islands", "Îles Caïmans", "Panama", 
            "Seychelles", "Belize", "Îles Marshall"
        ],
        "medium_risk": [
            "Luxembourg", "Irlande", "Pays-Bas", "Malte", 
            "Chypre", "Émirats Arabes Unis", "Singapour"
        ],
        "patterns": [
            "société holding", "beneficial owner", "nominee director",
            "trust", "fondation", "shell company"
        ]
    }
    
    # ============================================
    # RELATIONS SUSPECTES
    # ============================================
    
    SUSPICIOUS_RELATIONS = {
        "ownership": [
            "BENEFICIAL_OWNER_OF", "CONTROLS", "SHELL_COMPANY",
            "NOMINEE_FOR", "TRUST_BENEFICIARY"
        ],
        "financial": [
            "LAUNDERS_THROUGH", "HIDDEN_PAYMENT", "SANCTIONS_EVASION",
            "OVERINVOICING", "UNDERINVOICING"
        ],
        "influence": [
            "CORRUPTS", "BRIBES", "LOBBIES_FOR", "PROPAGANDA_FOR",
            "KOMPROMAT_ON"
        ],
        "supply_chain": [
            "SINGLE_SOURCE", "CONFLICT_MINERAL", "FORCED_LABOR",
            "SANCTION_CIRCUMVENTION"
        ]
    }
    
    # ============================================
    # EXEMPLES D'ENTRAÎNEMENT
    # ============================================
    
    def generate_training_examples(self) -> List[DoctrineExample]:
        """
        Génère des exemples d'entraînement basés sur la doctrine.
        Ces exemples enseignent au modèle:
        - Comment identifier les secteurs critiques
        - Comment détecter les acteurs hostiles
        - Comment interpréter les relations suspectes
        """
        examples = []
        
        # --- Exemples Secteurs Critiques ---
        for sector, data in self.CRITICAL_SECTORS.items():
            for company in data["companies"]:
                examples.append(DoctrineExample(
                    input_text=f"{company} est une entreprise française du secteur {sector}.",
                    expected_output={
                        "entities": [
                            {"name": company, "type": "ORGANIZATION", "sector": sector}
                        ],
                        "risk_level": data["risk_level"],
                        "flags": ["CRITICAL_SECTOR", "OIV_PROTECTED"]
                    },
                    category="CRITICAL_SECTOR"
                ))
        
        # --- Exemples Acteurs Hostiles ---
        for country, data in self.HOSTILE_ACTORS.items():
            for indicator in data["indicators"]:
                examples.append(DoctrineExample(
                    input_text=f"{indicator} est lié au gouvernement {country}.",
                    expected_output={
                        "entities": [
                            {"name": indicator, "type": "ORGANIZATION", "country": country}
                        ],
                        "risk_level": data["risk_level"],
                        "flags": ["HOSTILE_ACTOR", f"STATE_LINKED_{country.upper()}"]
                    },
                    category="HOSTILE_ACTOR"
                ))
        
        # --- Exemples Relations Suspectes ---
        examples.append(DoctrineExample(
            input_text="La société ABC Holdings aux Îles Caïmans détient 100% de XYZ France.",
            expected_output={
                "entities": [
                    {"name": "ABC Holdings", "type": "SHELL_COMPANY", "jurisdiction": "Cayman Islands"},
                    {"name": "XYZ France", "type": "ORGANIZATION", "country": "France"}
                ],
                "relations": [
                    {"source": "ABC Holdings", "target": "XYZ France", "type": "BENEFICIAL_OWNER_OF"}
                ],
                "risk_level": "HIGH",
                "flags": ["OFFSHORE_STRUCTURE", "OPACITY_RISK"]
            },
            category="SUSPICIOUS_OWNERSHIP"
        ))
        
        examples.append(DoctrineExample(
            input_text="RT France a publié un article reprenant les arguments du Kremlin.",
            expected_output={
                "entities": [
                    {"name": "RT France", "type": "MEDIA_OUTLET", "origin": "HOSTILE"},
                    {"name": "Kremlin", "type": "GOVERNMENT", "country": "Russia"}
                ],
                "relations": [
                    {"source": "RT France", "target": "Kremlin", "type": "PROPAGANDA_FOR"}
                ],
                "risk_level": "MEDIUM",
                "flags": ["INFLUENCE_OPERATION", "STATE_MEDIA"]
            },
            category="INFLUENCE_OPERATION"
        ))
        
        examples.append(DoctrineExample(
            input_text="L'usine de Safran dépend à 80% de composants chinois fournis par CRRC.",
            expected_output={
                "entities": [
                    {"name": "Safran", "type": "ORGANIZATION", "sector": "defense"},
                    {"name": "CRRC", "type": "ORGANIZATION", "country": "China"}
                ],
                "relations": [
                    {"source": "Safran", "target": "CRRC", "type": "DEPENDS_ON"}
                ],
                "risk_level": "CRITICAL",
                "flags": ["SUPPLY_CHAIN_VULNERABILITY", "HOSTILE_DEPENDENCY", "SINGLE_SOURCE"]
            },
            category="SUPPLY_RISK"
        ))
        
        # --- Exemples Sanctions ---
        examples.append(DoctrineExample(
            input_text="Igor Sechin, CEO de Rosneft, a été sanctionné par l'OFAC en 2022.",
            expected_output={
                "entities": [
                    {"name": "Igor Sechin", "type": "PERSON", "role": "CEO"},
                    {"name": "Rosneft", "type": "ORGANIZATION", "country": "Russia"}
                ],
                "relations": [
                    {"source": "Igor Sechin", "target": "Rosneft", "type": "LEADS"}
                ],
                "risk_level": "CRITICAL",
                "flags": ["SANCTIONED_INDIVIDUAL", "OFAC_SDN", "DO_NOT_TRANSACT"]
            },
            category="SANCTIONS"
        ))
        
        return examples
    
    def export_for_training(self, output_path: str = "data/doctrine/training_doctrine.jsonl"):
        """Exporte la doctrine en format JSONL pour entraînement"""
        import json
        import os
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        examples = self.generate_training_examples()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for ex in examples:
                f.write(ex.model_dump_json() + '\n')
        
        return {
            "examples_count": len(examples),
            "output_path": output_path,
            "categories": list(set(ex.category for ex in examples))
        }


# Export singleton
DOCTRINE = FrenchDoctrine()
