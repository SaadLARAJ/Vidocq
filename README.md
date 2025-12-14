# VIDOCQ v6.0 - Agent de Renseignement Autonome Universel

<div align="center">

![Version](https://img.shields.io/badge/version-6.0-blue)
![Status](https://img.shields.io/badge/status-Production%20Ready-green)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Architecture](https://img.shields.io/badge/architecture-Agentic%20GraphRAG-purple)

**L'agent de renseignement autonome qui cartographie, mémorise et alerte.**

*Le Palantir Souverain Français pour ceux que Palantir ignore.*

---

 **Agnostique** |  **Mémoire Cumulative** |  **Souveraineté Native** |  **Multi-Cas**

</div>

---

## 📋 Table des Matières

1. [Le Problème](#-le-problème)
2. [La Solution](#-la-solution--vidocq)
3. [Architecture Technique (Agentic GraphRAG)](#-architecture-technique-agentic-graphrag)
4. [Les 7 Killer Features](#-les-7-killer-features)
5. [Cas d'Usage Critiques](#️-cas-dusage-critiques-scénarios-réels) 🕵️ **NOUVEAU**
6. [Le Grand Graphe National](#-le-grand-graphe-national-vision) 🧠 **NOUVEAU**
7. [Stratégie Multi-Cas (Plateforme Universelle)](#-stratégie-multi-cas-plateforme-universelle)
8. [Système Anti-Bruit (CIA/OTAN)](#-système-anti-bruit-ciaotan-style)
9. [Gestion de la Confiance et Fiabilité](#-gestion-de-la-confiance-et-fiabilité)
10. [API Endpoints](#-api-endpoints)
11. [Discovery Engine v2.0](#-discovery-engine-v20-nouveau) ⚡
12. [Risk Scoring Multi-Dimensionnel](#-risk-scoring-multi-dimensionnel-nouveau) 📊
13. [Système de Cache Intelligent](#️-système-de-cache-intelligent-nouveau) 🗄️
14. [Comparatif Concurrentiel](#-comparatif-concurrentiel)
15. [Démarrage Rapide](#-démarrage-rapide)
16. [Roadmap et Vision](#-roadmap-et-vision)
17. [Souveraineté et Sécurité](#-souveraineté--sécurité)

---

##  Le Problème

> *"Qui sont les fournisseurs de mes fournisseurs ? Cette personne est-elle fiable ? Quels risques cachés menacent mon organisation ?"*

### La Cécité Stratégique

Les entreprises stratégiques (Défense, Énergie, Aéro, Finance) et les cabinets d'investigation sont **aveugles** sur plusieurs fronts :

| Domaine | Ce qu'ils voient | Ce qu'ils ignorent |
|---------|------------------|-------------------|
| **Supply Chain** | Fournisseurs Rang 1 | Rang 2, 3... N (La vraie chaîne) |
| **Due Diligence** | Bilans comptables | Réputation, scandales, liens cachés |
| **Recrutement** | CV officiel | Profils synthétiques, incohérences |
| **KYC/AML** | Listes de sanctions | Bénéficiaires effectifs, sociétés écrans |

### Les Solutions Actuelles

| Solution | Le Problème |
|----------|-------------|
| **Palantir** | 10M€/an + 18 mois d'intégration + Cloud Act US |
| **Bloomberg** | Données financières uniquement, aveugle sur le "terrain" |
| **Google + Excel** | Trop de bruit, pas de mémoire, trop lent |
| **Analystes humains** | 50 heures pour ce que Vidocq fait en 5 minutes |

---

## La Solution : Vidocq

**Vidocq n'est pas un moteur de recherche. C'est un Agent d'Investigation Autonome (Deeptech).**

### Comment ça fonctionne

Vous lui donnez un nom (entreprise, personne, pays). Il :

```
1. CLASSIFIE    → Détermine le type de cible (Entreprise / Personne / État)
2. CONSULTE     → Interroge sa mémoire (Investigations passées)
3. RECHERCHE    → Scanne le web (sources ouvertes, multilingue)
4. EXTRAIT      → Identifie entités et relations (LLM Chain-of-Thought)
5. VÉRIFIE      → Croise avec sources fiables (Wikidata, Sanctions, Registres)
6. FILTRE       → Élimine le bruit (Quarantaine CIA/OTAN)
7. ANALYSE      → Détecte contradictions, dangers, signaux faibles
8. GÉNÈRE       → Produit un rapport géo-sourcé avec preuves cliquables
```

### Le Différenciateur Clé : L'IA qui Apprend

<div align="center">

| ChatGPT | Palantir | **Vidocq** |
|---------|----------|------------|
| Oublie tout | Base statique | **Apprend de chaque investigation** |
| Pas de contexte | Config manuelle | **Mémoire cumulative automatique** |
| Générique | Complexe | **Adaptatif et spécialisé** |
| Amnésique | Rigide | **Graphe de Connaissance Vivant** |

</div>

### L'Effet Réseau 

```
JOUR 1: Investigation "Gazprom"
→ Vidocq découvre: "Gazprom → Alexei Miller (CEO)"
→ Stocké dans Neo4j + Qdrant

JOUR 30: Investigation "Rosneft"  
→ Vidocq consulte sa MÉMOIRE: "Je connais Alexei Miller!"
→ ALERTE: "Cette personne est déjà liée à une entité à risque"
→ L'investigation est ENRICHIE par le passé

JOUR 60: Investigation "Safran Supply Chain"
→ Vidocq détecte: "Fournisseur X a un lien avec Gazprom (découvert Jour 1)"
→ CONNEXION AUTOMATIQUE entre investigations non liées
```

**C'est l'Asset Propriétaire : le Graphe de Connaissance s'enrichit à chaque utilisation.**

---

## 🏗️ Architecture Technique (Agentic GraphRAG)

> **Ce n'est pas un "Wrapper ChatGPT". C'est une architecture Agentic GraphRAG propriétaire.**

### Le Moteur Tricéphale

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VIDOCQ v6.0 - AGENTIC GRAPHRAG               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ORCHESTRATEUR (Le Cerveau Stratégique)                         │
│  └─ S'adapte automatiquement selon la cible:                       │
│     • Cible ENTREPRISE → Agent "Supply Chain & Capital"            │
│     • Cible PERSONNE   → Agent "Influence & Réputation"            │
│     • Cible ÉTAT       → Agent "Géopolitique & Ressources"         │
│                                                                     │
│   GRAPHE DE CONNAISSANCE (La Mémoire - Neo4j)                    │
│  └─ Asset Propriétaire qui s'apprécie avec le temps:               │
│     • Entités: Personnes, Organisations, Lieux, Événements         │
│     • Relations: SUPPLIES, OWNS, FUNDS, OPPOSES, LOCATED_IN...     │
│     • Métadonnées: Score confiance, source, date, géolocalisation  │
│                                                                     │
│   AGENT CRITIQUE (Le Filtre de Vérité)                           │
│  └─ Contre l'hallucination et le bruit:                            │
│     • Source of Truth: Chaque lien = preuve cliquable (PDF, URL)   │
│     • Soft-Filtering: Données douteuses en "Quarantaine"           │
│     • Magic Switch: Révéler les signaux faibles à la demande       │
│                                                                     │
│   EMBEDDINGS VECTORIELS (Qdrant)                                  │
│  └─ Recherche sémantique et résolution d'entités:                  │
│     • Dimension: 768 (Gemini text-embedding-004)                   │
│     • Distance: Cosine Similarity                                   │
│     • Déduplication automatique des entités similaires             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Stack Technique Complète

| Couche | Technologie | Rôle | Souveraineté |
|--------|-------------|------|--------------|
| **API** | FastAPI | REST API haute performance | FR |
| **LLM** | Gemini 1.5 *(→ Mistral)* | Extraction + Classification |  Migration |
| **Graphe** | Neo4j + APOC | Relations entre entités |  Self-hosted |
| **Vecteurs** | Qdrant | Recherche sémantique |  Self-hosted |
| **Queue** | Celery + Redis | Tâches asynchrones |  Self-hosted |
| **Scraping** | DuckDuckGo + httpx | Collecte web |  FR |
| **Orchestration** | Docker Compose | Déploiement |  FR |

### Pipeline de Traitement

```
URL/Entité → Ingestion Furtive → Parsing → Chunking Sémantique
                                              ↓
                         Extraction LLM (Chain-of-Thought)
                                              ↓
                    Résolution Entités (Déduplication Vectorielle)
                                              ↓
              Vérification (Wikidata, Sanctions, Sources Fiables)
                                              ↓
                          Scoring Confiance (3 Niveaux)
                                              ↓
                    Stockage (Neo4j + Qdrant) + Alertes
```

---

##  Les Features

### 1.  Ghost Detector (Analyse du Vide)

**L'IA ne cherche pas ce qui est là, mais ce qui MANQUE.**

```python
GET /brain/ghost-scan/John%20Smith%20CEO

# Réponse:
{
  "suspicion_level": "HIGH",
  "anomalies": [
    "Aucun profil LinkedIn avant 2023",
    "Pas de diplôme vérifiable",
    "Aucune mention dans la presse avant sa nomination",
    "Nom très générique (possible alias)"
  ],
  "verdict": "PROFIL SYNTHÉTIQUE POSSIBLE - ESPIONNAGE OU FRAUDE"
}
```

**Cas d'usage:** Détection de faux CVs, profils d'espions, sociétés écrans.

---

### 2.  Wargaming (Simulation de Catastrophe)

**"Que se passe-t-il si X tombe ?"**

```python
GET /brain/wargame/Taiwan?scenario=EMBARGO

# Réponse:
{
  "trigger": "Embargo chinois sur Taiwan",
  "affected_entities": 47,
  "cascade_depth": 4,
  "critical_nodes": ["TSMC", "ASE Group", "UMC"],
  "your_exposure": [
    "Fournisseur Rang 2: MediaTek (Semi-conducteurs)",
    "Fournisseur Rang 3: TSMC (Fabrication wafers)"
  ],
  "estimated_impact": "Arrêt production dans 3 semaines"
}
```

**Cas d'usage:** Planification stratégique, tests de résilience, anticipation crises.

---

### 3.  Contradiction Detector (Guerre Narrative)

**Quand Reuters dit BLANC et RT dit NOIR.**

```python
GET /brain/contradictions/entity/Wagner

# Réponse:
{
  "narrative_war_detected": true,
  "western_narrative": "Mercenaires impliqués dans crimes de guerre",
  "adverse_narrative": "Forces de stabilisation africaines",
  "sources_occidental": ["Reuters", "Le Monde", "BBC"],
  "sources_adverse": ["RT", "Sputnik", "TASS"],
  "verdict": "CONFLIT INFORMATIQUE MAJEUR - Analyste requis"
}
```

**Cas d'usage:** Lutte contre la désinformation, analyse de réputation dans contextes sensibles.

---

### 4. Souveraineté Native

**Architecture 100% agnostique au fournisseur LLM.**

| Composant | MVP (Actuel) | Cible Souveraine |
|-----------|--------------|------------------|
| LLM | Gemini (Google/US) | **Mistral Large (FR)** |
| Cloud | Local/GCP | **SecNumCloud (OVH)** |
| Embeddings | Gemini | **CamemBERT / Mistral** |

> **Le Cloud Act américain** permet à la NSA d'accéder aux données chez providers US.
> Pour les clients Défense/OIV, Vidocq sur Mistral + SecNumCloud = **la seule option légale**.

---

### 5. Source of Truth (Traçabilité Cliquable)

**Chaque affirmation = une preuve vérifiable.**

```
Au lieu de:
  "Lien détecté avec la Russie" ❌

Vidocq affiche:
  "Lien détecté avec la Russie" 
  📎 Source: Rapport Annuel 2023, page 42 [CLIQUER]
  📎 Confiance: 87% (Source officielle)
```

**L'utilisateur ne vérifie pas l'IA. Il consulte la preuve que l'IA a trouvée.**

---

### 6. Alertes Temps Réel Cross-Clients

**Vidocq surveille les événements et alerte proactivement.**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SYSTÈME D'ALERTES MUTUALISÉ                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ÉVÉNEMENT DÉTECTÉ                                               │
│  └─ Reuters: "Scandale corruption chez Fournisseur X"              │
│                                                                     │
│   VIDOCQ CONSULTE LE GRAPHE GLOBAL                               │
│  └─ Fournisseur X présent dans:                                    │
│     • Supply Chain Entreprise A (Client Vidocq)                    │
│     • Supply Chain Entreprise B (Client Vidocq)                    │
│     • Due Diligence Cabinet C (Client Vidocq)                      │
│                                                                     │
│   ALERTES ENVOYÉES (Anonymisées)                                 │
│  └─ "Fournisseur X noté à risque par un autre utilisateur"         │
│  └─ Aucune indication de QUI a signalé → Confidentialité           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Exemple concret:**

```python
# Entreprise A fait une investigation
POST /discover/v2 {"entity": "Fournisseur X"}
→ Vidocq détecte: Violation ESG majeure
→ Fournisseur X tagué "HIGH_RISK" dans le graphe global

# 3 jours plus tard, Entreprise B consulte son graphe
GET /graph/visible
→ ALERTE: "⚠️ Fournisseur X (votre Rang 2) a été signalé à risque 
           par un autre utilisateur Vidocq. Due diligence recommandée."
```

**Valeur ajoutée:**
-  **Intelligence Collective:** Chaque client enrichit le graphe pour tous
-  **Confidentialité:** Impossible de savoir qui a signalé
-  **Proactivité:** Alerte AVANT que le risque ne vous impacte

---

### 7. Surveillance Continue (Watchlist)

**Placez des entités sous surveillance permanente.**

```python
# Ajouter une entité à surveiller
POST /watchlist/add
{
  "entity_name": "Concurrent X",
  "entity_type": "ORGANIZATION",
  "alert_types": ["news", "sanctions", "ownership_change", "scandal"],
  "frequency": "daily"
}

# Réponse:
{
  "status": "watching",
  "entity": "Concurrent X",
  "next_scan": "2024-01-15T06:00:00Z",
  "alerts_enabled": true
}
```

**Comment ça fonctionne:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SURVEILLANCE CONTINUE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   WATCHLIST ACTIVE                                                │
│  ├─ Concurrent X          → Scan quotidien                         │
│  ├─ Fournisseur Critique  → Scan hebdomadaire                      │
│  ├─ CEO nouveau partenaire → Scan quotidien                        │
│  └─ Pays à risque (Russie) → Scan temps réel                       │
│                                                                     │
│   PROCESSUS AUTOMATIQUE                                           │
│  1. Crawler OSINT lance recherche périodique                       │
│  2. Compare avec état précédent du graphe                          │
│  3. Détecte CHANGEMENTS (nouveau lien, nouveau risque, news)       │
│  4. Envoie ALERTE si changement significatif                       │
│                                                                     │
│   TYPES D'ALERTES                                                 │
│  ├─  Nouvelle mention presse                                     │
│  ├─  Nouveau risque sanctions                                    │
│  ├─  Changement de propriétaire/dirigeant                        │
│  ├─  Scandale/Corruption détecté                                 │
│  └─  Changement géopolitique affectant l'entité                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Exemple d'alerte reçue:**

```json
{
  "alert_type": "OWNERSHIP_CHANGE",
  "entity": "Fournisseur Stratégique Y",
  "severity": "HIGH",
  "summary": "Nouveau bénéficiaire effectif détecté: Holding basée aux Îles Caïmans",
  "source": "Registre du Commerce, 14/01/2024",
  "action_recommended": "Due diligence approfondie recommandée",
  "link": "https://infogreffe.fr/..."
}
```

**Cas d'usage:**
-  **Supply Chain:** Surveiller vos 50 fournisseurs critiques 24/7
-  **RH Sensible:** Alertes sur dirigeants de confiance (conflits d'intérêts)
-  **M&A:** Suivre une cible d'acquisition avant l'offre
-  **Sécurité:** Détecter les changements dans l'écosystème adverse

---

##  Cas d'Usage Critiques (Scénarios Réels)

> **Ce que Vidocq détecte et que personne d'autre ne voit.**

### Cas 1: Rachat Discret par Fonds Étrangers

```
┌─────────────────────────────────────────────────────────────────────┐
│   SCÉNARIO: Rachat d'un sous-traitant stratégique par un         │
│              fonds chinois via société écran aux Caïmans            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  STRUCTURE CACHÉE:                                                  │
│                                                                     │
│   Fonds Souverain Chinois (CIC / Safe)                          │
│       └─ Holding Luxembourg                                        │
│            └─ SPV Îles Caïmans                                     │
│                 └─ Société Écran Delaware                          │
│                      └─ "Investor Group LLC"                       │
│                           └─ VOTRE SOUS-TRAITANT              │
│                                                                     │
│  CE QUE VIDOCQ DÉTECTE:                                            │
│  ✓ Changement bénéficiaire effectif (UBO) via registres            │
│  ✓ Liens avec entités chinoises via OSINT                          │
│  ✓ Pattern "Holding → SPV → Écran" = Signal fort                   │
│  ✓ Corrélation avec intérêts stratégiques chinois                  │
│                                                                     │
│   ALERTE: "Acquisition potentielle par entité adverse"           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Cas 2: Holdings en Cascade (Poupées Russes)

```python
# Vidocq trace automatiquement les chaînes de propriété
GET /brain/trace-ownership/SocieteX

{
  "target": "SocieteX (France)",
  "ownership_chain": [
    {"level": 0, "entity": "SocieteX SARL", "country": "France", "owner": "Holding Alpha"},
    {"level": 1, "entity": "Holding Alpha", "country": "Luxembourg", "owner": "Beta Investments"},
    {"level": 2, "entity": "Beta Investments", "country": "Pays-Bas", "owner": "Gamma Capital"},
    {"level": 3, "entity": "Gamma Capital", "country": "Îles Caïmans", "owner": "Delta Trust"},
    {"level": 4, "entity": "Delta Trust", "country": "BVI", "owner": "???"},
    {"level": 5, "entity": "BÉNÉFICIAIRE EFFECTIF", "country": "Russie", "owner": "Oligarque Z"}
  ],
  "red_flags": [
    "5 niveaux de holdings = opacité intentionnelle",
    "Juridictions: Caïmans + BVI = paradis fiscaux",
    "Terminaison en Russie = risque sanctions"
  ],
  "risk_score": 92,
  "recommendation": "BLOCAGE recommandé - Due diligence niveau 3"
}
```

### Cas 3: Espionnage Industriel via Recrutement

```
SCÉNARIO: Candidat "parfait" pour poste R&D Défense

CE QUE LE CV DIT:
  ✓ PhD MIT en cybersécurité
  ✓ 10 ans chez Lockheed Martin
  ✓ Publications académiques

CE QUE VIDOCQ DÉTECTE (Ghost Detector):
  ✗ Aucun profil LinkedIn avant 2021
  ✗ Publications non indexées par Google Scholar
  ✗ Ancien employeur: aucune trace dans annuaires internes
  ✗ Email universitaire: domaine enregistré il y a 6 mois

VERDICT: "PROFIL SYNTHÉTIQUE - PROBABLE LÉGENDE D'ESPION"
```

### Cas 4: Manipulation Boursière via Rumeurs

```
ÉVÉNEMENT: Chute de 15% du cours de Société ABC

ANALYSE VIDOCQ (Contradiction Detector):
- 14h32: Article négatif publié par "Financial Observer" (blog)
- 14h45: Repris par 23 comptes Twitter coordonnés
- 15h00: Chute boursière commence
- 17h00: Démenti officiel (ignoré par les marchés)

PATTERN DÉTECTÉ: 
"Attack Narrative" - Campagne de désinformation coordonnée
Sources: IP ukrainiennes, comptes créés < 30 jours

ALERTE: "Manipulation informationnelle en cours"
```

### Cas 5: Contournement de Sanctions

```
SCÉNARIO: Fournisseur de composants électroniques

VIDOCQ DÉTECTE:
1. Fournisseur "Clean Tech Ltd" (Singapour) ✓ Apparence propre
2. MAIS: Dirigeant = ancien employé société sanctionnée russe
3. MAIS: Adresse = même bâtiment que filiale Rostec
4. MAIS: 80% des exports → "clients" en Arménie, Kazakhstan, Kirghizistan
   └─ Countries classiques de contournement sanctions

VERDICT: "PROBABLE FRONT COMPANY pour contournement OFAC"
RISQUE: Sanctions secondaires sur VOTRE entreprise
```

---

##  Le Grand Graphe National (Vision)

> **L'IA qui connaîtra l'économie française mieux que quiconque.**

### Le Concept

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LE GRAND GRAPHE VIDOCQ                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   CROISSANCE CUMULATIVE                                           │
│  └─ Chaque investigation enrichit le graphe                        │
│  └─ Chaque client apporte ses données                              │
│  └─ Chaque analyste corrige et améliore                            │
│                                                                     │
│   CARTOGRAPHIE ÉCONOMIQUE COMPLÈTE                              │
│  ├─ Entreprises françaises et leurs liens                          │
│  ├─ Supply chains stratégiques                                     │
│  ├─ Flux financiers et participations                              │
│  ├─ Personnes clés et réseaux d'influence                          │
│  └─ Risques géopolitiques par secteur                              │
│                                                                     │
│   IA QUI APPREND                                                  │
│  ├─ Feedback analystes → Fine-tuning modèle                        │
│  ├─ Patterns de risque → Détection automatique                     │
│  ├─ Simulation de scénarios → Prédiction impacts                   │
│  └─ Connaissance transversale → Connexions invisibles              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Apprentissage par les Analystes (RLHF)

```python
# L'analyste valide ou corrige une extraction
POST /feedback
{
  "claim_id": "claim_12345",
  "human_verdict": "CORRECT",  # ou "INCORRECT", "NEEDS_CONTEXT"
  "correction": null,
  "reasoning": "Relation confirmée via rapport annuel 2023"
}

# Ces données s'accumulent pour entraîner le modèle
GET /feedback/export-training

{
  "total_feedback": 15420,
  "accuracy_improvement": "+12% depuis lancement",
  "top_corrections": [
    "Confusion fréquente: PARTNER vs SUPPLIER",
    "Géolocalisation imprécise: villes chinoises"
  ],
  "model_version": "v2.3-finetuned-fr"
}
```

### Simulation de Scénarios (Wargaming Avancé)

```python
# L'État ou une entreprise stratégique demande:
# "Que se passe-t-il si la Chine envahit Taiwan?"

POST /brain/simulate
{
  "scenario": "TAIWAN_INVASION",
  "parameters": {
    "trigger": "Blocus maritime chinois",
    "duration_weeks": 8,
    "affected_sectors": ["semiconductors", "electronics", "automotive"]
  },
  "scope": "FRENCH_ECONOMY"
}

# Vidocq analyse son Grand Graphe et répond:
{
  "scenario": "TAIWAN_INVASION",
  "impact_assessment": {
    "companies_affected": 2847,
    "sectors_critical": ["Automobile", "Aérospatiale", "Défense", "Télécom"],
    "supply_chain_breaks": [
      {
        "component": "Semiconducteurs avancés (<7nm)",
        "dependency": "95% Taiwan (TSMC)",
        "time_to_shortage": "3-4 semaines",
        "french_companies_impacted": ["Renault", "Stellantis", "Valeo", "STMicro"]
      },
      {
        "component": "Terres rares",
        "dependency": "87% Chine",
        "time_to_shortage": "6-8 semaines",
        "french_companies_impacted": ["Safran", "Airbus", "Naval Group"]
      }
    ],
    "estimated_gdp_impact": "-2.3%",
    "recommended_actions": [
      "Constituer stocks stratégiques semiconducteurs",
      "Identifier fournisseurs alternatifs (Intel, Samsung)",
      "Accélérer production européenne (projet CHIPS Act)"
    ]
  }
}
```

### L'IA de la Souveraineté Nationale

> **Vidocq ambitionne de devenir l'infrastructure de renseignement économique de la France.**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VISION: IA SOUVERAINE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   OBJECTIF                                                        │
│  └─ Une IA qui comprend TOUT de l'économie française               │
│  └─ Fiscalité, actionnariat, supply chains, risques                │
│  └─ Capable de simuler n'importe quel scénario                     │
│                                                                     │
│   SOURCES D'APPRENTISSAGE                                         │
│  ├─ OSINT mondial (web, presse, réseaux)                           │
│  ├─ Registres officiels (Infogreffe, INSEE, Douanes)               │
│  ├─ Feedback analystes (DGSI, DGSE, Tracfin, entreprises)          │
│  ├─ Données sectorielles (fédérations, syndicats)                  │
│  └─ Rapports d'investigation (anonymisés)                          │
│                                                                     │
│   CAS D'USAGE SOUVERAIN                                          │
│  ├─ Screening investissements étrangers (IEF)                      │
│  ├─ Protection des pépites technologiques                          │
│  ├─ Détection ingérence économique                                 │
│  ├─ Anticipation crises supply chain                               │
│  └─ Cartographie réseaux d'influence hostiles                      │
│                                                                     │
│   CLIENTS CIBLES                                                 │
│  ├─ SGDSN, DGSI, DGSE, Tracfin                                     │
│  ├─ Direction Générale des Entreprises (DGE)                       │
│  ├─ Ministère des Armées                                           │
│  ├─ OIV (Opérateurs d'Importance Vitale)                           │
│  └─ Grandes entreprises stratégiques                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Effet Réseau: Plus de Clients = IA Plus Intelligente

```
JOUR 1: 10 clients → Graphe de 50,000 entités
        ↓
        Modèle détecte patterns basiques

AN 1:   100 clients → Graphe de 500,000 entités
        ↓
        Modèle prédit risques sectoriels

AN 3:   1000 clients → Graphe de 5,000,000 entités
        ↓
        Modèle simule impacts macro-économiques

AN 5:   Couverture nationale → LE GRAPHE ÉCONOMIQUE FRANÇAIS
        ↓
        IA de référence pour la souveraineté économique
```

**C'est l'asset stratégique: le modèle s'apprécie avec chaque utilisation.**



> **Vidocq n'est pas limité à la Supply Chain. C'est une plateforme d'investigation universelle.**

### Le Cheval de Troie

L'architecture est **agnostique à la cible**. Un même moteur, 5 marchés :

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VIDOCQ - PLATEFORME UNIVERSELLE                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   MODULE SUPPLY CHAIN (Fer de Lance)                             │
│  └─ Cible: Directeurs Achats, Compliance CSDDD                     │
│  └─ Besoin: "Qui sont mes fournisseurs de rang N?"                 │
│  └─ Loi: CSDDD (5000 ETI obligées de s'équiper)                    │
│                                                                     │
│   MODULE KYC/AML (Finance)                                        │
│  └─ Cible: Banques, Fonds d'investissement                         │
│  └─ Besoin: "Cette origine de fonds est-elle propre?"              │
│  └─ Valeur: Automatise la Due Diligence anti-blanchiment           │
│                                                                     │
│   MODULE M&A (Fusions-Acquisitions)                               │
│  └─ Cible: Private Equity, Cabinets Conseil                        │
│  └─ Besoin: "Cette cible d'acquisition cache-t-elle des risques?"  │
│  └─ Valeur: Le radar à cadavres dans le placard                    │
│                                                                     │
│   MODULE RH (Vetting Stratégique)                                 │
│  └─ Cible: DRH Défense, Nucléaire, R&D                             │
│  └─ Besoin: "Ce candidat est-il vraiment qui il prétend être?"     │
│  └─ Valeur: Ghost Detector contre menace interne                   │
│                                                                     │
│   MODULE MÉDIAS/ONG (Contre-Influence)                            │
│  └─ Cible: Directions Communication, Lobbys                        │
│  └─ Besoin: "Qui finance cette ONG qui nous attaque?"              │
│  └─ Valeur: Démasquer le lobbying caché                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Classification Automatique

L'Orchestrateur adapte sa stratégie selon la cible :

```python
GET /brain/classify/Gazprom
→ {"type": "ORGANIZATION", "sector": "Energy", "strategy": "supply_chain_capital"}

GET /brain/classify/Vladimir%20Putin
→ {"type": "PERSON", "role": "Political", "strategy": "influence_network"}

GET /brain/classify/Taiwan
→ {"type": "STATE", "region": "Asia-Pacific", "strategy": "geopolitical_resources"}
```

---

##  Système Anti-Bruit (CIA/OTAN Style)

> *"Raw Intelligence Never Dies"* - Aucune donnée n'est jamais supprimée.

### Les 3 Zones de Visibilité

| Zone | Score | Status | Affichage | Usage |
|------|-------|--------|-----------|-------|
| 🟢 Verte | ≥ 0.8 | `CONFIRMED` | Visible par défaut | Sources officielles, registres |
| 🟡 Orange | 0.5-0.8 | `UNVERIFIED` | Visible par défaut | Articles presse, LinkedIn |
| ⬜ Grise | < 0.5 | `QUARANTINE` | Caché mais stocké | Forums, blogs, rumeurs |

### Le "Magic Switch" (Démo Killer)

```python
# Vue propre pour la démo
GET /graph/visible
→ Graphe net, sans bruit

# L'investisseur demande: "Vous ne ratez pas des signaux faibles?"
GET /graph/visible?show_all=true
→ BOOM! Tout apparaît. "Raw Intelligence Never Dies."
```

### Pourquoi la Quarantaine ?

- **Contre l'hallucination:** Les données douteuses sont isolées, pas mélangées
- **Préservation Intel:** Un signal faible aujourd'hui peut être confirmé demain
- **Transparence:** L'analyste peut TOUJOURS accéder aux données brutes

---

##  Gestion de la Confiance et Fiabilité

### Le Système de Scoring

```
Score Final = (Source Weight × 0.4) + (Method Weight × 0.3) + (Corroboration × 0.3)
```

| Source | Poids | Exemples |
|--------|-------|----------|
| Registres Officiels | 0.95 | Infogreffe, SEC, Sanctions OFAC |
| Presse Majeure | 0.90 | Reuters, AP, Le Monde |
| Presse Locale | 0.70 | Journaux régionaux |
| LinkedIn/Social | 0.50 | Profils professionnels |
| Forums/Blogs | 0.30 | Discussions, rumeurs |

### L'Analogie "Assistant Juridique"

> **Vidocq ne remplace pas le jugement. Il supprime le bruit.**

```
AVANT VIDOCQ:
  Analyste lit 5000 pages de documents → 50 heures de travail

AVEC VIDOCQ:
  Vidocq surligne les 10 clauses critiques → Analyste valide en 1 heure
  Gain: 49 heures économisées
```

**On ne vend pas de l'automatisation aveugle. On vend du temps d'analyste à haute valeur ajoutée.**

---

## 📡 API Endpoints

### Cerveau (Intelligence)
| Endpoint | Fonction |
|----------|----------|
| `GET /brain/classify/{target}` | Classification Person/Company/State |
| `GET /brain/analyze/{target}` | Analyse complète avec mémoire |
| `GET /brain/ghost-scan/{target}` | Détection d'absences suspectes |
| `GET /brain/wargame/{trigger}` | Simulation catastrophe |
| `GET /brain/contradictions/{target}` | Détection guerre narrative |
| `GET /brain/report/{target}` | Rapport géo-sourcé |

### Investigation
| Endpoint | Fonction |
|----------|----------|
| `GET /investigate/{entity}` | Lance investigation complète |
| `POST /ingest` | Ingère une URL unique |
| `POST /discover` | Lance découverte OSINT |

### Graphe & Visibilité
| Endpoint | Fonction |
|----------|----------|
| `GET /graph/visible` | Graphe propre (démo) |
| `GET /graph/visible?show_all=true` | Tout voir (Magic Switch) |
| `GET /graph/geo` | Données géolocalisées pour carte |
| `GET /graph/stats/visibility` | Stats par zone confiance |
| `POST /search` | Recherche sémantique vectorielle |

### Apprentissage (RLHF)
| Endpoint | Fonction |
|----------|----------|
| `POST /feedback` | Soumettre correction analyste |
| `GET /feedback/stats` | Progression apprentissage |
| `GET /feedback/export-training` | Export pour fine-tuning |

### Risk Scoring (NOUVEAU)
| Endpoint | Fonction |
|----------|----------|
| `POST /risk/score` | Score multi-dimensionnel d'une entité |
| `GET /risk/supply-chain/{entity}` | Score de risque toute la supply chain |
| `GET /risk/geopolitical-map` | Carte des risques géopolitiques par pays |

### Discovery v2 (NOUVEAU)
| Endpoint | Fonction |
|----------|----------|
| `POST /discover/v2` | Découverte avec cache et parallélisation |
| `POST /discover/v2/ingest` | Découverte + ingestion automatique |

### Cache & Système (NOUVEAU)
| Endpoint | Fonction |
|----------|----------|
| `GET /cache/stats` | Statistiques du cache Redis |
| `DELETE /cache/clear` | Vider le cache (avec précaution) |
| `GET /health/full` | Health check complet de tous les composants |

---

##  Discovery Engine v2.0 

> **3x plus rapide grâce à la parallélisation et au caching intelligent.**

### Architecture du Discovery v2

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DISCOVERY ENGINE v2.0                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ENTRÉE                                                          │
│  └─ Nom d'entité (ex: "STMicroelectronics")                        │
│                                                                     │
│   PHASE 1: CHECK CACHE (Redis)                                   │
│  └─ Si déjà investigué < 24h → Retourne résultat immédiat         │
│                                                                     │
│   PHASE 2: GÉNÉRATION QUERIES (LLM)                              │
│  └─ 5 requêtes intelligentes multilingues                          │
│  └─ Fallback queries si LLM échoue                                 │
│                                                                     │
│   PHASE 3: EXÉCUTION PARALLÈLE (ThreadPoolExecutor)              │
│  └─ 3 workers simultanés                                           │
│  └─ Délai anti-bot aléatoire (1-2.5s)                              │
│                                                                     │
│   PHASE 4: DÉDUPLICATION                                          │
│  └─ Filtre URLs déjà traitées                                      │
│  └─ Stockage cache pour prochaine fois                             │
│                                                                     │
│   SORTIE                                                          │
│  └─ Liste d'URLs uniques à ingérer                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Comparaison v1 vs v2

| Fonctionnalité | Discovery v1 | Discovery v2 |
|----------------|--------------|--------------|
| Exécution | Séquentielle | **Parallèle (3 workers)** |
| Cache | Aucun | **Redis TTL 24h** |
| Déduplication URLs | Manuelle | **Automatique** |
| Temps moyen | ~30 secondes | **~10 secondes** |
| Retry logic | Basique | **Avancé avec fallback** |

### Exemple d'utilisation

```python
# Lancer une découverte v2
POST /discover/v2
{
  "entity": "TotalEnergies",
  "use_cache": true,
  "max_depth": 2
}

# Réponse:
{
  "status": "completed",
  "entity": "TotalEnergies",
  "urls_found": 23,
  "queries_used": 5,
  "cached": false,
  "urls": [
    "https://totalenergies.com/suppliers/...",
    "https://reuters.com/article/totalenergies-...",
    ...
  ]
}
```

---

##  Risk Scoring Multi-Dimensionnel (NOUVEAU)

> **Évaluez le risque réel de chaque entité avec 5 dimensions d'analyse.**

### Les 5 Dimensions du Score

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SCORING MULTI-DIMENSIONNEL                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   CONCENTRATION (20%)                                             │
│  └─ Dépendance à un seul fournisseur                               │
│  └─ Score élevé = risque de single-point-of-failure               │
│                                                                     │
│   GÉOPOLITIQUE (25%)                                              │
│  └─ Risque pays (Russie=95, France=5, Chine=70...)                 │
│  └─ Base de données 40+ pays avec scores                          │
│                                                                     │
│   PROFONDEUR (15%)                                                │
│  └─ Visibilité N-tier (Rang 1, 2, 3...)                            │
│  └─ Score élevé = mauvaise visibilité supply chain                 │
│                                                                     │
│   SANCTIONS (25%)                                                 │
│  └─ Exposition OFAC, SDN, Entity List                              │
│  └─ Détection automatique via mots-clés                            │
│                                                                     │
│   ESG (15%)                                                       │
│  └─ Environnemental, Social, Gouvernance                           │
│  └─ Forced labor, corruption, pollution...                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

SCORE FINAL = Σ (Dimension × Poids)
```

### Niveaux de Risque

| Niveau | Score | Action |
|--------|-------|--------|
| 🔴 `CRITICAL` | ≥ 80 | Action immédiate requise |
| 🟠 `HIGH` | 60-79 | Due diligence renforcée |
| 🟡 `MEDIUM` | 40-59 | Surveillance continue |
| 🟢 `LOW` | 20-39 | Vigilance standard |
| ⚪ `MINIMAL` | < 20 | Faible préoccupation |

### Base de Risque Géopolitique

```python
# Extrait de la base géopolitique intégrée
GET /risk/geopolitical-map

{
  "risk_map": {
    "CRITICAL": [
      {"country": "RUSSIA", "score": 95},
      {"country": "NORTH KOREA", "score": 100},
      {"country": "IRAN", "score": 90}
    ],
    "HIGH": [
      {"country": "CHINA", "score": 70},
      {"country": "TAIWAN", "score": 60}  // Tension géopolitique
    ],
    "MINIMAL": [
      {"country": "FRANCE", "score": 5},
      {"country": "GERMANY", "score": 5},
      {"country": "SWITZERLAND", "score": 3}
    ]
  },
  "total_countries": 40
}
```

### Exemple de Score Entité

```python
POST /risk/score
{
  "entity_name": "Gazprom",
  "locations": ["RUSSIA", "GERMANY"]
}

# Réponse:
{
  "entity": "Gazprom",
  "overall_score": 82.5,
  "risk_level": "CRITICAL",
  "breakdown": {
    "concentration": 45.0,
    "geopolitical": 95.0,
    "depth_visibility": 70.0,
    "sanctions": 90.0,
    "esg": 60.0
  },
  "risk_factors": [
    "High-risk country exposure: RUSSIA",
    "Entity name matches known sanctioned patterns: Gazprom",
    "Limited visibility beyond Tier-1 suppliers"
  ],
  "recommendations": [
    "Immediate sanctions compliance review required",
    "Conduct enhanced due diligence on high-risk geography suppliers",
    "Map deeper supply chain tiers (Tier 2+)"
  ]
}
```

### Score Supply Chain Entière

```python
GET /risk/supply-chain/Safran

# Réponse:
{
  "root_entity": "Safran",
  "supplier_count": 47,
  "average_risk": 34.2,
  "max_risk": 78.5,
  "critical_suppliers": 2,
  "suppliers": [
    {
      "entity": "Supplier X (China)",
      "depth": 2,
      "score": 78.5,
      "level": "HIGH",
      "factors": ["High-risk country exposure: CHINA"]
    },
    ...
  ]
}
```

---

##  Système de Cache Intelligent 

> **Évitez les recherches dupliquées et accélérez les investigations.**

### Architecture du Cache

```
┌─────────────────────────────────────────────────────────────────────┐
│                       DISCOVERY CACHE (Redis)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   CACHE RECHERCHES                                                │
│  └─ Clé: hash(query)                                               │
│  └─ Valeur: résultats JSON                                         │
│  └─ TTL: 24 heures                                                 │
│                                                                     │
│   DÉDUPLICATION URLs                                              │
│  └─ Clé: hash(url)                                                 │
│  └─ Valeur: {source, processed, timestamp}                         │
│  └─ TTL: 7 jours                                                   │
│                                                                     │
│   HISTORIQUE ENTITÉS                                              │
│  └─ Clé: hash(entity_name)                                         │
│  └─ Valeur: {urls, depth, last_updated}                            │
│  └─ TTL: 30 jours                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Bénéfices

| Métrique | Sans Cache | Avec Cache |
|----------|------------|------------|
| Recherche dupliquée | ~5 secondes | **< 10 ms** |
| Ingestion URL déjà vue | Ré-ingérée | **Ignorée** |
| Investigation répétée | Refaite | **Résultat immédiat** |
| Charge serveur | Haute | **Optimisée** |

### Statistiques Cache

```python
GET /cache/stats

{
  "enabled": true,
  "ttl_hours": 24,
  "keyspace": {
    "db0": {
      "keys": 1247,
      "expires": 1198
    }
  }
}
```


## Comparatif Concurrentiel

### La Matrice de Positionnement

| Concurrent | Sa Force | Sa Faiblesse Mortelle | Réponse Vidocq |
|------------|----------|----------------------|----------------|
| **PALANTIR** 🇺🇸 | Puissance militaire | Prix (>1M€) + Cloud Act | Accessible (10k€) + Souverain |
| **BLOOMBERG** 🇺🇸 | Données financières | Aveugle sur le "terrain" | OSINT temps réel |
| **ALTARES/D&B** | Données légales | Regarde le passé | Prédictif (risques futurs) |
| **MALTEGO** | Graphe visuel | Outil manuel complexe | Automatisé (Agent IA) |
| **GOOGLE** | Gratuit | Trop de bruit, amnésique | Productivité + Mémoire |

### Le Blue Ocean

```
PALANTIR → CAC40 + États (10M€/an)
        ↓
    [GAP ÉNORME]  ← VIDOCQ
        ↓
ETI STRATÉGIQUES → 5000 entreprises (10k€/an) = 50M€ de marché
```

---

##  Démarrage Rapide

### Prérequis

```bash
Docker + Docker Compose
Python 3.11+
Clés API: GEMINI_API_KEY
```

### Installation

```bash
# Clone
git clone https://github.com/your-org/vidocq.git
cd vidocq

# Variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés

# Lancer les services (Neo4j, Qdrant, Redis, Postgres)
docker-compose up -d

# Installer les dépendances Python
pip install -r requirements.txt

# Lancer l'API
uvicorn src.api.main:app --reload

# Dans un autre terminal: Lancer le worker Celery
celery -A src.ingestion.tasks worker --loglevel=info -P solo
```

### Premier Test

```bash
# Lancer une investigation
curl -X POST "http://localhost:8000/discover" \
  -H "Content-Type: application/json" \
  -d '{"query": "STMicroelectronics", "limit": 5}'

# Attendre 2-3 minutes...

# Voir le graphe
curl http://localhost:8000/graph/geo

# Voir les stats
curl http://localhost:8000/status
```

---

## Roadmap et Vision

### Phases de Développement

| Phase | Objectif | Statut |
|-------|----------|--------|
| **MVP** | Core + Pipeline + Discovery | ✅ Done |
| **v6.0** | Cerveau (Ghost Detector, Wargaming) | 🔄 En cours |
| **Seed** | UI War Room + Migration Mistral | 📋 Planifié |
| **Série A** | Certification SecNumCloud | 📋 Planifié |

### Ce qui manque pour Palantir-level

| Gap | Solution | Effort |
|-----|----------|--------|
| UI War Room | React + Sigma.js + Mapbox | 6 mois |
| Migration LLM | Mistral Large + SecNumCloud | 3 mois |
| Connecteurs | SAP, Oracle, APIs premium | 3 mois |
| Multi-utilisateurs | Auth0 + RBAC | 2 mois |

### Vision Long Terme

```
AUJOURD'HUI: Outil d'investigation
     ↓
2 ANS: Plateforme de sécurité économique
     ↓
5 ANS: Infrastructure souveraine de référence pour l'UE
```

---

##  Souveraineté & Sécurité

### Migration Souveraine (Roadmap)

| Composant | Actuel (MVP) | Cible (Souverain) |
|-----------|--------------|-------------------|
| LLM | Gemini (Google/US) | **Mistral Large (FR)** |
| Cloud | Local/GCP | **SecNumCloud (OVH)** |
| Embeddings | Gemini | **CamemBERT / Mistral** |
| Proxies | Publics | **Résidentiels FR** |

### Pourquoi c'est critique

> Le Cloud Act américain permet à la NSA d'accéder aux données stockées chez les providers US.
> 
> Pour les clients Défense/OIV, Vidocq sur Mistral + SecNumCloud = **la seule option légale**.

### Conformité RGPD

- **Base légale:** Intérêt Légitime (prévention fraude, sécurité économique)
- **B2B uniquement:** Données professionnelles, pas vie privée
- **Droit d'opposition:** Suppression de nœud à la demande
- **Privacy by Design:** Architecture prête pour conformité

---

##  Structure du Projet

```
vidocq/
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI app
│   │   ├── routes.py            # Tous les endpoints
│   │   └── dependencies.py      # Injection de dépendances
│   │
│   ├── brain/                   #  Le Cerveau
│   │   ├── core_logic.py        # Classification + Mémoire
│   │   ├── negative_space.py    # Ghost Detector
│   │   ├── contradiction_detector.py  # Guerre Narrative
│   │   ├── wargaming.py         # Simulation Catastrophe
│   │   └── reporter.py          # Rapports géo-sourcés
│   │
│   ├── pipeline/                # Extraction
│   │   ├── discovery.py         # Agent de découverte v1
│   │   ├── discovery_v2.py      # Discovery v2 (cache + parallel) NOUVEAU
│   │   ├── extractor.py         # Extraction LLM (COT v2.0)
│   │   ├── prompts.py           # Prompts versionnés
│   │   ├── tasks.py             # Celery tasks
│   │   └── resolver.py          # Résolution d'entités
│   │
│   ├── storage/                 #  Stockage
│   │   ├── graph.py             # Neo4j (batch APOC)
│   │   ├── vector.py            # Qdrant (768-dim)
│   │   └── cache.py             # Redis cache  NOUVEAU
│   │
│   ├── core/                    #  Core
│   │   ├── embedding.py         # Embeddings Gemini
│   │   ├── ontology.py          # Types entités/relations
│   │   ├── models.py            # Modèles Pydantic
│   │   ├── risk_scoring.py      # Scoring multi-dimensionnel  NOUVEAU
│   │   └── logging.py           # Logs structurés
│   │
│   └── ingestion/               #  Collecte
│       ├── tasks.py             # Tâches Celery
│       ├── stealth.py           # Anti-détection
│       ├── parser.py            # Parsing HTML
│       └── chunking.py          # Découpage sémantique
│
├── docker-compose.yml           # Orchestration (Neo4j, Qdrant, Redis, Postgres)
├── Dockerfile                   # Image Python
├── requirements.txt             # Dépendances
├── .env.example                 # Template configuration
└── README.md                    # Ce fichier
```

---

## Métriques Techniques

### Performance

| Métrique | Valeur |
|----------|--------|
| Temps par investigation | ~2-4 minutes |
| Entités extraites | 50-200 par investigation |
| Relations détectées | 100-500 par investigation |
| Précision initiale | ~85% |
| Précision après RLHF | ~95% (objectif) |

### Scalabilité

| Limite | Valeur |
|--------|--------|
| Max depth N-tier | 3 niveaux |
| Max sources par investigation | 50 URLs |
| Max entités graphe | 100k+ |
| Max vecteurs | 1M+ |

---

## Le Pitch Investisseur (60 secondes)

> *"Vidocq est un agent de renseignement autonome.*
> 
> *Vous lui donnez un nom. Il sait quoi chercher.*
> 
> *Il scrute le web, construit le graphe, détecte les dangers.*
> 
> *Ce que Palantir fait pour les États-Majors à 10 millions, Vidocq le fait pour les ETI à 10.000 euros.*
> 
> *Et surtout : il peut être 100% français, 100% souverain.*
> 
> *Je ne veux pas tuer Palantir. Je veux équiper tous ceux que Palantir ignore."*

---

##  Licence

Proprietary - All Rights Reserved


---

<div align="center">

**VIDOCQ v6.0**

*Le Radar Universel de Renseignement Autonome*

*Cartographier → Mémoriser → Alerter*

---

**Multi-Cas** | **Souverain** | **Agnostique** | **Évolutif**

</div>
