# src/core/ontology.py

ALLOWED_ENTITY_TYPES = [
    "PERSON",
    "ORGANIZATION", 
    "CITY",
    "COUNTRY",
    "EVENT",
    "CRYPTO_WALLET",
    "DOCUMENT"
]

ALLOWED_RELATIONS = [
    "OWNS",           # Propriété
    "FUNDS",          # Financement
    "EMPLOYS",        # Emploi
    "PARTNERS_WITH",  # Partenariat
    "OPPOSES",        # Opposition/Conflit
    "FAMILY_OF",      # Lien familial
    "ATTENDED",       # Participation événement
    "ACQUIRED",       # Acquisition
    "MET_WITH",       # Rencontre
    "INVESTED_IN",    # Investissement
    "CONTROLS",       # Contrôle
    
    # Core Supply Chain & Geo
    "MANUFACTURES",   # Fabrication
    "SUPPLIES",       # Fourniture
    "OUTSOURCES_TO",  # Sous-traitance
    "COMPONENT_OF",   # Composant de
    "LOCATED_IN",     # Localisation générique (si ville/pays non identifiable)
    "OPERATES_IN",    # Présence opérationnelle dans un lieu
    "MANUFACTURES_IN",# Usine ou fabrication dans un lieu

    # Nuanced & Speculative Relations
    "POTENTIALLY_SUPPLIES",
    "EXPLORING_MARKET",
    "REPORTEDLY_OPERATES_IN",
    
    # Fallback
    "RELATED_TO"      
]
