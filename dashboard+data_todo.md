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
