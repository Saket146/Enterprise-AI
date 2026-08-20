# Enterprise AI Operating System

Phase 3 delivers a guardrailed multi-agent enterprise operating system: human-in-the-loop workflow automation, enterprise analytics, RBAC/audit controls, prompt-injection defenses, AI evaluation, observability, and a six-service Docker deployment.

## Quick start

Copy `.env.example` to `.env`, set production-safe secrets, then run `docker compose up --build -d`. Open the web console at `http://localhost:5173` and the API documentation at `http://localhost:8000/docs`.

See [architecture](docs/PHASE_3_ARCHITECTURE.md), [system design](docs/SYSTEM_DESIGN.md), [API](docs/API.md), [deployment](docs/DEPLOYMENT.md), [database](docs/DATABASE.md), [agents](docs/AI_AGENTS.md), and [user guide](docs/USER_GUIDE.md).

## Overview

Enterprise AI Operating System is a production-grade multi-agent AI platform that simulates an enterprise organization.

The platform combines:

- Multi-Agent AI
- LangGraph
- Retrieval-Augmented Generation
- Knowledge Graphs
- PostgreSQL
- Qdrant
- Neo4j
- Redis
- Enterprise Security
- Explainable AI

---

## Architecture

Frontend

↓

FastAPI Gateway

↓

LangGraph Multi-Agent Engine

↓

Enterprise Databases

- PostgreSQL
- Neo4j
- Qdrant
- Redis

---

## Status

Phase 1 ✅

Project Initialization# Enterprise-AI
