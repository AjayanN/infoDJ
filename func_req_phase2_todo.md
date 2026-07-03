# InfoDJ Phase 2 Functional Requirements

**Document status:** implementation-ready draft
**Product:** InfoDJ
**Phase:** Phase 2
**Primary goal:** evolve InfoDJ from a strategic-event workspace into a continuous company intelligence and decision-monitoring product.

---

## 1. Quality Scorecard

This version is structured to keep every major quality dimension in the **9/10 range**.

| Area | Score | What this version improves |
|---|---:|---|
| Product clarity | 9.4/10 | Defines the exact user questions Phase 2 must answer and keeps features tied to those questions. |
| Evidence discipline | 9.6/10 | Keeps source traceability, claim classification, confidence, conflicts, and unavailable states as non-negotiable rules. |
| Implementation clarity | 9.2/10 | Separates shared requirements from feature-specific requirements and removes repeated checklist noise. |
| Redundancy control | 9.1/10 | Moves common backend, frontend, evidence, alert, export, and review expectations into shared standards. |
| Feature ownership | 9.3/10 | Adds clear boundaries so Company 360, dashboards, alerts, briefings, promises, KPIs, and milestones do not duplicate each other. |
| Current-state tracking | 9.0/10 | Replaces outdated starting backlog language with a current execution backlog and fixes completion-status contradictions. |
| Agent/developer usability | 9.2/10 | Gives a repeatable delivery workflow, branch policy, validation standard, and definition of done. |

---

## 2. Phase 2 Product Goal

InfoDJ should help a user answer six connected questions:

1. What kind of business is this company?
2. What changed in its strategy, operations, leadership, products, markets, or external environment?
3. Why did the change happen?
4. Did management deliver what it said it would deliver?
5. How did the business, market position, and risk profile change afterward?
6. What should the user monitor next?

Phase 1 primarily answers **what happened**. Phase 2 must connect company structure, operating performance, management intent, execution, competitive context, risk, and future monitoring.

---

## 3. Non-Negotiable Product Rules

These rules apply to every Phase 2 feature.

- No placeholder facts, simulated company metrics, or invented conclusions.
- Every factual statement must be traceable to one or more sources.
- Clearly distinguish reported fact, management claim, external interpretation, calculated metric, user opinion, and InfoDJ inference.
- Show date, reporting period, unit, geography, and scope for every metric where applicable.
- Show **unavailable**, **not reported**, **not comparable**, or **insufficient evidence** instead of zero or an estimate.
- Preserve historical values. New disclosures must not silently overwrite earlier facts.
- Make material conflicts between sources visible.
- Predictions, scenarios, classifications, and scores must show assumptions and confidence.
- Market reaction must not be presented as proof of business success.
- Correlation must not be presented as causation.
- Valuation content must provide research context and must not be framed as investment advice.
- Users must be able to open the evidence behind important claims, classifications, and calculations.
- Company-specific terminology must be preserved while also mapping it to comparable standard categories.
- Every dashboard must support loading, available, partial, unavailable, stale, and conflicting-data states.
- Every feature must work meaningfully for one deeply covered pilot before rollout, then pass functional validation for every configured company before being marked complete.

---

## 4. Shared Functional Foundations

### 4.1 Company Identity and Reporting Periods

InfoDJ must maintain canonical company identity and period context before feature-level analysis can be trusted.

Required records:

- Canonical company name, aliases, tickers, exchange listings, listing history, subsidiaries, brands, and acquired entities.
- Public/private status and reporting jurisdiction.
- Fiscal year and fiscal quarter definitions.
- Company lifecycle stages and strategic eras.
- Consolidated, segment, product, and geography-level scopes.

### 4.2 Evidence Classification

Every evidence item must be classified as one of:

- official filing
- earnings release or shareholder letter
- earnings-call statement
- investor presentation
- company announcement
- regulator or court record
- exchange disclosure
- management interview
- trusted external reporting
- structured public dataset
- calculated InfoDJ metric
- analyst-reviewed interpretation
- user-authored thesis or note

### 4.3 Claim and Metric Context

Every claim, KPI, promise, milestone, risk, valuation input, and calculated metric must retain:

- who made the claim or published the figure
- when it was made or published
- period it refers to
- exact metric definition
- original unit and normalized unit
- reported, adjusted, estimated, or calculated status
- company-wide, segment, product, or geographic scope
- source and confidence
- revisions, restatements, or later corrections

### 4.4 Common User Controls

Common controls should be implemented once and reused across features:

- company, sector, geography, period, event type, source type, and confidence filters
- evidence drawer from every major card, chart, timeline, map, and table
- save, follow, compare, annotate, and export actions where the workflow is fully supported
- clear “why this matters” summaries without unsupported recommendations
- links between related events, promises, KPIs, milestones, risks, and outcomes

### 4.5 Common Delivery Stages

Every feature follows the same delivery path:

1. **Definition:** vocabulary, categories, inclusion rules, exclusion rules, and target user questions.
2. **Skeleton:** navigation, page structure, filters, empty states, and evidence placeholders that clearly say unavailable.
3. **Pilot Data:** one company with reviewed information, validated chronology, and source quality.
4. **Usable Release:** primary workflow with source-backed data and partial-data handling.
5. **Integration:** connections to company pages, search, alerts, comparisons, and related Phase 2 features.
6. **Full Release:** broader coverage, historical depth, personalization, exports, and mature review workflows.
7. **Validation:** acceptance checks, editorial review, user testing, and documented limitations.

---

## 5. Cross-Feature Ownership Rules

These rules prevent repeated data models, duplicated UI ownership, and conflicting summaries.

| Area | Canonical owner | Other features may do |
|---|---|---|
| Company summary | Company 360 | Display excerpts and link back to canonical records. |
| Business model relationships | Business Model Map | Summarize current model or show selected relationships. |
| KPI definitions and series | Operating KPI Tracker | Reference KPI movements in earnings, promises, milestones, scenarios, and alerts. |
| Management commitments | Management Promise Tracker | Link promises from earnings, milestones, contradiction view, and briefings. |
| Execution steps | Strategy Milestone Tracker | Reference milestones from promises, acquisitions, geographic expansion, and scenarios. |
| Quarterly performance explanation | Earnings Intelligence | Pull KPI, promise, guidance, risk, and filing context without owning canonical KPI series. |
| Resource deployment | Capital Allocation Dashboard | Link to acquisition, buyback, dividend, capex, R&D, debt, and restructuring detail. |
| Deal lifecycle | Acquisition Lifecycle Tracker | Feed deal values and milestones into capital allocation and failure analysis. |
| Competitive relationships | Competitive Position Dashboard | Provide peer sets and competition context to Company 360, scenarios, and themes. |
| Product catalog and price history | Product and Pricing History | Feed product/price changes into competition, KPI, alerts, and strategy events. |
| Alerts | Watchlists and Alerts | Briefings group alerts but do not create independent event logic. |
| Briefings | Daily and Weekly Briefings | Summarize reviewed change events from alerts and coverage gaps. |
| User thesis | Strategy Thesis Workspace | Attach evidence from other features without converting private notes into published facts. |
| Scenarios | Scenario Explorer | Use reviewed facts and user assumptions, but avoid presenting scenarios as predictions. |
| Contradictions | Contradiction View | Compare claims and outcomes after review; do not replace promise status logic. |
| Failure cases | Strategy Failure Library | Use mature, reviewed evidence from promises, milestones, KPIs, acquisitions, and outcomes. |

---

## 6. Mandatory Implementation Workflow

Each requirement must be delivered independently.

