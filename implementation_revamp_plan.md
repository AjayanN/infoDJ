# InfoDJ Evidence-First Revamp - Execution TODO

## Purpose

Make InfoDJ a fast, trustworthy founder decision product. The default experience
must answer one current founder question from prepared, source-backed company
evidence. Company 360 remains the detailed research surface.

This runbook is ordered. Do not begin a later milestone until the listed
acceptance checks for the previous milestone pass.

## Non-negotiable rules

- [ ] Work on a dedicated branch named `feature/evidence-first-foundation`.
- [ ] Keep all facts source-backed: source URL, publisher, publication date,
  extraction time, company, sector, and review state.
- [ ] Label all output as `reported_fact`, `observed_pattern`,
  `founder_hypothesis`, or `unavailable`.
- [ ] Never represent headquarters country as operating geography.
- [ ] Preserve numeric values with unit/currency/period; do not flatten them
  into prose.
- [ ] Keep ordinary founder requests deterministic and fast. Runtime AI may
  improve cached wording but cannot be the only path to an answer.
- [ ] Run targeted tests before Docker Compose rebuilds. Merge only after
  successful tests, deployment smoke checks, and mobile review.

## Implementation progress

- [x] Replaced the broad revamp plan with this execution runbook.
- [x] Created, tested, merged, and deployed the first coverage foundation.
- [x] Added `headquarters_country`, `operating_regions`, and
  `revenue_geographies` schema fields.
- [x] Added `GET /companies/{slug}/coverage` with dimension-level missing
  reasons.
- [x] Removed the profile fallback that treated headquarters country as the
  operating geography.
- [x] Added focused geography and coverage API tests; 85 ingestion tests pass.
- [x] Activate the remaining 10 configured companies; all 20 are active.
- [x] Add the retrieval-ready evidence ledger and its idempotent backfill;
  3,524 existing events, turns, and financial facts are indexed.
- [x] Wire company activation and evidence-ledger rebuilding into the daily
  ingestion pipeline.
- [x] Backfill first-party sources for the ten newly activated companies:
  287 sources, 111 events, 51 turns, and 1,486 additional financial facts.
- [x] Make expected missing reviewed milestones non-fatal so the scheduler
  completes and rebuilds the ledger.
- [x] Refactor company-universe activation into declarative, idempotent
  metadata updates.
- [x] Pin ExxonMobil's canonical SEC identifier so annual-report ingestion is
  not redirected to a ticker-matched holding company.
- [x] Refresh Company 360 profiles after SEC filing extraction in the daily
  ingestion sequence.
- [ ] Populate reviewed Company 360 profile dimensions from the new sources.

## Coverage audit - 2026-08-16

**Verified baseline**

- [x] Audited all 20 active companies: 932 source documents, 145 successful
  extractions, and at least one successfully extracted SEC 10-K plus one
  SEC-backed profile snapshot for every company.
- [x] Repaired ExxonMobil's canonical SEC identifier and backfilled five
  annual reports, 14 events, 11 strategic turns, and its profile snapshot.
- [x] Parse geographic disclosures across the full SEC filing and refresh all
  Company 360 profiles; operating-region gaps fell from 18 to 2 and
  revenue-region gaps from 19 to 5.

**Priority 0 - coverage semantics and evidence quality**

- [ ] Extend the remaining geography parser coverage for Microsoft, Prologis,
  and the five companies without an explicit revenue-region disclosure.
- [x] Build reviewed, source-linked management promises from filings for 19
  companies. Prologis still needs an earnings or investor source containing a
  qualifying forward-looking statement.
- [ ] Complete sparse profile dimensions: Microsoft and Walmart revenue
  sources; Netflix subsidiaries, customer groups, payer/user model components;
  Prologis strategic priorities; and incomplete Business Model Map components
  for Microsoft, Walmart, and Netflix.

**Priority 1 - missing reusable data streams**

