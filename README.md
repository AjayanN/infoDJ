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
- canonical business-model summaries from the latest reviewed Business Model Map at the selected profile date, with profile text used only as a fallback
- company-scoped Latest Moves and Risk Signals, plus sector/country Situation Benchmarks that preserve Company 360 context through pagination

Dashboard ownership is intentionally separate from Company 360. `Company Coverage Overview` provides global cross-company coverage, while Company 360 provides one-company summaries and links into canonical detail features. Opening `Latest moves`, `Risk signals`, or `Compare peers` from Company 360 applies the selected company as dashboard scope; the dashboard visibly identifies that scope and provides a `Show all companies` action.

Profile snapshots are dated and versioned. New snapshots do not overwrite historical company state. Wikidata metadata synchronization creates the initial source-backed profile foundation, and reviewed snapshots can enrich it from filings, investor materials, and permitted official company pages.

Pilot data can be created with:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py seed_netflix
```

Collect a source-backed snapshot from a permitted official company website:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py refresh_company_profile --company netflix
```

The collector checks `robots.txt`, reads structured organization metadata when available, stores the official page as evidence, and leaves unsupported sections unavailable for analyst review.

Backfill the configured 20-company universe with Wikidata organization facts and permitted official-site metadata:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py refresh_company_profiles --limit 20
```

The daily ingestion scheduler runs the same refresh in two batches. Corporate domains are pinned in the company universe so localized consumer URLs do not replace the reviewed source target. Wikidata contributes identity and organization claims, official pages contribute structured metadata, and the latest complete extracted 10-K contributes business model, segments, offerings, customers, revenue mechanisms, leadership, competition, and strategic context. Reviewed company-specific normalization fallbacks cover filing formats that cannot be normalized safely by generic rules. Company 360 combines the latest non-empty reviewed values across those sources.

The configured 20-company universe is evaluated with section-specific semantic checks rather than non-empty values alone. Reviewed core terminology prevents filing headers and parser fragments from being published as business models, brands, or products. The refresh command supports a targeted repair with `--company <slug>`, independently reports Wikidata, official-site, SEC-profile, business-model, and semantic-validation failures, and rebuilds reviewed Business Model Maps after profile refresh.

Run the semantic gate independently with:

```bash
sudo docker compose -f infra/docker-compose.yml run --rm ingestion \
  .venv/bin/python manage.py validate_company_profiles --limit 20
```

The gate requires all 12 Company 360 sections, a meaningful business-model summary without known filing boilerplate, normalized list labels, all nine reviewed Business Model Map component types, and at least one relationship.

Company 360 endpoints:

```text
Ingestion:   GET /api/ingestion/companies/{slug}/profile
Product API: GET /api/app/companies/{slug}/profile
Historical:  GET /api/app/companies/{slug}/profile?as_of=YYYY-MM-DD
Scoped feed: GET /api/app/dashboard?section={section}&company={slug}
```

The Angular workspace opens Company 360 from company search results, autocomplete suggestions, and top-company dashboard rows.

Company 360 smoke check:

```bash
BASE_URL=http://localhost:8080/api/app \
  bash scripts/smoke/phase2_company_360.sh
```

## Business Model Map

Phase 2 Requirement 2 adds a dated, source-backed map of who pays, who uses the offering, what is delivered, how revenue is earned, which channels and partners matter, and which costs and assets support the model.

The Business Model Map includes:

- typed payer, user, offering, revenue, channel, partner, cost, and asset components
- explicit relationship edges such as `PAYS_FOR`, `USES`, `MONETIZED_BY`, and `DELIVERED_THROUGH`
- reported-versus-inferred labels and confidence for every component and relationship
- historical snapshot selection and before/after change analysis
- evidence links, completeness, freshness, and explicit missing-component gaps
- an accessible component-column and relationship-list view instead of relying only on a visual graph

The Netflix pilot seed creates reviewed 2011 and 2022 maps. A reviewed current map can also be generated from the latest reviewed Company 360 profile:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py build_business_model_map --company netflix
```

Collect a permitted current or archived page as dated draft evidence:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py collect_business_model_page \
  --company netflix \
  --url https://example.com/permitted-company-history-page \
  --effective-date 2015-12-31
```

The collector checks `robots.txt`, stores the page as evidence, and requires review before components or relationships are published.

Business Model endpoints:

```text
Ingestion: GET /api/ingestion/companies/{slug}/business-model
Product:   GET /api/app/companies/{slug}/business-model
History:   GET /api/app/companies/{slug}/business-model?as_of=YYYY-MM-DD&compare_to=YYYY-MM-DD
```

Open the map from the `Business model map` action on Company 360. Once opened, `Business Model` remains available in the left navigation.

Business Model smoke check:

```bash
BASE_URL=http://localhost:8080/api/app \
  bash scripts/smoke/phase2_business_model.sh