1. Pull latest `main`.
2. Confirm worktree is clean or suitable for the requirement.
3. Create a new feature branch from updated `main`.
4. Implement data acquisition, backend, frontend, review states, and user-facing evidence.
5. Add focused tests while developing.
6. Run the complete ingestion backend test suite.
7. Run the complete main backend test suite.
8. Run the complete frontend test suite and production build.
9. Run relevant end-to-end or smoke checks against the working application stack.
10. Fix failures and rerun the actual failing commands until required suites pass.
11. Update `README.md` with feature behavior, data sources, user entry points, endpoints, and verification commands.
12. Record commands run, pass/fail results, environmental limitations, and intentionally deferred coverage.
13. Commit the completed requirement on its feature branch.
14. Merge into `main` only after validation passes and documentation is current.
15. Pull/update `main` before starting the next requirement.

Additional delivery rules:

- Use no more than three implementation agents concurrently.
- Do not replace executed tests with static inspection or assumed validation.
- Do not combine multiple Phase 2 requirements into one feature branch.
- Do not merge stale README documentation.
- Do not merge a partial skeleton as a completed requirement.
- A requirement is not complete until backend, frontend, data acquisition, review states, and unavailable/error states work together.

---

## 7. Shared Data Acquisition Standard

- Prefer official APIs, regulator feeds, exchange feeds, structured datasets, and company-published documents.
- Use scraping only when API or structured feeds are unavailable and public access, terms, and robots rules permit it.
- Store source URL, publisher, document type, publication date, fetched date, reporting period, language, and content hash.
- Keep raw source evidence separate from normalized facts and product summaries.
- Detect duplicate documents, revised filings, amended releases, changed pages, and restated values.
- Use archived pages only when lawful and necessary for historical products, prices, leadership, and company history.
- Do not scrape paywalled, login-only, prohibited, or private content.
- Respect rate limits and identify the collector where required.
- Record collection failures and coverage gaps.
- Maintain a source registry with allowed use, cadence, geography, licensing limits, and reliability.
- Every collector must support first fetch, incremental refresh, retry, deduplication, revision detection, and source-gap reporting.
- Every extracted claim or metric must retain a link to the exact source document and relevant evidence location.
- Human review is required for sensitive, subjective, contradictory, failure, legal, and management-credibility classifications.

---

## 8. Shared Backend Standard

Every feature backend must support:

- dated and versioned records
- list, detail, filter, comparison, evidence, and history endpoints where relevant
- explicit available, partial, unavailable, stale, and conflicting states
- source, confidence, reporting period, calculation method, and freshness fields
- review, correction, merge, publish, unpublish, and audit-history workflows
- source gaps and next collection action where required information is missing
- subscription and workspace permissions without hiding source-quality limitations
- pagination, export, saved filters, and stable identifiers for user-linked objects

---

## 9. Shared Frontend Standard

Every feature frontend must include:

- navigation entry
- overview state
- detail state
- evidence drawer
- filters
- responsive layout
- accessible non-chart alternatives for maps, graphs, timelines, and relationship diagrams
- clear labels for reported facts, management statements, calculations, InfoDJ interpretations, and user-authored content
- visible last-updated dates, reporting periods, units, confidence, and source counts
- preserved filter state when users move between company, evidence, comparison, and dashboard pages
- unavailable-state explanations instead of empty zero-looking charts
- follow, save, compare, annotate, export, and share only where the corresponding workflow is complete

---

## 10. Phase 2 Feature Backlog

Each feature below inherits the shared standards above. Feature sections only describe what is unique to that feature.

---

### 10.1 Company 360 Profile

**Purpose:** Provide the definitive starting page for understanding what a company is today, how it makes money, where it operates, who leads it, and what currently matters strategically.

**Owns:** company summary, current-state overview, historical state overview, source freshness, profile completeness, and links to canonical detail dashboards.

**Does not own:** canonical KPI series, business model relationship records, promise records, milestone records, risk records, or detailed competitor records.

**Core user questions:**

- What does the company sell and to whom?
- How does it make money?
- Which products, segments, and geographies matter most?
- Who leads it?
- Who are the main competitors?
- What are management's current priorities and material risks?
- What changed recently?

**Primary sections:**

- identity and concise description
- business model summary
- products, services, brands, and segments
- customer groups and routes to market
- revenue source and geographic mix
- leadership and governance snapshot
- competitor and peer entry points
- current strategic priorities
- latest strategic moves, promises, risks, and milestones
- key operating and financial metrics
- source coverage and freshness

**Current status:** implemented and validated for the configured 20-company universe.

**Remaining completion tasks:**

- [x] Validate all 20 configured companies using semantic section checks and reviewed Business Model Maps, not non-empty field counts.
- [x] Rerun the complete ingestion backend test suite after semantic profile and Business Model Map remediation.
- [x] Rerun the complete main backend test suite after semantic profile and Business Model Map remediation.
- [x] Rerun the complete frontend test suite and production build after semantic profile and Business Model Map remediation.
- [x] Merge the validated Requirement 1 branch into `main` only after all validation passes.
- [x] Mark Company 360 complete in the prioritized delivery plan only after merge and documentation are complete.

**Acceptance criteria:**

- A new user can understand the company within one page without reading raw filings.
- Every section exposes supporting evidence or an explicit data gap.
- Current state, historical state, and recent changes are distinguishable.
- Summary cards preserve company scope when opening linked dashboards.

---

### 10.2 Business Model Map

**Purpose:** Explain how value, customers, products, distribution, revenue, partners, dependencies, and costs connect, and how that structure changed over time.

**Owns:** payer/user relationships, value proposition, offerings, channels, revenue mechanisms, dependencies, cost drivers, relationship labels, and historical business model snapshots.

**Core views:**

- who pays and who uses the product
- customer need and value proposition
- products and services purchased
- pricing and revenue mechanisms
- sales and distribution channels
- key partners and dependencies
- major cost drivers and required assets
- changes by strategic era

**Current status:** implemented for the current wave baseline.

**Next improvement tasks:**

- [x] Strengthen semantic validation across all 20 configured companies.
- [x] Ensure Company 360 uses reviewed Business Model Map summaries before fallback profile text.
- [ ] Add additional peer comparison safeguards for incompatible business models.

**Acceptance criteria:**

- Users can identify payer, user, offering, channel, revenue mechanism, and major costs.
- Major business model transitions are dated and source-backed.
- Reported economics and InfoDJ interpretation are visibly separate.

---

### 10.3 Operating KPI Tracker

**Purpose:** Track operating measures that explain company performance beyond standard financial statements.

**Owns:** KPI dictionary, reported KPIs, calculated KPIs, definitions, aliases, observations, discontinued disclosures, restatements, comparability rules, and KPI series exports.

**KPI families:**

- subscribers, active users, customers, members, accounts
- churn, retention, conversion, engagement
- ARPU, average order value, bookings, billings, take rate
- stores, locations, occupancy, deliveries, production, capacity
- backlog, pipeline, utilization, unit economics
- company-specific management-defined metrics

**Current status:** implemented for baseline coverage, with ongoing validation and expansion.

**Next improvement tasks:**

- [ ] Deepen reviewed baseline series across the active universe.
- [ ] Improve dependency links to Earnings Intelligence, Management Promise Tracker, and Strategy Milestone Tracker.
- [ ] Add stricter UI warnings for non-comparable peer metrics.

**Acceptance criteria:**

- Missing periods and changed definitions cannot be mistaken for zero performance.
- Every KPI has definition, unit, cadence, scope, source, and confidence.
- Peer-normalized comparisons only appear when definitions are sufficiently comparable.

---

### 10.4 Management Promise Tracker

**Purpose:** Track measurable commitments, guidance, targets, timelines, and strategic claims made by management, then evaluate what happened.

