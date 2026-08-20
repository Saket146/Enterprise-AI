# Deployment guide

1. Copy `.env.example` to `.env` and replace passwords and JWT secret with unique production values.
2. Build and start: `docker compose up --build -d`.
3. Confirm `http://localhost:8000/health`, then open `http://localhost:5173`.
4. Use the default administrator only for bootstrap, then change its password and create named admins.

The compose stack runs frontend, backend, PostgreSQL, Qdrant, Neo4j, and Redis. Volumes retain database data. Back up PostgreSQL and the Qdrant/Neo4j volumes before upgrades.

For a real production environment, terminate TLS at a reverse proxy, keep databases on private networks, use a managed secret store, configure backup/restore tests, and send audit logs to immutable central storage.
