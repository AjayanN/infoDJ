# InfoDJ Functional Requirements Phase 2 Todo

This document defines the Phase 2 functional expansion of InfoDJ from a strategic-event workspace into a continuous company intelligence and decision-monitoring product.

The plan covers the complete path for each feature:

```text
functional definition
-> information and evidence requirements
-> skeletal user experience
-> usable first release
-> cross-feature integration
-> full implementation
-> validation and release readiness
```

This is a functional plan. Technical implementation choices should support these requirements without weakening source quality, explainability, or the user experience.

## Mandatory Implementation Workflow

Each requirement must be delivered independently using this sequence:

1. Pull the latest `main` and confirm the worktree is suitable for starting the requirement.
2. Create a new feature branch from the updated `main`.
3. Implement the requirement across data acquisition, backend, frontend, review states, and user-facing evidence.
4. Add and run focused tests while developing.
5. Run the complete ingestion backend test suite.
6. Run the complete main backend test suite.
7. Run the complete frontend test suite and production build.
8. Run relevant end-to-end or smoke checks against the working application stack.
9. Fix failures and repeat the actual test commands until all required suites pass.
10. Commit the completed requirement on its feature branch.
11. Merge the feature branch into `main` only after all required verification passes.
12. Pull/update `main` again before creating the branch for the next requirement.

Additional delivery rules:

- Use no more than three implementation agents concurrently.
- Do not replace executed tests with static inspection or assumed validation.
- Do not combine multiple Phase 2 requirements into one feature branch.
- Do not merge a partially implemented requirement merely because its skeleton is visible.
- Record commands run, pass/fail results, known environmental limitations, and any intentionally deferred coverage.
- A requirement is not complete until backend, frontend, data acquisition, and unavailable/error states work together.

## Phase 2 Product Goal

InfoDJ should help a user answer six connected questions:

1. What kind of business is this company?
2. What changed in its strategy, operations, leadership, products, or environment?
3. Why did the change happen?
4. Did management deliver what it said it would deliver?
5. How did the business, market position, and risk profile change afterward?
6. What should the user monitor next?

Phase 1 primarily answers what happened. Phase 2 must connect company structure, operating performance, management intent, execution, competitive context, and future monitoring.

## Non-Negotiable Product Rules

- No placeholder facts, simulated company metrics, or invented conclusions.
- Every factual statement must be traceable to one or more sources.
- Clearly distinguish reported fact, management claim, external interpretation, calculated metric, user opinion, and InfoDJ inference.
- Show the date, reporting period, unit, geography, and scope of every metric where applicable.
- Show unavailable, not reported, not comparable, or insufficient evidence instead of zero or an estimate.
- Preserve historical values. New disclosures must not silently overwrite earlier facts.
- Material conflicts between sources must be visible.
- Predictions, scenarios, classifications, and scores must show assumptions and confidence.
- Market reaction must not be presented as proof of business success.
- Correlation must not be presented as causation.
- Valuation content must provide research context and must not be framed as investment advice.
- Users must be able to open the evidence behind important claims, classifications, and calculations.
- Company-specific terminology must be preserved while also mapping it to comparable standard categories.
- Every dashboard must have loading, available, partial, unavailable, stale, and conflicting-data states.
- Every feature must work meaningfully for one deeply covered pilot company before broad rollout.

## Shared Functional Foundations

These foundations should be established before or alongside the first Phase 2 features.

### A. Company Identity and Periods

- Canonical company identity, aliases, tickers, listing history, subsidiaries, brands, and acquired entities.
- Public/private status and relevant reporting jurisdiction.
- Fiscal year and fiscal quarter definitions.
- Company lifecycle stages and major strategic eras.
- Ability to distinguish consolidated company data from segment, product, and geographic data.

### B. Evidence Classification

Every evidence item should be functionally classified as one of:

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

### C. Claim and Metric Context

The product must retain:

- who made the claim
- when it was made
- the period it refers to
- exact metric definition
- original unit and normalized unit
- reported, adjusted, estimated, or calculated status
- company-wide or segment scope
- source and confidence
- later revisions or restatements

### D. Common User Controls

- Company, sector, geography, period, event type, and confidence filters.
- Evidence drawer from every major card or chart.
- Save, follow, compare, annotate, and export actions where relevant.
- Clear “why this matters” summaries without unsupported recommendations.
- Links between related events, promises, KPIs, milestones, risks, and outcomes.

### E. Common Delivery Stages

Each feature below follows these stages:

1. **Definition:** Confirm vocabulary, categories, inclusion rules, and user questions.
2. **Skeleton:** Add navigation, page structure, filters, empty states, and evidence placeholders that explicitly say unavailable.
3. **Pilot Data:** Complete reviewed information for one pilot company and validate chronology and source quality.
4. **Usable Release:** Deliver the primary workflow with source-backed data and partial-data handling.
5. **Integration:** Connect the feature to company pages, search, alerts, comparisons, and related Phase 2 features.
6. **Full Release:** Add broader coverage, historical depth, personalization, exports, and mature review workflows.
7. **Validation:** Complete acceptance checks, editorial review, and user testing before marking complete.

## Phase 2 Feature Backlog

### 1. Company 360 Profile

**Purpose**

Provide the definitive starting page for understanding what a company is today, how it makes money, where it operates, who leads it, and what currently matters strategically.

**Core user questions**

- What does the company sell and to whom?
- How does it make money?
- Which products, segments, and geographies matter most?
- Who leads the company and who are its main competitors?
- What are management's current priorities and material risks?
- What changed recently?

**Functional sections**

- Company identity and concise description.
- Business model summary.
- Products, services, brands, and major segments.
- Customer groups and routes to market.
- Revenue source and geographic mix.
- Leadership and governance snapshot.
- Competitor and peer set.
- Current strategic priorities.
- Latest strategic moves, promises, risks, and milestones.
- Key operating and financial metrics.
- Source coverage and freshness.

**Implementation todo**

- [ ] Define the standard Company 360 section order and required fields.
- [ ] Define which sections can be hidden and which must show unavailable states.
- [ ] Build a skeletal company page with section navigation and evidence access.
- [ ] Populate a complete reviewed pilot profile.
- [ ] Add period selectors for current view versus historical company eras.
- [ ] Add links from summary cards to detailed Phase 2 dashboards.
- [ ] Add recent-change markers showing what changed since the prior reporting period.
- [ ] Add peer comparison entry points.
- [ ] Add profile completeness and freshness indicators.
- [ ] Add a concise printable/exportable company brief.
- [ ] Validate that all summaries are specific to the company and not generic sector descriptions.

**Completion criteria**

- A new user can understand the company within one page without reading raw filings.
- Every section exposes supporting evidence or an explicit data gap.
- Current state, historical state, and recent changes are distinguishable.

### 2. Business Model Map

**Purpose**

Explain how value, customers, products, distribution, revenue, and costs connect, and how that structure changed over time.

**Core views**

- Who pays and who uses the product.
- Customer need and value proposition.
- Products and services purchased.
- Pricing and revenue mechanisms.
- Sales and distribution channels.
- Key partners and dependencies.
- Major cost drivers and required assets.
- Business model changes by strategic era.

**Implementation todo**

- [ ] Define standard business model components and company-specific extensions.
- [ ] Define relationship labels such as pays, uses, supplies, distributes, hosts, licenses, and regulates.
- [ ] Build a skeletal map and a readable text alternative.
- [ ] Add current-state business model cards.
- [ ] Add historical snapshots before and after major strategic turns.
- [ ] Show evidence and confidence for every relationship.
- [ ] Link pricing history, customer segments, suppliers, products, and revenue mix.
- [ ] Add a “what changed” comparison between two selected dates.
- [ ] Add peer business model comparison.
- [ ] Distinguish company-reported economics from InfoDJ interpretation.
- [ ] Review the pilot map with a business analyst for completeness and clarity.

**Completion criteria**

- Users can identify payer, user, offering, channel, revenue mechanism, and major costs.
- Major business model transitions are dated and source-backed.

### 3. Operating KPI Tracker

**Purpose**

Track the operating measures that actually explain company performance, not only standard financial statements.

**Example KPI families**

- Subscribers, active users, customers, members, or accounts.
- Churn, retention, conversion, and engagement.
- ARPU, average order value, bookings, billings, or take rate.
- Stores, locations, occupancy, deliveries, production, or capacity.
- Backlog, pipeline, utilization, or unit economics.
- Company-specific metrics and management-defined KPIs.