- [ ] Backfill SEC Company Facts for American Tower, Caterpillar, Disney,
  Ford, Freeport-McMoRan, and General Electric. Each has a valid CIK and a
  successfully extracted 10-K; the Company Facts task was not run for them.
- [ ] Add a market-data provider configuration and backfill 18 companies.
  Only Amazon and Pfizer currently have market prices.
- [ ] Implement and validate first-party product-price collection by sector;
  product-price observations are zero for all 20 companies.
- [ ] Implement Form 4 ownership/insider backfill and source-linked contract
  dependency extraction; both streams are zero for all 20 companies.

**Priority 2 - source resilience**

- [ ] Add source-specific retries/fallbacks for American Tower (robots denied)
  and Caterpillar (official-site timeout), while respecting robots and using
  first-party investor-relations sources where allowed.
- [ ] Raise source depth for thin portfolios, starting with Ford (23 sources),
  Disney (26), General Electric (30), American Tower (32), and Caterpillar
  (32), before treating cross-company comparisons as representative.

## Baseline: known gaps to fix

- [ ] 20 companies are configured but only 10 are active in the database.
- [ ] All current Company 360 semantic profile validations fail.
- [ ] Product-price observations, dependency contract terms, and insider
  transactions are currently empty.
- [ ] 573 source documents exist but only 55 successful extractions exist.
- [ ] Existing turns/events include generic wording and need evidence gating.
- [ ] `Company.country` means company domicile/headquarters and must not be
  shown as operating footprint (for example, Netflix is not US-only).

## Milestone 1 - Canonical evidence and geography contract

### 1.1 Add a retrieval-ready evidence ledger

- [ ] Add an `EvidenceRecord` model in
  `services/ingestion/apps/ingestion/models.py`.
- [ ] Include: company, sector, evidence type, event date, published date,
  source document, source excerpt, title, summary, geography, entities, tags,
  numeric metrics, confidence, review status, and extraction metadata.
- [ ] Keep the existing specialised Company 360 models. `EvidenceRecord` is an
  indexed read model, not a replacement for authoritative source objects.
- [ ] Add a unique source/claim fingerprint to make scheduler backfills
  idempotent.
- [ ] Add a migration and model tests for uniqueness, required provenance, and
  numeric metric preservation.

### 1.2 Correct geography semantics

- [x] Add `headquarters_country`, `operating_regions`,
  `revenue_geographies`, and `market_footprint_status` to the Company 360
  profile contract.
- [ ] Keep legacy `Company.country` as the configured domicile only; rename
  frontend labels to `Headquarters` until a migration can rename the field.
- [x] Build geographic extraction from annual-report segments and official
  geographic disclosures.
- [x] Add Netflix fixture assertions for UCAN, EMEA, LATAM, and APAC when
  directly supported by a source; do not fabricate country-level presence.
- [ ] Add source freshness and missing-reason fields for every geography item.

### 1.3 Coverage contract and API

- [ ] Define mandatory dimensions globally: identity, profile, business model,
  products/pricing, customers, revenue, geography, strategy, risks, sources.
- [ ] Add sector-required dimensions through a new sector schema registry.
- [x] Implement `GET /companies/{slug}/coverage` in ingestion API.
- [ ] Return each dimension's status, source count, freshness, missing reason,
  and last reviewed date.
- [ ] Update `audit_company360_coverage` to calculate the same score used by
  the API; no separate UI-only calculation.

**Acceptance**

- [ ] Netflix shows `Headquarters: United States` separately from sourced
  operating/revenue regions.
- [ ] API and CLI coverage scores agree exactly for ExxonMobil and Netflix.
- [ ] Every coverage result explains missing data instead of returning a vague
  percentage.

## Milestone 2 - Activate and baseline all 20 US companies

### 2.1 Company universe activation

- [x] Add an idempotent command that creates/activates all records from
  `company_universe.py` without overwriting reviewed data.
