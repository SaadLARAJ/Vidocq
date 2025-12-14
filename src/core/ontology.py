# src/core/ontology.py
# ShadowMap Investigation Ontology v2.0
# Multi-Domain: Supply Chain, Finance, Influence, Geopolitics, Disinformation

# =============================================================================
# ENTITY TYPES - What can be investigated
# =============================================================================

ALLOWED_ENTITY_TYPES = [
    # Core Actors
    "PERSON",           # Individual (CEO, politician, journalist, activist)
    "ORGANIZATION",     # Company, NGO, Government Agency, Political Party
    "GOVERNMENT",       # State actor (Ministry, Agency, Embassy)
    
    # Geographic
    "COUNTRY",
    "CITY",
    "REGION",           # Disputed territory, economic zone
    
    # Financial
    "BANK",             # Financial institution
    "SHELL_COMPANY",    # Suspected shell/offshore entity
    "FUND",             # Investment fund, hedge fund, sovereign wealth fund
    "CRYPTO_WALLET",    # Blockchain address
    
    # Media & Influence
    "MEDIA_OUTLET",     # News org, TV channel, website
    "SOCIAL_ACCOUNT",   # Twitter/X, Telegram, Facebook page
    "THINK_TANK",       # Policy institute, research org
    
    # Legal & Events
    "LAWSUIT",          # Legal case
    "SANCTION",         # Sanctions package
    "EVENT",            # Conference, meeting, incident
    
    # Assets
    "PROPERTY",         # Real estate, yacht, aircraft
    "PRODUCT",          # Specific product line
]

# =============================================================================
# RELATION TYPES - How entities connect
# =============================================================================

ALLOWED_RELATIONS = [
    # === OWNERSHIP & CONTROL ===
    "OWNS",                 # Direct ownership
    "CONTROLS",             # Control without ownership (voting rights, board)
    "BENEFICIAL_OWNER_OF",  # Ultimate beneficial owner (UBO)
    "SHAREHOLDER_OF",       # Minority stake
    "SUBSIDIARY_OF",        # Parent-child company
    "SHELL_FOR",            # Shell company relationship
    
    # === FINANCIAL ===
    "FUNDS",                # Financial support
    "INVESTED_IN",          # Investment
    "TRANSACTED_WITH",      # Financial transaction
    "RECEIVED_PAYMENT_FROM",# Incoming funds
    "LAUNDERS_THROUGH",     # Suspected money laundering
    
    # === SUPPLY CHAIN ===
    "SUPPLIES",             # Confirmed supplier
    "POTENTIALLY_SUPPLIES", # Suspected supplier
    "MANUFACTURES",         # Production
    "OUTSOURCES_TO",        # Subcontracting
    "DEPENDS_ON",           # Critical dependency
    
    # === EMPLOYMENT & ASSOCIATION ===
    "EMPLOYS",
    "EMPLOYED_BY",
    "BOARD_MEMBER_OF",      # Board/governance role
    "ADVISOR_TO",
    "FAMILY_OF",
    "ASSOCIATE_OF",         # Known associate
    
    # === INFLUENCE & POLITICS ===
    "LOBBIES",              # Lobbying activity
    "DONATES_TO",           # Political/charitable donation
    "AFFILIATED_WITH",      # Political affiliation
    "INFLUENCES",           # Influence relationship
    "PATRON_OF",            # Patronage
    
    # === MEDIA & DISINFORMATION ===
    "PUBLISHES",            # Media publishing
    "AMPLIFIES",            # Amplifies content/narrative
    "PROPAGATES",           # Spreads (disinformation)
    "QUOTES",               # Cites as source
    "COORDINATES_WITH",     # Coordinated activity
    "FUNDED_BY",            # Media funding source
    
    # === LEGAL & CONFLICT ===
    "SUED_BY",
    "SANCTIONED_BY",
    "OPPOSES",
    "ALLIES_WITH",
    "CONFLICTS_WITH",
    
    # === GEOGRAPHIC ===
    "LOCATED_IN",
    "OPERATES_IN",
    "HEADQUARTERED_IN",
    "REGISTERED_IN",        # Legal registration (often offshore)
    "MANUFACTURES_IN",
    
    # === TEMPORAL ===
    "FORMERLY",             # Past relationship (use with other relation)
    "SINCE",                # Start date marker
    
    # === FALLBACK ===
    "RELATED_TO",           # Unspecified relationship
    "MENTIONED_WITH",       # Co-occurrence without clear relation
]

# =============================================================================
# INVESTIGATION MODES - Types of investigations the agent can run
# =============================================================================

INVESTIGATION_MODES = {
    "UBO_TRACE": {
        "description": "Trace ultimate beneficial owners through corporate structures",
        "target_relations": ["BENEFICIAL_OWNER_OF", "OWNS", "CONTROLS", "SHELL_FOR", "SHAREHOLDER_OF"],
        "keywords": ["beneficial owner", "shareholder", "ownership structure", "offshore", "nominee director"]
    },
    "DISINFO_TRACE": {
        "description": "Map disinformation networks and propagators",
        "target_relations": ["AMPLIFIES", "PROPAGATES", "COORDINATES_WITH", "FUNDED_BY", "PUBLISHES"],
        "keywords": ["fake news", "disinformation", "propaganda", "troll farm", "bot network", "state media"]
    },
    "MONEY_FLOW": {
        "description": "Track suspicious financial flows",
        "target_relations": ["TRANSACTED_WITH", "FUNDS", "LAUNDERS_THROUGH", "RECEIVED_PAYMENT_FROM"],
        "keywords": ["money laundering", "wire transfer", "shell company", "offshore account", "sanctions evasion"]
    },
    "INFLUENCE_MAP": {
        "description": "Map political and lobbying influence networks",
        "target_relations": ["LOBBIES", "DONATES_TO", "INFLUENCES", "ADVISOR_TO", "AFFILIATED_WITH"],
        "keywords": ["lobbying", "political donation", "revolving door", "think tank", "policy influence"]
    },
    "SUPPLY_CHAIN": {
        "description": "Map supply chain dependencies and risks",
        "target_relations": ["SUPPLIES", "MANUFACTURES", "DEPENDS_ON", "OUTSOURCES_TO"],
        "keywords": ["supplier", "manufacturer", "factory", "raw materials", "logistics"]
    },
    "SANCTION_EXPOSURE": {
        "description": "Identify exposure to sanctioned entities",
        "target_relations": ["SANCTIONED_BY", "TRANSACTED_WITH", "SUPPLIES", "CONTROLS"],
        "keywords": ["sanctions", "OFAC", "EU sanctions", "designated entity", "blocked person"]
    }
}

# Risk indicators for automatic flagging
HIGH_RISK_JURISDICTIONS = [
    "RUSSIA", "IRAN", "NORTH KOREA", "SYRIA", "VENEZUELA", "BELARUS", "MYANMAR",
    "CAYMAN ISLANDS", "BRITISH VIRGIN ISLANDS", "PANAMA", "SEYCHELLES", "CYPRUS"
]