**Implementation todo**

- [ ] Create a functional KPI dictionary with name, definition, unit, cadence, scope, and aliases.
- [ ] Separate reported KPIs from calculated KPIs.
- [ ] Record definition changes and discontinued disclosures.
- [ ] Build skeletal KPI summary cards and trend charts.
- [ ] Add annual, quarterly, monthly, and event-aligned views where data permits.
- [ ] Add growth, change, and per-unit calculations with visible formulas.
- [ ] Add segment and geography filters.
- [ ] Mark restated, estimated, non-comparable, or definition-changed periods.
- [ ] Link KPI movements to earnings, promises, milestones, and strategic turns.
- [ ] Add peer-normalized comparisons only when definitions are sufficiently comparable.
- [ ] Add alerts for material KPI acceleration, slowdown, target crossing, or disclosure discontinuation.
- [ ] Validate each pilot KPI series against original reports.

**Completion criteria**

- The tracker explains which operating drivers moved and why they matter.
- Missing periods and changed definitions cannot be mistaken for zero performance.

### 4. Management Promise Tracker

**Purpose**

Track measurable commitments, guidance, targets, timelines, and strategic claims made by management, then evaluate what happened.

**Promise statuses**

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

**Implementation todo**

- [ ] Define what qualifies as a promise versus aspiration, guidance, or general commentary.
- [ ] Capture speaker, role, statement date, target period, metric, baseline, target, and conditions.
- [ ] Build a skeletal promise register with status and deadline filters.
- [ ] Add promise detail pages with original statement and evidence.
- [ ] Add progress updates and a complete revision history.
- [ ] Connect promises to KPIs, milestones, earnings periods, and strategic turns.
- [ ] Add overdue and approaching-deadline views.
- [ ] Add management-level and company-level delivery summaries.
- [ ] Prevent automatic achieved/missed labels where definitions changed or evidence is incomplete.
- [ ] Add contradiction flags when later statements materially differ.
- [ ] Add watchlist alerts for new, revised, achieved, missed, or withdrawn promises.
- [ ] Complete editorial review before publishing negative classifications.

**Completion criteria**

- Every status is supported by dated evidence and a clear evaluation rule.
- Users can see the original commitment, subsequent changes, and final outcome.

### 5. Earnings Intelligence

**Purpose**

Turn each reporting period into a concise explanation of performance, management interpretation, guidance, risks, and strategic change.

**Functional sections**

- Headline performance and key surprises.
- Operating KPI movement.
- Segment and geographic performance.
- Management explanation of drivers.
- Guidance introduced, raised, maintained, reduced, or withdrawn.
- New promises and updates to existing promises.
- Strategic announcements and capital allocation decisions.
- Emerging and declining risks.
- Questions management did not clearly answer.
- Changes from the previous quarter.

**Implementation todo**

- [ ] Define a standard earnings-period brief and terminology.
- [ ] Build a skeletal quarterly timeline and earnings detail page.
- [ ] Combine filing, release, presentation, and call evidence without merging their source identities.
- [ ] Add actual-versus-guidance and period-over-period comparisons.
- [ ] Add management explanation and independent fact sections.
- [ ] Track new, changed, and removed disclosures.
- [ ] Link the period to KPIs, promises, risks, products, and strategic turns.
- [ ] Add quarter comparison and year-over-year comparison.
- [ ] Add source timestamps and freshness status during reporting season.
- [ ] Add watchlist notifications and inclusion in daily/weekly briefings.
- [ ] Provide a one-page earnings brief export.
- [ ] Validate figures, units, fiscal periods, and guidance language before release.

**Completion criteria**

- Users can understand what changed in the quarter and why without reading every source.
- Management explanation is clearly separated from measured outcome and InfoDJ interpretation.

### 6. Strategy Milestone Tracker

**Purpose**

Translate a strategic decision into expected execution steps and show whether those steps occurred.

**Milestone types**

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

**Implementation todo**

- [ ] Define milestone categories, statuses, dependencies, and evidence requirements.
- [ ] Distinguish management-announced milestones from analyst-inferred milestones.
- [ ] Build a skeletal milestone timeline on strategic-turn pages.
- [ ] Add due dates, ranges, dependencies, owners, and measurable success conditions.
- [ ] Add status history: expected, started, completed, delayed, changed, cancelled, failed, unknown.
- [ ] Link milestones to promises, KPIs, products, acquisitions, and regulatory events.
- [ ] Show progress and blockers without inventing completion percentages.
- [ ] Add upcoming, overdue, and recently completed views.
- [ ] Add alerts for status and deadline changes.
- [ ] Add post-completion outcome review.
- [ ] Validate that inferred milestones are visibly labeled and editable through review.

**Completion criteria**

- Users can see how a strategy was expected to unfold and what has actually happened.

### 7. Capital Allocation Dashboard

**Purpose**

Show where management deploys company resources and whether those choices align with stated strategy.

**Allocation categories**

- acquisitions and investments
- capital expenditure
- research and development
- buybacks
- dividends
- debt issuance and repayment
- restructuring
- content or inventory investment
- major internal strategic programs

**Implementation todo**

- [ ] Define allocation categories and rules preventing double counting.
- [ ] Build skeletal annual and quarterly allocation views.
- [ ] Show absolute value, share of available cash, and trend where meaningful.
- [ ] Link allocations to management rationale and strategic priorities.
- [ ] Add announced versus completed transactions.
- [ ] Add debt maturity and repayment context.
- [ ] Add acquisition, buyback, dividend, capex, and R&D drilldowns.
- [ ] Add comparison with operating cash flow and free cash flow.
- [ ] Add peer and historical comparisons with scope warnings.
- [ ] Show outcomes separately from initial rationale.
- [ ] Flag large allocation shifts and unexplained divergences from stated priorities.
- [ ] Validate adjusted and reported figures and currency conversions.

**Completion criteria**

- Users can identify the company's largest resource commitments and their strategic purpose.
- Allocation decisions and subsequent outcomes remain separate.

### 8. Competitive Position Dashboard

**Purpose**

Explain who the company competes with, where competition occurs, how positions differ, and how competitive actions change over time.

**Functional sections**

- Competitor and substitute map.
- Product and customer overlap.
- Geographic and channel overlap.
- Pricing and packaging comparison.
- Scale and operating KPI comparison.
- Competitive actions and responses.
- Market-share evidence where reliable.
- Possible moat strengths, erosion, and uncertainty.

**Implementation todo**

- [ ] Define competitor relationship types and effective date ranges.
- [ ] Build a skeletal competitor map and comparison table.
- [ ] Allow company-wide and product-level competitor sets.
- [ ] Add evidence explaining why each company is considered a competitor.
- [ ] Add product, pricing, geography, and customer comparisons.
- [ ] Create a timeline of competitive actions and responses.
- [ ] Link performance changes to competition only as context, not proven causation.
- [ ] Add market-share series with source and methodology labels.
- [ ] Add moat evidence categories and opposing evidence.
- [ ] Add peer-set version history because competitors change over time.
- [ ] Connect competitive changes to risks, scenarios, and strategic turns.
- [ ] Review subjective moat classifications before publication.

**Completion criteria**

- Users can understand where competition occurs and what evidence supports a position change.

### 9. Product and Pricing History

**Purpose**

Maintain a dated history of products, features, plans, packaging, and prices and connect those changes to business outcomes.

**Implementation todo**

- [ ] Define product hierarchy: family, product, edition, plan, feature, and add-on.
- [ ] Define price context: currency, geography, billing period, taxes, promotion, and customer segment.
- [ ] Build skeletal product catalog and change timeline.
- [ ] Record launches, major updates, renames, bundling, discontinuations, and migrations.
- [ ] Record list-price and packaging changes without treating promotional prices as standard prices.
- [ ] Add before-and-after product and plan comparison.
- [ ] Link changes to strategic turns, promises, KPIs, and competitive responses.
- [ ] Add geography and customer-segment filters.
- [ ] Add archived evidence and confidence for historical prices.
- [ ] Add alerts for followed product and price changes.
- [ ] Add peer pricing comparison with unit and feature normalization warnings.
- [ ] Validate historical chronology and distinguish announcement from effective date.

**Completion criteria**

- Users can reconstruct what was offered, to whom, and at what price at a selected date.

### 10. Acquisition Lifecycle Tracker

**Purpose**

Track an acquisition from rumor or announcement through closing, integration, promised benefits, and long-term outcome.

