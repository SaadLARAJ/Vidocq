"""
ShadowMap Enterprise v4.0 - Closed Ontology

Defines the ONLY allowed entity types and relation types for extraction.
LLMs are constrained to extract ONLY these relations - no free-form relations allowed.

This prevents ontology drift and ensures consistent graph structure.
"""

from typing import Literal


# =============================================================================
# ENTITY TYPES (Closed Set)
# =============================================================================

ALLOWED_ENTITY_TYPES = [
    "PERSON",           # Individual human
    "ORGANIZATION",     # Company, government agency, NGO, criminal group
    "LOCATION",         # City, country, address, coordinates
    "EVENT",            # Meeting, attack, acquisition, conference
    "CRYPTO_WALLET",    # Cryptocurrency wallet address
    "DOCUMENT",         # Contract, report, leaked document
]

EntityType = Literal[
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "EVENT",
    "CRYPTO_WALLET",
    "DOCUMENT"
]


# =============================================================================
# RELATION TYPES (Closed Set)
# =============================================================================

ALLOWED_RELATIONS = [
    "OWNS",             # Entity A owns Entity B (property, company, asset)
    "FUNDS",            # Entity A provides funding to Entity B
    "EMPLOYS",          # Entity A employs Entity B
    "PARTNERS_WITH",    # Entity A has partnership/alliance with Entity B
    "OPPOSES",          # Entity A opposes/conflicts with Entity B
    "FAMILY_OF",        # Entity A has family relationship with Entity B
    "LOCATED_IN",       # Entity A is located in Location B
    "ATTENDED",         # Entity A attended Event B
    "ACQUIRED",         # Entity A acquired Entity B
    "MET_WITH",         # Entity A met with Entity B
    "INVESTED_IN",      # Entity A invested in Entity B
    "CONTROLS",         # Entity A has control over Entity B
]

RelationType = Literal[
    "OWNS",
    "FUNDS",
    "EMPLOYS",
    "PARTNERS_WITH",
    "OPPOSES",
    "FAMILY_OF",
    "LOCATED_IN",
    "ATTENDED",
    "ACQUIRED",
    "MET_WITH",
    "INVESTED_IN",
    "CONTROLS"
]


# =============================================================================
# RELATION TYPE CONSTRAINTS
# =============================================================================

# Maps relation types to allowed (subject_type, object_type) pairs
# Format: relation -> [(subject_type, object_type), ...]
RELATION_CONSTRAINTS: dict[str, list[tuple[str, str]]] = {
    "OWNS": [
        ("PERSON", "ORGANIZATION"),
        ("PERSON", "CRYPTO_WALLET"),
        ("ORGANIZATION", "ORGANIZATION"),
        ("ORGANIZATION", "CRYPTO_WALLET"),
    ],
    "FUNDS": [
        ("PERSON", "PERSON"),
        ("PERSON", "ORGANIZATION"),
        ("ORGANIZATION", "PERSON"),
        ("ORGANIZATION", "ORGANIZATION"),
        ("ORGANIZATION", "EVENT"),
    ],
    "EMPLOYS": [
        ("ORGANIZATION", "PERSON"),
    ],
    "PARTNERS_WITH": [
        ("PERSON", "PERSON"),
        ("ORGANIZATION", "ORGANIZATION"),
        ("PERSON", "ORGANIZATION"),
    ],
    "OPPOSES": [
        ("PERSON", "PERSON"),
        ("ORGANIZATION", "ORGANIZATION"),
        ("PERSON", "ORGANIZATION"),
    ],
    "FAMILY_OF": [
        ("PERSON", "PERSON"),
    ],
    "LOCATED_IN": [
        ("PERSON", "LOCATION"),
        ("ORGANIZATION", "LOCATION"),
        ("EVENT", "LOCATION"),
    ],
    "ATTENDED": [
        ("PERSON", "EVENT"),
        ("ORGANIZATION", "EVENT"),
    ],
    "ACQUIRED": [
        ("PERSON", "ORGANIZATION"),
        ("ORGANIZATION", "ORGANIZATION"),
    ],
    "MET_WITH": [
        ("PERSON", "PERSON"),
        ("PERSON", "ORGANIZATION"),
    ],
    "INVESTED_IN": [
        ("PERSON", "ORGANIZATION"),
        ("ORGANIZATION", "ORGANIZATION"),
    ],
    "CONTROLS": [
        ("PERSON", "ORGANIZATION"),
        ("ORGANIZATION", "ORGANIZATION"),
        ("PERSON", "CRYPTO_WALLET"),
    ],
}


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def is_valid_entity_type(entity_type: str) -> bool:
    """
    Check if an entity type is in the allowed ontology.

    Args:
        entity_type: Entity type to validate

    Returns:
        True if entity type is allowed, False otherwise

    Example:
        >>> is_valid_entity_type("PERSON")
        True
        >>> is_valid_entity_type("SPACESHIP")
        False
    """
    return entity_type in ALLOWED_ENTITY_TYPES


def is_valid_relation_type(relation_type: str) -> bool:
    """
    Check if a relation type is in the allowed ontology.

    Args:
        relation_type: Relation type to validate

    Returns:
        True if relation type is allowed, False otherwise

    Example:
        >>> is_valid_relation_type("OWNS")
        True
        >>> is_valid_relation_type("LIKES")
        False
    """
    return relation_type in ALLOWED_RELATIONS


def is_valid_relation_constraint(
    relation_type: str,
    subject_type: str,
    object_type: str
) -> bool:
    """
    Check if a relation respects type constraints.

    Args:
        relation_type: Type of relation
        subject_type: Type of subject entity
        object_type: Type of object entity

    Returns:
        True if the relation is valid for these entity types, False otherwise

    Example:
        >>> is_valid_relation_constraint("EMPLOYS", "ORGANIZATION", "PERSON")
        True
        >>> is_valid_relation_constraint("EMPLOYS", "PERSON", "ORGANIZATION")
        False  # Persons don't employ organizations in our ontology
    """
    if relation_type not in RELATION_CONSTRAINTS:
        return False

    allowed_pairs = RELATION_CONSTRAINTS[relation_type]
    return (subject_type, object_type) in allowed_pairs


def get_allowed_relations_for_types(
    subject_type: str,
    object_type: str
) -> list[str]:
    """
    Get all allowed relation types between two entity types.

    Args:
        subject_type: Type of subject entity
        object_type: Type of object entity

    Returns:
        List of allowed relation types

    Example:
        >>> get_allowed_relations_for_types("PERSON", "ORGANIZATION")
        ["OWNS", "FUNDS", "PARTNERS_WITH", "OPPOSES", "MET_WITH", "INVESTED_IN", "CONTROLS"]
    """
    allowed = []
    for relation, pairs in RELATION_CONSTRAINTS.items():
        if (subject_type, object_type) in pairs:
            allowed.append(relation)
    return allowed


def get_ontology_stats() -> dict[str, int | list[str]]:
    """
    Get statistics about the ontology.

    Returns:
        Dictionary with entity type count, relation type count, and lists

    Example:
        >>> get_ontology_stats()
        {
            "entity_type_count": 6,
            "relation_type_count": 12,
            "entity_types": ["PERSON", "ORGANIZATION", ...],
            "relation_types": ["OWNS", "FUNDS", ...]
        }
    """
    return {
        "entity_type_count": len(ALLOWED_ENTITY_TYPES),
        "relation_type_count": len(ALLOWED_RELATIONS),
        "entity_types": ALLOWED_ENTITY_TYPES,
        "relation_types": ALLOWED_RELATIONS,
    }
