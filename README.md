# ShadowMap Entreprise v4.0

**Plateforme de graphe de connaissances OSINT de qualité militaire**

ShadowMap transforme les renseignements non structurés provenant d'actualités, de documents et de sources ouvertes en un graphe de connaissances navigable et traçable, avec une notation de confiance rigoureuse et des pistes d'audit complètes.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   SHADOWMAP ENTREPRISE v4.0                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [FastAPI]  ──▶  [File d'attente Redis]  ──▶  [Workers Celery]   │
│      │                                      │                   │
│      │         ┌────────────────────────────┼──────────┐       │
│      │         │                            │          │       │
│      │         ▼                            ▼          ▼       │
│      │    File:Analyse             File:Extraction  File:Écriture│
│      │         │                            │          │       │
│      │         ▼                            ▼          ▼       │
│      │    [Unstructured]            [SpaCy + LLM]  [Neo4j]    │
│      │                                      │                  │
│      │                                      ▼                  │
│      │                              File:Résolution            │
│      │                                      │                  │
│      │                                      ▼                  │
│      │                              [Résolution d'entité]      │
│      │                                      │                  │
│      │                         ┌────────────┴────────────┐    │
│      │                         ▼                         ▼    │
│      │                   [Fusion automatique]    [File HITL]   │
│      │                   (score > seuil)        (0.80-seuil)  │
│      │                                                        │
│  ════════════════════════════════════════════════════════════ │
│                        COUCHE DE STOCKAGE                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Neo4j   │  │  Qdrant  │  │ Postgres │  │  Redis   │      │
│  │ (Graphe) │  │ (Vecteur)│  │ (Audit)  │  │ (Cache)  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Principes fondamentaux

### 1. Qualité de production
- **Python 3.11+** avec des indications de type strictes sur TOUTES les fonctions
- **Pydantic v2** pour tous les modèles de données
- **Journalisation structurée** via structlog (AUCUNE instruction `print()`)
- **Tests complets** with 100% de couverture sur les chemins critiques

### 2. Architecture à sécurité intégrée
- Le système s'arrête proprement si les services critiques (Neo4j, Postgres, Redis) sont indisponibles
- **File de messages morts (DLQ)** pour toutes les tâches ayant échoué - rien ne disparaît
- Tentatives de reconnexion exponentielles avec backoff via Celery

### 3. Rigueur mathématique

**Formule de confiance V4:**
```
C = min(0.99, (S × M) × (1 + log₁₀(N)/10))

Où:
  S = Poids de fiabilité de la source (0.0-1.0)
  M = Poids de confiance de la méthode (0.0-1.0)
  N = Nombre de corroborations (≥ 1)
```

- **ZÉRO nombre magique** - tous les seuils sont dans [src/config.py](src/config.py)
- Protection mathématique contre les cas limites (division par zéro, valeurs négatives)

### 4. Provenance complète

Chaque affirmation dans le graphe inclut :
- `source_url` - URL de la source originale
- `extraction_model` - Modèle utilisé (ex: "gpt-4o-2024-05-13")
- `prompt_version` - Version du prompt (ex: "v1.2")
- `confidence_score` - Score de confiance calculé
- `extracted_at` - Horodatage ISO
- `evidence_snippet` - Extrait de texte prouvant l'affirmation

### 5. Conformité OpSec
- **StealthSession** pour toutes les requêtes HTTP
- Délais d'attente aléatoires (1.5-4.0 secondes)
- Rotation des User-Agents
- Limitation de débit par domaine

## Démarrage rapide

### Prérequis

- Python 3.11+
- Docker & Docker Compose
- Clé API OpenAI (pour l'extraction GPT-4o)

### Installation

1.  **Cloner et configurer l'environnement :**
```bash
git clone <repository>
cd shadowmap
cp .env.example .env
# Modifiez .env et ajoutez votre OPENAI_API_KEY
```

2.  **Démarrer l'infrastructure :**
```bash
docker-compose up -d
```

3.  **Installer les dépendances Python :**
```bash
pip install poetry
poetry install
```

4.  **Exécuter les tests :**
```bash
pytest tests/core/ -v
```

Résultat attendu : `29 passed in 0.16s`

### Statut actuel - PHASE 0 ✅

**PHASE 0 : Socle & Observabilité** - **TERMINÉE**

Fichiers générés :
1. ✅ [docker-compose.yml](docker-compose.yml) - Configuration de l'infrastructure
2. ✅ [src/config.py](src/config.py) - Configuration centralisée
3. ✅ [src/core/logging.py](src/core/logging.py) - Journalisation structurée
4. ✅ [src/core/scoring.py](src/core/scoring.py) - Calculateur de confiance
5. ✅ [src/core/models.py](src/core/models.py) - Modèles Pydantic
6. ✅ [src/core/ontology.py](src/core/ontology.py) - Ontologie fermée
7. ✅ [tests/core/test_scoring.py](tests/core/test_scoring.py) - Suite de tests

**Critères de validation :** `pytest tests/core/` → **100% PASS** ✅

## Ontologie

### Types d'entités (Ensemble fermé)
- `PERSON` - Humains individuels
- `ORGANIZATION` - Entreprises, agences, groupes
- `LOCATION` - Villes, pays, coordonnées
- `EVENT` - Réunions, attaques, conférences
- `CRYPTO_WALLET` - Adresses de crypto-monnaie
- `DOCUMENT` - Contrats, rapports, fuites

### Types de relations (Ensemble fermé)
- `OWNS` (possède), `FUNDS` (finance), `EMPLOYS` (emploie), `PARTNERS_WITH` (est partenaire avec)
- `OPPOSES` (s'oppose à), `FAMILY_OF` (famille de), `LOCATED_IN` (situé à), `ATTENDED` (a assisté à)
- `ACQUIRED` (a acquis), `MET_WITH` (a rencontré), `INVESTED_IN` (a investi dans), `CONTROLS` (contrôle)

Voir [src/core/ontology.py](src/core/ontology.py) pour les définitions complètes et les contraintes.

## Configuration

Toute la configuration se trouve dans [src/config.py](src/config.py) via Pydantic Settings.

Paramètres clés :
- `SOURCE_WEIGHTS` - Scores de fiabilité par domaine
- `METHOD_WEIGHTS` - Confiance par méthode d'extraction
- `MERGE_THRESHOLDS` - Seuils de fusion automatique par type d'entité
- `HITL_MINIMUM_SCORE` - Score minimum pour la revue par un humain (0.80)

Outrepasser via les variables d'environnement ou le fichier `.env`.

## Tests

```bash
# Exécuter tous les tests
pytest

# Exécuter avec la couverture de code
pytest --cov=src --cov-report=html

# Exécuter une suite de tests spécifique
pytest tests/core/test_scoring.py -v
```

## Normes de qualité du code

### Modèles REQUIS

✅ **Écritures par lots dans Neo4j :**
```python
session.run("""
    UNWIND $entities AS entity
    MERGE (e:Entity {id: entity.id})
    ON CREATE SET e.name = entity.name
""", entities=entity_list)
```

✅ **Journalisation structurée :**
```python
import structlog
logger = structlog.get_logger()
logger.info("entity_extracted", entity_id=entity.id, confidence=0.85)
```

✅ **Seuils pilotés par la configuration :**
```python
from src.config import settings
threshold = settings.MERGE_THRESHOLDS["PERSON"]
```

### Modèles INTERDITS

❌ **Écritures individuelles dans Neo4j :**
```python
for entity in entities:  # NE JAMAIS FAIRE ÇA
    session.run("MERGE (e:Entity {name: $name})", name=entity.name)
```

❌ **Instructions d'impression :**
```python
print(f"Extracted entity: {entity}")  # UTILISER STRUCTLOG
```

❌ **Nombres magiques :**
```python
if score > 0.92:  # D'OÙ VIENT 0.92 ?
```

## Feuille de route

- [x] **PHASE 0 :** Socle & Observabilité
- [ ] **PHASE 1 :** Ingestion & Robustesse
- [ ] **PHASE 2 :** Intelligence (Extraction & Résolution)
- [ ] **PHASE 3 :** Stockage & Recherche
- [ ] **PHASE 4 :** API & Intégration

## Licence

Propriétaire - ShadowMap Entreprise v4.0

## Support

Pour les problèmes ou les questions, contactez l'équipe d'ingénierie de ShadowMap.