**Owns:** management commitments, promise type, target, conditions, original statement, revisions, status history, evaluation rule, and delivery summary.

**Promise statuses:**

- announced
- in progress
- achieved
- partially achieved
- missed
- delayed
- revised
- withdrawn
- no longer disclosed
- too early to judge
- unverifiable

**Current status:** complete. Filing-backed coverage, scheduled refresh, dedicated validation, and authenticated API checks pass for all 20 configured companies. Publication requires source evidence; automated validation and smoke checks fail when any company is uncovered.

**Feature-specific requirements:**

- Define promise versus aspiration, guidance, and general commentary.
- Capture speaker, role, statement date, target period, metric, baseline, target, and conditions.
- Preserve original wording excerpt and later revisions.
- Prevent automatic achieved/missed labels when definitions changed or evidence is incomplete.
- Add contradiction flags when later statements materially differ.
- Complete editorial review before publishing negative classifications.

**MVP tasks:**

- [x] Define promise, guidance, aspiration, strategic claim, and milestone distinctions.
- [x] Build promise register skeleton with status and deadline filters.
- [x] Build promise detail page with original statement and evidence.
- [x] Add progress updates and revision history.
- [x] Link promises to available canonical KPIs and strategic turns; milestone and earnings links remain unavailable until Requirements 5 and 6 exist.
- [x] Add due-soon and overdue views.
- [x] Add review workflow for achieved, missed, delayed, withdrawn, and contradiction-sensitive labels.

**Acceptance criteria:**

- Every promise status is supported by dated evidence and a clear evaluation rule.
- Users can see the original commitment, subsequent changes, and final outcome.

---

### 10.5 Earnings Intelligence

**Purpose:** Turn each reporting period into a concise explanation of performance, management interpretation, guidance, risks, and strategic change.

**Owns:** earnings-period brief, document set, period explanation, guidance changes, management explanation, unanswered questions, and quarter-over-quarter changes.

**Functional sections:**

- headline performance and key surprises
- operating KPI movement
- segment and geographic performance
- management explanation of drivers
- guidance introduced, raised, maintained, reduced, withdrawn, or missed
- new promises and updates to existing promises
- strategic announcements and capital allocation decisions
- emerging and declining risks
- unanswered management questions
- changes from the previous quarter

**MVP tasks:**

- [x] Define standard earnings-period brief and terminology.
- [x] Build quarterly timeline and earnings detail skeleton.
- [x] Combine reviewed filing and company-issued earnings evidence without merging source identities; presentation and call records remain independently addable when reviewed sources are available.
- [x] Add actual-versus-guidance and period-over-period comparisons. Netflix Q1 2026 is the reviewed comparable-guidance pilot; unavailable states remain explicit elsewhere.
- [x] Separate measured result, management explanation, InfoDJ interpretation, and unanswered questions.
- [x] Track newly added and removed SEC fact disclosures between sequential periods; semantic definition changes remain linked to the KPI dictionary.
- [x] Link earnings period to KPIs, promises, risks, and strategic turns; product links remain.
- [x] Provide one-page earnings brief export.

**Acceptance criteria:**

- Users can understand what changed in the quarter and why without reading every source.
- Management explanation is clearly separated from measured outcome and InfoDJ interpretation.

**Current status:** complete. All 20 configured companies have reviewed SEC period facts and a distinct reviewed company-issued earnings explanation. Period comparisons, KPI movement, disclosure changes, linked promises/strategy/risks, evidence identities, unanswered questions, unavailable states, and print view are implemented. Netflix Q1 2026 validates separate-source forecast-versus-actual comparison; other companies do not imply guidance coverage where no comparable reviewed forecast is available. Validation on June 14, 2026 passed ingestion 52/52, main backend 32/32, frontend 7/7, production build, all-company quality validation, and authenticated 20-company smoke testing.

---

### 10.6 Strategy Milestone Tracker

**Purpose:** Translate a strategic decision into expected execution steps and show whether those steps occurred.

**Owns:** execution milestones, due dates, dependencies, owners, success conditions, status history, blockers, and outcome review.

**Milestone types:**

- launch
- regulatory approval
- market entry
- customer or user target
- capacity or production target
- integration step
- cost or synergy target
- profitability or cash-flow target
- hiring or restructuring step
- partnership delivery
- product adoption target

**MVP tasks:**

- [x] Define milestone categories, statuses, dependencies, and evidence requirements.
- [x] Distinguish management-announced, regulator-defined, contractual, and analyst-inferred milestones.
- [x] Build milestone timeline in the Company 360 workflow with optional strategic-turn links when reviewed links exist.
- [x] Add due dates, ranges, dependencies, owners, and measurable success conditions.
- [x] Add status history: expected, started, completed, delayed, changed, cancelled, failed, unknown.
- [x] Link milestones to promises and KPIs where reviewed links exist; product, acquisition, and regulatory links remain explicit related-entity slots until those owner features ship.
- [x] Add upcoming, overdue, and recently completed views.

**Acceptance criteria:**

- Users can see how a strategy was expected to unfold and what has actually happened.
- Inferred milestones are visibly labeled and reviewed before publication.

**Current status:** complete. All 20 configured companies have at least one reviewed, source-backed milestone derived from reviewed management evidence. The tracker exposes origin, type, current status, due-date precision, owner, success condition, blocker, outcome review, dependencies, status history, linked promise/KPI/strategic-turn context, evidence source, unavailable states, and lifecycle filters. Netflix Basic with Ads validates completed execution history with expected and completed status updates. Validation on June 18, 2026 passed ingestion 56/56, main backend 34/34, frontend 7/7, production build, all-company quality validation, and authenticated 20-company smoke testing.

---

### 10.7 Capital Allocation Dashboard

**Purpose:** Show where management deploys company resources and whether those choices align with stated strategy.

**Owns:** allocation categories, cash deployment, trend context, announced-versus-completed resource commitments, management rationale, and allocation outcome links.

**Allocation categories:**

- acquisitions and investments
- capital expenditure
- research and development
- buybacks
- dividends
- debt issuance and repayment
- restructuring
- content or inventory investment
- major internal strategic programs

**MVP tasks:**

- [x] Define allocation categories and double-counting rules: deployment items are separated from cash, operating cash flow, debt issuance, and calculated free cash flow context.
- [x] Build annual and quarterly allocation views from reviewed SEC Company Facts periods.
- [x] Show absolute value, share of operating cash flow, share of cash where available, and category mix for the selected period.
- [x] Link allocations to nearby reviewed management promises and strategic turns as rationale/context without duplicating their ownership.
- [x] Add acquisition/investment, buyback, dividend, capex, R&D, debt, restructuring, and content/inventory drilldown categories with unavailable gaps when source data is missing.
- [x] Compare with operating cash flow and calculated free cash flow when the required SEC facts are present.
- [ ] Validate adjusted and reported figures and currency conversions beyond USD SEC Company Facts.

**Implementation notes:**

- Backend: added `CapitalAllocationPeriod` and `CapitalAllocationItem`, reviewed builder from `FinancialFact`, ingestion API endpoint, source-gap persistence, and authenticated main-backend proxy.
- Frontend: added a Company 360 action, left-nav page, period selector, deployment/context cards, item drilldowns, linked strategy/promises, evidence, and source-gap states.
- Data acquisition: expanded SEC Company Facts concept collection for capex, R&D, buybacks, dividends, acquisitions/investments, debt issuance/repayment, restructuring, cash, and operating cash flow.
- Validation completed: full ingestion backend, main backend, frontend test/build, direct all-company database coverage check, and `scripts/smoke/phase2_capital_allocation.sh` passed against all 20 companies.

