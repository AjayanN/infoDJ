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
- user-facing component cards without inline audit labels, with source traceability preserved in the evidence section
- an interactive shared-node bubble-map value-flow view where repeated component names collapse into one high-contrast bubble, relationship connectors link the nodes, the graph sits in a larger scrollable canvas, bubbles can be repositioned inside that canvas, hovering a connector focuses that relationship, hovering a node focuses all relationships connected to it, and leaving the graph clears the focus
- historical snapshot selection and before/after change analysis
- evidence links, completeness, freshness, and explicit missing-component gaps
- an accessible component-column view backed by source documents and explicit missing-data states

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

Peer context includes compatibility safeguards. Same-sector companies can still appear as context, but each peer row is labelled as comparable, partial, or incompatible based on reviewed component-type overlap and critical payer, offering, revenue, and channel coverage. Weak matches show a visible warning so users do not treat unlike business models as directly comparable.

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
- dependency labels showing where a selected KPI is used by Earnings Intelligence, Management Promise Tracker, and Strategy Milestone Tracker
- reviewed SEC-backed baseline-depth coverage showing definition count, observation count, annual and quarterly coverage, source count, and first/latest covered period

Peer normalization is guarded separately from same-sector discovery. Reviewed comparable peer metrics appear only when the selected KPI and peer KPI share reviewed comparability, matching unit, matching cadence, active status, and peer-comparable flags. Same-sector KPI candidates that fail those checks are shown as blocked with the exact reason, such as missing reviewed comparability, unit mismatch, cadence mismatch, or a reviewed non-comparable status.

KPI dependency labels are explicit across related dashboards. Earnings rows label aligned KPI observations as operating context rather than causation, management promises label linked KPIs as evaluation metrics, and strategy milestones label linked KPIs as execution evidence.

The Netflix pilot contains source-backed 2022 paid streaming memberships, regional Q4 observations, and calculated quarter-over-quarter growth. Every company in the current 20-company universe also receives annual and quarterly SEC Company Facts series for every stored concept. Those baseline series are labeled `Company-wide reported financial context`; they are not presented as company-specific operating KPIs such as subscribers, stores, deliveries, occupancy, or production.

Open any company from search or Company 360 and select `Operating KPI tracker`; after loading, `Operating KPIs` remains in the left navigation.

Refresh the official SEC data and all-company tracker coverage idempotently. KPI series are rebuilt automatically after each company’s facts are stored:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py ingest_sec_companyfacts --all --limit 500
```

`build_companyfacts_kpis --all` remains available to rebuild from facts already stored in the database without making network requests.

Validate all-company baseline depth without fetching new data:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py validate_operating_kpi_baselines --all
```

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

Open `Earnings intelligence` from Company 360 for the quarterly timeline, measured results, reviewed management drivers, KPI movement with dependency labels, forecast-versus-actual comparisons where available, linked strategy and risks, distinct evidence sources, evidence gaps, and print export.

Requirement 5 verification on June 14, 2026: ingestion `52/52`, main backend `32/32`, frontend `7/7`, production build passed, all-company validator passed, and the authenticated gateway smoke test passed for all 20 companies.

## Strategy Milestone Tracker

Phase 2 Requirement 6 turns reviewed management commitments into execution milestones with explicit origin, status, due-date precision, success conditions, blockers, status history, and source evidence. The baseline covers all 20 configured companies and does not infer due dates when management did not provide one.

Milestone origins are separated as management-announced, regulator-defined, contractual, or analyst-inferred. Inferred milestones must be reviewed before publication. Status history is append-only and supports expected, started, completed, delayed, changed, cancelled, failed, and unknown states. Netflix's Basic with Ads launch is the completed-history pilot: the tracker records the expected milestone from the October 13, 2022 announcement and the reviewed completed update on November 3, 2022.

Milestone rules are conservative. Categories describe the execution step itself, due dates preserve source precision, unknown dates are never treated as overdue, dependencies must name the source-backed upstream condition, and status changes require reviewed evidence rather than elapsed time alone.

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

Reported, adjusted, and currency validation is explicit. Published rows are labelled as reported SEC Company Facts or calculated free cash flow; adjusted/non-GAAP capital allocation figures remain unavailable until a reviewed reconciliation source exists. Mixed or non-USD deployment units create a currency-conversion source gap rather than being summed silently.

Capital Allocation endpoints:

