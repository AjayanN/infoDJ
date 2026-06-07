# InfoDJ

InfoDJ is a company intelligence workspace for tracking what changed inside public companies, the evidence behind those changes, and the strategic patterns that show up across companies.

The current product includes:

- Django ingestion service for company metadata, source documents, events, strategic turns, SEC companyfacts, market prices, and dashboard quality gates.
- Django main backend for authenticated product APIs and ingestion API proxying.
- Angular frontend for dashboard, search, impact, pattern, scorecard, compare, and account views.
- Source-backed Company 360 profiles with historical snapshots, section gaps, recent events and turns, financial context, evidence, and conflict/change visibility.
- Kong gateway plus Postgres, Redis, Loki, Promtail, and Grafana via Docker Compose.

## Repository Layout

```text
services/
  ingestion/       Django ingestion, curation, market data, SEC facts, dashboard data APIs
  main/backend/    Django product backend, auth, subscriptions, dashboard/search proxy APIs
  main/frontend/   Angular frontend
  gateway/         Kong gateway config

infra/
  docker-compose.yml
  env/
  logging/

docs/
scripts/
```

## Run With Docker Compose

Create the env files from examples first:

```bash
cp infra/env/ingestion.env.example infra/env/ingestion.env
cp infra/env/main.env.example infra/env/main.env
```

Optional API keys for richer data:

```text
FMP_API_KEY=
ALPHA_VANTAGE_API_KEY=
```

Start the working stack:

```bash
sudo docker compose -f infra/docker-compose.yml up -d \
  gateway ingestion main-backend postgres redis \
  logging-loki logging-promtail logging-grafana main-frontend
```

Open the frontend:

```text
http://localhost:4200
```

Useful service URLs:

```text
Frontend:       http://localhost:4200
Main backend:   http://localhost:8100
Gateway:        http://localhost:8080
Ingestion API:  http://localhost:8001
Grafana:        http://localhost:3000
Postgres:       localhost:15432
Redis:          localhost:16379
```

## Dashboard Data Pipeline

The dashboard data is source-backed and quality-gated. The ingestion service builds these surfaces:

- latest strategic moves
- strategic patterns
- risk signals
- market impact windows
- strategy scorecards
- comparable turns
- company situations
- source confidence and source gaps

Key ingestion commands:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py daily_company_update --limit 20 --skip-gdelt

sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py ingest_sec_companyfacts --all --limit 500

sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py ingest_market_prices --all --include-benchmarks --provider auto

sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py rebuild_specific_turns

sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py audit_data_quality
```

Market data provider selection:

- `FMP_API_KEY` enables Financial Modeling Prep prices.
- `ALPHA_VANTAGE_API_KEY` enables Alpha Vantage fallback.
- Stooq is available as a no-key fallback where supported.

## Dashboard Pagination

The authenticated main backend proxies paginated ingestion data to the frontend.

Search supports independent pagination for:

- companies
- business events
- strategic turns

Dashboard sections return:

```text
page
page_size
total_pages
has_next
has_previous
eligible_count
raw_count
excluded_count
```

This distinction matters because company cards show raw totals, while search and dashboard lists show eligible, quality-gated rows.

## Company 360 Profile

Phase 2 Requirement 1 adds a complete company starting page that explains what the company is, how it operates, what changed recently, and which profile sections still lack reviewed evidence.

Company 360 includes:

- company identity, description, aliases, sector, country, website, and founding date
- business model, subsidiaries, brands, segments, products, customer groups, revenue sources, geographies, leadership, competitors, and strategic priorities
- latest source-backed business events and strategic turns
- latest available SEC financial facts
- profile completeness, freshness, historical changes, and same-date source conflicts
- source evidence and explicit section-level gaps instead of placeholder content
- historical snapshot selection, peer/dashboard entry points, and a printable company brief

Profile snapshots are dated and versioned. New snapshots do not overwrite historical company state. Wikidata metadata synchronization creates the initial source-backed profile foundation, and reviewed snapshots can enrich it from filings, investor materials, and permitted official company pages.

Pilot data can be created with:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py seed_netflix
```

Collect a draft snapshot from a permitted official company website:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py refresh_company_profile --company netflix
```

The collector checks `robots.txt`, reads structured organization metadata when available, stores the official page as evidence, and leaves unsupported sections unavailable for analyst review.

Company 360 endpoints:

```text
Ingestion:   GET /api/ingestion/companies/{slug}/profile
Product API: GET /api/app/companies/{slug}/profile
Historical:  GET /api/app/companies/{slug}/profile?as_of=YYYY-MM-DD
```

The Angular workspace opens Company 360 from company search results, autocomplete suggestions, and top-company dashboard rows.

Company 360 smoke check:

```bash
BASE_URL=http://localhost:8080/api/app \
  bash scripts/smoke/phase2_company_360.sh
```

## Test Commands

Run tests inside Docker Compose:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py test apps.ingestion

sudo docker compose -f infra/docker-compose.yml exec -T main-backend \
  python manage.py test apps.search

sudo docker compose -f infra/docker-compose.yml exec -T main-frontend \
  npm run build
```

For complete branch verification against freshly built images, run the suites sequentially. Both Django services otherwise default to the same PostgreSQL test database name.

```bash
sudo docker compose -f infra/docker-compose.yml build ingestion main-backend main-frontend

sudo docker compose -f infra/docker-compose.yml run --rm ingestion \
  .venv/bin/python manage.py test --noinput

sudo docker compose -f infra/docker-compose.yml run --rm \
  -e DATABASE_URL=sqlite:///tmp/main-test.sqlite3 \
  main-backend python manage.py test --noinput

sudo docker compose -f infra/docker-compose.yml run --rm main-frontend \
  npm test

sudo docker compose -f infra/docker-compose.yml run --rm main-frontend \
  npm run build
```

The frontend test command executes TypeScript unit tests. The production build separately validates Angular templates, strict typing, and bundle generation.

Frontend smoke check:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T main-frontend \
  node -e "fetch('http://localhost:4200/').then(async r => console.log(r.status, (await r.text()).includes('infodj-root')))"
```

## Data Quality Notes

Not every ingested row is dashboard-grade. The dashboard API separates:

- raw source/event/turn counts
- eligible rows that pass quality gates
- source gaps explaining missing or incomplete dashboard data

Current known gaps to keep improving:

- Some companies may lack market price windows if provider quotas or ticker coverage block backfills.
- Pattern and compare dashboards currently use eligible turn types; a reviewed strategy taxonomy is still needed.
- Company situation matching is still thin and should be enriched beyond sector/country.
- Scorecards are evidence-backed where market and SEC facts exist, but may be partial for incomplete event windows.

See `plan_to_upgrade_ingestion.md` for the ingestion upgrade plan.
