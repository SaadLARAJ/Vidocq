# ShadowMap

**Advanced OSINT Knowledge Graph Platform**

*A high-performance, event-driven OSINT pipeline implementation exploring hybrid NLP/LLM extraction and polyglot persistence.*

This project demonstrates a production-grade architecture for transforming unstructured web data into structured intelligence.

## Requirements

- Docker Engine 24+ & Docker Compose
- Python 3.11+
- OpenAI API Key (or compatible LLM provider)

## Quick Start

### 1. Infrastructure Setup
Start the persistence layer (Neo4j, Postgres, Qdrant, Redis):
```bash
docker-compose up -d
```
*Ensure ports 7474, 7687, 6333, 5432, and 6379 are available.*

### 2. Configuration
Copy the environment template:
```bash
cp ../.env.example .env
```
Edit `.env` to configure your LLM provider and database credentials.

### 3. Installation
```bash
pip install -r requirements.txt
```

## Usage

### Start API Server
```bash
uvicorn src.api.main:app --reload
```
Swagger UI: `http://localhost:8000/docs`

### Start Worker
```bash
celery -A src.ingestion.tasks worker --loglevel=info
```

## Architecture Overview

The system follows an event-driven architecture:

1.  **Ingestion**: `src/ingestion/` - Stealth scraping & semantic chunking.
2.  **Pipeline**: `src/pipeline/` - Hybrid extraction (SpaCy + LLM) & Entity Resolution.
3.  **Storage**: `src/storage/` - Polyglot persistence (Graph, Vector, Relational).
4.  **API**: `src/api/` - REST endpoints.

## Development

- **LLM Integration**: The extractor is currently configured to use a simulation mode for development to prevent API usage. To enable real inference, update `src/pipeline/extractor.py`.
- **Fail-Closed**: The system is designed to halt operations upon storage failure to ensure data consistency.