```bash
GET /api/ingestion/companies/<slug>/capital-allocation
GET /api/app/companies/<slug>/capital-allocation
```

Open `Capital allocation dashboard` from Company 360 for period selection, deployment totals, cash-flow context, category mix, source-backed item drilldowns, linked strategy/promises, evidence cards, and unavailable category gaps.

Capital Allocation smoke check:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py validate_capital_allocation_context --all

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

## Geographic Expansion Map

Phase 2 Requirement 12 adds a Geographic Expansion Map for reviewed countries and regions, dated entry or exit evidence where available, local partnerships, regulatory barriers, revenue contribution, outcomes, evidence, and source gaps.

The baseline builder uses reviewed Company 360 geographies and source-backed international expansion, market-entry, and regulatory events. Generic geographic presence is not treated as a dated market entry. Missing revenue contribution, local partnerships, regulatory barriers, and outcomes are shown as source gaps instead of inferred values.

The map exposes geography-level definitions, expansion event-type definitions, an accessible market list, an entry/exit timeline, separate announcement/launch/operational-start/scale-up/reduction/exit date slots, and validation guardrails for country naming, historical boundaries, currency, and reporting scope. Products, customer segments, channels, local partners, regulatory approvals/restrictions, revenue, users, locations, and outcomes remain unavailable unless reviewed market-specific evidence supports them.

Geographic Expansion endpoints:

```bash
GET /api/ingestion/companies/<slug>/geographic-expansion
GET /api/app/companies/<slug>/geographic-expansion
```

Open `Geographic expansion map` from Company 360 for snapshot controls, status and market-type filters, country/region rows, entry/exit timeline, evidence cards, methodology guardrails, and source gaps.

Geographic Expansion smoke check:

```bash
sudo docker compose -f infra/docker-compose.yml exec -T ingestion \
  .venv/bin/python manage.py validate_geographic_expansion --all

BASE_URL=http://localhost:8080/api/app scripts/smoke/phase2_geographic_expansion.sh
```

Requirement 12 verification on June 21, 2026: geographic expansion builder populated all 20 configured companies with reviewed expansion snapshots and 28 country/region market rows; direct database coverage confirmed every configured company has at least one reviewed market row; ingestion API validation passed for all 20 companies with 86 explicit source gaps; authenticated gateway smoke passed for all 20 companies; ingestion backend `71/71`, main backend `36/36`, frontend `7/7`, and frontend production build passed.

## Leadership Decision Record

Phase 2 Requirement 13 adds a Leadership Decision Record for leadership roles, tenure context, stated priorities, material decisions, succession events, evidence, and explicit non-causation guardrails.

The baseline builder creates a reviewed snapshot for every configured company. It publishes role rows only from reviewed Company 360 leadership or reviewed leadership-change events. Tenure start/end dates, departures, succession plans, board changes, decision links, compensation context, and tenure performance remain explicit source gaps unless a reviewed source supports them. Performance during tenure is shown only as context and is not treated as leadership causation.

Leadership attribution is bounded. Company-level decisions are not assigned to one person unless the source does so, performance during tenure is contextual rather than causal, and departure reasons or personal allegations remain unavailable unless authoritative reviewed sources support them.

Leadership Decision Record endpoints:

```bash
GET /api/ingestion/companies/<slug>/leadership-decisions
GET /api/app/companies/<slug>/leadership-decisions
```

Open `Leadership decision record` from Company 360 for snapshot controls, role and decision filters, role rows, decision/priority rows, non-causation guardrails, evidence cards, and source gaps.

Leadership Decision Record smoke check:

```bash
BASE_URL=http://localhost:8080/api/app scripts/smoke/phase2_leadership_decisions.sh
```

Requirement 13 verification on June 21, 2026: leadership builder populated all 20 configured companies with reviewed snapshots and 6 reviewed role rows from available leadership data; ingestion API validation passed for all 20 companies with 32 explicit source gaps and no unsupported departure or performance-causation claims; source-gap resolver checked 396 gaps, created 3 candidate mappings, and updated 95; authenticated gateway smoke passed for all 20 companies; ingestion backend `75/75`, main backend `40/40`, frontend `7/7`, and frontend production build passed.

## Ownership and Insider Activity

Phase 2 Requirement 14 adds Ownership and Insider Activity for reviewed ownership context, economic versus voting-control separation, institutional and insider rows where disclosed, transaction-plan gaps, evidence, and source-gap resolution candidates.

