# InfoDJ Gateway

Kong Gateway scaffold for the InfoDJ service architecture.

This uses Kong in DB-less declarative mode. It does not require a Kong database
or an Enterprise license for the basic routing used here.

## Routes

| Public path | Upstream | Notes |
| --- | --- | --- |
| `GET /health` | Gateway local | Returns JSON from Kong using the request-termination plugin. |
| `/api/app/*` | `main-backend:8100` | Proxies to the main product backend and preserves the `/api/app` prefix. |
| `/api/ingestion/*` | `ingestion:8001` | Proxies to the ingestion API and strips `/api/ingestion`. Intended for admin/internal use. |
| `/admin/*` | `main-backend:8100` | Proxies to the main backend admin path. |

## Local Docker Compose

```bash
docker compose -f infra/docker-compose.yml up gateway ingestion main-backend postgres redis
```

Gateway proxy:

```text
http://localhost:8080
```

Kong Admin API:

```text
http://localhost:8002
```

## Configuration

Routes and plugins are configured in:

```text
services/gateway/kong.yml
```

## Frontend Usage

The Angular frontend should call the gateway, not the backend services directly:

```text
GET /api/app/...
GET /api/ingestion/companies
GET /api/ingestion/companies/netflix/events
```

Kong routes these requests to the correct backend service.