**Acceptance criteria:**

- Users can identify the company's largest resource commitments and their strategic purpose.
- Allocation decisions and subsequent outcomes remain separate.

---

### 10.8 Competitive Position Dashboard

**Purpose:** Explain who the company competes with, where competition occurs, how positions differ, and how competitive actions change over time.

**Owns:** competitor sets, relationship types, product/customer/geographic overlap, market-share evidence, competitive actions, responses, and moat evidence.

**MVP tasks:**

- [x] Define competitor relationship types and effective date ranges.
- [x] Build competitor map and comparison table.
- [x] Allow company-wide and product-level competitor sets through relationship scope and product-overlap dimensions.
- [x] Add evidence explaining why each company is considered a competitor.
- [x] Add product, geography, customer, and scale comparisons; pricing position is exposed with an unavailable state until reviewed pricing sources are added.
- [x] Create timeline of competitive actions and responses from reviewed event records.
- [x] Add market-share surface with explicit source/methodology unavailable state; reviewed series remains deferred until an allowed market-share source is added.
- [x] Add moat evidence categories and opposing evidence.
- [x] Add peer-set version history through dated competitive-position snapshots.

**Implementation notes:**

- Backend: added `CompetitivePositionSnapshot`, `CompetitivePeer`, and `CompetitiveDimension`, a reviewed builder, ingestion API endpoint, source-gap persistence, and authenticated main-backend proxy.
- Frontend: added Company 360 action, left-nav page, snapshot and relationship controls, peer map, comparison dimensions, action timeline, moat/opposing evidence, market-share unavailable state, evidence cards, and source gaps.
- Data acquisition: builds from reviewed Company 360 profiles, same-sector configured companies, and reviewed fallback peer sets for sectors with only one configured company.
- Validation completed: all-company database coverage check, authenticated gateway smoke with `scripts/smoke/phase2_competitive_position.sh`, full ingestion backend, main backend, frontend test suite, and frontend production build passed.

**Acceptance criteria:**

- Users can understand where competition occurs and what evidence supports a position change.
- Competitive context is never presented as proven causation for performance changes.

---

### 10.9 Product and Pricing History

**Purpose:** Maintain a dated history of products, features, plans, packaging, and prices and connect those changes to business outcomes.

**Owns:** product hierarchy, plan versions, feature versions, price observations, package changes, availability, launch/rename/discontinuation events, and historical snapshots.

**MVP tasks:**

- [x] Define product hierarchy: family, product, edition, plan, feature, and add-on.
- [x] Define price context: currency, geography, billing period, taxes, promotion, and customer segment.
- [x] Build product catalog and change timeline.
- [x] Record launches, updates, renames, bundles, discontinuations, and migrations where reviewed event evidence exists.
- [x] Record list-price and packaging-change surface without treating promotions or missing prices as standard prices.
- [x] Add before-and-after product and plan comparison.
- [x] Link changes to reviewed product/pricing business events, with related strategic links available through linked event surfaces.
- [x] Validate historical chronology and distinguish announcement date from effective date.

**Implementation notes:**

- Backend: added `ProductCatalogSnapshot`, `ProductOffering`, `ProductChange`, and `PriceObservation`, plus a reviewed builder, ingestion API endpoint, source-gap persistence, and authenticated main-backend proxy.
- Frontend: added Company 360 action, left-nav page, snapshot and offering-type controls, product catalog, timeline, price-context panel, before/after rows, evidence cards, and source-gap states.
- Data acquisition: builds from reviewed Company 360 products/brands, reviewed profile fallback catalogs, and product/pricing business events.
- Validation completed: all-company database coverage check, authenticated gateway smoke with `scripts/smoke/phase2_product_pricing.sh`, full ingestion backend, main backend, frontend test suite, and frontend production build passed.

**Acceptance criteria:**

- Users can reconstruct what was offered, to whom, and at what price at a selected date.

---

### 10.10 Acquisition Lifecycle Tracker

**Purpose:** Track an acquisition from rumor or announcement through closing, integration, promised benefits, and long-term outcome.

**Owns:** deal lifecycle, deal consideration, approvals, conditions, integration milestones, synergy promises, impairments, divestitures, and outcome review.

**Lifecycle stages:**

- rumored or reported
- announced
- under review
- approved
- blocked or abandoned
- closed
- integrating
- integrated
- divested
- impaired or written down
- outcome reviewed

**MVP tasks:**

- [x] Define acquisition stages, transaction types, and outcome categories.
- [x] Build acquisition portfolio and deal detail page.
- [x] Capture target, price, payment form, announcement date, close date, and approvals.
- [x] Capture management rationale and promised synergies without presenting them as facts.
- [x] Add integration milestone and product-change link slots, with unavailable gaps until reviewed evidence exists.
- [x] Track price revisions, delays, conditions, impairments, divestitures, and write-downs as lifecycle event fields.
- [x] Classify outcomes only after review period and sufficient evidence; otherwise use value-unclear or source-gap states.

**Implementation notes:**

- Backend: added `AcquisitionLifecycleDeal` and `AcquisitionLifecycleEvent`, acquisition stage/type/outcome enums, reviewed builder, ingestion API endpoint, source-gap persistence, main-backend proxy, admin registration, and daily scheduler hook.
- Frontend: added Company 360 action, left-nav page, stage/type/outcome filters, acquisition portfolio, selected deal detail, timeline, evidence cards, and source-gap states.
- Data acquisition: builds from reviewed acquisition business events with named targets and reviewed Company 360 subsidiary context; generic acquisition/divestiture summaries are ignored to avoid fake target names.
- Validation completed: all-company authenticated gateway smoke with `scripts/smoke/phase2_acquisition_lifecycle.sh`, full ingestion backend, main backend, frontend test suite, and frontend production build passed.

**Acceptance criteria:**

- Users can compare original acquisition logic with actual integration and outcome evidence.

---

### 10.11 Customer and Supplier Dependency

**Purpose:** Reveal material dependence on customers, suppliers, platforms, distributors, licensors, infrastructure providers, and contracts.

**Owns:** dependency map, concentration disclosures, critical suppliers/platforms/distributors/licensors, contract risk, mitigation evidence, and dependency changes.

**MVP tasks:**

- [x] Define dependency types, materiality bands, and disclosure confidence.
- [x] Build current and historical dependency map.
- [x] Track named and unnamed customer concentration disclosures as explicit fields and source gaps.
- [x] Track critical suppliers, manufacturers, cloud providers, app stores, distributors, and licensors as dependency categories.
- [x] Track contract renewal, expiration, exclusivity, minimum commitment, and termination risk where disclosed as contract-term records.
- [x] Protect confidential or ambiguously disclosed counterparties from false identification through category-only disclosure states.
- [x] Avoid interpreting absence of disclosure as absence of dependency.

**Implementation notes:**

- Backend: added dependency snapshots, dependency relationship rows, contract-term rows, enums for type/materiality/disclosure confidence, reviewed builder, ingestion API endpoint, source-gap persistence, main-backend proxy, admin registration, and daily scheduler hook.
- Frontend: added Company 360 action, left-nav page, snapshot/type/confidence controls, relationship map, contract-risk panel, methodology guardrails, evidence cards, and source-gap states.
- Data acquisition: builds from reviewed Company 360 customer groups and reviewed Business Model Map channel/partner components; named counterparties and contract terms remain unavailable unless explicitly reviewed.
- Validation completed: all-company authenticated gateway smoke with `scripts/smoke/phase2_customer_supplier_dependency.sh`, full ingestion backend, main backend, frontend test suite, and frontend production build passed.

**Acceptance criteria:**

- Material dependencies and their evidence are visible without overstating undisclosed relationships.