The baseline builder creates a reviewed snapshot for every configured company. It publishes insider-context rows only from reviewed leadership context and does not estimate ownership percentages, voting power, institutional positions, Form 4 transactions, or 10b5-1 plans. Missing ownership details are shown as source gaps and routed to the source-gap resolver for proxy, Form 4, Schedule 13D/13G, and 13F candidate documents where available.

Ownership and Insider Activity endpoints:

```bash
GET /api/ingestion/companies/<slug>/ownership-insider
GET /api/app/companies/<slug>/ownership-insider
```

Open `Ownership and insider activity` from Company 360 for snapshot controls, holder and transaction filters, position/context rows, insider transaction rows, economic-versus-voting control guardrails, evidence cards, and source gaps.

Ownership and Insider Activity smoke check:

```bash
BASE_URL=http://localhost:8080/api/app scripts/smoke/phase2_ownership_insider.sh
```

Requirement 14 verification on June 21, 2026: ownership builder populated all 20 configured companies with reviewed snapshots and 6 reviewed insider-context rows from available leadership data; ingestion API validation passed for all 20 companies with 32 explicit source gaps and no fabricated transactions; source-gap resolver checked 364 gaps and updated 95 candidate mappings; authenticated gateway smoke passed for all 20 companies; ingestion backend `73/73`, main backend `38/38`, frontend `7/7`, and frontend production build passed.

## Valuation Context

Phase 2 Requirement 15 adds Valuation Context for historical market value, reproducible valuation observations, selected peer comparison, event-aligned snapshots, methodology, and source gaps. It is research context only and is not investment advice or a trading recommendation.

The baseline builder creates one reviewed snapshot for every configured company from stored market prices and SEC companyfacts. It calculates market capitalization, price to sales, price to earnings, enterprise value, and EV to revenue only when required inputs are available and meaningful. Missing share counts, non-positive denominators, missing debt/cash inputs, absent peer values, and missing event price windows are shown as source gaps rather than estimated.

Valuation Context endpoints:

```bash
GET /api/ingestion/companies/<slug>/valuation-context
GET /api/app/companies/<slug>/valuation-context
```

Open `Valuation context` from Company 360 for snapshot controls, measure filters, formulas, numerator/denominator inputs, source periods, peer rows, event-aligned non-causal context, evidence cards, and unavailable input states.

Requirement 15 verification on July 1, 2026: valuation builder populated all 20 configured companies with reviewed snapshots and 100 observation rows; 13 companies had at least one applicable measure and seven companies correctly exposed unavailable-input states because required share-count or related inputs were missing; peer context produced 69 rows and event-aligned context produced 12 rows. Ingestion API smoke passed for all 20 configured companies; ingestion backend `84/84`, main backend `42/42`, frontend `7/7`, and frontend production build passed.

## Regulatory and Litigation Calendar

Phase 2 Requirement 16 adds Regulatory and Litigation Calendar for reviewed regulatory reviews, investigations, litigation, approvals, compliance obligations, deadlines, exposure context, evidence, and legal guardrails.

The baseline builder creates one reviewed snapshot for every configured company from reviewed `REGULATORY_RESPONSE` business events and linked source documents. It classifies matter type, stage, status, jurisdiction, authority, business area, materiality, allegation or issue, company response, interim/final outcome, and exposure context only when supported by source text. Missing authorities, future procedural dates, and quantified exposure/remedy context are shown as source gaps and routed to the source-gap collector for `10-K`, `10-Q`, and `8-K` sources.

Regulatory and Litigation Calendar endpoints:

```bash
GET /api/ingestion/companies/<slug>/regulatory-litigation
GET /api/app/companies/<slug>/regulatory-litigation
```

Open `Regulatory and litigation calendar` from Company 360 for matter filters, status and materiality summaries, calendar rows, legal guardrail text, evidence cards, and unavailable data states. The dashboard records disclosed procedural context only; it does not make legal conclusions, predict outcomes, or estimate exposure unless a reviewed source states it.

Requirement 16 verification on July 2, 2026: regulatory/litigation builder populated all 20 configured companies with reviewed snapshots and 32 reviewed matter rows. Ingestion API smoke passed for all 20 companies with at least one reviewed matter, explicit legal guardrails, and source gaps for missing authority/deadline/exposure details where applicable. Authenticated main-backend proxy smoke passed for Netflix. Ingestion backend `86/86`, main backend `44/44`, frontend `7/7`, and frontend production build passed.

