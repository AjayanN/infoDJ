# Dashboard + Data Todo

This file defines the non-MVP dashboard and data standard for InfoDJ.

Core rule:

```text
No placeholder data. If data is unavailable, show unavailable with source gap metadata and add an ingestion task/source.
```

## Product Standard

The product dashboard should not expose generic extraction rows as insight.

User-facing data must be:

- source-backed
- specific to the company
- tied to an event date
- confidence-scored
- traceable to source documents
- marked unavailable when missing

Internal extracted rows can be noisy. User-facing dashboards cannot be noisy.

## Dashboard Standard

Remove duplicated admin tables from first-level dashboard screens when the same information is already shown graphically.

Current immediate UI change:

```text
Remove dashboard Classification -> Sectors table.
Keep and improve charts.
Move detailed sector table to a future drilldown/export view only.
```

Primary dashboards to build as first-class product surfaces:

1. Company Strategic Intelligence Dashboard
2. Strategic Turn Impact Dashboard
3. Strategic Pattern Dashboard
4. Companies Like Mine Dashboard
5. Risk Signals Dashboard
6. Source Confidence Dashboard
7. Event Scanner / Latest Strategic Moves
8. Founder / Business Question Dashboard
9. Strategy Scorecard
10. Compare Strategic Turns

## Dashboard Backlog

Each dashboard must use real source-backed data only. If required data is missing, the dashboard must show a clear unavailable state and create/record the source gap.

### 1. Company Strategic Intelligence Dashboard

Purpose:

- Make one company page the primary product surface.
- Show what the company did, why it mattered, what pressure caused it, and what happened after.

Core views:

- strategic timeline
- event category bands
- major turn detail panel
- source evidence panel
- impact summary
- similar historical moves
- source confidence

Required data:

- company metadata
- curated business events
- high-quality strategic turns
- source documents
- SEC filings
- Wikipedia/Wikimedia references
- GDELT/news metadata
- market prices
- financial facts
- peer/index benchmarks

Backend/API work:

- `GET /api/app/companies/{slug}/intelligence`
- `GET /api/app/companies/{slug}/timeline`
- `GET /api/app/companies/{slug}/turns/{turn_id}`
- `GET /api/app/companies/{slug}/source-confidence`

UI work:

- timeline canvas/list
- event category filters
- source drawer
- impact panel
- unavailable-state panel for missing market/financial data

Quality gate:

- hide generic turns
- every visible turn must include exact company action and source claim
- every impact metric must include source/provider/window

### 2. Strategic Turn Impact Dashboard

Purpose:

- Validate market, financial, and operating impact after a strategic move.

Core views:

- event-window stock reaction
- index-adjusted return
- sector-adjusted return
- competitor-adjusted return
- revenue/margin/free-cash-flow before vs after
- volume/volatility movement

Required windows:

```text
T+1 day
T+7 days
T+30 days
T+90 days
T+1 year
T+3 years
T+5 years
```

Required data:

- event date
- ticker
- daily price and volume
- index/sector benchmark prices
- peer ticker set
- SEC companyfacts financials

Backend/API work:

- `GET /api/app/turns/{turn_id}/impact`
- `POST /api/app/market-prices/backfill`
- `POST /api/app/financial-facts/backfill`

UI work:

- return-window chart
- benchmark comparison chart
- before/after financial table and chart
- unavailable metric cards with source gap reason

Quality gate:

- never call stock return “strategy success”
- label it as market reaction only
- require benchmark-adjusted numbers when possible

### 3. Strategic Pattern Dashboard

Purpose:

- Convert company histories into reusable strategic patterns.

Example patterns:

- Services to SaaS
- Hardware to software
- One-product company to platform
- Marketplace expansion
- Subscription model shift
- Freemium to enterprise
- Founder-led to professional CEO
- Failed acquisition
- Successful acquisition
- Turnaround after layoffs
- International expansion
- Cloud migration
- AI repositioning
- Regulatory survival
- Vertical integration
- Cost-cutting before profitability

Required data:

- normalized strategic turn types
- event outcomes
- source-backed pattern labels
- impact metrics
- failed/success examples

Backend/API work:

- `GET /api/app/patterns`
- `GET /api/app/patterns/{slug}`
- `GET /api/app/patterns/{slug}/companies`
- `GET /api/app/patterns/{slug}/impact-summary`

UI work:

- pattern cards
- success/failure split
- average time-to-impact chart
- best examples and failed examples
- source confidence indicators

Quality gate:

- no pattern success rate until enough reviewed events exist
- show sample size and confidence

### 4. Companies Like Mine Dashboard

Purpose:

- Let users benchmark their situation against similar historical company situations.

Inputs:

- industry
- company stage
- revenue range
- funding stage
- geography
- business model
- crisis type
- growth problem
- margin problem
- product problem

Outputs:

- similar companies
- similar strategic situations
- moves they tried
- what worked
- what failed
- warning signs

Required data:

- company metadata
- lifecycle stage
- revenue/size facts
- business model classification
- event pressure/trigger
- outcomes and impact metrics

Backend/API work:

- `POST /api/app/benchmarks/companies-like-mine`
- `GET /api/app/benchmarks/filter-options`

UI work:

- filter form
- similarity results
- side-by-side move comparison
- evidence links

Quality gate:

- similarity score must expose reason fields
- do not show “similar” without matching dimensions

### 5. Risk Signals Dashboard

Purpose:

- Surface warning signs and show what companies did next.

Risk signals:

- revenue slowdown
- margin compression
- rising debt
- customer concentration
- founder/CEO exit
- repeated layoffs
- acquisition integration issues
- declining R&D productivity
- stock underperformance vs sector
- negative sentiment
- regulatory pressure

Required data:

- SEC financial facts
- market prices and sector benchmarks
- leadership events
- layoff/restructuring events
- regulatory/legal events
- sentiment/news metadata when available

Backend/API work:

- `GET /api/app/risk-signals`
- `GET /api/app/companies/{slug}/risk-signals`
- `GET /api/app/risk-signals/{signal}/historical-examples`

UI work:

- risk heatmap
- signal trend chart
- “what happened next” examples
- source confidence panel

Quality gate:

- risk signal must include source and calculation method
- no sentiment signal unless source supports it

### 6. Source Confidence Dashboard

Purpose:

- Make data trust visible.

Show:

- source count
- source type split
- extraction confidence
- date confidence
- duplicate detection
- human review status
- conflicting source notes
- missing source gaps

Required data:

- source documents
- extraction statuses
- review statuses
- source types
- confidence scores
- source gaps

Backend/API work:

- `GET /api/app/data-quality`
- `GET /api/app/companies/{slug}/data-quality`
- `GET /api/app/events/{id}/source-confidence`

UI work:

- source quality dashboard
- confidence badges
- gap list
- review queue links

Quality gate:

- every user-facing event/turn must expose confidence status

### 7. Event Scanner / Latest Strategic Moves Dashboard

Purpose:

- Make the product feel alive with new daily strategic moves.

Sections:

- new acquisitions
- CEO changes
- restructuring
- layoffs
- new product lines
- market expansion
- AI announcements
- major partnerships
- spin-offs
- divestitures
- regulatory events

Required data:

- daily GDELT/news metadata
- SEC 8-K/10-Q/10-K updates
- Wikipedia/Wikimedia changes where useful
- company press releases where allowed

Backend/API work:

- `GET /api/app/events/latest`
- `GET /api/app/events/latest?category=ACQUISITION`
- `GET /api/app/events/{id}/similar-history`

UI work:

- latest moves feed
- filters by category/sector/date
- similar historical moves panel

Quality gate:

- latest events must be source-backed and dated
- speculative news should be marked lower confidence

### 8. Founder / Business Question Dashboard

Purpose:

- Let users start from decision questions, not raw data exploration.

Question groups:

- early founder
- growth-stage founder
- investor
- student/consultant
- operator/product leader

Example questions:

- What strategic moves helped companies get their first growth spike?
- When did similar companies pivot?
- Which companies expanded internationally too early?
- Which acquisition types usually failed?
- Which strategic turns created long-term shareholder value?

Required data:

- indexed event/turn facts
- pattern library
- company-stage classifications
- impact metrics
- confidence and source metadata

Backend/API work:

- `GET /api/app/questions`
- `POST /api/app/questions/answer`
- `GET /api/app/questions/{slug}/examples`

UI work:

- question template gallery
- answer page with evidence
- comparison examples

Quality gate:

- answers must cite event IDs/source IDs
- no unsupported recommendations

### 9. Strategy Scorecard Dashboard

Purpose:

- Score each strategic turn across multiple evidence-backed dimensions.

Dimensions:

- market reaction
- revenue impact
- margin impact
- competitive advantage
- execution risk
- long-term value
- confidence

Classifications:

- strong success
- partial success
- too early to judge
- market-positive, business-negative
- market-negative, business-positive
- failed strategy
- defensive necessity