**Lifecycle stages**

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

**Implementation todo**

- [ ] Define acquisition stages, transaction types, and outcome categories.
- [ ] Build a skeletal acquisition portfolio and deal detail page.
- [ ] Capture target, price, payment form, announcement date, close date, and approvals.
- [ ] Capture management rationale and promised synergies without presenting them as facts.
- [ ] Add integration milestones, leadership changes, restructuring, and product effects.
- [ ] Link financial, KPI, market, and competitive outcomes.
- [ ] Track price revisions, delays, conditions, impairments, divestitures, and write-downs.
- [ ] Add acquisition portfolio summaries by strategy, size, and status.
- [ ] Add comparable acquisition examples.
- [ ] Add outcome classification only after a defined review period and sufficient evidence.
- [ ] Add alerts for approval, closing, integration, impairment, or divestiture events.
- [ ] Complete source and editorial review for deal values and outcome labels.

**Completion criteria**

- Users can compare original acquisition logic with actual integration and outcome evidence.

### 11. Customer and Supplier Dependency

**Purpose**

Reveal material dependence on customers, suppliers, platforms, distributors, licensors, infrastructure providers, and contracts.

**Implementation todo**

- [ ] Define dependency types, materiality bands, and disclosure confidence.
- [ ] Build a skeletal dependency map with current and historical views.
- [ ] Track named and unnamed customer concentration disclosures.
- [ ] Track critical suppliers, manufacturers, cloud providers, app stores, distributors, and licensors.
- [ ] Track contract renewal, expiration, exclusivity, minimum commitment, and termination risk where disclosed.
- [ ] Add geography and product scope.
- [ ] Link dependencies to risk signals, outages, pricing changes, and strategic responses.
- [ ] Add concentration trends and material dependency changes.
- [ ] Protect legitimately confidential or ambiguously disclosed counterparties from false identification.
- [ ] Add alerts for material contract, supplier, or platform changes.
- [ ] Add mitigation actions and alternative-provider evidence.
- [ ] Validate materiality and avoid interpreting absence of disclosure as absence of dependency.

**Completion criteria**

- Material dependencies and their evidence are visible without overstating undisclosed relationships.

### 12. Geographic Expansion Map

**Purpose**

Show where and when a company entered, expanded, reduced, or exited markets and what happened afterward.

**Implementation todo**

- [ ] Define geography levels and entry/exit event types.
- [ ] Build a skeletal map plus accessible list and timeline views.
- [ ] Record announcement, launch, operational start, scale-up, reduction, and exit dates separately.
- [ ] Add products, customer segments, channels, and local partners by market.
- [ ] Add regulatory approvals, restrictions, and material barriers.
- [ ] Add revenue, users, locations, or other local outcomes where reported.
- [ ] Link geographic moves to milestones, promises, risks, and capital allocation.
- [ ] Add country and regional comparison.
- [ ] Add market-entry strategy classification such as direct, partnership, acquisition, franchise, or digital-only.
- [ ] Add expansion-wave and retreat patterns.
- [ ] Add alerts for launches, exits, restrictions, and target changes.
- [ ] Validate country naming, historical boundaries, currencies, and reporting scope.

**Completion criteria**

- Users can see where expansion occurred, the chosen route, barriers encountered, and available outcomes.

### 13. Leadership Decision Record

**Purpose**

Connect leadership tenures, stated priorities, major decisions, and company outcomes without reducing performance to one person.

**Implementation todo**

- [ ] Define leadership roles, interim status, co-leadership, and tenure boundaries.
- [ ] Build a skeletal leadership timeline and leader detail page.
- [ ] Capture appointments, departures, role changes, board changes, and succession plans.
- [ ] Capture each leader's stated priorities and material decisions.
- [ ] Link decisions to strategic turns, promises, capital allocation, acquisitions, and milestones.
- [ ] Show company performance during tenure with explicit non-causation language.
- [ ] Add continuity and reversal analysis across leadership transitions.
- [ ] Add management-team stability and concentration views.
- [ ] Add compensation-goal context where publicly disclosed and relevant.
- [ ] Add alerts for leadership and succession events.
- [ ] Prevent unverified departure reasons or personal allegations from appearing as fact.
- [ ] Complete editorial review for sensitive leadership classifications.

**Completion criteria**

- Users can reconstruct who was responsible for stated priorities and when major decisions occurred.

### 14. Ownership and Insider Activity

**Purpose**

Show how ownership, voting control, institutional positions, and insider transactions change over time.

**Implementation todo**

- [ ] Define ownership categories and reporting limitations by jurisdiction.
- [ ] Build skeletal ownership snapshot and historical trend views.
- [ ] Track founder, executive, director, institutional, strategic, government, and public ownership where disclosed.
- [ ] Distinguish economic ownership from voting control.
- [ ] Record insider purchases, sales, grants, exercises, and planned-sale indicators where available.
- [ ] Add beneficial ownership thresholds and filing dates.
- [ ] Link major ownership changes to governance and strategic events.
- [ ] Add dilution, buyback, secondary offering, and share-class changes.
- [ ] Avoid interpreting individual insider transactions without transaction context.
- [ ] Add alerts for material ownership, control, or insider-activity changes.
- [ ] Show reporting delay and coverage limitations.
- [ ] Validate transaction type, shares, value, and ownership after transaction.

**Completion criteria**

- Users can understand material ownership and control changes without receiving unsupported trading signals.

### 15. Valuation Context

**Purpose**

Provide historical and peer valuation context around company performance and strategic events without giving investment advice.

**Functional views**

- Historical market value and enterprise value.
- Common valuation multiples where meaningful.
- Peer ranges and company historical ranges.
- Valuation before and after strategic turns.
- Growth, margin, and risk context behind multiple changes.

**Implementation todo**

- [ ] Define supported valuation measures and company-type applicability rules.
- [ ] Build skeletal valuation summary with prominent research-context disclaimer.
- [ ] Show formulas, dates, currencies, and source periods.
- [ ] Handle negative, missing, or non-meaningful denominators explicitly.
- [ ] Add historical range and selected peer comparison.
- [ ] Add event-aligned valuation snapshots without claiming the event caused the change.
- [ ] Add links to earnings, KPIs, market reaction, and strategic turns.
- [ ] Explain changes using evidence-backed contributing factors and uncertainty.
- [ ] Add user-selectable peer sets while preserving the default reviewed peer set.
- [ ] Add export of underlying values and calculations.
- [ ] Prevent buy/sell language, price targets, or implied recommendations.
- [ ] Validate split adjustments, share counts, debt, cash, fiscal periods, and currencies.

**Completion criteria**

- Every valuation measure is reproducible and appropriately contextualized.

### 16. Regulatory and Litigation Calendar

**Purpose**

Track material regulatory reviews, investigations, court cases, approvals, obligations, and deadlines affecting the business.

**Implementation todo**

- [ ] Define matter types, jurisdictions, authorities, stages, and materiality rules.
- [ ] Build a skeletal calendar, matter list, and matter detail page.
- [ ] Capture filing, hearing, response, decision, appeal, compliance, and expiration dates.
- [ ] Separate allegation, company response, interim decision, and final outcome.
- [ ] Add potential business exposure only when sourced, with ranges and uncertainty.
- [ ] Link matters to products, geographies, risks, milestones, and strategic responses.
- [ ] Add upcoming deadlines and recent decisions.
- [ ] Add watchlist alerts with severity and confidence controls.
- [ ] Add recurring obligation and remedy monitoring.
- [ ] Preserve status history after cases close or rules change.
- [ ] Avoid legal conclusions not present in authoritative sources.
- [ ] Require editorial review for material unresolved matters.

**Completion criteria**

- Users can see what is pending, what happens next, and which business areas may be affected.

### 17. Sector and Theme Intelligence

**Purpose**

Connect companies and strategic moves to investable or operational themes such as AI, cloud, electric vehicles, energy transition, advertising cycles, or cybersecurity.

**Implementation todo**

- [ ] Define a reviewed hierarchy of sectors, industries, themes, and subthemes.
- [ ] Define exposure types: revenue, cost, capex, product, customer, supply chain, regulatory, and narrative.
- [ ] Build skeletal theme pages and company exposure cards.
- [ ] Add evidence and effective dates for each exposure.
- [ ] Distinguish material operating exposure from management mentions or marketing language.
- [ ] Show companies, strategic moves, KPIs, risks, and capital allocation associated with a theme.
- [ ] Add increasing, stable, decreasing, and uncertain exposure trends.
- [ ] Add cross-company theme comparison and timeline.
- [ ] Add theme watchlists and briefings.
- [ ] Add emerging-theme review workflow before broad publication.
- [ ] Link theme exposure to scenarios and macro sensitivities.
- [ ] Validate taxonomy overlap and prevent duplicate or overly broad labels.