## Sector and Theme Intelligence

Phase 2 Requirement 17 adds Sector and Theme Intelligence for reviewed sector/theme taxonomy, company exposure cards, materiality labels, effective evidence dates, related events, KPI links, risk signals, capital allocation links, evidence, and source gaps.

The baseline builder creates one reviewed snapshot for every configured company from reviewed event themes, active KPI definitions, reviewed capital-allocation rows, and company sector metadata. Broad sector classification is kept as `Narrative only`; operating exposure requires evidence from a reviewed event, KPI, or capital-allocation row. Missing operating exposure, strategic-move links, KPI links, or capital-allocation links are routed to source-gap collection for `10-K`, `10-Q`, `8-K`, official sources, and reviewed extraction candidates.

Sector and Theme Intelligence endpoints:

```bash
GET /api/ingestion/companies/<slug>/sector-themes
GET /api/app/companies/<slug>/sector-themes
```

Open `Sector and theme intelligence` from Company 360 for taxonomy labels, theme pages, exposure cards, materiality filters, related events/KPIs/capital rows, evidence cards, and unavailable data states.

Requirement 17 verification on July 2, 2026: sector/theme builder populated all 20 configured companies with reviewed snapshots and 324 exposure rows. Ingestion API smoke passed for all 20 companies with at least one operating exposure and at least one theme page per company; gaps remain explicit where KPI or capital-allocation links are not yet available. Authenticated main-backend proxy smoke passed for Netflix. Ingestion backend `88/88`, main backend `46/46`, frontend `7/7`, and frontend production build passed.

## Macro Sensitivity Profile

Phase 2 Requirement 18 adds Macro Sensitivity Profile for macro factor registry, exposure channels, direction labels, management-disclosed sensitivities, calculated-relationship limitations, stress-period examples, evidence, and source gaps.

The baseline builder creates one reviewed snapshot for every configured company from reviewed company events, sector/theme exposures, financial facts, and market data availability. It separates management-disclosed or theme-derived sensitivity context from calculated historical relationships. Calculated relationships stay as explicit placeholders until aligned macro series, company metric series, sample size, lag assumptions, currency handling, and reporting-period alignment are available. The dashboard does not claim causation from simple correlations.

Macro Sensitivity Profile endpoints:

```bash
GET /api/ingestion/companies/<slug>/macro-sensitivity
GET /api/app/companies/<slug>/macro-sensitivity
```

Open `Macro sensitivity profile` from Company 360 for macro factor filters, exposure channel filters, direction labels, methods, sample sizes, stress-period examples, limitations, evidence cards, and unavailable data states.

Requirement 18 verification on July 2, 2026: macro sensitivity builder populated all 20 configured companies with reviewed snapshots, 513 sensitivity rows, and 40 stress-example writes. Ingestion API smoke passed for all 20 companies with at least one sensitivity row, calculated relationship placeholder, and explicit non-causation limitation. Authenticated main-backend proxy smoke passed for Netflix. Ingestion backend `90/90`, main backend `48/48`, frontend `7/7`, and frontend production build passed.

## Strategy Thesis Workspace

Phase 2 Requirement 19 adds a private, authenticated Strategy Thesis Workspace for user-authored company theses. This workspace is product data in the main backend, not ingestion-published company facts.

The workspace includes:

- thesis states: draft, active, strengthening, weakening, invalidated, completed, and archived
- company-linked thesis statements, assumptions, review dates, time horizons, and confidence scores
- supporting, opposing, and neutral evidence attachments from companies, events, strategic turns, KPIs, promises, source pages, URLs, dashboard rows, or private notes
- explicit separation between referenced evidence summaries and private user-authored notes
- milestones, indicators, and confidence/state revision history with reasons
- ingestion-backed evidence suggestions through authenticated search
- privacy labels for private and shared user-generated content

Strategy Thesis Workspace endpoints:

```bash
GET  /api/app/theses
POST /api/app/theses
GET  /api/app/theses/<id>
POST /api/app/theses/<id>/evidence
POST /api/app/theses/<id>/milestones
POST /api/app/theses/<id>/indicators
POST /api/app/theses/<id>/confidence
GET  /api/app/theses/evidence-suggestions?q=<query>&company=<slug>
```