Required data:

- impact windows
- financial facts
- peer/sector benchmarks
- source confidence
- reviewed outcomes

Backend/API work:

- `GET /api/app/turns/{turn_id}/scorecard`
- `POST /api/app/turns/{turn_id}/scorecard/rebuild`

UI work:

- radar/bar scorecard
- evidence panel per score
- confidence explanation

Quality gate:

- no score without evidence
- every score must show confidence and reason

### 10. Compare Strategic Turns Dashboard

Purpose:

- Compare two or more strategic moves across timing, context, and results.

Examples:

- Netflix streaming pivot vs Blockbuster response
- Adobe subscription shift vs Autodesk subscription shift
- Nvidia CUDA/GPU strategy vs Intel CPU strategy
- Amazon AWS vs Google Cloud
- Meta Reality Labs vs Apple Vision Pro

Comparison dimensions:

- timing
- company stage
- market condition
- pressure/trigger
- initial investor reaction
- revenue impact
- margin impact
- moat creation
- execution period
- long-term result

Required data:

- strategic turn records
- event impact metrics
- source-backed summaries
- peer/index benchmarks
- pattern classification

Backend/API work:

- `POST /api/app/compare/strategic-turns`
- `GET /api/app/compare/suggest-turns?q=...`

UI work:

- comparison selector
- side-by-side panels
- impact charts
- difference summary

Quality gate:

- do not compare turns without matching minimum data quality
- show unavailable fields explicitly

## Data Quality Rules

User-facing strategic turns require:

- specific company action
- source claim
- source count
- source type
- extraction confidence
- date confidence
- impact data or explicit impact-unavailable reason

Hide or downgrade generic turns like:

```text
Company adapts to regulatory and legal risk.
Adapt to legal, regulatory, and compliance pressure.
```

Prefer specific event rows until a turn has a strong narrative.

## Free Source Plan

### Company Metadata

Use:

- Wikidata SPARQL
- SEC submissions API
- Wikipedia / Wikimedia references

Daily scheduler responsibility:

- refresh known companies
- update CIK/ticker/aliases/sector/country
- detect missing ticker/CIK as a source gap

### Filings and Financials

Use official SEC APIs:

- Submissions API
- Companyfacts API
- Frames API

Source references:

- SEC EDGAR APIs: https://www.sec.gov/edgar/sec-api-documentation

Daily scheduler responsibility:

- fetch latest 10-K, 10-Q, 8-K metadata
- fetch companyfacts for financial metrics
- map revenue, operating income, net income, assets, liabilities, cash flow, shares, capex where available
- never invent missing financial facts

### Market Data

Use free sources first:

- Stooq downloadable CSV/history
- Free public historical stock APIs only after license/rate-limit review

Source references:

- Stooq historical data: https://stooq.com/db/h/

Daily scheduler responsibility:

- refresh historical daily close/volume for known tickers
- refresh benchmark ETFs/indices for sector-adjusted return
- compute event windows only when market data exists

Benchmark proxies:

```text
SPY or ^SPX -> broad market
QQQ or ^NDX -> technology/growth benchmark
XLK -> Information Technology
XLF -> Financials
XLE -> Energy
XLV -> Health Care
XLY -> Consumer Discretionary
XLP -> Consumer Staples
XLI -> Industrials
XLU -> Utilities
XLC -> Communication Services
XLB -> Materials
XLRE -> Real Estate
```

### News and Event Discovery

Use:

- GDELT DOC 2.0
- Wikipedia references
- company press releases when allowed
- website scraping only when robots/terms allow it
- Common Crawl later for large-scale archive work

Source references:

- GDELT DOC 2.0: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

Daily scheduler responsibility:

- fetch English source metadata first
- store source URL/title/publisher/date/snippet/language
- do not store copyrighted full text unless permitted and necessary
- prefer extracted facts, short evidence, and source links

### Macro and Sector Context

Use:

- FRED API for macro series
- sector ETF price series from free market source

Source references:

- FRED API: https://fred.stlouisfed.org/docs/api/fred/

Daily scheduler responsibility:

- refresh configured macro series when API key exists
- mark macro unavailable when key is missing
- do not block company ingestion on macro refresh failure

## Scraping Policy

Scraping is allowed only when:

- public page access is allowed
- robots/terms do not prohibit it
- rate limiting is conservative
- data stored is minimal and source-linked
- failures are tracked as ingestion jobs

Prefer APIs over scraping.

Scraping candidates:

- company investor relations press releases
- company newsrooms
- public HTML tables with permissive access
- Wikipedia references

Avoid:

- paywalled articles
- login-required pages
- content with explicit no-scrape restrictions
- storing full copyrighted articles

## Daily Scheduler Stages

The daily scheduler should run these source stages:

```text
1. company_metadata
2. source_discovery_sec
3. source_discovery_wikipedia
4. source_discovery_gdelt
5. financial_facts_sec_companyfacts
6. market_prices_stooq
7. macro_context_fred
8. article_extraction
9. business_event_extraction
10. strategic_turn_rebuild
11. data_quality_scoring
```

Each stage must be idempotent by:

- company
- source
- date
- provider
- metric type when applicable

## Implementation Phases

### Phase 1: Dashboard Cleanup and Search Quality

- Remove repeated sector classification table from dashboard.
- Keep graph-first sector coverage.
- Filter generic strategic-turn search results.
- Show source-specific business events above strategic turns.

### Phase 2: Market Data Foundation

- Add market price tables.
- Add Stooq client.
- Add daily price refresh command.
- Add event-window return calculation.
- Add market/index/sector-adjusted return fields.

### Phase 3: SEC Financial Facts Foundation

- Add financial fact tables.
- Add SEC companyfacts client.
- Add quarterly/annual metric mapper.
- Add before/after event financial windows.

### Phase 4: Source Gap Tracking

- Add source gap table or status model.
- Record missing ticker, missing CIK, missing market data, missing financial facts, missing macro key.
- Show unavailable data honestly in the dashboard.

### Phase 5: Source Confidence

- Score source count, source type, extraction confidence, review status, conflict flags.
- Show confidence in every user-facing event/turn.

### Phase 6: Company Strategic Intelligence Dashboard

- Build the company intelligence API.
- Build timeline and event-detail UI.
- Add source evidence drawer.
- Add unavailable states for missing market/financial impact.
- Make this the primary company page.

### Phase 7: Strategic Turn Impact Dashboard

- Add event-window impact APIs.
- Add stock/index/sector benchmark charts.
- Add financial before/after charts.
- Label stock data as market reaction, not strategy success.

### Phase 8: Source Confidence Dashboard

- Build data-quality APIs.
- Build source confidence dashboard.
- Add confidence badges to search, timeline, and turn pages.
- Add source gap queue.

### Phase 9: Event Scanner Dashboard

- Build latest strategic moves API.
- Add category/sector/date filters.
- Add similar historical moves panel.
- Integrate daily GDELT/SEC/Wikipedia source refreshes.

### Phase 10: Strategic Pattern Dashboard

- Add pattern taxonomy.
- Map strategic turns to patterns.
- Build pattern pages with examples, risks, impact windows, and confidence.

### Phase 11: Companies Like Mine Dashboard

- Add filter metadata and similarity scoring.
- Build benchmark query API.
- Build company/situation comparison UI.

### Phase 12: Risk Signals Dashboard

- Add risk signal models/calculations.
- Build heatmap and signal timeline.
- Link each risk signal to historical responses.

### Phase 13: Founder / Business Question Dashboard

- Add question templates.
- Build evidence-backed answer API.
- Add role-specific question galleries.

### Phase 14: Strategy Scorecard Dashboard

- Add scorecard model.
- Add evidence-backed score calculations.
- Build scorecard visualization and confidence explanations.

### Phase 15: Compare Strategic Turns Dashboard

- Add compare-turns API.
- Add turn suggestion search.
- Build side-by-side comparison UI with impact charts.

## Commands To Maintain

Daily source command:

```bash
.venv/bin/python manage.py daily_company_update \
  --include-gdelt \
  --include-market-data \
  --include-financial-facts \
  --include-macro-context \
  --include-quality-scoring
```

Scheduler command:

```bash
.venv/bin/python manage.py run_ingestion_api_with_scheduler \
  --host 0.0.0.0 \
  --port 8001 \
  --scheduler-timezone UTC \
  --limit 20 \
  --batch-size 10 \
  --include-gdelt \
  --include-market-data \
  --include-financial-facts \
  --include-macro-context \
  --include-quality-scoring \
  --split-batches
```

## Verification Standard

Every new data source must include:

- client tests
- command tests
- API/source failure test
- no-placeholder-data test
- scheduler option propagation test
- dashboard unavailable-state test

Every dashboard feature must include:

- actual API-backed data
- empty/unavailable state
- source/confidence display
- no generic placeholder rows