**Completion criteria**

- Theme exposure is evidence-based, dated, and more meaningful than keyword frequency.

### 18. Macro Sensitivity Profile

**Purpose**

Explain which economic variables materially affect a company and how the company historically behaved under different conditions.

**Example factors**

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

**Implementation todo**

- [ ] Define macro factors and exposure channels.
- [ ] Build a skeletal sensitivity profile with positive, negative, mixed, and uncertain labels.
- [ ] Support company-wide, segment, geography, revenue, and cost sensitivities.
- [ ] Add management-disclosed sensitivities and separate calculated historical relationships.
- [ ] Show periods, methods, sample size, and limitations for historical relationships.
- [ ] Add prior stress-period examples.
- [ ] Link sensitivities to risks, earnings explanations, scenarios, and sector themes.
- [ ] Add current macro condition context and upcoming relevant releases.
- [ ] Add sensitivity changes caused by business model or geographic shifts.
- [ ] Avoid causal claims from simple correlations.
- [ ] Add alerts only for factors explicitly followed by the user or materially linked to the company.
- [ ] Validate series alignment, lag assumptions, currencies, and reporting periods.

**Completion criteria**

- Users can identify material macro exposure, supporting evidence, and analytical limitations.

### 19. Strategy Thesis Workspace

**Purpose**

Allow users to form, document, test, and update a structured thesis using InfoDJ evidence.

**Workspace components**

- Thesis statement.
- Scope and time horizon.
- Supporting and opposing evidence.
- Assumptions.
- Expected milestones and KPIs.
- Risks and disconfirming indicators.
- Current confidence and status.
- Decision journal and revision history.

**Implementation todo**

- [ ] Define thesis states: draft, active, strengthening, weakening, invalidated, completed, and archived.
- [ ] Build a skeletal private thesis workspace.
- [ ] Allow evidence attachment from any company, event, turn, KPI, promise, or source page.
- [ ] Allow user-authored notes that remain clearly separate from published facts.
- [ ] Add assumptions, milestones, indicators, review dates, and time horizon.
- [ ] Add supporting versus opposing evidence balance.
- [ ] Add change history with reasons for confidence updates.
- [ ] Add alerts when linked facts, milestones, or risks change.
- [ ] Add templates for company strategy, acquisition, turnaround, expansion, and competitive theses.
- [ ] Add controlled sharing and collaboration with permissions.
- [ ] Add exportable thesis brief with evidence links.
- [ ] Protect private workspaces and clearly label shared user-generated content.

**Completion criteria**

- A user can maintain a falsifiable, evidence-linked thesis and see why it changed over time.

### 20. Watchlists and Alerts

**Purpose**

Let users follow companies, themes, products, leaders, promises, milestones, risks, and regulatory matters and receive useful change notifications.

**Alert categories**

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

**Implementation todo**

- [ ] Define followable entity types and alert categories.
- [ ] Build skeletal watchlist creation, edit, and detail views.
- [ ] Add follow/unfollow actions throughout InfoDJ.
- [ ] Add in-product notification center.
- [ ] Add email delivery with immediate, daily, and weekly options.
- [ ] Add severity, confidence, company, category, and quiet-hour controls.
- [ ] Group duplicate updates into one evidence-backed alert.
- [ ] Show what changed, why it matters, previous state, and source.
- [ ] Allow mark read, save, dismiss, mute, and feedback actions.
- [ ] Add delivery history and failed-delivery visibility.
- [ ] Add alert quality monitoring for noise, duplication, and missed events.
- [ ] Validate preference, unsubscribe, privacy, and account-tier behavior.

**Completion criteria**

- Alerts represent meaningful changes rather than every new document or mention.

### 21. Daily and Weekly Briefings

**Purpose**

Provide a personalized summary of material changes across followed companies and topics.

**Briefing sections**

- Most important changes.
- Companies requiring attention.
- New strategic moves.
- Earnings and guidance updates.
- Promise and milestone changes.
- Risk escalation and regulatory deadlines.
- Competitive and theme developments.
- Corrections, conflicts, and confidence changes.

**Implementation todo**

- [ ] Define materiality, prioritization, and duplicate-grouping rules.
- [ ] Build skeletal in-product daily and weekly briefing pages.
- [ ] Add personalized scope based on watchlists and preferences.
- [ ] Add concise “what changed” and “why it matters” summaries with evidence.
- [ ] Add links to underlying dashboards and source documents.
- [ ] Add email delivery and archive.
- [ ] Add timezone, schedule, day-of-week, and pause controls.
- [ ] Add read/unread, save, share, and feedback controls.
- [ ] Prevent repeated items unless their status materially changed.
- [ ] Add coverage-gap notices when followed entities lack current evidence.
- [ ] Add team briefings for shared watchlists in a later release.
- [ ] Measure usefulness through opens, drilldowns, saves, dismissals, and user feedback.

**Completion criteria**

- A briefing is concise, personalized, source-backed, and materially different from a raw news feed.

### 22. Scenario Explorer

**Purpose**

Let users explore evidence-based best, base, and worst cases with explicit assumptions and indicators rather than hidden forecasts.

**Scenario components**

- Scenario statement and horizon.
- Starting facts and baseline.
- Assumptions.
- KPI, financial, market, regulatory, and competitive drivers.
- Expected milestones.
- Leading indicators.
- Disconfirming indicators.
- Confidence and evidence quality.

**Implementation todo**

- [ ] Define scenario templates and required assumption fields.
- [ ] Build a skeletal three-scenario comparison workspace.
- [ ] Allow user-created and reviewed InfoDJ scenarios to remain visibly distinct.
- [ ] Link assumptions to KPIs, macro factors, promises, milestones, and risks.
- [ ] Allow ranges and qualitative outcomes without false precision.
- [ ] Show which assumptions differ between scenarios.
- [ ] Add indicator monitoring and scenario-status updates.
- [ ] Add sensitivity controls for selected assumptions where reliable.
- [ ] Add scenario history and revisions.
- [ ] Add comparison with actual outcomes after the horizon.
- [ ] Add export and controlled sharing.
- [ ] Prevent scenarios from being displayed as predictions or investment recommendations.

**Completion criteria**

- Every scenario is reproducible from visible assumptions and linked evidence.

### 23. Contradiction View

**Purpose**

Highlight meaningful inconsistencies between management statements, filings, reported outcomes, external evidence, and earlier disclosures.

**Contradiction types**

- statement versus later result
- statement versus filing
- guidance versus actual outcome
- old statement versus new statement
- promise versus action
- strategy narrative versus capital allocation
- source versus source
- reported metric versus changed definition

**Implementation todo**

- [ ] Define contradiction, clarification, revision, and normal evolution separately.
- [ ] Build a skeletal contradiction queue and detail comparison.
- [ ] Display both claims with dates, speakers, scopes, and sources.
- [ ] Add materiality, confidence, and review status.
- [ ] Allow explanations such as changed conditions, definition changes, or incomplete evidence.
- [ ] Link contradictions to promises, KPIs, earnings, capital allocation, and strategic turns.
- [ ] Add reviewed labels: confirmed contradiction, likely contradiction, apparent conflict, resolved, or not a contradiction.
- [ ] Add correction and dispute workflow.
- [ ] Add watchlist alerts only for material reviewed conflicts.
- [ ] Track repeat patterns without assigning intent.
- [ ] Require human review before publishing sensitive contradiction claims.
- [ ] Preserve the full resolution and correction history.

**Completion criteria**

- The view presents evidence neutrally and never implies deception without authoritative support.

### 24. Strategy Failure Library

**Purpose**

Create a structured, evidence-backed library of failed or materially underperforming strategic moves and the warning signs that preceded them.

**Failure categories**

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

**Implementation todo**

