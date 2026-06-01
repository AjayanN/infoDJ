# InfoDJ Service Architecture Format

This is the target service format for moving InfoDJ from one Django MVP into a three-service system.

## Service Map

| Service | Name | Purpose | Runtime | Owns data? | Public? |
| --- | --- | --- | --- | --- | --- |
| 1 | `infodj-ingestion` | Daily source collection, extraction, curation candidates, strategic turns | Django management commands + Celery-ready Django app | Yes, curated ingestion DB | Internal |
| 2 | `infodj-gateway` | API gateway, auth boundary, routing, rate limiting, observability | Kong Gateway in DB-less mode | No | Public |
| 3 | `infodj-main` | Angular admin/product UI and product backend | Angular + Django backend | Owns users/workflows; reads ingestion data through APIs | Public through gateway |

## Repository Format

Recommended initial repo layout:

```text
InfoDJ/
  services/
    ingestion/          # current repo content can become this service
    gateway/            # gateway config or lightweight app
    main/               # Angular frontend + Django backend
  infra/
    docker-compose.yml
    env/
      ingestion.env.example
      gateway.env.example
      main.env.example
    gateway/
    postgres/
  docs/
    service_architecture_format.md
```

Current repo can stay as `infodj-ingestion` for now. When we create the gateway and main app, either use a monorepo structure above or separate repos:

```text
infodj-ingestion
infodj-gateway
infodj-main
```

For the next phase, monorepo is simpler because service wiring, Docker Compose, and local development stay in one place.

## Service 1: Ingestion And Curation

Current location:

```text
/home/famei/InfoDJ/services/ingestion
```

Primary responsibilities:

- Maintain company universe.
- Pull source metadata and source documents.
- Run daily source refresh.
- Extract source text.
- Produce `BusinessEvent` and `StrategicTurn` records.
- Preserve evidence through `source_claim`, `actual_change`, filing dates, and source counts.

Primary command:

```bash
.venv/bin/python services/ingestion/manage.py daily_company_update
```

Daily idempotency rule:

```text
Skip a company/source for the current date when ingestion_ingestionjob already has:
company_id = company
source = source name
status = SUCCEEDED
created_at::date = today
```

Important commands:

```bash
.venv/bin/python services/ingestion/manage.py ingest_sector_companies --limit 20 --sec-limit 80 --wikipedia-limit 25 --full-history
.venv/bin/python services/ingestion/manage.py extract_sector_events --limit 20 --forms 10-K --filing-limit 8 --reuse-extractions
.venv/bin/python services/ingestion/manage.py daily_company_update --limit 20 --skip-gdelt
```

Internal API routes to expose later:

```text
GET  /internal/health
GET  /internal/companies
GET  /internal/companies/{slug}/events
GET  /internal/companies/{slug}/strategic-turns
GET  /internal/jobs
POST /internal/jobs/daily-update
POST /internal/jobs/company/{slug}/refresh
```

## Service 2: API Gateway

Recommended first implementation:

```text
Kong Gateway in DB-less mode
```

Gateway responsibilities:

- TLS termination when deployed behind real certificates.
- Route requests to internal services.
- Rate limit public APIs.
- Add auth middleware or forward auth to main service.
- Keep ingestion service private.

Current gateway config:

```text
services/gateway/kong.yml
```

Initial route map:

```text
/api/app/*          -> infodj-main backend
/api/ingestion/*    -> infodj-ingestion internal API, admin-only
/admin/*            -> infodj-main admin/product UI
/health             -> gateway health
```

Example ports:

```text
gateway:           8080 public local port
main-backend:      8100 internal
main-angular:      4200 dev only
ingestion-api:     8001 internal
postgres:          5432 internal/local
redis:             6379 internal/local
```

## Service 3: Main Product Service

Recommended format:

```text
main/
  backend/
    manage.py
    config/
    apps/
      accounts/
      review/
      timelines/
      search/
  frontend/
    angular.json
    src/
      app/
        admin/
        companies/
        events/
        strategic-turns/
```

Backend responsibilities:

- Users and permissions.
- Review workflow.
- Published company profile APIs.
- Search/filter APIs.
- Optional local projections of curated ingestion data.

Frontend responsibilities:

- Angular admin UI.
- Company event review table.
- Strategic-turn timeline.
- Source evidence viewer.
- Review controls: approve, reject, merge, publish.