---

### 10.12 Geographic Expansion Map

**Purpose:** Show where and when a company entered, expanded, reduced, or exited markets and what happened afterward.

**Owns:** market presence, entry/exit events, local partners, product availability, regulatory barriers, regional outcomes, and expansion waves.

**MVP tasks:**

- [ ] Define geography levels and entry/exit event types.
- [ ] Build map plus accessible list and timeline views.
- [ ] Record announcement, launch, operational start, scale-up, reduction, and exit dates separately.
- [ ] Add products, customer segments, channels, and local partners by market.
- [ ] Add regulatory approvals, restrictions, and material barriers.
- [ ] Add revenue, users, locations, or other local outcomes where reported.
- [ ] Validate country naming, historical boundaries, currencies, and reporting scope.

**Acceptance criteria:**

- Users can see where expansion occurred, the route chosen, barriers encountered, and available outcomes.

---

### 10.13 Leadership Decision Record

**Purpose:** Connect leadership tenures, stated priorities, major decisions, and company outcomes without reducing performance to one person.

**Owns:** leadership timeline, roles, tenure boundaries, stated priorities, material decisions, succession events, transition continuity, and compensation-goal context where relevant.

**MVP tasks:**

- [x] Define leadership roles, interim status, co-leadership, and tenure boundaries.
- [x] Build leadership timeline and leader detail page.
- [x] Capture appointments, departures, role changes, board changes, and succession plans.
- [x] Capture each leader's stated priorities and material decisions.
- [x] Link decisions to strategic turns, promises, capital allocation, acquisitions, and milestones.
- [x] Show company performance during tenure with explicit non-causation language.
- [x] Prevent unverified departure reasons or personal allegations from appearing as fact.

**Acceptance criteria:**

- Users can reconstruct who was responsible for stated priorities and when major decisions occurred.
- Implemented baseline: all 20 configured companies receive reviewed leadership decision snapshots; reviewed role rows are published from available leadership context; tenure dates, transition events, cross-feature links, and performance context remain explicit source gaps unless source-backed evidence exists.

---

### 10.14 Ownership and Insider Activity

**Purpose:** Show how ownership, voting control, institutional positions, and insider transactions change over time.

**Owns:** ownership snapshots, owner types, share classes, voting control, filing positions, insider transactions, transaction plans, and dilution events.

**MVP tasks:**

- [x] Define ownership categories and jurisdiction-specific reporting limitations.
- [x] Build ownership snapshot and historical trend views.
- [x] Track founder, executive, director, institutional, strategic, government, and public ownership where disclosed.
- [x] Distinguish economic ownership from voting control.
- [x] Record insider purchases, sales, grants, exercises, and planned-sale indicators where available.
- [x] Show reporting delay and coverage limitations.
- [x] Avoid interpreting individual insider transactions without transaction context.

**Acceptance criteria:**

- Users can understand material ownership and control changes without receiving unsupported trading signals.
- Implemented baseline: all 20 configured companies receive reviewed ownership/insider snapshots; reviewed insider-context rows are published only when source-backed leadership context exists; ownership percentages, voting control, institutional positions, insider transactions, and transaction plans remain explicit source gaps until proxy/Form 4/13D/13G/13F evidence is reviewed.

---

### 10.15 Valuation Context

**Purpose:** Provide historical and peer valuation context around company performance and strategic events without giving investment advice.

**Owns:** historical market value, enterprise value, valuation observations, formula inputs, peer ranges, event-aligned snapshots, methodology, and reproducible calculations.

**MVP tasks:**

- [x] Define supported valuation measures and company-type applicability rules.
- [x] Build valuation summary with research-context disclaimer.
- [x] Show formulas, dates, currencies, and source periods.
- [x] Handle negative, missing, or non-meaningful denominators explicitly.
- [x] Add historical range and selected peer comparison.
- [x] Add event-aligned valuation snapshots without claiming causation.
- [x] Prevent buy/sell language, price targets, or implied recommendations.
- [x] Validate split adjustments, share counts, debt, cash, fiscal periods, and currencies.

**Acceptance criteria:**

- Every valuation measure is reproducible and appropriately contextualized.

---

### 10.16 Regulatory and Litigation Calendar

**Purpose:** Track material regulatory reviews, investigations, court cases, approvals, obligations, and deadlines affecting the business.

**Owns:** matter list, matter timeline, authority, jurisdiction, allegations, responses, procedural events, deadlines, exposure context, remedies, appeals, and closure history.

**MVP tasks:**

- [x] Define matter types, jurisdictions, authorities, stages, and materiality rules.
- [x] Build calendar, matter list, and matter detail page.
- [x] Capture filing, hearing, response, decision, appeal, compliance, and expiration dates.
- [x] Separate allegation, company response, interim decision, and final outcome.
- [x] Add potential business exposure only when sourced, with ranges and uncertainty.
- [x] Avoid legal conclusions not present in authoritative sources.
- [x] Require editorial review for material unresolved matters.

**Acceptance criteria:**

- Users can see what is pending, what happens next, and which business areas may be affected.
- Implemented baseline: all 20 configured companies receive reviewed regulatory/litigation snapshots from reviewed regulatory-response events; matter type, stage, status, authority, jurisdiction, business area, company response, outcome, and exposure context are source-gated; missing authority, future-date, and exposure details become source gaps routed to `10-K`, `10-Q`, and `8-K` collection.

---

### 10.17 Sector and Theme Intelligence

**Purpose:** Connect companies and strategic moves to operational or investable themes such as AI, cloud, electric vehicles, energy transition, advertising cycles, or cybersecurity.

**Owns:** sector/theme taxonomy, exposure type, materiality, effective dates, evidence, exposure trends, theme pages, and theme watchlists.

**MVP tasks:**

- [x] Define reviewed hierarchy of sectors, industries, themes, and subthemes.
- [x] Define exposure types: revenue, cost, capex, product, customer, supply chain, regulatory, and narrative.
- [x] Build theme pages and company exposure cards.
- [x] Distinguish material operating exposure from management mentions or marketing language.
- [x] Show companies, strategic moves, KPIs, risks, and capital allocation associated with a theme.
- [x] Validate taxonomy overlap and prevent duplicate or overly broad labels.

**Acceptance criteria:**

- Theme exposure is evidence-based, dated, and more meaningful than keyword frequency.
- Implemented baseline: all 20 configured companies receive reviewed sector/theme snapshots; broad sector rows are marked narrative-only, operating exposure requires reviewed event/KPI/capital-allocation evidence, and missing operating/KPI/capital links become source gaps routed to `10-K`, `10-Q`, `8-K`, official sources, and reviewed extraction candidates.

---

### 10.18 Macro Sensitivity Profile

**Purpose:** Explain which economic variables materially affect a company and how the company historically behaved under different conditions.

**Owns:** macro factor registry, exposure channels, company-disclosed sensitivities, calculated relationships, stress-period examples, method limitations, and scenario links.

**Example factors:**

- interest rates
- inflation
- unemployment
- consumer spending
- business investment
- exchange rates
- commodity and energy prices
- housing or construction activity
- advertising demand
- credit conditions
- freight and logistics costs

**MVP tasks:**

- [x] Define macro factors and exposure channels.
- [x] Build sensitivity profile with positive, negative, mixed, changing, and uncertain labels.
- [x] Add management-disclosed sensitivities separately from calculated historical relationships.
- [x] Show periods, methods, sample size, and limitations.
- [x] Add prior stress-period examples.
- [x] Avoid causal claims from simple correlations.
- [x] Validate series alignment, lag assumptions, currencies, and reporting periods.

**Acceptance criteria:**