- [x] Seed the missing companies: Ford, Tesla, Caterpillar, General Electric,
  Disney, Netflix, Prologis, American Tower, Freeport-McMoRan, and Newmont.
- [ ] Add a test that the active universe contains all configured companies.

### 2.2 First-party source baseline

- [ ] For every company ingest annual reports, 10-K/10-Q filings, earnings
  releases, investor presentations, official newsroom pages, product pages,
  and official pricing pages where available.
- [ ] Store source authority and collection reason.
- [ ] Deduplicate source documents by canonical URL and content fingerprint.
- [ ] Add a retry queue with error category, retry time, and visible source gap.

### 2.3 Structured profile baseline

- [ ] Populate the profile fields: segments, products, customers, revenue
  sources, geographies, leadership, competitors, and priorities.
- [ ] Build all Business Model Map component types: payer, user, offer,
  delivery, revenue, key costs, and relationships.
- [ ] Require a reviewed management-promise record only when the source basis
  supports it; otherwise expose a transparent source gap.

**Acceptance**

- [ ] All 20 companies exist and are active.
- [ ] Every company has a current profile, Business Model Map, and direct
  source links.
- [ ] `validate_company_profiles --limit 20` reports only explicit, actionable
  missing dimensions; no parser fragments or filing boilerplate.

## Milestone 3 - Sector-specific enrichment modules

### 3.1 Create a sector module interface

- [ ] Add a registry keyed by sector in
  `services/ingestion/apps/ingestion/services/`.
- [ ] Each module declares source collectors, required dimensions, extraction
  normalisers, freshness windows, quality gates, and fixture companies.
- [ ] Invoke modules from `daily_company_update` and
  `scheduled_daily_update`; no manual-only path is acceptable.

### 3.2 Implement Energy first

- [ ] Collect ExxonMobil and NextEra official annual reports, earnings
  materials, project updates, regulator material, and investor presentations.
- [ ] Extract assets/projects, production/capacity, realised prices, capex,
  reserves where disclosed, operating regions, permits/regulatory matters,
  and commodity sensitivity.
- [ ] Create source-backed price/contract data only where an official source
  publishes it; otherwise show `unavailable`.
- [ ] Add Energy fixture tests, including a complete ExxonMobil gap report.

### 3.3 Implement remaining sector modules

- [ ] Communication: audience, subscribers, advertising, licensing, content,
  distribution, regional revenue.
- [ ] Technology: offering, packaging, pricing, adoption, usage, customer
  segment, cost-to-serve.
- [ ] Financials, Health Care, Consumer, Consumer Staples, Industrials,
  Materials, Real Estate, and Utilities: implement the schema declared in the
  sector playbook and source it from first-party/regulator evidence.

**Acceptance**

- [ ] Scheduled ingestion improves or preserves coverage on rerun.
- [ ] At least two companies per active sector have comparable sourced facts.
- [ ] No sector-specific value appears without a dated source and unit where
  relevant.

## Milestone 4 - Quality, review, and fast retrieval

### 4.1 Evidence quality gates

- [ ] Reject generic event/turn phrasing from founder-visible datasets.
- [ ] Require a specific company action, event date, direct source, and
  confidence threshold for decision-case eligibility.
- [ ] Add conflict detection when reputable sources disagree.
- [ ] Add reviewer states: queued, approved, rejected, superseded.

### 4.2 Retrieval indexes and precomputation

- [ ] Enable PostgreSQL full-text search and `pgvector` extension.
- [ ] Create indexes for company, sector, evidence type, tags, event date,
  geography, review state, and embedding.
- [ ] Precompute `ComparableDecisionCase` records by sector, founder stage,
  decision topic, and evidence version.
- [ ] Precompute chart-ready series for revenue, price, geography, milestones,
  and sector-specific metrics.
- [ ] Add cache keys based on founder context plus evidence version.