```

## Operating KPI Tracker

Phase 2 Requirement 3 tracks company-specific operating measures with their definitions, units, cadence, scope, aliases, source evidence, quality conditions, and comparability rules.

The tracker includes:

- reported and InfoDJ-calculated KPI series with visible formulas
- quarterly, annual, monthly, and event-aligned metric definitions
- segment and geography filters plus comparable-period controls
- visible estimate, restatement, non-comparable, definition-change, discontinued-disclosure, and missing-period states
- movement and target-crossing alerts, related strategic-event overlays, definition history, and export-ready rows
- peer comparisons only after definition and unit comparability are reviewed

The Netflix pilot contains source-backed 2022 paid streaming memberships, regional Q4 observations, and calculated quarter-over-quarter growth. Every company in the current 20-company universe also receives annual and quarterly SEC Company Facts series for every stored concept. Those baseline series are labeled `Company-wide reported financial context`; they are not presented as company-specific operating KPIs such as subscribers, stores, deliveries, occupancy, or production.

Open any company from search or Company 360 and select `Operating KPI tracker`; after loading, `Operating KPIs` remains in the left navigation.

Refresh the official SEC data and all-company tracker coverage idempotently. KPI series are rebuilt automatically after each company’s facts are stored:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py ingest_sec_companyfacts --all --limit 500
```

`build_companyfacts_kpis --all` remains available to rebuild from facts already stored in the database without making network requests.

Companies outside the United States require equivalent connectors for their home regulator, exchange filings, and official investor-relations downloads. The same KPI dictionary and observation schema can ingest those sources while retaining their regulator and evidence links.

Collect a permitted official CSV with `period_end`, `value`, and optional period/scope columns. Imported records remain inactive and non-comparable until analyst review:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py collect_kpi_csv \
  --company netflix \
  --url https://example.com/permitted-official-kpi.csv \
  --metric-slug paid-memberships \
  --metric-name "Paid memberships" \
  --unit "million memberships"
```

When no structured download exists, the equivalent `collect_kpi_html_table` command can read the first permitted investor-relations table with `period_end` and `value` headers. Structured CSV remains the preferred source.

Operating KPI endpoints:

```text
Ingestion: GET /api/ingestion/companies/{slug}/operating-kpis
Product:   GET /api/app/companies/{slug}/operating-kpis
Filters:   ?metric={slug}&segment={segment}&geography={geography}&start=YYYY-MM-DD&end=YYYY-MM-DD&comparable_only=true
```

Authenticated smoke check:

```bash
BASE_URL=http://localhost:8080/api/app \
  bash scripts/smoke/phase2_operating_kpis.sh
```

## Management Promise Tracker

Phase 2 Requirement 4 records measurable management commitments, guidance, targets, aspirations, and strategic claims without treating them as equivalent. Commitments and targets require a defined outcome or deadline; guidance describes an expected reporting result; aspirations remain non-binding; strategic claims describe management's intended direction. Execution steps belong to the Strategy Milestone Tracker rather than this register.

The tracker includes:

- original statement, speaker, role, statement date, target window, scope, conditions, and source evidence
- announced, in-progress, achieved, partially achieved, missed, delayed, revised, withdrawn, no-longer-disclosed, too-early, and unverifiable states
- append-only reviewed status updates and deadline revisions
- visible evaluation rules, confidence, and links to canonical KPIs and strategic turns
- status, promise-type, due-soon, overdue, and historical `as_of` filters
- unpublished `NEEDS_REVIEW` candidates from source-backed KPI targets
- explicit unavailable states when a company has no reviewed commitments

Automated collection never publishes negative delivery classifications. Candidates remain unpublished until an analyst reviews the original statement, metric definition, conditions, deadline, and outcome evidence. Admin users can correct, reject, publish, and add reviewed status updates through the Django admin.

Build candidates from existing source-backed KPI targets:

```bash
sudo docker compose -f infra/docker-compose.yml run --rm ingestion \
  .venv/bin/python manage.py build_management_promises --company netflix
```

Management Promise endpoints:

```text
Ingestion: GET /companies/{slug}/management-promises
Product:   GET /api/app/companies/{slug}/management-promises
Filters:   ?status={status}&type={type}&due=due_soon|overdue&as_of=YYYY-MM-DD&promise={slug}
```

Open the tracker from `Management promise tracker` on Company 360. The Netflix pilot includes a reviewed launch commitment with its original statement, evaluation rule, evidence, linked strategic turn, and achieved status update.

Authenticated smoke check:

```bash
BASE_URL=http://localhost:8080/api/app \
  bash scripts/smoke/phase2_management_promises.sh
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

If the frontend reports `Ingestion data is currently unavailable`, verify `gateway`, `ingestion`, and `main-backend` are running. The dashboard proxy requests company coverage, jobs, and dashboard data concurrently; `/api/ingestion/companies` uses independent grouped counts to avoid cross-product timeouts as KPI coverage grows.

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