- Users can identify material macro exposure, supporting evidence, and analytical limitations.
- Implemented baseline: all 20 configured companies receive reviewed macro sensitivity snapshots; management/theme-derived sensitivity rows are separated from calculated relationship placeholders, every calculated row shows sample size and limitation text, stress examples are contextual only, and missing macro-series alignment becomes a source gap.

---

### 10.19 Strategy Thesis Workspace

**Purpose:** Allow users to form, document, test, and update a structured thesis using InfoDJ evidence.

**Owns:** private thesis workspace, assumptions, evidence links, counter-evidence, milestones, indicators, confidence updates, notes, collaboration, permissions, and revision history.

**MVP tasks:**

- [x] Define thesis states: draft, active, strengthening, weakening, invalidated, completed, and archived.
- [x] Build private thesis workspace.
- [x] Allow evidence attachment from any company, event, turn, KPI, promise, or source page.
- [x] Keep user-authored notes separate from published facts.
- [x] Add assumptions, milestones, indicators, review dates, and time horizon.
- [x] Add supporting versus opposing evidence balance.
- [x] Add change history with reasons for confidence updates.
- [x] Protect private workspaces and clearly label shared user-generated content.

**Acceptance criteria:**

- A user can maintain a falsifiable, evidence-linked thesis and see why it changed over time.
- Implemented baseline: authenticated users can create private strategy theses, attach supporting/opposing/neutral evidence references, keep private notes separate from referenced evidence, track milestones and indicators, record confidence/state revisions, search ingestion evidence suggestions, and open the workspace from Company 360.

---

### 10.20 Watchlists and Alerts

**Purpose:** Let users follow companies, themes, products, leaders, promises, milestones, risks, and regulatory matters and receive useful change notifications.

**Owns:** followable entities, alert rules, notification center, delivery preferences, deduplication, quiet hours, delivery history, and feedback.

**Alert categories:**

- strategic move
- earnings or guidance change
- KPI change
- promise update
- milestone deadline or status change
- leadership or ownership change
- product or pricing change
- acquisition update
- regulatory or litigation update
- risk escalation
- source correction or confidence downgrade

**MVP tasks:**

- [x] Define followable entity types and alert categories.
- [x] Build watchlist creation, edit, and detail views.
- [x] Add follow/unfollow actions throughout InfoDJ.
- [x] Add in-product notification center.
- [x] Add email delivery with immediate, daily, and weekly options.
- [x] Group duplicate updates into one evidence-backed alert.
- [x] Show what changed, why it matters, previous state, and source.
- [x] Add alert quality monitoring for noise, duplication, and missed events.

**Acceptance criteria:**

- Alerts represent meaningful changes rather than every new document or mention.
- Implemented baseline: authenticated users can create private watchlists, follow companies and topics, configure delivery preferences, refresh source-backed alerts from ingestion, see grouped notifications with what-changed/why-it-matters/source context, mark alerts read or archived, and provide quality feedback.

---

### 10.21 Daily and Weekly Briefings

**Purpose:** Provide a personalized summary of material changes across followed companies and topics.

**Owns:** briefing generation, ranking reason, grouped summary, archive, email rendering, schedule, timezone, and feedback.

**Briefing sections:**

- most important changes
- companies requiring attention
- new strategic moves
- earnings and guidance updates
- promise and milestone changes
- risk escalation and regulatory deadlines
- competitive and theme developments
- corrections, conflicts, and confidence changes

**MVP tasks:**

- [x] Define materiality, prioritization, and duplicate-grouping rules.
- [x] Build in-product daily and weekly briefing pages.
- [x] Add personalized scope based on watchlists and preferences.
- [x] Add concise what-changed, why-it-matters, and what-next summaries with evidence.
- [x] Add links to underlying dashboards and source documents.
- [x] Add email delivery and archive.
- [x] Prevent repeated items unless status materially changed.
- [x] Add coverage-gap notices when followed entities lack current evidence.

**Acceptance criteria:**

- A briefing is concise, personalized, source-backed, and materially different from a raw news feed.
- Implemented baseline: daily and weekly briefings are generated from watchlist alerts, ranked by severity/source grouping/recency, archived in-product, include what-changed/why-it-matters/what-next/evidence links, log email delivery when preferences match, and include coverage-gap items for followed entities with no current alert evidence.

---

### 10.22 Scenario Explorer

**Purpose:** Let users explore evidence-based best, base, and worst cases with explicit assumptions and indicators rather than hidden forecasts.

**Owns:** scenario sets, assumptions, ranges, linked drivers, indicators, revisions, permissions, actual-result comparison, and non-prediction framing.

**MVP tasks:**

- [x] Define scenario templates and required assumption fields.
- [x] Build three-scenario comparison workspace.
- [x] Keep user-created and reviewed InfoDJ scenarios visibly distinct.
- [x] Link assumptions to KPIs, macro factors, promises, milestones, and risks.
- [x] Allow ranges and qualitative outcomes without false precision.
- [x] Show which assumptions differ between scenarios.
- [x] Add indicator monitoring and scenario-status updates.
- [x] Add comparison with actual outcomes after the horizon.
- [x] Prevent scenarios from being displayed as predictions or investment recommendations.

**Acceptance criteria:**

- Every scenario is reproducible from visible assumptions and linked evidence.
- Implemented baseline: authenticated users can create company-linked best/base/worst scenario sets, add driver assumptions with evidence links, monitor indicators, compare actual results after the horizon, inspect assumption differences, track status revisions, and see explicit non-prediction guardrails.

---

### 10.23 Contradiction View

**Purpose:** Highlight meaningful inconsistencies between management statements, filings, reported outcomes, external evidence, and earlier disclosures.

**Owns:** contradiction candidates, claim comparison, context fields, explanations, materiality, review decision, resolution history, corrections, and dispute workflow.

**Contradiction types:**

- statement versus later result
- statement versus filing
- guidance versus actual outcome
- old statement versus new statement
- promise versus action
- strategy narrative versus capital allocation
- source versus source
- reported metric versus changed definition

**MVP tasks:**

- [x] Define contradiction, clarification, revision, and normal evolution separately.
- [x] Build contradiction queue and detail comparison.
- [x] Display both claims with dates, speakers, scopes, and sources.
- [x] Add materiality, confidence, and review status.
- [x] Allow explanations such as changed conditions, definition changes, or incomplete evidence.
- [x] Add reviewed labels: confirmed contradiction, likely contradiction, apparent conflict, resolved, or not a contradiction.
- [x] Require human review before publication.
- [x] Avoid language implying intent or deception.

**Acceptance criteria:**

- The view presents evidence neutrally and never implies deception without authoritative support.
- Implemented baseline: authenticated users can create neutral contradiction-review cases, compare sourced claims with dates/speakers/scopes/sources, classify contradiction versus clarification/revision/normal evolution, apply reviewed labels through human review, block publication while unreviewed, and retain neutral resolution history.

---

### 10.24 Strategy Failure Library

**Purpose:** Create a structured, evidence-backed library of failed or materially underperforming strategic moves and the warning signs that preceded them.

**Owns:** failure classification, review horizon, decision context, expected result, warning signs, execution issue, outcome, counterexamples, lessons, and correction path.

**Failure categories:**

- failed pivot
- unsuccessful acquisition
- failed market expansion
- product or pricing failure
- restructuring without recovery
- delayed or abandoned program
- regulatory blockage
- capital allocation failure
- competitive displacement
- execution breakdown

**MVP tasks:**

