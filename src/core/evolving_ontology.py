"""
VIDOCQ - Evolving Ontology with Inheritance
Dynamic, extensible ontology system.

"Types aren't static. They evolve with knowledge."

Features:
1. Hierarchical entity types with inheritance
2. Dynamic type creation
3. Type inference from context
4. Relation constraints
"""

from typing import Dict, List, Set, Optional, Any, Type
from pydantic import BaseModel, Field
from enum import Enum
from dataclasses import dataclass, field

from src.core.logging import get_logger

logger = get_logger(__name__)


class OntologyNode(BaseModel):
    """A node in the ontology hierarchy"""
    name: str
    parent: Optional[str] = None
    description: str = ""
    
    # Inherited properties from parent
    inherited_properties: List[str] = []
    
    # Own properties
    properties: Dict[str, str] = {}  # property_name -> type
    
    # Valid relations this type can have
    valid_relations: List[str] = []
    
    # Risk indicators for this type
    risk_indicators: List[str] = []
    
    # Aliases
    aliases: List[str] = []


class EntityHierarchy:
    """
    Hierarchical entity type system with inheritance.
    
    Example:
        ENTITY
        ├── ORGANIZATION
        │   ├── COMPANY
        │   │   ├── SHELL_COMPANY
        │   │   └── BANK
        │   └── NGO
        ├── PERSON
        │   ├── PEP (Politically Exposed Person)
        │   └── EXECUTIVE
        └── LOCATION
            ├── COUNTRY
            └── JURISDICTION
    """
    
    def __init__(self):
        self._types: Dict[str, OntologyNode] = {}
        self._initialize_base_ontology()
    
    def _initialize_base_ontology(self):
        """Initialize with base entity types"""
        
        # Root
        self.add_type(OntologyNode(
            name="ENTITY",
            description="Base type for all entities",
            properties={"name": "str", "aliases": "List[str]"},
            valid_relations=["RELATED_TO"]
        ))
        
        # Organizations
        self.add_type(OntologyNode(
            name="ORGANIZATION",
            parent="ENTITY",
            description="Any organized group",
            properties={"registration_country": "str", "founded_date": "date"},
            valid_relations=["OWNS", "OPERATES_IN", "PARTNERS_WITH"]
        ))
        
        self.add_type(OntologyNode(
            name="COMPANY",
            parent="ORGANIZATION",
            description="Commercial entity",
            properties={"industry": "str", "stock_ticker": "str"},
            valid_relations=["SUPPLIES", "COMPETES_WITH", "ACQUIRED"],
            risk_indicators=["offshore_registration", "rapid_ownership_changes"]
        ))
        
        self.add_type(OntologyNode(
            name="SHELL_COMPANY",
            parent="COMPANY",
            description="Company with minimal operations, often for financial structuring",
            risk_indicators=["no_employees", "registered_agent_only", "tax_haven_jurisdiction"],
            properties={"nominee_directors": "bool"}
        ))
        
        self.add_type(OntologyNode(
            name="BANK",
            parent="COMPANY",
            description="Financial institution",
            properties={"swift_code": "str", "banking_license": "str"},
            valid_relations=["PROCESSES_TRANSACTIONS", "HOLDS_ACCOUNTS"],
            risk_indicators=["correspondent_banking", "sanctions_exposure"]
        ))
        
        self.add_type(OntologyNode(
            name="DEFENSE_CONTRACTOR",
            parent="COMPANY",
            description="Military/defense industry company",
            properties={"security_clearance": "str", "export_licenses": "List[str]"},
            risk_indicators=["dual_use_tech", "arms_export"],
            valid_relations=["SUPPLIES_MILITARY", "CONTRACTS_WITH"]
        ))
        
        self.add_type(OntologyNode(
            name="NGO",
            parent="ORGANIZATION",
            description="Non-governmental organization",
            properties={"mission": "str", "funding_sources": "List[str]"},
            risk_indicators=["foreign_agent_status", "political_ties"]
        ))
        
        self.add_type(OntologyNode(
            name="MEDIA_OUTLET",
            parent="ORGANIZATION",
            description="News or media organization",
            properties={"ownership": "str", "editorial_stance": "str"},
            valid_relations=["PUBLISHES", "FUNDED_BY", "AMPLIFIES"],
            risk_indicators=["state_controlled", "disinformation_history"]
        ))
        
        # Persons
        self.add_type(OntologyNode(
            name="PERSON",
            parent="ENTITY",
            description="Individual human",
            properties={"nationality": "str", "date_of_birth": "date"},
            valid_relations=["EMPLOYED_BY", "DIRECTS", "RELATED_TO_PERSON"]
        ))
        
        self.add_type(OntologyNode(
            name="PEP",
            parent="PERSON",
            aliases=["Politically Exposed Person"],
            description="Person with political influence",
            properties={"political_role": "str", "term_dates": "str"},
            risk_indicators=["corruption_allegations", "unexplained_wealth"],
            valid_relations=["CONTROLS", "INFLUENCED_BY"]
        ))
        
        self.add_type(OntologyNode(
            name="EXECUTIVE",
            parent="PERSON",
            description="Corporate executive",
            properties={"title": "str", "companies": "List[str]"},
            valid_relations=["CEO_OF", "BOARD_MEMBER", "BENEFICIAL_OWNER_OF"]
        ))
        
        self.add_type(OntologyNode(
            name="OLIGARCH",
            parent="PERSON",
            description="Ultra-wealthy individual with political influence",
            properties={"estimated_wealth": "float", "industries": "List[str]"},
            risk_indicators=["sanctions", "asset_hiding", "political_patronage"],
            valid_relations=["CONTROLS", "FINANCES", "CONNECTED_TO"]
        ))
        
        # Locations
        self.add_type(OntologyNode(
            name="LOCATION",
            parent="ENTITY",
            description="Geographic location",
            properties={"coordinates": "str", "iso_code": "str"}
        ))
        
        self.add_type(OntologyNode(
            name="COUNTRY",
            parent="LOCATION",
            description="Nation state",
            properties={"government_type": "str", "sanctions_status": "str"},
            valid_relations=["ALLIED_WITH", "SANCTIONED_BY"]
        ))
        
        self.add_type(OntologyNode(
            name="JURISDICTION",
            parent="LOCATION",
            description="Legal jurisdiction",
            properties={"tax_rate": "float", "transparency_index": "float"},
            risk_indicators=["tax_haven", "secrecy_jurisdiction", "weak_aml"]
        ))
        
        # Products/Assets
        self.add_type(OntologyNode(
            name="ASSET",
            parent="ENTITY",
            description="Valuable item or property",
            properties={"value": "float", "acquisition_date": "date"},
            valid_relations=["OWNED_BY", "REGISTERED_IN"]
        ))
        
        self.add_type(OntologyNode(
            name="WEAPON_SYSTEM",
            parent="ASSET",
            description="Military equipment",
            properties={"classification": "str", "export_controlled": "bool"},
            risk_indicators=["dual_use", "proliferation_concern"]
        ))
        
        self.add_type(OntologyNode(
            name="FINANCIAL_INSTRUMENT",
            parent="ASSET",
            description="Financial product or security",
            properties={"instrument_type": "str", "issuer": "str"},
            risk_indicators=["complex_structure", "offshore_issuance"]
        ))
    
    def add_type(self, node: OntologyNode):
        """Add a type to the ontology"""
        # Inherit from parent if exists
        if node.parent and node.parent in self._types:
            parent = self._types[node.parent]
            
            # Inherit properties
            inherited = list(parent.properties.keys())
            if parent.inherited_properties:
                inherited.extend(parent.inherited_properties)
            node.inherited_properties = inherited
            
            # Inherit valid relations
            node.valid_relations = list(set(node.valid_relations + parent.valid_relations))
        
        self._types[node.name] = node
        
        # Also register aliases
        for alias in node.aliases:
            self._types[alias] = node
        
        logger.debug("ontology_type_added", name=node.name, parent=node.parent)
    
    def get_type(self, name: str) -> Optional[OntologyNode]:
        """Get a type by name (or alias)"""
        return self._types.get(name.upper())
    
    def is_subtype_of(self, child: str, parent: str) -> bool:
        """Check if one type inherits from another"""
        child_node = self.get_type(child)
        if not child_node:
            return False
        
        current = child_node
        while current:
            if current.name == parent.upper():
                return True
            if current.parent:
                current = self.get_type(current.parent)
            else:
                break
        
        return False
    
    def get_all_properties(self, type_name: str) -> Dict[str, str]:
        """Get all properties including inherited"""
        node = self.get_type(type_name)
        if not node:
            return {}
        
        props = dict(node.properties)
        
        # Walk up tree for inherited
        current = node
        while current.parent:
            parent = self.get_type(current.parent)
            if parent:
                for k, v in parent.properties.items():
                    if k not in props:
                        props[k] = v
                current = parent
            else:
                break
        
        return props
    
    def get_risk_indicators(self, type_name: str) -> List[str]:
        """Get all risk indicators including inherited"""
        node = self.get_type(type_name)
        if not node:
            return []
        
        risks = list(node.risk_indicators)
        
        current = node
        while current.parent:
            parent = self.get_type(current.parent)
            if parent:
                risks.extend(parent.risk_indicators)
                current = parent
            else:
                break
        
        return list(set(risks))
    
    def infer_type(self, entity_data: Dict[str, Any]) -> str:
        """
        Infer the most specific type from entity data.
        
        Uses heuristics based on properties present.
        """
        name = entity_data.get("name", "").lower()
        properties = entity_data.get("properties", {})
        
        # Heuristics
        if any(x in name for x in ["ministry", "government", "republic"]):
            return "COUNTRY"
        
        if any(x in name for x in ["bank", "financial", "credit"]):
            return "BANK"
        
        if entity_data.get("is_shell") or entity_data.get("offshore"):
            return "SHELL_COMPANY"
        
        if any(x in name for x in ["defense", "military", "aerospace", "thales", "lockheed"]):
            return "DEFENSE_CONTRACTOR"
        
        if entity_data.get("type") == "PERSON":
            if entity_data.get("political_role") or entity_data.get("is_pep"):
                return "PEP"
            if entity_data.get("title") in ["CEO", "CFO", "President", "Director"]:
                return "EXECUTIVE"
            return "PERSON"
        
        if entity_data.get("type") == "ORGANIZATION":
            return "COMPANY"
        
        return entity_data.get("type", "ENTITY")
    
    def validate_relation(
        self, 
        source_type: str, 
        relation: str, 
        target_type: str
    ) -> bool:
        """
        Validate that a relation is valid between two types.
        """
        source = self.get_type(source_type)
        if not source:
            return True  # Unknown types allowed
        
        # Check if relation is in valid relations (including inherited)
        valid = source.valid_relations
        current = source
        while current.parent:
            parent = self.get_type(current.parent)
            if parent:
                valid = valid + parent.valid_relations
                current = parent
            else:
                break
        
        return relation in valid or relation == "RELATED_TO"
    
    def list_types(self, parent: str = None) -> List[str]:
        """List all types, optionally filtered by parent"""
        if parent:
            return [
                name for name, node in self._types.items()
                if node.parent == parent
            ]
        return list(set(n.name for n in self._types.values()))


# Singleton
ONTOLOGY = EntityHierarchy()


def get_entity_type(name_or_data) -> OntologyNode:
    """Get entity type from name or data"""
    if isinstance(name_or_data, str):
        return ONTOLOGY.get_type(name_or_data)
    elif isinstance(name_or_data, dict):
        type_name = ONTOLOGY.infer_type(name_or_data)
        return ONTOLOGY.get_type(type_name)
    return None


def is_high_risk_type(type_name: str) -> bool:
    """Check if a type has high-risk indicators"""
    risks = ONTOLOGY.get_risk_indicators(type_name)
    return len(risks) > 0