Open `Strategy thesis workspace` from Company 360 or `Theses` in the left navigation. Evidence suggestions depend on ingestion search availability; private thesis records remain available even when ingestion is temporarily unavailable.

## Watchlists and Alerts

Phase 2 Requirement 20 adds private authenticated watchlists and an in-product notification center. Watchlist records, delivery preferences, alert status, and feedback are product data in the main backend. Alert evidence is refreshed from ingestion dashboards and search results.

The baseline includes:

- followable entity types for companies, themes, products, leaders, promises, milestones, risks, and regulatory matters
- alert categories for strategic moves, earnings/guidance, KPI changes, promises, milestones, leadership/ownership, product/pricing, acquisitions, regulatory/litigation, risk escalation, and source corrections
- watchlist creation, followed entity management, and a Company 360 `Follow for alerts` action
- in-product notification center with unread/read/archive status
- delivery preferences for in-product alerts and email frequency: immediate, daily, weekly, or disabled
- duplicate grouping using deterministic dedupe keys and source counts
- alert rows that show what changed, why it matters, previous state when available, source label, source date, and source link
- alert quality monitoring through duplicate-group ratio and user feedback

Watchlist and alert endpoints:

```bash
GET  /api/app/watchlists
POST /api/app/watchlists
POST /api/app/watchlists/follow-company
POST /api/app/watchlists/<id>/items
GET  /api/app/notifications
POST /api/app/notifications/refresh
PATCH /api/app/notifications/<id>
POST /api/app/notifications/<id>/feedback
GET  /api/app/notifications/delivery-preference
PATCH /api/app/notifications/delivery-preference
```

Refresh source-backed alerts for all users:

```bash
python manage.py refresh_watchlist_alerts --limit 12
```

Open `Alerts` in the left navigation or use `Follow for alerts` from Company 360. Alerts are intentionally grouped meaningful changes, not every new document or mention.

## Daily and Weekly Briefings

Phase 2 Requirement 21 adds personalized daily and weekly briefings. Briefings summarize the user’s watchlist alerts and coverage gaps; they do not create independent event logic.

The baseline includes:

- daily and weekly briefing cadences
- materiality ranking by severity, duplicate grouping, recency, and followed-entity scope
- in-product briefing archive with ready, sent, and archived states
- concise what-changed, why-it-matters, and what-next fields for every briefing item
- evidence labels, source dates, and source links from the underlying notification
- personalized scope from active watchlists and followed entities
- repeated alert suppression through notification dedupe keys
- coverage-gap notices for followed entities with no current source-backed alert evidence
- email delivery logs when user delivery preferences match the briefing cadence
- briefing feedback for relevance monitoring

Briefing endpoints:

```bash
GET  /api/app/briefings
POST /api/app/briefings
GET  /api/app/briefings/<id>
PATCH /api/app/briefings/<id>
POST /api/app/briefings/<id>/feedback
```

Generate briefings for all users with active watchlists:

```bash
python manage.py generate_briefings --cadence DAILY
python manage.py generate_briefings --cadence WEEKLY
```

Open `Briefings` in the left navigation. Generate a daily or weekly briefing after following companies/topics and refreshing alerts.

## Scenario Explorer

Phase 2 Requirement 22 adds a private authenticated Scenario Explorer. Scenarios are user assumption workspaces, not predictions, investment advice, or probability-weighted forecasts.

The baseline includes:

- best, base, and worst case templates for every scenario set
- visible user-created versus InfoDJ-reviewed source labels
- explicit thesis, company scope, horizon start, and horizon end
- assumptions linked to KPIs, macro factors, promises, milestones, risks, competitive factors, regulatory factors, or other drivers
- qualitative outcomes and optional low/high ranges without false precision
- assumption-difference view showing how best/base/worst cases diverge
- indicator monitoring with status labels
- scenario status revisions and archive workflow
- actual-result comparison after the horizon
- source-backed evidence suggestions from ingestion search
- non-prediction guardrails on API and frontend surfaces

Scenario endpoints:

```bash
GET  /api/app/scenarios
POST /api/app/scenarios
GET  /api/app/scenarios/<id>
PATCH /api/app/scenarios/<id>
PATCH /api/app/scenarios/<id>/cases/<case_id>
POST /api/app/scenarios/<id>/cases/<case_id>/assumptions
POST /api/app/scenarios/<id>/indicators
POST /api/app/scenarios/<id>/actual-results
GET  /api/app/scenarios/evidence-suggestions?q=<query>&company=<slug>
```