- [ ] Define failure, partial failure, temporary setback, incomplete, and too early to judge.
- [ ] Define minimum evidence and review period for each classification.
- [ ] Build a skeletal library with category, sector, stage, and outcome filters.
- [ ] Build case-study pages covering context, decision, thesis, execution, warning signs, outcome, and lessons.
- [ ] Include management rationale and avoid hindsight-only framing.
- [ ] Show early indicators that were actually observable at the time.
- [ ] Link promises, milestones, KPIs, capital allocation, leadership, and market context.
- [ ] Add comparable successful and mixed cases.
- [ ] Add pattern-level statistics only after sufficient reviewed sample size.
- [ ] Add “what could have changed the outcome” as reviewed analysis, not fact.
- [ ] Add failure cases to question answers, scenarios, and company comparisons.
- [ ] Require editorial review and a clear appeals/correction path.

**Completion criteria**

- Every case has a defensible outcome definition, sufficient elapsed time, and evidence available to the user.

## Backend, Frontend, and Data Acquisition Workstreams

The following workstreams are mandatory parts of each requirement. A feature is not complete when only its dashboard shell or backend records exist.

### Shared Data Acquisition Rules

- Prefer official APIs, regulator feeds, exchange feeds, structured datasets, and company-published documents.
- Use scraping only when an API or structured feed is unavailable and public access, terms, and robots rules permit it.
- Store source URL, publisher, document type, publication date, fetched date, reporting period, language, and content hash.
- Keep raw source evidence separate from normalized facts and product summaries.
- Detect duplicate documents, revised filings, amended releases, changed pages, and restated values.
- Use archived pages for historical products, prices, leadership, and company history when lawful and necessary.
- Do not scrape paywalled, login-only, prohibited, or private content.
- Respect rate limits, identify the collector where required, and record collection failures and coverage gaps.
- Maintain a source registry documenting allowed use, expected cadence, geography, licensing limits, and reliability.
- Every collector must support first fetch, incremental refresh, retry, deduplication, revision detection, and source-gap reporting.
- Every extracted claim or metric must retain a link to the exact source document and relevant evidence location.
- Human review is required for sensitive, subjective, contradictory, failure, legal, and management-credibility classifications.

### Shared Backend Requirements

- Maintain dated and versioned records rather than overwriting historical state.
- Provide list, detail, filter, comparison, evidence, and history capabilities for each feature where relevant.
- Return explicit `available`, `partial`, `unavailable`, `stale`, and `conflicting` states.
- Include source, confidence, reporting period, calculation method, and freshness in responses.
- Support review, correction, merge, publish, unpublish, and audit-history workflows.
- Record source gaps and the next collection action when required information is missing.
- Enforce subscription and workspace permissions without hiding source-quality limitations.
- Support pagination, export, saved filters, and stable identifiers for user-linked objects.

### Shared Frontend Requirements

- Every feature needs a navigation entry, overview state, detail state, evidence drawer, filters, and responsive layout.
- Never display an empty chart as zero data; show the reason information is unavailable.
- Clearly label reported facts, management statements, calculations, InfoDJ interpretations, and user-authored content.
- Provide visible last-updated dates, reporting periods, units, confidence, and source counts.
- Preserve filter state when users move between company, evidence, comparison, and dashboard pages.
- Provide accessible non-chart alternatives for maps, graphs, timelines, and relationship diagrams.
- Add follow, save, compare, annotate, export, and share actions only where the corresponding workflow is complete.

### 1. Company 360 Profile Workstreams

**Data/API and scraping**

- [ ] Fetch company identity, descriptions, aliases, industry, country, website, founding date, subsidiaries, and brands from Wikidata, regulator submissions, exchange records, and official company pages.
- [ ] Fetch segment, geography, revenue mix, leadership, risks, and priorities from annual reports, proxy statements, investor presentations, earnings releases, and company leadership pages.
- [ ] Scrape official About, Products, Leadership, Investor Relations, and newsroom pages when structured feeds are unavailable and access is permitted.
- [ ] Detect profile changes such as new segments, renamed products, leadership changes, and revised strategic priorities.

**Backend**

- [ ] Add versioned company profile, segment, brand, leadership, priority, peer, and profile-completeness records.
- [ ] Provide company overview, historical snapshot, section detail, recent changes, evidence, completeness, and export interfaces.
- [ ] Aggregate latest KPIs, promises, milestones, risks, and strategic events without duplicating their source records.

**Frontend**

- [ ] Build the Company 360 overview with anchored section navigation and current/historical date controls.
- [ ] Add segment, product, geography, leadership, competitor, priority, metric, and recent-change cards.
- [ ] Add completeness, freshness, partial-data, conflict, evidence, and printable brief views.

### 2. Business Model Map Workstreams

**Data/API and scraping**

- [ ] Fetch business descriptions, segment economics, customer types, channels, partners, cost drivers, and dependencies from filings, presentations, official product pages, and earnings materials.
- [ ] Use permitted archived-page collection to reconstruct historical offerings, channels, and payer/user relationships.
- [ ] Extract dated relationships while preserving whether they were reported by the company or inferred by InfoDJ.

**Backend**

- [ ] Add versioned business-model component and relationship records with effective dates, scope, evidence, and confidence.
- [ ] Provide current map, historical snapshot, date comparison, component detail, relationship evidence, and peer comparison interfaces.
- [ ] Support reviewed relationship labels and prevent unsupported inferred links from publishing automatically.

**Frontend**

- [ ] Build an interactive business-model map and an accessible structured text/list alternative.
- [ ] Add component drawers, evidence links, current-versus-past comparison, and reported-versus-inferred labels.
- [ ] Add filters for customer, product, channel, geography, revenue mechanism, and strategic era.

### 3. Operating KPI Tracker Workstreams

**Data/API and scraping**

- [ ] Fetch KPIs from regulator filings, earnings releases, shareholder letters, presentations, supplemental spreadsheets, and official statistical tables.
- [ ] Parse downloadable filing facts and spreadsheets before attempting HTML table extraction.
- [ ] Scrape permitted investor-relations tables only when no structured download exists.
- [ ] Capture metric definitions, units, scope, cadence, restatements, discontinued disclosure, and company terminology.

**Backend**

- [ ] Add KPI dictionary, aliases, observations, definition versions, restatements, calculations, targets, and comparability records.
- [ ] Provide company KPI list, series, breakdown, definition history, peer comparison, event overlay, and export interfaces.
- [ ] Calculate growth and per-unit metrics with formulas and block comparisons when definitions are incompatible.

**Frontend**

- [ ] Build KPI summary cards, selectable trend charts, tables, breakdowns, and definition panels.
- [ ] Add period, segment, geography, reported/calculated, and comparable-only controls.
- [ ] Mark missing periods, changed definitions, estimates, restatements, and discontinued KPIs visibly.

### 4. Management Promise Tracker Workstreams

**Data/API and scraping**

- [ ] Fetch promises and guidance from earnings calls, releases, shareholder letters, presentations, filings, investor-day materials, and official interviews.
- [ ] Fetch later results and statements needed to evaluate progress from subsequent reporting periods.
- [ ] Use licensed transcripts or official transcripts; do not scrape restricted transcript providers.
- [ ] Preserve speaker, exact date, target period, conditions, original wording excerpt, and revisions.

**Backend**

- [ ] Add promise, promise type, target, condition, status event, revision, evaluation rule, and evidence records.
- [ ] Provide promise register, detail, history, due-soon, overdue, company delivery summary, and review interfaces.
- [ ] Link promises to KPIs, milestones, earnings, strategic turns, contradictions, and alerts.

**Frontend**

- [ ] Build promise status boards, timeline, deadline filters, detail pages, and original-versus-current target comparison.
- [ ] Add evaluation evidence, revision history, confidence, reviewer status, and dispute/correction display.
- [ ] Add follow controls and clear aspiration, guidance, commitment, and inferred-target labels.

### 5. Earnings Intelligence Workstreams

**Data/API and scraping**

- [ ] Fetch periodic filings, earnings releases, shareholder letters, presentations, supplemental tables, and official call transcripts.
- [ ] Fetch prior guidance and consensus only from sources licensed for intended use; otherwise compare actuals with company guidance only.
- [ ] Monitor investor-relations feeds and regulator filing feeds for new and amended reporting documents.
- [ ] Capture fiscal period, release sequence, amendments, reported figures, management explanations, and question/answer statements separately.

**Backend**

- [ ] Add earnings period, document set, result, guidance, explanation, risk change, announcement, and period-summary records.
- [ ] Provide earnings timeline, period detail, period comparison, guidance changes, related KPIs/promises, evidence, and brief export interfaces.
- [ ] Detect new, raised, maintained, reduced, withdrawn, missed, and non-comparable guidance under reviewed rules.

