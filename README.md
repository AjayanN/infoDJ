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

Global search is company-neutral and searches companies, source-backed events, and eligible strategic turns. The dashboard scorecard feed is coverage-balanced: the best eligible turn from each configured company appears before additional turns. Comparison groups include only quality-gated turns from at least two distinct companies, with company and event-date context shown in the frontend.

Daily event extraction now rebuilds specific source-backed turns after curation. Validate the complete dashboard universe with:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py validate_dashboard_coverage

BASE_URL=http://localhost:8080/api/app \
  bash scripts/smoke/sprint1_dashboard_search.sh
```

Dashboard foundation verification on June 14, 2026 passed for all 20 configured companies: every company was searchable and represented in the scorecard feed, with 60 eligible scorecards and six cross-company comparison groups. Full suites passed with 44 ingestion tests, 30 main-backend tests, 7 frontend tests, and a successful frontend production build.

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
- explicit unavailable states when selected filters have no matching reviewed commitments

Automated collection never publishes negative delivery classifications. Candidates remain unpublished until an analyst reviews the original statement, metric definition, conditions, deadline, and outcome evidence. Admin users can correct, reject, publish, and add reviewed status updates through the Django admin.

Build reviewed filing-backed statements for the full configured universe, plus candidates from source-backed KPI targets:

```bash
sudo docker compose -f infra/docker-compose.yml run --rm ingestion \
  .venv/bin/python manage.py build_management_promises

sudo docker compose -f infra/docker-compose.yml run --rm ingestion \
  .venv/bin/python manage.py validate_management_promises
```

Management Promise endpoints:

```text
Ingestion: GET /companies/{slug}/management-promises
Product:   GET /api/app/companies/{slug}/management-promises
Filters:   ?status={status}&type={type}&due=due_soon|overdue&as_of=YYYY-MM-DD&promise={slug}
```

Open the tracker from `Management promise tracker` on Company 360. Every one of the 20 configured companies must have at least one reviewed, published, filing-backed management statement. The refresh scheduler rebuilds these records from the newest stored 10-K containing the reviewed statement, and semantic validation fails when any configured company lacks source evidence, original statement text, outcome evidence, or an evaluation rule.

Company-facing functionality is accepted against the complete configured company universe, not a single-company pilot or sample. The authenticated Management Promise smoke test requests and validates all 20 companies.

Requirement 4 verification: all 20 companies passed live source/evidence validation and authenticated API smoke checks on June 14, 2026. Full suites passed with 44 ingestion tests, 30 main-backend tests, 7 frontend tests, and a successful frontend production build.

Authenticated smoke check:

```bash
BASE_URL=http://localhost:8080/api/app \
  bash scripts/smoke/phase2_management_promises.sh
```

## Earnings Intelligence

Phase 2 Requirement 5 provides a reviewed Earnings Intelligence baseline for all 20 configured companies. Each period preserves its SEC 10-Q source, groups filed Company Facts by accession and reporting period, shows selected metrics and prior-period changes, connects canonical KPI observations, and links reviewed promises, strategic turns, and risk signals within the period.

Official SEC Exhibit 99 earnings releases or shareholder letters are collected for the latest period and remain `NEEDS_REVIEW` until exact operating-driver excerpts match the reviewed editorial catalog. Filing facts, management explanation, InfoDJ interpretation, and unanswered questions remain separate. Netflix also has a reviewed Q1 2026 forecast-versus-actual pilot with separate prior-quarter forecast and current-quarter actual sources; other companies show an explicit unavailable state when comparable reviewed numeric guidance has not been mapped.

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py build_earnings_intelligence --collect-exhibits

sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py publish_reviewed_earnings_excerpts

sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py validate_earnings_intelligence

BASE_URL=http://localhost:8080/api/app \
  bash scripts/smoke/phase2_earnings_intelligence.sh
```

```text
Ingestion: GET /companies/{slug}/earnings?period=FY2026-Q1
Product:   GET /api/app/companies/{slug}/earnings?period=FY2026-Q1
```

Open `Earnings intelligence` from Company 360 for the quarterly timeline, measured results, reviewed management drivers, KPI movement, forecast-versus-actual comparisons where available, linked strategy and risks, distinct evidence sources, evidence gaps, and print export.

Requirement 5 verification on June 14, 2026: ingestion `52/52`, main backend `32/32`, frontend `7/7`, production build passed, all-company validator passed, and the authenticated gateway smoke test passed for all 20 companies.

## Strategy Milestone Tracker

