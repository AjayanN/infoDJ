# InfoDJ Service Architecture

InfoDJ should be split into three services.

For the concrete service/repo/port/API/deployment format, see
`docs/service_architecture_format.md`.

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

The daily job is idempotent by company, source, and date. If a successful job already exists today for a company/source pair, that source step is skipped.

Useful options:

```bash
.venv/bin/python services/ingestion/manage.py daily_company_update --limit 20 --sec-limit 30 --wikipedia-limit 10
.venv/bin/python services/ingestion/manage.py daily_company_update --skip-gdelt
.venv/bin/python services/ingestion/manage.py daily_company_update --skip-event-extraction
```

For production scheduling, run this from cron, systemd timer, Kubernetes CronJob, or Celery Beat.

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

## Daily Job Rule

The ingestion service should only fetch a source for a company once per day unless forced manually.

Current implementation:

- `daily_company_update` calls `ingest_sector_companies` with `daily_idempotent=True`.
- `ingest_sector_companies` skips a source when `ingestion_ingestionjob` already has a `SUCCEEDED` row for that company, source, and current date.
- Event extraction can safely rerun because rule events are rebuilt from available source documents and cached extractions.