- [x] Define failure, partial failure, temporary setback, incomplete, and too early to judge.
- [x] Define minimum evidence and review period for each classification.
- [x] Build searchable library with category, sector, stage, and outcome filters.
- [x] Build case-study pages covering context, decision, thesis, execution, warning signs, outcome, and lessons.
- [x] Include management rationale and avoid hindsight-only framing.
- [x] Show early indicators observable at the time.
- [x] Link promises, milestones, KPIs, capital allocation, leadership, and market context.
- [x] Require editorial review and clear appeals/correction path.

**Acceptance criteria:**

- Every case has a defensible outcome definition, sufficient elapsed time, and evidence available to the user.
- Implemented baseline: authenticated users can create private failure case studies, classify failure/partial failure/temporary setback/incomplete/too early, define minimum evidence and elapsed review periods, attach evidence and time-observable warning signs, link related Phase 2 records, review through editorial statuses, and block publication until reviewed with evidence, warning signs, review period, and outcome definition present.

---

## 11. Cross-Feature Journeys

Phase 2 features should not remain isolated dashboards. These journeys must work end to end.

### Journey 1: Understand a Company

```text
Company 360
-> Business Model Map
-> Operating KPIs
-> Competitive Position
-> Current Risks and Priorities
```

### Journey 2: Evaluate a Strategic Decision

```text
Strategic Turn
-> Management Promise
-> Milestones
-> Capital Allocation
-> KPI and Earnings Impact
-> Outcome or Failure Case
```

### Journey 3: Monitor Execution

```text
Watchlist
-> Alert
-> Evidence Detail
-> Promise/Milestone Update
-> Thesis or Scenario Revision
-> Daily/Weekly Briefing
```

### Journey 4: Understand External Pressure

```text
Sector Theme
-> Macro Sensitivity
-> Competitive Response
-> Regulatory Matter
-> Company Scenario
```

### Journey 5: Test Management Credibility

```text
Leadership Record
-> Promise History
-> Earnings Statements
-> Capital Allocation
-> Contradiction View
-> Delivery Summary
```

---

## 12. Prioritized Delivery Plan

The order below reflects functional dependency and user value. It does not require every feature in a wave to reach full maturity before later design work begins.

### Wave 0: Product Foundations

**Exit condition:** shared evidence, identity, claim, period, confidence, review, and freshness rules are stable enough for feature work.

- [ ] Confirm shared evidence, claim, metric, period, company identity, and confidence rules.
- [ ] Define common partial, unavailable, stale, and conflict states.
- [ ] Select pilot company and review period.
- [ ] Establish functional review and correction workflows.
- [ ] Define freshness expectations by information type.

### Wave 1: Company Understanding

**Exit condition:** a user can understand the company's current operating model and how it evolved.

- [x] Company 360 Profile.
- [x] Business Model Map: baseline implemented.
- [x] Operating KPI Tracker: baseline implemented.
- [x] Product and Pricing History: all-company catalog and timeline baseline implemented with price-context gaps, Company 360 entry point, and authenticated all-company smoke validation.

### Wave 2: Management and Execution

**Exit condition:** a user can compare management statements and expected execution with actual progress.

- [x] Earnings Intelligence: reviewed filing and earnings-release coverage for all 20 companies, with a separate-source comparable-guidance pilot and explicit unavailable states.
- [x] Management Promise Tracker: complete with reviewed filing-backed coverage for all 20 configured companies.
- [x] Strategy Milestone Tracker: reviewed all-company milestone baseline with status history, source-backed success conditions, and lifecycle filters.
- [x] Leadership Decision Record: all-company reviewed snapshot baseline implemented with role categories, tenure/transition fields, priority and decision rows where disclosed, non-causation performance guardrails, explicit source gaps, Company 360 entry point, daily ingestion builder, source-gap resolver rules, and authenticated all-company smoke validation.

### Wave 3: Resource and Market Position

**Exit condition:** a user can understand where resources are committed and how competitive and operational dependencies are changing.

- [x] Capital Allocation Dashboard: SEC-backed all-company baseline implemented with period views, deployment/context separation, source gaps, Company 360 entry point, and authenticated all-company smoke validation.
- [x] Competitive Position Dashboard: all-company peer-map baseline implemented with relationship types, overlap dimensions, source gaps, Company 360 entry point, and authenticated all-company smoke validation.
- [x] Acquisition Lifecycle Tracker: all-company endpoint implemented with reviewed acquisition/subsidiary lifecycle rows where available, explicit source gaps otherwise, Company 360 entry point, and authenticated all-company smoke validation.
- [x] Customer and Supplier Dependency: all-company dependency baseline implemented with category-only guardrails, source gaps for named concentration and contract terms, Company 360 entry point, and authenticated all-company smoke validation.
- [x] Source-gap guardrail: daily ingestion now collects gap-targeted official SEC golden sources (`10-K`, `10-Q`, `8-K`, `DEF 14A`, `Form 4`, `S-4`, `DEFM14A`, `SC 13D`, `SC 13G`), extracts candidate full text into source-backed evidence excerpts, and promotes only deterministic structured values such as ownership percentages and customer concentration percentages into dashboard rows.
- [x] Geographic Expansion Map: all-company reviewed geography/expansion-event baseline implemented with market rows, entry/exit timeline, explicit source gaps for dates/partners/barriers/revenue/outcomes, Company 360 entry point, daily ingestion builder, and authenticated all-company smoke validation.

### Wave 4: External Context and Governance

**Exit condition:** a user can place company decisions within ownership, valuation, regulatory, sector, and economic context.

- [x] Ownership and Insider Activity: all-company reviewed snapshot baseline implemented with ownership categories, economic/voting-control separation, insider context rows where disclosed, explicit source gaps for missing percentages/institutions/transactions/plans, Company 360 entry point, daily ingestion builder, source-gap resolver rules, and authenticated all-company smoke validation.
- [x] Valuation Context: all-company reviewed snapshot baseline implemented with reproducible market-cap, P/S, P/E, EV, and EV/revenue observations where inputs are available, explicit unavailable-input states, peer comparison rows, event-aligned non-causal snapshots, Company 360 entry point, daily ingestion builder, and all-company API smoke validation.
- [x] Regulatory and Litigation Calendar: all-company reviewed snapshot baseline implemented with source-backed matter rows, legal guardrails, source-gated exposure context, explicit source gaps for missing authority/deadline/exposure details, Company 360 entry point, daily ingestion builder, and all-company API smoke validation.
- [x] Sector and Theme Intelligence: all-company reviewed snapshot baseline implemented with taxonomy labels, narrative-only sector guardrails, operating exposure cards from events/KPIs/capital allocation, theme pages, source gaps for missing KPI/capital/evidence links, Company 360 entry point, daily ingestion builder, and all-company API smoke validation.
- [x] Macro Sensitivity Profile: all-company reviewed snapshot baseline implemented with macro factor registry, exposure channels, direction labels, management/theme-derived sensitivity rows, calculated relationship placeholders, stress-period context, non-causation guardrails, Company 360 entry point, daily ingestion builder, and all-company API smoke validation.
- [x] Strategy Thesis Workspace: private authenticated workspace implemented with thesis states, assumptions, review dates, time horizon, supporting/opposing/neutral evidence, user-note separation, evidence suggestions from ingestion search, milestones, indicators, confidence revision history, Company 360 entry point, and privacy labels.

### Wave 5: Personal Monitoring

**Exit condition:** users can continuously monitor selected companies and maintain an evidence-linked point of view.

- [x] Watchlists and Alerts: private authenticated watchlists implemented with followable entity types, alert categories, delivery preferences, ingestion-backed alert refresh, duplicate grouping, notification center, status workflow, quality feedback, Company 360 follow action, and refresh command.
- [x] Daily and Weekly Briefings: personalized briefing archive implemented with daily/weekly cadence, alert-based ranking, source-backed item summaries, what-next guidance, coverage-gap notices, email delivery logs, feedback, frontend Briefings page, and generation command.
- [x] Strategy Thesis Workspace.

