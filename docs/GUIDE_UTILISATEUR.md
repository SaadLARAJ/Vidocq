# 🔍 ShadowMap - Guide d'Utilisation

## C'est Quoi ShadowMap ?

ShadowMap est un système d'intelligence automatisé qui découvre, extrait et analyse des informations sur n'importe quelle entité (entreprise, personne, état).

**En une phrase** : Tu donnes un nom → le système trouve tout ce qu'il peut sur internet → il analyse, score, et détecte les contradictions.

---

## 🚀 Comment Lancer une Investigation ?

### Option 1 : Pipeline Complet (RECOMMANDÉ) ✨

**Nouvel endpoint qui utilise TOUS les modules AI :**

```bash
# Via GET (facile pour tester)
GET http://localhost:8000/investigate/full/Thales%20Group

# Via POST (plus de contrôle)
POST http://localhost:8000/investigate/full
{
    "target": "Thales Group",
    "max_urls": 20
}
```

**Ce que ça fait (10 étapes automatiques) :**

```
1. PROVENANCE      → Démarre un audit trail
2. CLASSIFICATION  → Identifie le type (Company/Person/State)
3. DISCOVERY       → Recherche sur internet (multilangue)
4. LANGUAGE        → Détecte les langues des sources
5. EXTRACTION      → Extrait entités et claims via Gemini
6. ONTOLOGY        → Infère les types précis (ex: DEFENSE_CONTRACTOR)
7. SCORING         → Score multi-facteurs (source + LLM + relevance)
8. CONTRADICTION   → Détecte les guerres narratives
9. BAYESIAN FUSION → Calcule probabilité réelle des claims
10. VERSIONING     → Versionne les faits dans le temps
```

---

### Option 2 : Discovery V3 + Ingestion (Ancien)

```bash
POST http://localhost:8000/discover/v3/ingest
{
    "entity": "Thales Group",
    "max_urls": 20
}
```

⚠️ **Différence** : Cet endpoint ne fait PAS :
- Bayesian fusion
- Ontology inference
- Provenance tracking
- Contradiction detection intégrée

---

## 📊 Comprendre les Résultats

### Exemple de Réponse

```json
{
    "status": "complete",
    "pipeline_version": "2.0",
    "target": "Thales Group",
    
    "classification": {
        "type": "COMPANY",
        "confidence": 0.95,
        "sector": "Defense/Aerospace"
    },
    
    "discovery": {
        "urls_discovered": 15,
        "coverage_score": 0.75,
        "critical_gaps": ["ownership"]  // ⚠️ Manque info
    },
    
    "extraction": {
        "entities_extracted": 42,
        "claims_extracted": 89,
        "languages_detected": ["en", "fr"]
    },
    
    "ontology": {
        "entity_types": {
            "Thales": "DEFENSE_CONTRACTOR",
            "Gemalto": "COMPANY"
        },
        "high_risk_entities": ["Some Offshore Ltd (SHELL_COMPANY)"]
    },
    
    "scoring": {
        "confirmed": 12,
        "unverified": 45,
        "quarantined": 8,
        "contested": 3,
        "narrative_wars": 1
    },
    
    "bayesian_fusion": {
        "total_fused": 89,
        "highly_likely": 35,
        "uncertain": 20
    },
    
    "recommendations": [
        "⚠️ GUERRE NARRATIVE: 1 conflit détecté",
        "🔴 GAPS CRITIQUES: ownership - Investigation manuelle requise"
    ]
}
```

---

## 🧠 Architecture Simplifiée

```
┌─────────────────────────────────────────────────────────────┐
│                         UTILISATEUR                         │
│              POST /investigate/full {"target": X}           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    UNIFIED PIPELINE v2.0                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   BRAIN     │───▶│  DISCOVERY  │───▶│  EXTRACTOR  │     │
│  │ (Classify)  │    │  (Search)   │    │ (Gemini AI) │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                  │                  │             │
│         ▼                  ▼                  ▼             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  ONTOLOGY   │    │  COVERAGE   │    │  LANGUAGE   │     │
│  │ (Type Risk) │    │   (Gaps)    │    │ (Detect)    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            ▼                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   UNIFIED SCORER                     │   │
│  │  • Source Intelligence (trust score)                 │   │
│  │  • Contradiction Detection (narrative wars)          │   │
│  │  • Bayesian Fusion (probability)                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                │
│                            ▼                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ PROVENANCE  │    │  TEMPORAL   │    │   STORAGE   │     │
│  │ (Audit)     │    │ (Versions)  │    │ (Neo4j)     │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │    RÉSULTAT     │
                    │  JSON complet   │
                    └─────────────────┘
```

---

## 📁 Fichiers Clés

| Module | Fichier | Rôle |
|--------|---------|------|
| **Pipeline** | `src/pipeline/unified_pipeline.py` | Orchestrateur principal |
| **Brain** | `src/brain/core_logic.py` | Classification intelligente |
| **Discovery** | `src/pipeline/discovery_v3.py` | Recherche multilangue |
| **Extraction** | `src/pipeline/extractor.py` | Extraction via Gemini |
| **Prompts** | `src/pipeline/prompts.py` | Prompts avec few-shot |
| **Scoring** | `src/core/unified_scoring.py` | Score multi-facteurs |
| **Bayesian** | `src/core/bayesian_fusion.py` | Fusion probabiliste |
| **Ontology** | `src/core/evolving_ontology.py` | Types avec héritage |
| **Provenance** | `src/core/provenance.py` | Chain of custody |
| **Temporal** | `src/core/temporal_versioning.py` | Versionnage des faits |
| **Language** | `src/core/language_detection.py` | Détection LLM |
| **Coverage** | `src/pipeline/coverage_analysis.py` | Analyse des gaps |
| **Contradiction** | `src/brain/contradiction_detector.py` | Guerres narratives |

---

## 🔧 Autres Endpoints Utiles

```bash
# Voir le graphe de connaissances
GET /graph/analyze

# Rapport géo-sourcé (FR vs RU sources)
GET /brain/report/{target}

# Classifier seulement
GET /brain/classify/{target}

# Voir données cachées (quarantine)
GET /graph/visible?show_all=true

# Wargame: "Que se passe-t-il si X tombe?"
GET /brain/wargame/{trigger}?scenario=EMBARGO
```

---

## 💡 Conseils

1. **Toujours utiliser `/investigate/full`** pour une analyse complète
2. **Regarder les `recommendations`** en premier dans la réponse
3. **`high_risk_entities`** = entités à surveiller de près
4. **`narrative_wars > 0`** = désaccord entre sources (attention !)
5. **`critical_gaps`** = informations manquantes = peut-être suspectes

---

## 🏃 Quick Start

```bash
# 1. Démarrer l'API
cd ShadowMap
uvicorn src.api.app:app --reload

# 2. Lancer une investigation
curl http://localhost:8000/investigate/full/Thales%20Group

# 3. Voir les résultats dans Neo4j Browser
# http://localhost:7474
```

C'est tout ! 🎉