Open `Scenario explorer` from Company 360 or `Scenarios` in the left navigation.

## Contradiction View

Phase 2 Requirement 23 adds a neutral Contradiction View for comparing sourced claims. The workflow is designed to avoid implying deception, intent, or wrongdoing without authoritative support.

The baseline includes:

- contradiction, clarification, revision, and normal-evolution conflict types
- categories such as guidance versus actual outcome, promise versus action, source versus source, and metric-definition changes
- review queue and detail comparison for two or more claims
- claim dates, speakers, scopes, source labels, source URLs, and source payloads
- materiality, confidence score, explanation, correction path, and review status
- reviewed labels: confirmed contradiction, likely contradiction, apparent conflict, resolved, and not a contradiction
- human-review requirement before publication
- resolution history and correction/dispute notes
- source-backed evidence suggestions from ingestion search

Contradiction endpoints:

```bash
GET  /api/app/contradictions
POST /api/app/contradictions
GET  /api/app/contradictions/<id>
PATCH /api/app/contradictions/<id>
POST /api/app/contradictions/<id>/claims
POST /api/app/contradictions/<id>/review
GET  /api/app/contradictions/evidence-suggestions?q=<query>&company=<slug>
```

Open `Contradiction view` from Company 360 or `Contradictions` in the left navigation.

## Strategy Failure Library

Phase 2 Requirement 24 adds a private authenticated Strategy Failure Library for reviewed case studies of failed or materially underperforming strategic moves.

The baseline includes:

- failure categories for pivots, acquisitions, market expansions, product/pricing moves, restructurings, delayed programs, regulatory blockages, capital allocation, competitive displacement, and execution breakdowns
- classifications for failure, partial failure, temporary setback, incomplete, and too early to judge
- searchable/filterable library by company, category, classification, and stage
- case-study detail covering decision context, management rationale, original thesis, expected result, execution issue, outcome definition, actual outcome, counterexamples, lessons, and correction path
- minimum evidence and elapsed review period fields
- evidence records with dates, summaries, source URLs, and source payloads
- early warning signs marked as observable at the time
- links to promises, milestones, KPIs, capital allocation, leadership, market context, acquisitions, and contradiction records
- editorial review status, review history, confidence score, and publication guardrail
- source-backed evidence suggestions from ingestion search

Strategy failure endpoints:

```bash
GET  /api/app/strategy-failures
POST /api/app/strategy-failures
GET  /api/app/strategy-failures/<id>
PATCH /api/app/strategy-failures/<id>
POST /api/app/strategy-failures/<id>/evidence
POST /api/app/strategy-failures/<id>/warning-signs
POST /api/app/strategy-failures/<id>/related-links
POST /api/app/strategy-failures/<id>/review
GET  /api/app/strategy-failures/evidence-suggestions?q=<query>&company=<slug>
```

Open `Strategy failure library` from Company 360 or `Failures` in the left navigation.

## Foundation Standards

Phase 2 Wave 0 adds an authenticated Foundation Standards page so shared product rules are visible and testable before deeper feature maturity work.

The baseline includes:

- shared evidence, claim, metric, period, company identity, and confidence rules
- common available, partial, unavailable, stale, and conflict states
- a selected pilot company and review period
- source-gap, correction, and editorial-review workflows
- freshness expectations by information type

Foundation endpoint:

```bash
GET /api/app/foundations/standards
```

Open `Standards` in the left navigation.

## Phase 2 Acceptance

The Phase 2 implementation is treated as repository-complete when the 24 functional baselines, Foundation Standards, source-gap workflows, all-company validators, authenticated smoke checks, backend suites, frontend tests, and production build pass. The master checklist in `func_req_phase2_todo.md` records the acceptance evidence and the product-owner feedback addressed during implementation. Broader external beta feedback remains a future product-growth activity rather than a blocker for the repository implementation checklist.

## Source Gap Resolution Guardrail

Open source gaps are now routed back into ingestion instead of remaining as passive UI messages. The daily company update runs `resolve_source_gaps` after the Phase 2 builders and creates reviewed-source candidates from existing `SourceDocument` rows for acquisition lifecycle, competitive market-share, customer/supplier dependency, contract-term, concentration, product-pricing, geographic expansion, leadership, and ownership/insider gaps.