Phase 2 Requirement 6 turns reviewed management commitments into execution milestones with explicit origin, status, due-date precision, success conditions, blockers, status history, and source evidence. The baseline covers all 20 configured companies and does not infer due dates when management did not provide one.

Milestone origins are separated as management-announced, regulator-defined, contractual, or analyst-inferred. Inferred milestones must be reviewed before publication. Status history is append-only and supports expected, started, completed, delayed, changed, cancelled, failed, and unknown states. Netflix's Basic with Ads launch is the completed-history pilot: the tracker records the expected milestone from the October 13, 2022 announcement and the reviewed completed update on November 3, 2022.

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py build_strategy_milestones

sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py validate_strategy_milestones

BASE_URL=http://localhost:8080/api/app \
  bash scripts/smoke/phase2_strategy_milestones.sh
```

```text
Ingestion: GET /companies/{slug}/strategy-milestones
Product:   GET /api/app/companies/{slug}/strategy-milestones
Filters:   ?status={status}&type={type}&origin={origin}&view=all|upcoming|overdue|completed&milestone={slug}
```

Open `Strategy milestone tracker` from Company 360 for the milestone register, lifecycle filters, selected milestone detail, linked promise/KPI/strategic-turn context, dependencies, evidence sources, and unavailable states.

Requirement 6 verification on June 18, 2026: ingestion `56/56`, main backend `34/34`, frontend `7/7`, production build passed, all-company validator passed, and the authenticated gateway smoke test passed for all 20 companies. `makemigrations --check --dry-run` still reports the pre-existing ingestion index/job-type drift unrelated to this requirement; company milestone migrations are applied and consistent.

## Capital Allocation Dashboard

Phase 2 Requirement 7 adds a source-backed Capital Allocation Dashboard for each configured company. It shows where management deployed resources across capex, R&D, acquisitions/investments, buybacks, dividends, debt, restructuring, and content/inventory investment, while keeping cash balances, operating cash flow, and calculated free cash flow as context rather than deployment.

The dashboard uses SEC Company Facts as the structured baseline. `ingest_sec_companyfacts` now collects additional capital allocation concepts and rebuilds reviewed `CapitalAllocationPeriod` and `CapitalAllocationItem` records after each companyfacts run. Missing categories are stored and displayed as source gaps; they are not treated as zero. Free cash flow is calculated only when operating cash flow and capex are both available for the same period.

Capital Allocation endpoints:

```bash
GET /api/ingestion/companies/<slug>/capital-allocation
GET /api/app/companies/<slug>/capital-allocation
```

Open `Capital allocation dashboard` from Company 360 for period selection, deployment totals, cash-flow context, category mix, source-backed item drilldowns, linked strategy/promises, evidence cards, and unavailable category gaps.

Capital Allocation smoke check:

```bash
BASE_URL=http://localhost:8080/api/app scripts/smoke/phase2_capital_allocation.sh
```

Requirement 7 verification on June 19, 2026: SEC Company Facts ingestion populated all 20 configured companies with 1,397 reviewed capital allocation periods and 5,925 allocation items; direct database coverage confirmed every company has a latest reviewed period with operating cash-flow context; authenticated gateway smoke passed for all 20 companies; ingestion backend `58/58`, main backend `34/34`, frontend `7/7`, and frontend production build passed.

## Competitive Position Dashboard

Phase 2 Requirement 8 adds a reviewed Competitive Position Dashboard for each configured company. It owns competitor relationships, peer-map context, product/customer/geographic overlap, scale and moat evidence categories, opposing evidence, competitive action timelines, and explicit market-share source gaps.

The baseline is generated from reviewed Company 360 profiles, configured same-sector peers, and reviewed fallback peer sets for single-company sectors. It separates direct competitors, category competitors, substitutes, platform competitors, supplier/customer overlap, and peer benchmarks. The methodology explicitly states that competitive context is descriptive and does not imply causation.

Competitive Position endpoints:

```bash
GET /api/ingestion/companies/<slug>/competitive-position
GET /api/app/companies/<slug>/competitive-position
```

Open `Competitive position dashboard` from Company 360 for snapshot controls, relationship filters, peer map, comparison dimensions, competitive actions, moat evidence, opposing evidence, market-share unavailable state, evidence cards, and source gaps.

Competitive Position smoke check:

```bash
BASE_URL=http://localhost:8080/api/app scripts/smoke/phase2_competitive_position.sh
```

Requirement 8 verification on June 19, 2026: competitive-position builder populated all 20 configured companies with reviewed snapshots, at least one peer link, and comparison dimensions; direct database coverage confirmed `20/20`; authenticated gateway smoke passed for all 20 companies; ingestion backend `60/60`, main backend `34/34`, frontend `7/7`, and frontend production build passed.

## Product and Pricing History

Phase 2 Requirement 9 adds a reviewed Product and Pricing History baseline for each configured company. It owns the product hierarchy, current catalog snapshot, dated product and pricing-change timeline, before/after comparison rows, price context, promotion policy, evidence, and source gaps.

The baseline is generated from reviewed Company 360 product and brand data, reviewed profile fallbacks, and product/pricing business events. List-price observations require explicit source-backed amount, currency, geography, billing period, tax, promotion, and customer-segment context. Missing prices are shown as unavailable and are not estimated or treated as zero.

Product and Pricing endpoints:

```bash
GET /api/ingestion/companies/<slug>/product-pricing
GET /api/app/companies/<slug>/product-pricing
```

Open `Product and pricing history` from Company 360 for snapshot controls, offering-type filters, product catalog, launch/update/packaging/pricing timeline, list-price context, before/after rows, evidence cards, and source gaps.

Product and Pricing smoke check:

```bash
BASE_URL=http://localhost:8080/api/app scripts/smoke/phase2_product_pricing.sh
```

Requirement 9 verification on June 19, 2026: product/pricing builder populated all 20 configured companies with reviewed catalog snapshots, 182 offerings, and 52 timeline changes; direct database coverage confirmed `20/20`; authenticated gateway smoke passed for all 20 companies; ingestion backend `62/62`, main backend `34/34`, frontend `7/7`, and frontend production build passed.

## Acquisition Lifecycle Tracker

Phase 2 Requirement 10 adds an Acquisition Lifecycle Tracker for reviewed acquisition and subsidiary/portfolio evidence. It tracks deal stage, transaction type, outcome category, announcement/close dates, deal consideration, approvals, management rationale, promised synergies, integration notes, outcome review, lifecycle events, evidence, and source gaps.

The baseline builder uses reviewed acquisition business events when they name a specific target, and reviewed Company 360 subsidiary context as conservative portfolio evidence. Generic acquisition/divestiture summaries are ignored so they do not become fake deal targets. Missing purchase price, payment form, approvals, synergies, and outcome reviews are shown as unavailable source gaps rather than estimates.

Acquisition Lifecycle endpoints:

```bash
GET /api/ingestion/companies/<slug>/acquisition-lifecycle
GET /api/app/companies/<slug>/acquisition-lifecycle
```

Open `Acquisition lifecycle tracker` from Company 360 for stage/type/outcome filters, portfolio list, selected deal detail, lifecycle timeline, evidence cards, and source gaps.

Acquisition Lifecycle smoke check:

```bash
BASE_URL=http://localhost:8080/api/app scripts/smoke/phase2_acquisition_lifecycle.sh
```

Requirement 10 verification on June 19, 2026: acquisition lifecycle builder validated all 20 configured companies; companies with reviewed subsidiary/acquired-entity context expose lifecycle rows and companies without reviewed targets expose acquisition source gaps; authenticated gateway smoke passed for all 20 companies; ingestion backend `64/64`, main backend `34/34`, frontend `7/7`, and frontend production build passed.

## Customer and Supplier Dependency

Phase 2 Requirement 11 adds a Customer and Supplier Dependency map for reviewed customer groups, supplier categories, platforms, distributors, licensors, infrastructure providers, partners, and contract-risk disclosures. It separates named counterparties from category-only dependencies so confidential or ambiguous counterparties are not published as facts.

The baseline builder uses reviewed Company 360 customer groups and reviewed Business Model Map channel/partner components. Missing named counterparties, concentration percentages, renewal dates, exclusivity, minimum commitments, termination rights, and critical-supplier details are shown as source gaps. Absence of disclosure is not interpreted as absence of dependency.

Customer and Supplier Dependency endpoints:

```bash
GET /api/ingestion/companies/<slug>/customer-supplier-dependency
GET /api/app/companies/<slug>/customer-supplier-dependency
```

Open `Customer and supplier dependency` from Company 360 for snapshot controls, dependency-type and disclosure-confidence filters, dependency relationships, contract-risk states, evidence cards, methodology guardrails, and source gaps.

Customer and Supplier Dependency smoke check:

```bash
BASE_URL=http://localhost:8080/api/app scripts/smoke/phase2_customer_supplier_dependency.sh
```

Requirement 11 verification on June 20, 2026: dependency builder populated all 20 configured companies with reviewed dependency snapshots and 176 category-level dependency rows; authenticated gateway smoke passed for all 20 companies; ingestion backend `66/66`, main backend `34/34`, frontend `7/7`, and frontend production build passed.

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
