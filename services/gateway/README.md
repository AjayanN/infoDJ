# InfoDJ Gateway

Minimal Nginx gateway scaffold for the InfoDJ three-service architecture.

## Routes

| Public path | Upstream | Notes |
| --- | --- | --- |
| `GET /health` | Gateway local | Returns `200 ok` without contacting upstream services. |
| `/api/app/*` | `MAIN_BACKEND_URL` | Proxies to the main product backend with the `/api/app/` prefix stripped. |
| `/api/ingestion/*` | `INGESTION_URL` | Proxies to the ingestion API with the `/api/ingestion/` prefix stripped. Intended for admin/internal use. |
| `/admin/*` | `MAIN_BACKEND_URL` | Proxies to the main backend admin/product UI path. |

## Environment

```text
MAIN_BACKEND_URL=http://main-backend:8100
INGESTION_URL=http://ingestion:8001
```

For local host testing without Docker Compose, point these at services running on the host:

```bash
docker build -t infodj-gateway services/gateway
docker run --rm -p 8080:80 \
  -e MAIN_BACKEND_URL=http://host.docker.internal:8100 \
  -e INGESTION_URL=http://host.docker.internal:8001 \
  infodj-gateway
```

On Linux, add `--add-host=host.docker.internal:host-gateway` if Docker does not resolve `host.docker.internal`.

## Health Behavior

`GET /health` is intentionally shallow: it verifies that the gateway container and Nginx worker are serving requests. It does not check the main backend, ingestion service, database, or Redis. Upstream service health checks should live in their own services and can be composed by orchestration later.
