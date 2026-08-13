# Founder Experience Revamp - Implementation Plan

## Product outcome

InfoDJ becomes a founder decision cockpit. A founder selects sector, business type, current stage, and immediate objective. InfoDJ presents a small set of evidence-backed directions, risks, comparable company journeys, and monetisation options. Company 360 remains the source-level drill-down instead of the first screen.

## Guardrails

- [ ] Mark every statement as reported fact, observed pattern, founder hypothesis, or unavailable.
- [ ] Retain source URL, publication date, extraction date, and confidence for every chart point and recommendation.
- [ ] Never infer values, lifecycle transitions, prices, or geographic differences without evidence.
- [ ] Show insufficient evidence plainly rather than fabricating an answer.
- [ ] Treat mobile layouts and accessible text alternatives as first-class requirements.

## Milestone 0 - Baseline and delivery controls

- [ ] Create and maintain a feature branch for each independently deployable milestone.
- [ ] Establish fixture companies across Technology, Communication, and Energy.
- [ ] Record baseline API payloads, coverage, and UI screenshots for fixture companies.
- [ ] Add CI commands for frontend typecheck/tests and ingestion tests.
- [ ] Require Docker Compose rebuild, smoke test, and public tunnel verification before merge.
- [ ] Push merged main to the configured remote after each accepted milestone.

**Acceptance:** a repeatable deployment checklist exists and a regression run validates the pilot companies.

## Milestone 1 - Canonical coverage and evidence contract

### Coverage model

- [ ] Define profile completeness for the 12 Company 360 profile fields.
- [ ] Define decision readiness separately: product/pricing, customer, competitor, market, risks, strategic moves, and evidence freshness.
- [ ] Define first-party-source coverage and source confidence.
- [ ] Define freshness rules per data type and show a last-reviewed date.
- [ ] Return field-level missing reasons and source counts through an API contract.
- [ ] Use the same current snapshot window as Company 360 when calculating coverage.
- [ ] Prevent historic snapshots from satisfying a current-profile field.
- [ ] Correct country metadata where a US company is incorrectly excluded.

### Evidence model

- [ ] Store source URL, publisher, publication date, excerpt/location, ingestion time, and confidence for every claim.
- [ ] Add claim type: reported fact, observed pattern, founder hypothesis, unavailable.
- [ ] Add evidence strength: strong, moderate, weak, missing.
- [ ] Add provenance tests for APIs and visualisations.

**Acceptance:** Exxon's displayed coverage and its API score agree exactly, with explicit missing-field reasons.

## Milestone 2 - Sector and stage playbook model

- [ ] Create a configurable sector-playbook schema: founder questions, metrics, milestones, risks, pricing models, and source requirements.
- [ ] Create stage definitions: Validate, Build, Launch, Grow, and Scale.
- [ ] Support business-type refinements within a sector.
- [ ] Map strategic events to observed milestones; do not claim unobserved startup stages.
- [ ] Build pilot playbooks:
  - [ ] Technology: adoption, retention, pricing, cloud/AI economics, defensibility.
  - [ ] Communication: audience, subscription, advertising, distribution, content economics.
  - [ ] Energy: assets, projects, commodity exposure, permits, capex, geography.
- [ ] Define reusable templates for Financials, Healthcare, Consumer, Industrials, Materials, Real Estate, and Utilities.

**Acceptance:** each pilot sector returns relevant founder questions without generic metric overload.

## Milestone 3 - Founder onboarding and context

- [ ] Add onboarding for sector, business type, stage, and immediate objective.
- [ ] Add optional geography, target customer, revenue model, and constraints.
- [ ] Persist and allow editing founder context.
- [ ] Generate a question-led start screen, not a data-heavy dashboard.
- [ ] Provide clear loading, empty, and error states.
- [ ] Reset page scroll on navigation and preserve expected back-navigation behaviour.
- [ ] Verify mobile, tablet, and desktop layouts.

**Acceptance:** a new founder reaches a relevant cockpit in under one minute on a phone.

