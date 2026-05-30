# InfoDJ Local Infra

This folder wires the documented three-service architecture for local development.

Services:

- `gateway`: Kong API gateway public entrypoint on port `8080`
- `ingestion`: current Django ingestion service on port `8001`
- `ingestion-daily`: one-shot daily ingestion job profile
- `main-backend`: placeholder main Django backend on port `8100`
- `main-frontend`: placeholder Angular frontend on port `4200`
- `postgres`: PostgreSQL 16
- `redis`: Redis 7

Before running, create env files from examples:

```bash
cp infra/env/ingestion.env.example infra/env/ingestion.env
cp infra/env/main.env.example infra/env/main.env
cp infra/env/gateway.env.example infra/env/gateway.env
```

Run core services:

```bash
docker compose -f infra/docker-compose.yml up gateway ingestion main-backend postgres redis
```

Run the daily ingestion job:

```bash
docker compose -f infra/docker-compose.yml --profile jobs run --rm ingestion-daily
```

Gateway routes:

```text
GET /health
/api/ingestion/* -> ingestion service
/api/app/*       -> main backend
/admin/*         -> main backend admin
```

Kong Admin API is exposed locally on:

```text
http://localhost:8002
```
