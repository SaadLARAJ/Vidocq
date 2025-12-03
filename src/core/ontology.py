# src/core/ontology.py

ALLOWED_ENTITY_TYPES = [
    "PERSON",
    "ORGANIZATION", 
    "LOCATION",
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
    "LOCATED_IN",     # Localisation
    "ATTENDED",       # Participation événement
    "ACQUIRED",       # Acquisition
    "MET_WITH",       # Rencontre
    "INVESTED_IN",    # Investissement
    "CONTROLS"        # Contrôle
]