**Frontend**

- [ ] Build earnings timeline, quarter brief, actual-versus-guidance view, segment/KPI tabs, and change-from-prior-quarter view.
- [ ] Separate measured results, management explanation, InfoDJ interpretation, and unanswered-question sections.
- [ ] Add rapid-update, partial-document, amended-report, stale, and fully-reviewed states.

### 6. Strategy Milestone Tracker Workstreams

**Data/API and scraping**

- [ ] Fetch milestones from strategic announcements, investor presentations, filings, regulatory decisions, product pages, and subsequent progress updates.
- [ ] Monitor official newsroom, regulator, project, and product pages for status or deadline changes.
- [ ] Preserve whether a milestone is management-announced, regulator-defined, contractual, or analyst-inferred.

**Backend**

- [ ] Add milestone, dependency, success condition, target date/range, status history, owner, and outcome-review records.
- [ ] Provide strategic-turn milestones, upcoming, overdue, dependency map, evidence history, and status-update review interfaces.
- [ ] Link milestones to promises, KPIs, acquisitions, products, regulations, and alerts.

**Frontend**

- [ ] Build milestone timelines, status boards, dependency views, overdue/upcoming lists, and milestone detail drawers.
- [ ] Show announced versus inferred milestones, changing deadlines, blockers, evidence, and outcome reviews.
- [ ] Add calendar and list alternatives and follow/alert controls.

### 7. Capital Allocation Dashboard Workstreams

**Data/API and scraping**

- [ ] Fetch cash flow, capex, R&D, debt, dividends, buybacks, acquisitions, investments, and restructuring figures from filings and official transaction announcements.
- [ ] Fetch debt maturities and authorization/completion details from notes, debt filings, and investor materials.
- [ ] Use regulator structured facts where possible and filing-table extraction when concepts are company-specific.

**Backend**

- [ ] Add normalized allocation categories, transactions, authorizations, completion amounts, management rationale, and outcome links.
- [ ] Provide allocation trends, category detail, announced-versus-completed, cash-flow context, peer comparison, and export interfaces.
- [ ] Prevent double counting between cash-flow lines, acquisition consideration, debt activity, and strategic-program disclosures.

**Frontend**

- [ ] Build allocation mix, trend, transaction timeline, debt maturity, buyback, dividend, capex, R&D, and acquisition views.
- [ ] Add absolute, percentage-of-cash-flow, per-share, and historical comparison controls where meaningful.
- [ ] Link every allocation to rationale, strategic priority, completion status, evidence, and later outcome.

### 8. Competitive Position Dashboard Workstreams

**Data/API and scraping**

- [ ] Fetch named competitors from filings, official market disclosures, regulator decisions, company materials, and reviewed industry datasets.
- [ ] Fetch product, pricing, geography, customer, scale, and market-share evidence from official company pages and reliable public datasets.
- [ ] Scrape permitted public pricing and product pages with dated snapshots for comparison.
- [ ] Record source methodology for market share and avoid combining incompatible market definitions.

**Backend**

- [ ] Add versioned competitor sets, relationship types, product overlaps, comparative measures, market-share series, actions, responses, and moat evidence.
- [ ] Provide competitor map, comparison, timeline, peer-set history, moat evidence, and market-share interfaces.
- [ ] Require review for subjective competitor, moat, displacement, and position-change classifications.

**Frontend**

- [ ] Build competitor map, comparison matrix, action-response timeline, product/pricing comparison, and market-share views.
- [ ] Add scope controls for company, product, customer, geography, channel, and date.
- [ ] Show supporting and opposing moat evidence and confidence rather than a single unexplained score.

### 9. Product and Pricing History Workstreams

**Data/API and scraping**

- [ ] Fetch current products, plans, features, and prices from official product, pricing, help, app-store, and announcement pages.
- [ ] Use permitted archived pages and historical announcements to reconstruct prior products and prices.
- [ ] Capture currency, geography, taxes, billing period, customer segment, promotion status, announcement date, and effective date.

**Backend**

- [ ] Add product hierarchy, product versions, plan versions, features, prices, packaging, availability, change events, and evidence records.
- [ ] Provide catalog, selected-date snapshot, change timeline, before/after comparison, geography comparison, and peer comparison interfaces.
- [ ] Detect official-page changes and route material product or price changes through review.

**Frontend**

- [ ] Build current catalog, historical timeline, plan comparison, price-history chart/table, and selected-date snapshot.
- [ ] Add geography, currency, customer, product family, and billing-period controls.
- [ ] Show launch, rename, bundle, migration, discontinuation, announced, and effective dates distinctly.

### 10. Acquisition Lifecycle Tracker Workstreams

**Data/API and scraping**

- [ ] Fetch transaction filings, company announcements, regulator approvals, merger documents, financial statements, and integration updates.
- [ ] Fetch deal consideration, financing, closing conditions, management rationale, synergy targets, impairments, and divestitures from official sources.
- [ ] Monitor competition authorities and relevant regulator case pages where public feeds or permitted access exist.

**Backend**

- [ ] Add deal, party, consideration, lifecycle event, approval, condition, synergy promise, integration milestone, impairment, divestiture, and outcome records.
- [ ] Provide acquisition portfolio, deal detail, lifecycle timeline, integration progress, promised-versus-realized, and comparable deal interfaces.
- [ ] Support multi-step, revised, partially acquired, abandoned, and subsequently divested transactions.

**Frontend**

- [ ] Build acquisition portfolio cards, deal detail, lifecycle timeline, regulatory status, integration tracker, and outcome review.
- [ ] Add filters for status, year, size, strategy, geography, and outcome maturity.
- [ ] Keep announced synergies, realized outcomes, market reaction, and editorial outcome classification separate.

### 11. Customer and Supplier Dependency Workstreams

**Data/API and scraping**

- [ ] Fetch concentration, supplier, platform, distributor, licensing, and contract-risk disclosures from filings, annual reports, contract exhibits, and official announcements.
- [ ] Fetch outages, terminations, renewals, disputes, and mitigation updates from authoritative public sources.
- [ ] Do not infer unnamed counterparties from speculation or scrape confidential relationship data.

**Backend**

- [ ] Add dependency entity, type, scope, materiality, concentration observation, contract term, event, mitigation, and evidence records.
- [ ] Provide dependency map, concentration trends, contract calendar, change history, risk links, and evidence interfaces.
- [ ] Support unnamed disclosed dependencies without falsely assigning an identity.

**Frontend**

- [ ] Build dependency map/list, concentration trends, critical relationship cards, contract calendar, and change timeline.
- [ ] Add product, geography, dependency type, materiality, named/unnamed, and confidence filters.
- [ ] Show disclosed fact, estimated exposure, mitigation, and unknown information distinctly.

### 12. Geographic Expansion Map Workstreams

**Data/API and scraping**

- [ ] Fetch market entry, exit, availability, local partnership, regulatory, location, and geographic result data from filings and official regional pages.
- [ ] Use company location APIs, downloadable store/location lists, or permitted page collection where available.
- [ ] Preserve announcement, legal entry, product availability, first revenue, scale-up, reduction, and exit dates separately.

**Backend**

- [ ] Add geographic market, presence period, entry mode, product availability, local partner, regulatory barrier, metric, and expansion event records.
- [ ] Provide map/list data, country detail, expansion waves, entry/exit timeline, outcome, and comparison interfaces.
- [ ] Normalize changing country names, regions, currencies, and company-specific geographic reporting groups.

**Frontend**

- [ ] Build interactive map, accessible country list, expansion timeline, regional KPI/revenue view, and market detail page.
- [ ] Add date, product, presence status, entry mode, partner, and outcome filters.
- [ ] Show announced, launched, scaled, reduced, exited, restricted, and unknown states visually and textually.

### 13. Leadership Decision Record Workstreams

**Data/API and scraping**

- [ ] Fetch appointments, departures, biographies, board roles, compensation goals, and succession disclosures from filings, proxy statements, and official leadership pages.
- [ ] Fetch stated priorities and decisions from earnings materials, investor presentations, official interviews, and company announcements.
- [ ] Monitor leadership-page changes but validate them against dated official disclosures.

**Backend**

- [ ] Add person, role, tenure, interim/co-leader status, priority, decision link, succession event, compensation objective, and evidence records.
- [ ] Provide leadership timeline, leader detail, tenure decisions, priority history, transition comparison, and evidence interfaces.
- [ ] Protect sensitive departure reasons and require review for inferred responsibility or reversal classifications.