## Milestone 4 - Evidence-backed decision engine

- [ ] Create a deterministic, evidence-first response layer before any generative summary.
- [ ] Return at most three directions: fastest learning, lowest risk, highest upside.
- [ ] For each direction show next action, rationale, comparable examples, trade-offs, risks, required evidence, and source links.
- [ ] Return monetisation/pricing models only when source-backed or labelled as a pattern.
- [ ] Generate concise human-readable synthesis from structured facts, never raw ingestion dumps.
- [ ] Add abstention behaviour for missing or conflicting evidence.
- [ ] Add reviewer tooling to correct claim classification or confidence.

**Acceptance:** every recommendation is traceable to evidence or visibly labelled as a hypothesis.

## Milestone 5 - Founder-first visual cockpit

- [ ] Build a stage/milestone journey showing comparable company events chronologically.
- [ ] Build a three-path decision comparison instead of long dashboard tabs.
- [ ] Build a risk radar with category, severity, confidence, and source count.
- [ ] Build a business-model and monetisation canvas for the selected sector.
- [ ] Build a peer landscape with sector, geography, evidence strength, and similarity filters.
- [ ] Build a coverage passport showing known, stale, and missing data.
- [ ] Move detailed company metrics, sources, and raw event lists into Company 360 drill-downs.
- [ ] Provide accessible text alternatives and no-data states for all visualisations.

**Acceptance:** the dashboard answers where am I, what should I do next, and why without tab-by-tab reading.

## Milestone 6 - Reusable ingestion enrichment

- [ ] Convert enrichment into sector modules invoked by the scheduler.
- [ ] Define source authority, relevance, freshness, and deduplication gates.
- [ ] Capture products, pricing, geographic variation, revenue streams, milestones, competitors, risks, and strategic changes.
- [ ] Preserve direct-source links and extraction metadata for every record.
- [ ] Add product/pricing history builders that distinguish disclosed prices from product-only evidence.
- [ ] Expand Energy coverage for Exxon and peers using official filings, investor materials, and regulator sources.
- [ ] Add rerunnable backfill commands and idempotency checks.
- [ ] Add per-company data-gap reports to guide future collectors.

**Acceptance:** scheduled ingestion improves the structured datasets used by the cockpit; no manual-only data path is required.

## Milestone 7 - Quality, rollout, and feedback

- [ ] Add unit tests for scoring, stage mapping, playbook selection, decision responses, and provenance.
- [ ] Add API contract and frontend interaction tests.
- [ ] Add mobile visual regression coverage for onboarding, cockpit, and Company 360.
- [ ] Add ingestion fixture tests and scheduler-order tests.
- [ ] Conduct pilot review with Technology, Communication, and Energy fixtures.
- [ ] Track unanswered founder questions, missing evidence, stale sources, and failed collectors.
- [ ] Prioritise the next sector from measured coverage and founder demand.
- [ ] Document ingestion, rebuild, tests, deployment, and rollback runbooks.

**Acceptance:** pilot releases are traceable, responsive, repeatable to deploy, and ready to expand sector by sector.

## Recommended sequence

1. Baseline and canonical coverage contract.
2. Sector/stage schema and three pilot playbooks.
3. Founder onboarding and a read-only cockpit shell.
4. Structured decision engine with evidence traces.
5. Visualisations and Company 360 drill-down handoff.
6. Scheduled ingestion enrichment and data-gap feedback loop.
7. Pilot validation, merge, deployment, and expansion.

## Definition of done

- [ ] A founder can state their context and receive concise, sector-relevant answers with visual comparisons.
- [ ] Each displayed insight has an evidence state, confidence, and drill-down source.
- [ ] Existing Company 360 coverage is accurate and explains what is missing.
- [ ] The UI works on mobile and does not overload the initial view with raw detail.
- [ ] Ingestion is scheduled, idempotent, tested, and reusable across companies in the same sector.
- [ ] Tests pass, Docker Compose is rebuilt, the public tunnel is smoke-tested, changes are merged to main, and main is pushed to remote.