Gap-targeted golden source collection now runs before source-gap resolution. It looks at open source gaps and collects the official SEC filing classes most likely to fill them, including `10-K`, `10-Q`, `8-K`, `DEF 14A`, `Form 4`, `S-4`, `DEFM14A`, `SC 13D`, and `SC 13G`. This is the bridge between empty dashboard sections and the real quarterly/proxy/ownership filings that can fill them.

Gap-targeted source collection command:

```bash
.venv/bin/python manage.py collect_source_gap_sources --limit 20 --filing-limit 160
.venv/bin/python manage.py collect_source_gap_sources --company netflix --filing-limit 160
```

Resolution candidates are not treated as completed facts. Each candidate stores the source document, candidate type, evidence excerpt, confidence score, review status, and next extraction action. Feature builders should only promote a candidate into a dashboard row after extracting the required fields from the cited source.

Source gap resolver command:

```bash
.venv/bin/python manage.py resolve_source_gaps --limit 500
.venv/bin/python manage.py resolve_source_gaps --company netflix
```

Candidate extraction command:

```bash
.venv/bin/python manage.py extract_source_gap_candidates --limit 100
.venv/bin/python manage.py extract_source_gap_candidates --dashboard ownership_insider_activity --gap-type ownership_percentages --limit 50
```

Candidate promotion command:

```bash
.venv/bin/python manage.py promote_source_gap_candidates --limit 100
.venv/bin/python manage.py promote_source_gap_candidates --dashboard ownership_insider_activity --gap-type institutional_positions --limit 50
```

Candidate promotion is intentionally deterministic. It only writes dashboard rows when extracted source text contains explicit structured values, such as Schedule 13G/13D ownership percentages or 10-K customer concentration percentages. Unsupported or ambiguous candidates stay in source-gap review instead of becoming dashboard facts. Proxy prose is not auto-promoted until a structured proxy table parser is available.

Source-gap APIs include the first resolution candidates for review:

```bash
GET /api/ingestion/source-gaps?dashboard=acquisition_lifecycle
```

The dashboard `Compare peers`/company-situations section also falls back to reviewed Competitive Position peer evidence when no configured same-sector peer row exists. External peers remain labelled as outside the configured company universe.

Candidate promotion verification on July 1, 2026: live promotion checked 163 extracted candidates, promoted 6 source-gap candidates into 3 current-dashboard ownership rows, and left 157 ambiguous candidates in review. The Tesla Ownership and Insider Activity API now returns source-backed Schedule 13G rows for Elon R. Musk `20.5%`, BlackRock `5.9%`, and Vanguard Group `7.23%`; no customer concentration rows were promoted because no extracted candidate contained a deterministic concentration disclosure. Ingestion backend `82/82`, main backend `40/40`, frontend `7/7`, and frontend production build passed.

Candidate extraction verification on June 21, 2026: full-text extraction checked 100 pending source-gap candidates, extracted 79 source documents, updated 96 candidates with source-backed evidence excerpts and extraction metadata, and marked 4 candidates failed for follow-up. Persisted candidate statuses after the run were 96 `EXTRACTED`, 4 `FAILED`, and 72 still `CANDIDATE`; no extracted candidate was promoted into a dashboard fact without review. Ingestion backend `79/79`, main backend `40/40`, frontend `7/7`, and frontend production build passed.

Gap-targeted collection verification on June 21, 2026: all 20 configured companies were collected from official SEC EDGAR sources for open gaps; the first pass checked 20 companies, collected 17, found 2,720 filings, inserted 2,290 source documents, and exposed 3 ticker-resolution failures; the ticker resolver was fixed to prefer configured universe tickers and the failed JPMorgan Chase, Visa, and Ford collections then succeeded with 476 more filings found and 390 inserted. Source-gap resolution then created 74 new candidate mappings and updated 172 candidates. Ingestion backend `77/77`, main backend `40/40`, frontend `7/7`, and frontend production build passed.

Source-gap guardrail verification on June 20, 2026: migration applied cleanly; resolver checked 246 open gaps and created 47 source-linked resolution candidates across 17 configured companies; no candidate was promoted to reviewed fact status; all 20 configured companies were present in the local ingestion DB; dashboard coverage validator passed with 20 companies, 59 scorecards, and six comparison groups; ingestion backend `69/69`, main backend `34/34`, frontend `7/7`, and frontend production build passed.

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