**Frontend**

- [ ] Build leadership timeline, executive cards, leader detail, stated-priority view, decision record, and transition comparison.
- [ ] Add role, period, business area, decision type, and active/former filters.
- [ ] Label company performance during tenure as context rather than personal attribution.

### 14. Ownership and Insider Activity Workstreams

**Data/API and scraping**

- [ ] Fetch beneficial ownership, share classes, voting rights, institutional holdings, and insider transactions from regulator and exchange filings.
- [ ] Fetch buybacks, offerings, conversions, grants, exercises, and planned-sale information from official filings.
- [ ] Use structured regulator feeds when available; do not rely on scraped third-party transaction summaries as primary evidence.

**Backend**

- [ ] Add ownership snapshots, owner types, share classes, voting control, filing positions, insider transactions, transaction plans, and dilution events.
- [ ] Provide ownership summary, history, control structure, insider activity, material-change, and evidence interfaces.
- [ ] Account for filing delays, amended filings, indirect ownership, derivative transactions, and transaction-code context.

**Frontend**

- [ ] Build ownership composition, historical trend, control structure, insider transaction table, and major-change timeline.
- [ ] Add owner type, person/institution, transaction type, date, value, planned/open-market, and confidence filters.
- [ ] Display reporting lag, transaction context, and non-recommendation language prominently.

### 15. Valuation Context Workstreams

**Data/API and scraping**

- [ ] Fetch adjusted market prices, shares, debt, cash, financial facts, and corporate actions from licensed or permitted market sources and official filings.
- [ ] Fetch peer inputs using the same source family and aligned periods where possible.
- [ ] Do not scrape websites whose terms prohibit reuse of market or valuation data.

**Backend**

- [ ] Add dated valuation observations, formula inputs, multiples, peer sets, event snapshots, calculation versions, and applicability flags.
- [ ] Provide historical valuation, selected-date snapshot, peer comparison, event context, methodology, and export interfaces.
- [ ] Block invalid multiples and expose formulas, period alignment, currency conversion, and missing-input reasons.

**Frontend**

- [ ] Build valuation summary, historical range, peer distribution, event-aligned view, formula drawer, and underlying-data table.
- [ ] Add date, multiple, peer set, reported/adjusted, and currency controls.
- [ ] Show research-context disclaimer and avoid price targets, upside/downside, or buy/sell language.

### 16. Regulatory and Litigation Calendar Workstreams

**Data/API and scraping**

- [ ] Fetch matters from regulator APIs, court or tribunal public records, exchange disclosures, company filings, and official authority announcements.
- [ ] Monitor public case pages and calendars through feeds or permitted low-rate collection when no API exists.
- [ ] Capture allegation, response, procedural event, deadline, interim order, final decision, appeal, remedy, and closure separately.

**Backend**

- [ ] Add matter, authority, jurisdiction, party, allegation, proceeding event, deadline, exposure, remedy, appeal, status history, and evidence records.
- [ ] Provide calendar, matter list/detail, upcoming deadlines, recent decisions, company exposure, and review interfaces.
- [ ] Require human review for materiality, potential exposure, unresolved allegations, and legal-status summaries.

**Frontend**

- [ ] Build calendar/list views, matter detail, procedural timeline, deadline cards, exposure context, and linked business areas.
- [ ] Add jurisdiction, authority, matter type, status, severity, company, and date filters.
- [ ] Clearly separate allegations, company responses, interim actions, and final outcomes.

### 17. Sector and Theme Intelligence Workstreams

**Data/API and scraping**

- [ ] Fetch sector classifications from recognized structured sources and theme evidence from filings, products, capex, revenue disclosures, announcements, and official strategy materials.
- [ ] Fetch external theme indicators from authoritative public datasets where licensing allows.
- [ ] Do not classify material exposure using keyword frequency alone.

**Backend**

- [ ] Add taxonomy, theme, exposure type, company exposure, evidence, trend, related KPI, event, risk, and allocation records.
- [ ] Provide theme overview, company exposure, exposure comparison, event timeline, trend, and watchlist interfaces.
- [ ] Add review workflow for new themes, overlapping labels, exposure materiality, and narrative-only mentions.

**Frontend**

- [ ] Build theme pages, exposure cards, company comparison, strategic-move timeline, KPI/risk links, and evidence views.
- [ ] Add sector, subtheme, exposure type, materiality, geography, trend, and confidence filters.
- [ ] Distinguish operating exposure, financial exposure, strategic investment, customer exposure, and management narrative.

### 18. Macro Sensitivity Profile Workstreams

**Data/API and scraping**

- [ ] Fetch macro series from official statistical agencies, central banks, FRED or equivalent sources, and commodity/exchange datasets with permitted use.
- [ ] Fetch company-disclosed sensitivities from filings, earnings materials, and risk disclosures.
- [ ] Record release dates and later revisions so analysis does not use information unavailable at the historical date.

**Backend**

- [ ] Add macro series registry, observations, revisions, company exposure channels, calculated relationships, lags, methods, sample periods, and stress episodes.
- [ ] Provide sensitivity profile, factor history, company overlay, stress-period examples, methodology, and scenario-link interfaces.
- [ ] Enforce minimum sample and quality rules and label correlations as non-causal.

**Frontend**

- [ ] Build factor cards, sensitivity matrix, aligned company/macro charts, stress-period comparisons, and methodology drawers.
- [ ] Add period, factor, segment, geography, lag, reported/calculated, and confidence controls.
- [ ] Show positive, negative, mixed, changing, insufficient-data, and uncertain relationships.

### 19. Strategy Thesis Workspace Workstreams

**Data/API and scraping**

- [ ] Reuse published InfoDJ evidence rather than creating a separate external scraping pipeline for private theses.
- [ ] Allow users to attach permitted external links and notes without treating them as verified InfoDJ facts.
- [ ] Refresh linked InfoDJ evidence and notify users when a source is corrected, revised, or removed.

**Backend**

- [ ] Add private thesis, assumption, evidence link, counter-evidence, milestone, indicator, confidence update, note, collaborator, permission, and revision records.
- [ ] Provide create/edit/archive, evidence search/link, revision history, sharing, export, and alert interfaces.
- [ ] Enforce owner, collaborator, team, and public-template permissions and maintain audit history.

**Frontend**

- [ ] Build thesis editor, evidence board, supporting/opposing columns, assumptions, indicators, review dates, and revision timeline.
- [ ] Add evidence search and attach actions throughout InfoDJ.
- [ ] Add private/shared labels, collaboration controls, templates, export, and linked-change notifications.

### 20. Watchlists and Alerts Workstreams

**Data/API and scraping**

- [ ] Use changes produced by all approved collectors rather than independently scraping the same sources for alerts.
- [ ] Maintain entity change events with previous state, new state, source, confidence, materiality, and deduplication key.
- [ ] Record delayed or failed source refreshes so silence is not mistaken for no change.

**Backend**

- [ ] Add watchlist, followed entity, alert rule, change event, notification, delivery attempt, digest preference, mute, and feedback records.
- [ ] Provide watchlist management, follow/unfollow, notification center, preference, delivery history, and feedback interfaces.
- [ ] Group duplicates, apply user thresholds, enforce quiet hours, and support in-product and email delivery.

**Frontend**

- [ ] Build watchlist overview/detail, global follow controls, notification center, rule editor, and delivery preferences.
- [ ] Show what changed, why it matters, old/new values, confidence, evidence, and related dashboard link.
- [ ] Add read, save, dismiss, mute, unsubscribe, and alert-quality feedback actions.

### 21. Daily and Weekly Briefings Workstreams

**Data/API and scraping**

- [ ] Build briefings from reviewed change events, alerts, coverage gaps, and watchlist scope rather than a separate news scrape.
- [ ] Include source freshness and failed-collector context when relevant.
- [ ] Deduplicate the same development across filings, releases, news metadata, and later corrections.

**Backend**

- [ ] Add briefing configuration, generated edition, section, item, ranking reason, delivery, archive, and feedback records.
- [ ] Provide current briefing, archive, preferences, regenerate-preview, item feedback, and email-render interfaces.
- [ ] Rank by user relevance, materiality, novelty, confidence, and prior inclusion while preventing unsupported personalization claims.

**Frontend**