Main service should not directly own source ingestion. It should call ingestion APIs or consume read-only views.

## Data Ownership

Ingestion DB owns:

```text
companies_company
ingestion_sourcedocument
ingestion_articleextraction
ingestion_ingestionjob
curation_businessevent
curation_strategicturn
curation_strategicturnsource
```

Main service owns:

```text
users
teams
roles
review_assignments
saved_filters
published_profiles
product_settings
```

Preferred data sharing:

```text
main service -> gateway -> ingestion internal API -> ingestion DB
```

Avoid direct writes from the main service into ingestion tables.

## Docker Compose Format

Target local services:

```yaml
services:
  gateway:
    build: ./services/gateway
    ports:
      - "8080:8000"
      - "8002:8001"

  ingestion:
    build: ./services/ingestion
    command: .venv/bin/python manage.py run_ingestion_api_with_scheduler --host 0.0.0.0 --port 8001 --scheduler-timezone UTC --limit 20 --batch-size 10 --include-gdelt --split-batches
    env_file: ./infra/env/ingestion.env
    depends_on:
      - postgres
      - redis

  ingestion-daily:
    build: ./services/ingestion
    command: .venv/bin/python manage.py daily_company_update --limit 20 --skip-gdelt
    env_file: ./infra/env/ingestion.env
    depends_on:
      - postgres
      - redis

  main-backend:
    build: ./services/main/backend
    env_file: ./infra/env/main.env
    depends_on:
      - postgres

  main-frontend:
    build: ./services/main/frontend
    ports:
      - "4200:4200"

  postgres:
    image: postgres:16

  redis:
    image: redis:7

  logging-loki:
    image: grafana/loki:3.2.1
    ports:
      - "3100:3100"

  logging-promtail:
    image: grafana/promtail:3.2.1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro

  logging-grafana:
    image: grafana/grafana:11.2.2
    ports:
      - "3000:3000"
```

For the Docker Compose deployment, the `ingestion` service runs both the API and scheduler. For larger production deployments, the scheduler can be split into one of:

- Kubernetes CronJob
- systemd timer
- cron
- Celery Beat

## Environment Variables

Ingestion service:

```text
DJANGO_SECRET_KEY=
DJANGO_DEBUG=false
DATABASE_URL=postgres://...
CELERY_BROKER_URL=redis://redis:6379/0
SEC_USER_AGENT=InfoDJ/0.1 business-event-research contact@example.com
```

Gateway:

```text
KONG_DATABASE=off
KONG_DECLARATIVE_CONFIG=/usr/local/kong/declarative/kong.yml
KONG_PROXY_LISTEN=0.0.0.0:8000
KONG_ADMIN_LISTEN=0.0.0.0:8001
```

Main service:

```text
DATABASE_URL=postgres://...
INGESTION_API_URL=http://gateway/api/ingestion
JWT_SECRET=
```

## Daily Job Contract

Daily job behavior:

```text
1. For each company in active company universe:
2. Skip source if company/source already succeeded today.
3. Fetch new SEC/Wikipedia/GDELT source metadata.
4. Store only non-duplicate source rows.
5. Reuse existing article extractions where available.
6. Rebuild rule-generated curation events.
7. Preserve review status for manually reviewed/published rows later.
8. Record job success/failure in ingestion_ingestionjob.
```

Current MVP caveat:

```text
Rule event rebuild currently deletes and rebuilds rule-generated rows.
Before production review workflow, add stable event fingerprints so approved rows are updated rather than recreated.
```

## API Gateway Contract

Initial public routes:

```text
GET /api/app/companies
GET /api/app/companies/{slug}
GET /api/app/companies/{slug}/timeline
GET /api/app/events?company=&sector=&event_type=&status=
POST /api/app/events/{id}/review
```

Internal/admin-only routes:

```text
POST /api/ingestion/jobs/daily-update
POST /api/ingestion/companies/{slug}/refresh
GET  /api/ingestion/jobs
GET  /api/ingestion/jobs/{id}
```

## Next Build Order

1. Keep current repo as `infodj-ingestion`.
2. Add read-only JSON APIs to ingestion for companies, events, turns, and jobs.
3. Create `infodj-gateway` with route config.
4. Create `infodj-main` with Angular frontend and Django backend.
5. Build the admin review table around `curation_businessevent`.
6. Add stable event fingerprints before letting users approve/publish rows.
