# InfoDJ Service Architecture

InfoDJ should be split into three services.

For the concrete service/repo/port/API/deployment format, see
`docs/service_architecture_format.md`.

For server sizing and infra migration notes, see `docs/infra_migration.md`.

## 1. Ingestion and Curation Service

The ingestion and curation service lives under `services/ingestion`.

Responsibilities:

- Resolve company metadata.
- Discover public sources from SEC EDGAR, Wikipedia references, GDELT, and later additional sources.
- Extract source text.
- Generate reviewable business events and strategic turns.
- Store curated source and event tables in PostgreSQL.
- Run as a scheduled daily job.

Primary daily entrypoint:

```bash
.venv/bin/python services/ingestion/manage.py daily_company_update
```

Long-running scheduler entrypoint:

```bash
.venv/bin/python services/ingestion/manage.py scheduled_daily_update --at 02:00 --timezone UTC --limit 20
```

Docker Compose runs the ingestion API and scheduler in one container:

```bash
.venv/bin/python services/ingestion/manage.py run_ingestion_api_with_scheduler --host 0.0.0.0 --port 8001 --scheduler-timezone UTC --limit 20 --batch-size 10 --include-gdelt --include-market-data --include-financial-facts --include-macro-context --include-quality-scoring --split-batches
```

Default Docker Compose scheduler slots:

```text
02:00 UTC -> companies 1-10
04:00 UTC -> companies 11-20
06:00 UTC -> retry failed source jobs only
```

The daily job is idempotent by company, source, and date. If a successful job already exists today for a company/source pair, that source step is skipped.

Useful options:

```bash
.venv/bin/python services/ingestion/manage.py daily_company_update --limit 20 --sec-limit 30 --wikipedia-limit 10
.venv/bin/python services/ingestion/manage.py daily_company_update --skip-gdelt
.venv/bin/python services/ingestion/manage.py daily_company_update --skip-event-extraction
.venv/bin/python services/ingestion/manage.py daily_company_update --include-market-data --include-financial-facts --include-macro-context --include-quality-scoring
```

The dashboard/data implementation plan lives in `dashboard+data_todo.md`.

Data rule:

```text
No placeholder data. Missing market, financial, macro, or source-confidence data must be marked unavailable until a real source integration fills it.
```

Planned free source integrations:

- SEC companyfacts/frames for financial metrics.
- Stooq historical CSV/download data for daily prices and benchmarks.
- FRED API for macro context when a free API key is configured.
- GDELT DOC 2.0, Wikipedia/Wikimedia references, SEC filings, and allowed company pages for event discovery.

For the Docker Compose server deployment, the `ingestion` service runs the API and scheduler together to keep the always-on service count low. For larger production deployments, the scheduler can be split into Kubernetes CronJob, systemd timer, cron, Celery Beat, or a separate worker container.

## 2. API Gateway

The API gateway should sit in front of internal services.

Responsibilities:

- Authentication and authorization.
- Rate limiting.
- Request routing.
- API versioning.
- Shared logging and request tracing.
- Public API boundary for the Angular frontend and future external consumers.

Recommended implementation:

- Use Kong Gateway in DB-less mode for the first implementation.
- Route `/api/ingestion/*` to the ingestion service.
- Route `/api/app/*` and `/admin/*` to the main service backend.

## 3. Main Product Service

The main service should own the user-facing application.

Responsibilities:

- Angular admin and analyst UI.
- User accounts and permissions.
- Review workflows.
- Published timelines and company profiles.
- Search and filtering over curated events.
- Future founder/analyst product features.

Recommended implementation:

- Angular frontend.
- Django backend initially, because Django Admin and ORM are already useful.
- Transition specific high-throughput API surfaces to FastAPI later if needed.

Profile images are owned by the main service. The Django backend stores avatar
file paths on `accounts.UserProfile` and stores the actual files under
`MEDIA_ROOT`. In local Docker Compose this is `/app/media`, backed by the
`main_media` Docker volume. Kong routes `/media/*` to `main-backend` so the
Angular frontend can render saved avatars after login. The main backend should
set `MEDIA_PUBLIC_BASE_URL` to the public gateway origin, such as
`http://localhost:8080`, so serialized avatar URLs are browser-accessible.

## 4. Log Search Service

The log search service provides a Splunk-like search surface for container logs.

Recommended implementation for the current Docker Compose deployment:

- Grafana Loki as the log store.
- Promtail as the Docker log collector.
- Grafana as the query/search UI.

Local endpoints:

```text
Grafana: http://localhost:3000
Loki API: http://localhost:3100
```

Default Grafana login for local/dev:

```text
admin / admin
```

Useful LogQL searches:

```text
{service="ingestion"}
{service="gateway"}
{service="main-backend"}
```

## Data Boundary

PostgreSQL remains the system of record for curated data:

- `companies_company`
- `ingestion_sourcedocument`
- `ingestion_articleextraction`
- `curation_businessevent`
- `curation_strategicturn`
- `curation_strategicturnsource`
- `ingestion_ingestionjob`

The main service should read curated data through API endpoints, not by directly mutating ingestion tables.

Sprint 1 dashboard/search boundary:

- Ingestion owns curated-data search because company, event, and strategic-turn tables live there.
- Main backend exposes the product-facing endpoints under `/api/app/*`.
- Angular calls only the main backend through Kong.

Current dashboard/search endpoints:

```text
GET /api/app/dashboard
GET /api/app/categories
GET /api/app/search?q=netflix&language=en
GET /api/app/search/suggest?q=net&language=en
```

Internal ingestion endpoints:

```text
GET /api/ingestion/search?q=netflix&language=en
GET /api/ingestion/search/suggest?q=net&language=en
```

Search implementation:

- Postgres full-text search is used for business events and strategic turns when running on PostgreSQL.
- `pg_trgm` is enabled for company suggestions.
- SQLite/local test fallback uses case-insensitive matching so tests can run without Postgres-specific extensions.
- Search returns curated English-facing fields and avoids raw article text.

## Daily Job Rule

The ingestion service should only fetch a source for a company once per day unless forced manually.

Current implementation:

- `daily_company_update` calls `ingest_sector_companies` with `daily_idempotent=True`.
- `ingest_sector_companies` skips a source when `ingestion_ingestionjob` already has a `SUCCEEDED` row for that company, source, and current date.
- Event extraction can safely rerun because rule events are rebuilt from available source documents and cached extractions.
- `scheduled_daily_update` is the persistent scheduler process. In Docker Compose, `run_ingestion_api_with_scheduler` starts it beside the ingestion API in the same container.