- [ ] Build daily/weekly briefing reader, archive, preference controls, saved items, and source drilldowns.
- [ ] Add company/theme grouping and concise changed/why-it-matters/what-next presentation.
- [ ] Add schedule, timezone, pause, email, mark-read, save, share, and feedback controls.

### 22. Scenario Explorer Workstreams

**Data/API and scraping**

- [ ] Reuse reviewed KPIs, macro series, promises, milestones, risks, and competitive facts as scenario inputs.
- [ ] Fetch no external forecast automatically unless its licensing permits use and its author, date, assumptions, and horizon are retained.
- [ ] Refresh linked inputs and preserve the original scenario-input snapshot for historical review.

**Backend**

- [ ] Add scenario set, scenario, assumption, range, driver link, indicator, outcome, revision, permission, and actual-result records.
- [ ] Provide create/edit/compare, linked-input refresh, sensitivity, history, share, export, and outcome-review interfaces.
- [ ] Keep user scenarios separate from reviewed InfoDJ scenarios and expose all formulas and assumptions.

**Frontend**

- [ ] Build best/base/worst comparison, assumption editor, driver table, range view, indicator monitor, and revision timeline.
- [ ] Add visible changed-assumption highlighting and links to supporting or opposing evidence.
- [ ] Add save, clone, share, export, and compare-with-actual workflows with non-prediction language.

### 23. Contradiction View Workstreams

**Data/API and scraping**

- [ ] Compare versioned claims and outcomes already collected from filings, earnings materials, official announcements, and reviewed external evidence.
- [ ] Preserve source revisions and avoid comparing statements with different scopes, definitions, periods, or conditions as if equivalent.
- [ ] Collect authoritative corrections and company responses when a conflict is identified.

**Backend**

- [ ] Add claim, claim version, comparison pair, contradiction candidate, explanation, materiality, review decision, resolution, correction, and evidence records.
- [ ] Provide candidate review queue, published contradiction list, detail comparison, resolution history, dispute, and alert interfaces.
- [ ] Require human approval before publication and retain neutral labels and audit history.

**Frontend**

- [ ] Build side-by-side claim comparison, context fields, timeline, evidence, possible explanations, review status, and resolution history.
- [ ] Add filters for contradiction type, company, speaker, materiality, confidence, status, and period.
- [ ] Add correction/dispute presentation and avoid language implying intent or deception.

### 24. Strategy Failure Library Workstreams

**Data/API and scraping**

- [ ] Reuse strategic turns, milestones, promises, KPIs, acquisitions, geographic moves, capital allocation, and outcome evidence.
- [ ] Fetch later filings, impairments, closures, exits, discontinued products, restructurings, and authoritative retrospectives needed to establish mature outcomes.
- [ ] Use external reporting only as supporting evidence and retain what was knowable at the time of the original decision.

**Backend**

- [ ] Add failure case, classification, review horizon, decision context, expected result, warning sign, execution issue, outcome, counterexample, lesson, and review records.
- [ ] Provide library search, case detail, pattern summary, comparable success/mixed cases, evidence, correction, and question-answer integration interfaces.
- [ ] Enforce elapsed-time, evidence-count, review, and sample-size gates before publishing failure or pattern statistics.

**Frontend**

- [ ] Build searchable failure library, case-study page, decision-to-outcome timeline, warning-sign panel, evidence, and comparable cases.
- [ ] Add category, sector, lifecycle stage, company size, geography, outcome maturity, and confidence filters.
- [ ] Show original rationale, contemporaneous evidence, later outcome, uncertainty, and reviewed lessons without hindsight-only judgment.

## Cross-Feature Journeys

Phase 2 features should not remain isolated dashboards. The following journeys must work end to end.

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

## Prioritized Delivery Plan

The order below reflects functional dependency and user value. It does not imply that every feature in a wave must wait for all preceding features to reach full maturity.

### Wave 0: Product Foundations

- [ ] Confirm shared evidence, claim, metric, period, company identity, and confidence rules.
- [ ] Define common partial/unavailable/conflict states.
- [ ] Select the pilot company and review period.
- [ ] Establish functional review and correction workflows.
- [ ] Define freshness expectations by information type.

### Wave 1: Company Understanding

- [ ] Company 360 Profile.
- [ ] Business Model Map.
- [ ] Operating KPI Tracker.
- [ ] Product and Pricing History.

**Wave 1 exit condition:** A user can understand the company's current operating model and how it evolved.

### Wave 2: Management and Execution

- [ ] Earnings Intelligence.
- [ ] Management Promise Tracker.
- [ ] Strategy Milestone Tracker.
- [ ] Leadership Decision Record.

**Wave 2 exit condition:** A user can compare management statements and expected execution with actual progress.

### Wave 3: Resource and Market Position

- [ ] Capital Allocation Dashboard.
- [ ] Competitive Position Dashboard.
- [ ] Acquisition Lifecycle Tracker.
- [ ] Customer and Supplier Dependency.
- [ ] Geographic Expansion Map.

**Wave 3 exit condition:** A user can understand where resources are committed and how competitive and operational dependencies are changing.

### Wave 4: External Context and Governance

- [ ] Ownership and Insider Activity.
- [ ] Valuation Context.
- [ ] Regulatory and Litigation Calendar.
- [ ] Sector and Theme Intelligence.
- [ ] Macro Sensitivity Profile.

**Wave 4 exit condition:** A user can place company decisions within ownership, valuation, regulatory, sector, and economic context.

### Wave 5: Personal Monitoring

- [ ] Watchlists and Alerts.
- [ ] Daily and Weekly Briefings.
- [ ] Strategy Thesis Workspace.

**Wave 5 exit condition:** Users can continuously monitor selected companies and maintain an evidence-linked point of view.

### Wave 6: Advanced Decision Intelligence

- [ ] Scenario Explorer.
- [ ] Contradiction View.
- [ ] Strategy Failure Library.

**Wave 6 exit condition:** Users can test future possibilities, challenge narratives, and learn from reviewed historical failures.

## Pilot-to-Scale Rollout

Every feature should move through the following rollout gates.

### Gate 1: One Company, One Period

- Complete one company manually with reviewed evidence.
- Confirm that labels, timelines, and unavailable states make sense.
- Identify company-specific terms missing from the common model.

### Gate 2: One Company, Full History

- Cover major strategic eras and reporting periods.
- Confirm that revisions, restatements, acquisitions, and definition changes work historically.

### Gate 3: Small Comparable Cohort

- Add companies with similar business models and reporting styles.
- Validate comparisons, peer sets, KPI normalization, and pattern labels.

### Gate 4: Cross-Sector Cohort

- Add companies with different operating metrics and capital structures.
- Confirm that dashboards adapt rather than force irrelevant fields.

### Gate 5: Broad Release

- Publish feature coverage and known limitations.
- Add monitoring for stale, incomplete, conflicting, and low-confidence data.
- Maintain correction and user-feedback workflows.

## Functional Test Standard

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

## Definition of Done for Each Feature

A feature is complete only when:

- [ ] Its purpose and target user questions are documented.
- [ ] Inclusion, exclusion, classification, and calculation rules are documented.
- [ ] The skeleton, empty states, partial states, and evidence views exist.
- [ ] At least one pilot company has complete reviewed coverage.
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

## Phase 2 Success Measures

Product success should be measured through functional user outcomes rather than the number of dashboards shipped.

- Users can understand a new company faster.
- Users can trace strategic decisions to promises, milestones, resources, and outcomes.
- Users can identify what materially changed since their last visit.
- Users can monitor selected companies without reading every source document.
- Users open supporting evidence for important conclusions.
- Users create and revise theses using opposing as well as supporting evidence.
- Alert and briefing dismissal rates remain low enough to show relevance.
- Corrections and conflicting evidence are handled transparently.
- Feature coverage expands without increasing unsupported conclusions.

## Immediate Starting Backlog

Start Phase 2 with these concrete functional tasks:

- [ ] Approve the shared product and evidence rules in this document.
- [ ] Select the first pilot company and historical coverage period.
- [ ] Define the Company 360 information architecture.
- [ ] Define the business model component dictionary.
- [ ] Define the first company-specific KPI dictionary.
- [ ] Define promise, guidance, aspiration, and milestone distinctions.
- [ ] Define the earnings brief format.
- [ ] Build skeletons for Company 360, KPI Tracker, Earnings Intelligence, and Promise Tracker.
- [ ] Populate those four features for the pilot company using reviewed evidence.
- [ ] Run user review before moving to Wave 2 integrations.