### 4.3 APIs

- [ ] Implement `GET /companies/{slug}/coverage`.
- [ ] Implement `GET /companies/{slug}/decision-cases`.
- [ ] Implement `GET /sectors/{sector}/decision-cases?stage=&objective=`.
- [ ] Implement `GET /sectors/{sector}/evidence-summary`.
- [ ] Return source links, evidence state, confidence, freshness, and
  deterministic fallback content in every response.

**Acceptance**

- [ ] Normal founder response needs no runtime AI call.
- [ ] Founder API returns within a defined target under warm cache.
- [ ] Every displayed decision case opens its original supporting source.

## Milestone 5 - Founder decision experience

### 5.1 Guided context

- [ ] Keep one question per screen: company name, sector, business type,
  current stage, immediate objective.
- [ ] Ask geography, customer, revenue model, and constraints only when they
  improve the selected sector/stage decision.
- [ ] Save context incrementally and restore it safely.
- [ ] Provide a stable progress animation plus loading/error/empty states.

### 5.2 Decision home

- [ ] Replace initial dashboard overload with one question: `What should you
  prove next?`.
- [ ] Show at most three comparable decision paths.
- [ ] Each path contains a specific action, comparable cases, trade-off, risk,
  success metric, evidence confidence, and source drawer.
- [ ] Show a concise stage journey visual: current proof -> test -> learning ->
  next stage.
- [ ] Keep Company 360 behind an intentional `Research company` action.

### 5.3 Experiment loop

- [ ] Add `FounderExperiment`: selected path, hypothesis, test, metric,
  threshold, owner, due date, result, and next decision.
- [ ] Add a weekly check-in and progress timeline.
- [ ] Capture unanswered questions and missing evidence as ingestion backlog.

**Acceptance**

- [ ] A new founder reaches a source-backed next action in under one minute on
  a phone.
- [ ] No initial page renders raw Company 360 sections, source passports, or
  long data tables.
- [ ] Founder can open Company 360 only when they want deeper research.

## Milestone 6 - Test, deploy, and measure product-market fit

### 6.1 Required tests

- [ ] Ingestion unit tests for each collector, parser, dedupe rule, source
  gap, geography rule, and sector module.
- [ ] API contract tests for coverage, evidence, decision cases, and cache
  invalidation.
- [ ] Backend tests for provenance, permissions, and deterministic fallbacks.
- [ ] Frontend tests for onboarding, decision-home loading/empty states, source
  drawers, mobile layout, and Company 360 routing.
- [ ] Docker Compose smoke tests for migrations, scheduler, ingestion API,
  backend API, and public web path.

### 6.2 Release process

- [ ] Create a feature branch per deployable milestone.
- [ ] Run focused tests, then full relevant test suite.
- [ ] Rebuild with Docker Compose.
- [ ] Verify `https://ajayan.tech/infodj/` and API health.
- [ ] Merge to `main` only after acceptance checks pass.
- [ ] Push `main` to the configured remote once repository credentials exist.

### 6.3 PMF measurements

- [ ] Measure onboarding completion and time to first decision.
- [ ] Measure decision-path selection, experiment creation, weekly check-in,
  source-drawer open rate, and return rate.
- [ ] Ask one feedback question after the first decision: `Was this useful for
  your next action?`.
- [ ] Start with Energy pilot founders; only broaden once the evidence quality
  and repeat-use metrics are good.

## Immediate execution sequence

1. [x] Create the `feature/evidence-first-foundation` branch.
2. [ ] Add the evidence/geography coverage contract and migration.
3. [ ] Add API/CLI coverage parity tests for ExxonMobil and Netflix.
4. [ ] Activate missing configured companies idempotently.
5. [ ] Implement Energy enrichment and run a source-backed ExxonMobil backfill.
6. [ ] Validate data quality before changing the founder home again.
7. [ ] Build precomputed decision cases, then the minimal decision home.
