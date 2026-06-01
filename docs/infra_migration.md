# InfoDJ Infra Migration Notes

This note captures practical guidance for moving the Docker Compose stack to a server.

## Current Services

Core services:

```text
gateway
ingestion
main-backend
postgres
redis
```

Optional log search services:

```text
logging-loki
logging-promtail
logging-grafana
```

Run the full stack with log search:

```bash
docker compose -f infra/docker-compose.yml up -d \
  gateway ingestion main-backend postgres redis \
  logging-loki logging-promtail logging-grafana
```

## Recommended Initial Server

For the current Docker Compose deployment:

```text
CPU:  2 vCPU
RAM:  8 GB
Disk: 80 GB SSD
```

This gives room for:

```text
PostgreSQL business data
Docker images and volumes
Loki log storage
Grafana
Redis
Kong gateway
Django ingestion and main backend
Future Angular/main service work
```

Minimum workable size for light testing:

```text
CPU:  2 vCPU
RAM:  4 GB
Disk: 40 GB SSD
```

For 30 days of logs or heavier ingestion/API traffic:

```text
CPU:  4 vCPU
RAM:  8-16 GB
Disk: 160+ GB SSD
```

## Postgres vs Loki

PostgreSQL is the application database.

It stores:

```text
companies
source documents
article extractions
business events
strategic turns
ingestion jobs
users/admin data
```

Loki is a log aggregation database, similar in purpose to AWS CloudWatch Logs.

It stores:

```text
container logs
API request logs
scheduler logs
service errors
Kong gateway logs
Postgres container logs
Redis container logs
```

Keep these separate:

```text
Postgres = relational business/application database
Loki     = time-series log aggregation database
```

## Loki Size Expectations

Current Loki retention:

```yaml
retention_period: 168h
```

That means roughly 7 days of logs.

Expected storage for the current stack:

```text
Low traffic/dev:        50 MB - 500 MB for 7 days
Moderate API testing:   500 MB - 2 GB for 7 days
Noisy ingestion/debug:  2 GB - 10 GB for 7 days
```

Main causes of Loki growth:

```text
Long retention, such as 30-90 days
Debug-level logs everywhere
Logging full article text or API payloads
Using high-cardinality labels like request_id, url, or user_id
Keeping Docker JSON logs forever outside Loki
```

Rules:

```text
Do not log full article text.
Do not log full scraped payloads.
Do not add request_id, URL, user_id, or document_id as Loki labels.
Use labels for stable low-cardinality fields like service, container, stream.
```

## Docker Log Rotation

Docker stores container logs separately from Loki. Without rotation, Docker's own JSON logs can grow even if Loki retention is short.

Add this logging policy to long-running services before production:

```yaml
logging:
  driver: json-file
  options:
    max-size: "50m"
    max-file: "3"
```

Recommended next step:

```text
Apply the Docker logging policy to gateway, ingestion, main-backend, postgres, redis, logging-loki, logging-promtail, and logging-grafana.
```

## Log Search

Grafana:

```text
http://localhost:3000
```

Default local login:

```text
admin / admin
```

Loki API:

```text
http://localhost:3100
```

Useful LogQL searches:

```text
{service="ingestion"}
{service="gateway"}
{service="main-backend"}
{service="postgres"}
{service="redis"}
{service="ingestion"} |= "Daily ingestion scheduler"
{service="gateway"} |= "GET /api/ingestion/health"
```

## Migration Checklist

1. Install Docker Engine and Docker Compose on the server.
2. Clone the GitHub repository.
3. Create `infra/env/*.env` files from examples.
4. Set production secrets and non-default passwords.
5. Start Postgres and run Django migrations.
6. Start core services.
7. Start logging services.
8. Verify Kong, ingestion API, Grafana, and Loki readiness.
9. Confirm the daily scheduler logs show the 02:00/04:00/06:00 UTC schedule.
10. Add backups for Postgres volumes.
11. Add Docker log rotation before sustained production runs.
