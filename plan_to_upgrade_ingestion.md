# Plan To Upgrade Ingestion

Goal:

```text
Dashboards must render only source-backed, dashboard-appropriate data.
Weak candidate signals, generic turns, missing impact facts, and unsupported comparisons must be blocked by eligibility gates and surfaced as source gaps.
```

## Current Audit Baseline

Initial live database audit on 2026-06-03 showed:

- 20 companies
- 829 source documents
- 35 article extractions
- 216 business events
- 215 strategic turns
- 377 strategic turn source links
- 121 ingestion jobs
- 216/216 business events are dated and source-linked
- 39/216 business events contain generic rule text
- 215/215 strategic turns fail the current `is_specific_strategic_turn()` filter
- all extracted events currently come from SEC EDGAR 10-K source documents
- market prices and SEC companyfacts tables do not exist

Conclusion:

- company coverage, latest candidate events, source confidence, and risk-signal candidate dashboards can exist with clear caveats
- strategic turns, patterns, scorecards, compare, impact, and founder-question answers are not dashboard-grade until ingestion and eligibility gates improve

Post Phase 1 live audit on 2026-06-03 showed:

- 20 companies
- 853 source documents
- 35 article extractions
- 220 business events
- 215 strategic turns
- 377 strategic turn source links
- 161 ingestion jobs
- 106 business events pass the dashboard eligibility gate for latest moves
- 68 risk events pass the risk-signal eligibility gate
- 0 strategic turns pass the strategic-turn eligibility gate
- 0 comparable repeated turn types pass the strategic-turn eligibility gate
- strategic pattern, strategy scorecard, compare, and impact dashboards must stay unavailable until turn rebuild, market prices, and companyfacts ingestion are implemented

Post provider implementation live audit on 2026-06-03 showed:

- 170 SEC companyfacts were ingested for Netflix from the SEC companyfacts API
- 0 market prices were ingested because Stooq returned an API-key requirement page and Yahoo chart returned HTTP 429 from inside Compose
- `financial_facts` dashboard gap resolved for the live dataset
- `market_prices` remains an open blocker for impact windows
- `turn_impact` section exists and stays unavailable until market price rows are present

## Product Rules

1. No dashboard should render a row just because a model row exists.
2. Every dashboard row must pass a dashboard-specific eligibility contract.
3. Every missing requirement must create or update a source gap.
4. SEC 10-K risk-factor language is a candidate signal, not a strategic turn.
5. A strategic turn must describe a specific company action, not generic pressure.
6. Market reaction is not strategy success.
7. Financial impact must come from SEC companyfacts or be marked unavailable.

## Dashboard Data Contracts

### Company Strategic Intelligence

Minimum eligible data:

- company metadata
- dated source-backed business events
- source claim
- actual company action
- confidence score
- source document
- source type
- review status

Additional high-quality data:

- clustered strategic turns
- source evidence snippets
- source confidence
- unavailable impact fields when market/financial data is missing

### Strategic Turn Impact

Minimum eligible data:

- eligible strategic turn
- event date
- company ticker
- daily stock price and volume
- benchmark/index price series
- event windows: T+1, T+7, T+30, T+90, 1Y, 3Y, 5Y

Financial impact data:

- SEC companyfacts revenue
- operating income/margin
- free cash flow
- debt
- capex
- before/after periods

### Strategic Pattern

Minimum eligible data:

- reviewed strategic turn
- normalized pattern label
- sample size
- confidence status
- source-backed examples

Rules:

- do not show success rate until minimum reviewed sample exists
- do not include generic turns

### Companies Like Mine

Minimum eligible data:

- sector
- geography
- company stage
- business model
- revenue band
- pressure trigger
- matched dimensions
- similarity reasons

Rules:

- never show “similar” without reason fields
- mark missing dimensions as source gaps

### Risk Signals

Minimum eligible data:

- dated source-backed risk event or calculated financial/market risk
- source and method
- confidence score

Risk signal sources:

- SEC business/risk/MD&A text
- layoffs/restructuring events
- leadership events
- regulatory/legal events
- revenue/margin/debt trends from companyfacts
- sector-adjusted stock underperformance from market data

### Source Confidence

Minimum eligible data:

- source document counts
- source type split
- source status
- extraction status
- review status
- missing source gaps

### Event Scanner / Latest Strategic Moves

Minimum eligible data:

- event date
- company action
- event type
- source document
- source claim
- confidence score

Preferred sources:

- SEC 8-K
- company press releases
- investor relations/newsroom
- high-quality supporting news metadata

### Founder / Business Question Dashboard

Minimum eligible data:

- question template
- eligible event/turn examples
- source IDs
- evidence fields

Rules:

- no unsupported advice
- cite event/source IDs

### Strategy Scorecard

Minimum eligible data:

- eligible strategic turn
- evidence-backed dimension scores
- confidence reason per dimension

Do not score:

- market reaction without price data
- revenue/margin impact without companyfacts
- long-term value without sufficient windows

### Compare Strategic Turns

Minimum eligible data:

- two or more eligible turns
- same comparable dimension or pattern
- event dates
- company stage/context
- pressure trigger
- source confidence

Rules:

- do not compare generic turns
- show missing dimensions explicitly

## Ingestion Upgrade Phases

### Phase 1: Eligibility And Source Gaps

Implement:

- persisted `SourceGap`
- dashboard eligibility functions
- dashboard data APIs use eligibility filters
- audit command reports eligibility counts
- UI displays eligibility status and source gaps

Status: implemented in the current branch.

Tests:

- source gap creation/update
- generic event rejection
- generic turn rejection
- dashboard API excludes ineligible rows

### Phase 2: Better Event Sources

Implement:

- SEC 8-K ingestion for major dated events
- SEC 10-Q/10-K section-aware extraction
- company press release / investor relations metadata ingestion
- Wikipedia reference extraction as supporting evidence
- GDELT/news metadata as support only

Quality rules:

- 10-K risk text defaults to risk candidate
- 8-K and press releases can create strategic-move candidates
- supporting sources can raise confidence but not replace authoritative sources

### Phase 3: Evidence Confluence

Implement event clusters by:

- company
- event type
- event date/window
- action phrase
- source type

Promotion rules:

- one authoritative source plus specific action can be eligible
- two independent sources improve confidence
- generic text or no action remains candidate-only

### Phase 4: Strategic Turn Rebuild

Implement:

- rebuild turns from eligible event clusters only
- action-specific title
- before/after/trigger/outcome derived from evidence
- source links
- no generic template titles

Tests:

- current generic turns are excluded
- eligible event cluster creates one turn
- repeated source documents do not create duplicate turns

### Phase 5: Market Data

Implement:

- ticker mapping
- Stooq daily OHLCV client
- benchmark series: SPY, QQQ, sector ETFs
- event-window return calculator

Dashboard enablement:

- Strategic Turn Impact
- Strategy Scorecard
- Compare Strategic Turns

Status: partially implemented in the current branch. The `MarketPrice` model, Stooq command, scheduler hook, dashboard section, and event-window calculation exist. Live Stooq access currently requires an API key, so a configured provider credential or alternate permitted price source is still needed to populate rows.

### Phase 6: SEC Companyfacts

Implement:

- SEC companyfacts client
- metric mapper
- quarterly/annual facts table
- before/after financial windows

Dashboard enablement:

- impact dashboard
- risk signals
- scorecard
- companies-like-mine revenue bands

Status: partially implemented in the current branch. The `FinancialFact` model, SEC companyfacts client, ingestion command, scheduler hook, dashboard source-confidence counts, and live Netflix backfill are working. Before/after trend windows still need to be promoted into scorecard dimensions after strategic-turn rebuild.

### Phase 7: Company Situation Enrichment

Implement:

- lifecycle stage
- revenue band
- business model
- crisis/growth/margin/product problem tags
- similarity reasons

Dashboard enablement:

- Companies Like Mine
- Founder / Business Questions

### Phase 8: Pattern Taxonomy

Implement:

- pattern labels
- pattern assignment
- reviewed outcome labels
- minimum sample-size gate

Dashboard enablement:

- Strategic Pattern
- Compare Strategic Turns
- Founder / Business Questions

## API Plan

Ingestion internal APIs:

- `GET /dashboard-data`
- `GET /data-quality/source-gaps`
- `POST /data-quality/source-gaps/rebuild`
- `GET /events/eligible`
- `GET /turns/eligible`
- `GET /patterns`
- `GET /impact/availability`

Main app APIs:

- proxy `dashboard-data` through `GET /api/app/dashboard`
- expose dashboard-specific endpoints only after eligibility exists

## UI Plan

Rules:

- dashboard tabs fetch eligible data only
- if eligible rows are zero, show source gaps and next ingestion task
- source confidence visible on every row
- no table of internal extraction rows as product insight

## Verification Standard

Every phase must run:

```bash
docker compose -f infra/docker-compose.yml run --rm ingestion .venv/bin/python manage.py test apps.ingestion
docker compose -f infra/docker-compose.yml run --rm main-backend python manage.py test apps.search
docker compose -f infra/docker-compose.yml run --rm main-frontend npm run build
bash scripts/smoke/sprint1_dashboard_search.sh
docker compose -f infra/docker-compose.yml exec -T ingestion .venv/bin/python manage.py audit_data_quality --sample-size 10
```

If Docker image rebuild is blocked by credential helper issues, run tests with source mounts and copy changed files into running containers only for temporary local validation.
