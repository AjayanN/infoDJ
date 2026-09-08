# InfoDJ Active Backlog

### Evidence conflicts and decision relevance

- **Outcome:** disputed dates and formation-only records cannot silently qualify as customer-validation evidence.
- **Remaining acceptance:** provide an explicit reviewed conflict-resolution workflow; classify actions against the requested decision, not stage/age alone.
- **Open research:** reconcile Ford first-sale records (July 15 versus July 23, 1903) using the underlying transaction evidence.
- **Review:** data/historical-lifecycle/REVIEW-2026-09-07.md.
- **Owner/status:** InfoDJ historical evidence goal / open.

This file is the single register for unfinished product, data, and operational work.

## Rules

- Add a concise item when work is accepted but not complete.
- Include the outcome, acceptance criteria, and any dependency.
- Keep only active or pending work here.
- **Remove an item immediately when it is complete.** Git history, issues, and pull requests remain the completion record.
- Do not use this file to preserve a completed-task archive.

## Active

### Product-episode founder stories and reusable historical ingestion

- **Outcome:** founders learn connected product-building histories across product, customers, pricing, team, marketing, IP, legal and operations, matched to their situation and immediate decision.
- **Plan:** docs/founder-story-plan/START_HERE.txt; machine-readable architecture, source catalog, contracts, 14 task files and 16 acceptance gates.
- **Acceptance:** all acceptance.json gates have source, runtime and visual evidence; old and newly added companies use the same pipeline; no pilot-only completion or fabricated history.
- **Status:** comprehensive planning completed; implementation tasks have not started. Existing historical evidence work is the baseline, not proof these new gates pass.

### Historical lifecycle evidence — all companies

- **Outcome:** founders receive only historical, stage-matched comparable actions across every company in the InfoDJ universe.
- **Acceptance:** every company has verified primary or authoritative founding evidence; each supported lifecycle stage has at least two exact-date, source-linked historical actions; every surfaced event has a lifecycle episode, company age where exact founding evidence permits it, industry context, and source URL.
- **Dependency:** historical primary-source research and review.

### Founder comparison precision

- **Outcome:** comparison considers sector, stage, company age, business model, target customer, and decision type.
- **Acceptance:** onboarding captures available dimensions; API returns match rationale and abstains below two verified comparables.
- **Dependency:** historical lifecycle pilot coverage.

### Historical source coverage queue

- **Outcome:** source gaps become actionable research work rather than invisible empty states.
- **Acceptance:** each missing sector/stage/decision combination is recorded with primary-source targets and an owner/status.
- **Dependency:** lifecycle episode coverage reporting.
- **Research registry:** `data/historical-lifecycle/SOURCE_REGISTRY.md` lists each company’s founding source, SEC API endpoint, and verified lifecycle links.

#### Current exact-date targets

| Company / sector | Missing evidence | Primary-source target |
| --- | --- | --- |
| ExxonMobil / Energy | First post-merger operating product, customer, or capital move with a day-level action date | Company archive; CIK 0000034088 SEC filings |
| Pfizer / Health Care | Early product/customer validation event before long-term maturity | Pfizer history archive; CIK 0000078003 SEC filings |
| Freeport-McMoRan / Materials | 1981 formation/first operating move with a day-level date | Investor archive; CIK 0000831259 SEC filings |
| Newmont / Materials | 1921–1925 formation/public-share action with a day-level date | Newmont archive; CIK 0001164727 SEC filings |
| NextEra Energy / Utilities | 1984 holding-company or 1997 clean-energy-unit action with a day-level date | Investor archive; CIK 0000753308 SEC filings |


### Lifecycle scope and operating lineage

- **Outcome:** distinguish company, product, and business-line stages; legal incorporation, IPOs, mergers and operating inception cannot silently substitute for one another.
- **Acceptance:** preserve sourced lineage and anchor type; compute product age from a sourced product inception; expose scope and subject in the API and UI; test mature-company product validation separately from startup validation.
- **Remaining work:** capture sourced product/business-line inception and founder comparison scope in onboarding; match using the selected subject's age and show the subject in the UI. Company-stage evidence must be reviewed separately for a product action that also establishes a company's early operating stage.
- **Owner/status:** InfoDJ historical evidence goal / open.