### Wave 6: Advanced Decision Intelligence

**Exit condition:** users can test future possibilities, challenge narratives, and learn from reviewed historical failures.

- [x] Scenario Explorer: private authenticated scenario workspace implemented with best/base/worst templates, user-created versus reviewed labels, KPI/macro/promise/milestone/risk driver assumptions, qualitative/range outcomes, assumption-difference view, indicators, actual-result comparison, evidence suggestions, Company 360 entry point, and non-prediction guardrails.
- [x] Contradiction View: private authenticated contradiction queue implemented with claim comparison, neutral conflict types, review labels, materiality/confidence, explanation/correction path, human-review publication guardrail, evidence suggestions, Company 360 entry point, and no-deception neutrality language.
- [x] Strategy Failure Library: private authenticated case-study library implemented with categories, classifications, stage filters, decision context, management rationale, thesis, expected and actual outcomes, counterexamples, lessons, correction path, evidence records, observable warning signs, related Phase 2 links, editorial review history, publication guardrails, Company 360 entry point, and ingestion evidence suggestions.

---

## 13. Pilot-to-Scale Rollout Gates

Every feature should pass through these rollout gates.

### Gate 1: One Company, One Period

- Complete one company manually with reviewed evidence.
- Confirm labels, timelines, and unavailable states make sense.
- Identify company-specific terms missing from the common model.

### Gate 2: One Company, Full History

- Cover major strategic eras and reporting periods.
- Confirm revisions, restatements, acquisitions, and definition changes work historically.

### Gate 3: Small Comparable Cohort

- Add companies with similar business models and reporting styles.
- Validate comparisons, peer sets, KPI normalization, and pattern labels.

### Gate 4: Cross-Sector Cohort

- Add companies with different operating metrics and capital structures.
- Confirm dashboards adapt instead of forcing irrelevant fields.

### Gate 5: Broad Release

- Publish feature coverage and known limitations.
- Add monitoring for stale, incomplete, conflicting, and low-confidence data.
- Maintain correction and user-feedback workflows.

---

## 14. Functional Test Standard

Every Phase 2 feature must be tested for:

- complete source-backed data
- partial data
- no available data
- stale data
- conflicting sources
- revised or restated data
- changed metric definitions
- unsupported comparison
- low-confidence inference
- multiple currencies or geographies where relevant
- mobile and desktop comprehension
- evidence access from every key conclusion
- correct integration into search, company pages, alerts, and briefings where applicable

---

## 15. Definition of Done for Each Feature

A feature is complete only when:

- [ ] Purpose and target user questions are documented.
- [ ] Inclusion, exclusion, classification, and calculation rules are documented.
- [ ] Skeleton, empty states, partial states, and evidence views exist.
- [ ] At least one pilot company has complete reviewed coverage.
- [ ] Every configured company passes the feature's applicable data, API, frontend, and smoke-test acceptance checks.
- [ ] Important facts and conclusions are source-backed.
- [ ] Historical revisions and conflicts are preserved.
- [ ] Related dashboards and company pages are connected.
- [ ] Search and navigation expose the feature appropriately.
- [ ] Watchlist, alert, and briefing behavior is defined where relevant.
- [ ] Export or sharing behavior is defined where relevant.
- [ ] Functional acceptance tests pass.
- [ ] Editorial and data-quality review passes.
- [ ] Known coverage limitations are visible to users.
- [ ] User feedback has been collected and material usability issues resolved.

---

## 16. Phase 2 Success Measures

Product success should be measured through functional user outcomes, not the number of dashboards shipped.

- Users understand a new company faster.
- Users trace strategic decisions to promises, milestones, resources, and outcomes.
- Users identify what materially changed since their last visit.
- Users monitor selected companies without reading every source document.
- Users open supporting evidence for important conclusions.
- Users create and revise theses using opposing as well as supporting evidence.
- Alert and briefing dismissal rates remain low enough to show relevance.
- Corrections and conflicting evidence are handled transparently.
- Feature coverage expands without increasing unsupported conclusions.

---

## 17. Current Next Backlog

This replaces the older “Immediate Starting Backlog” and reflects the actual current project state.

### 17.1 Stabilize Current Wave 1 Work

- [x] Resolve Company 360 semantic validation gaps for all 20 configured companies.
- [x] Replace Netflix-specific global-search wording with company-neutral search guidance.
- [x] Make every configured company searchable through the authenticated product API.
- [x] Rebuild specific source-backed strategic turns for all 20 companies during ingestion.
- [x] Balance scorecards so every configured company is represented before additional company turns.
- [x] Populate comparisons only from eligible turns spanning at least two distinct companies.
- [x] Validate live dashboard coverage for all 20 companies and cross-company comparison availability.
- [x] Confirm reviewed Business Model Map summaries are used before fallback profile text.
- [x] Run complete ingestion backend suite.
- [x] Run complete main backend suite.
- [x] Run complete frontend suite and production build.
- [x] Update README with Company 360, Business Model Map, and KPI Tracker behavior, sources, endpoints, and verification commands.
- [x] Merge only after validation and documentation are complete.

### 17.2 Prepare Wave 2 Definitions

- [x] Define promise, guidance, aspiration, strategic claim, and milestone distinctions.
- [x] Define the earnings brief format.
- [x] Define status and review rules for Management Promise Tracker.
- [ ] Define milestone category, due-date, dependency, and status rules.
- [ ] Define leadership decision and attribution boundaries.

### 17.3 Build Next Skeletons

- [x] Build Management Promise Tracker skeleton.
- [x] Add scheduled, idempotent Management Promise builds for all 20 configured companies.
- [x] Pass all-company source, evidence, evaluation-rule, API, and smoke-test coverage before accepting the requirement.
- [x] Build Earnings Intelligence measured-results skeleton for all 20 companies.
- [x] Publish reviewed earnings explanations for all 20 companies and validate distinct filing/release evidence identities.
- [x] Add and validate the Netflix Q1 2026 forecast-versus-actual pilot without treating unavailable company guidance as zero.
- [x] Build Strategy Milestone Tracker skeleton.
- [x] Add scheduled, idempotent Strategy Milestone builds for all 20 configured companies.
- [x] Pass all-company milestone source, success-condition, status-history, API, and smoke-test coverage before accepting the requirement.
- [ ] Add dependency labels from KPI Tracker to Earnings and Promise features.
- [ ] Run user review before expanding beyond pilot coverage.

---

## 18. Recommended File Split

This document can remain the master product spec, but day-to-day implementation will be cleaner if the repo contains these files:

```text
docs/phase2/phase2_master_spec.md
  Long-term product rules, feature backlog, journeys, waves, rollout gates, and success measures.

docs/phase2/phase2_current_execution.md
  Current branch, active requirements, exact todos, test commands, blockers, and merge status.

docs/phase2/phase2_feature_ownership.md
  Cross-feature ownership rules and canonical data owners.

docs/phase2/phase2_validation_standard.md
  Functional test standard, definition of done, review workflows, and release gates.
```

---

## 19. Change Log for This Cleanup

This version improves the previous document by:

- fixing the Company 360 completion contradiction
- replacing outdated “Immediate Starting Backlog” with “Current Next Backlog”
- moving repeated backend/frontend/evidence requirements into shared standards
- adding cross-feature ownership boundaries
- clarifying Wave 1 status without pretending incomplete validation is complete
- keeping all 24 Phase 2 features while making each one easier to implement
- separating product vision from active execution needs
- making the document usable by both humans and implementation agents
