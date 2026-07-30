# Company 360 UI Redesign Todo

This todo is a product UI backlog for every feature reachable from Company 360. It focuses on what users should see and understand, not backend implementation details. Each section has a recommended UI name that can become the design/task name when we start implementation.

## Implementation Reset: 2026-07-28

- [ ] The initial Company 360 UI pass was rejected in product review. It layered new panels onto the existing page structure and did not constitute a redesign. Do not use its commits, builds, or HTTP smoke checks as acceptance evidence for this backlog.
- [ ] Do not mark a feature complete because it has a shared shell, a restyled card, or a working route. Each feature must use the UI model appropriate to the task it fulfills and must be reviewed in a browser with real company data.
- [ ] The Company 360 profile must not retain separate legacy blocks below the new workspace. Financial context, profile changes, source gaps, and evidence must be integrated into the same research flow and deduplicated where needed.
- [x] Dashboard redesign is in scope. It is the entry point to Company 360 and is implemented as a coverage control room, company directory, and activity feed. The company search interaction was browser-tested with live data.
- [ ] All Company 360 feature pages remain incomplete until their individual acceptance criterion is met. The intended interaction model for each page is part of that criterion: graph, map, workbench, board, timeline, matrix, calendar, table, or briefing as appropriate.

## Delivered And Browser-Checked: 2026-07-28

- [x] Company 360 profile briefing was consolidated into one research workspace. The old duplicate financial, change, gap, and source panels were removed; financial facts are deduplicated and limited to the active evidence rail. Verified with real Netflix data at desktop and mobile widths.
- [x] Dashboard was rebuilt as a coverage control room with a command search, coverage totals, workflow switcher, sector comparison, actionable company directory, and refresh ledger. Verified with real data at desktop and mobile widths, including workflow switching and navigation to Netflix Company 360.
- [x] Business Model Canvas, Operating Metrics Workbench, Promise Ledger, Strategy Execution Timeline, Quarterly Intelligence Brief, Capital Deployment Map, Competitive Battlefield Map, Product Timeline Studio, Deal Journey Board, Dependency Risk Map, and Market Footprint Atlas were rebuilt as route-specific workspaces and browser-checked with real Netflix data at desktop and mobile widths.
- [x] Leadership Tenure Timeline, Ownership and Insider Ledger, Valuation Context Workbench, Regulatory Matter Docket, Theme Exposure Radar, and Macro Exposure Profile were rebuilt as route-specific workspaces and browser-checked with real Netflix data at desktop and mobile widths.
- [x] Thesis Evidence Board was rebuilt as a private research workspace with separate evidence, checkpoints, indicators, and revisions. Verified at desktop and mobile widths.
- [x] Claim Reconciliation Desk, Failure Pattern Library, Scenario Planning Lab, Executive Briefing Feed, Signal Inbox, and Foundations Workbench were rebuilt as task-specific user-workspace and standards surfaces. Verified at desktop and mobile widths.
- [x] Dashboard workflow drill-downs were differentiated into an event feed, pattern library, risk watch, confidence audit, peer directory/matrix, scorecard, impact lab, and question desk. The Latest event feed was browser-checked at desktop and mobile widths.
- [x] Shared Source Lens is available from every Company 360 evidence workspace that has a source record; it deduplicates sources and keeps provenance, purpose, and power-user details out of the primary analysis surface. Verified with live Netflix regulatory evidence at desktop and mobile widths.
- [x] Evidence Gap cards now use a shared complete model: missing information, why it matters, likely source, and refresh status. Verified with live Netflix regulatory gaps.
- [x] Final cross-route audit: all 17 Company 360 research routes opened through the normal Company 360 navigation with live Netflix data, retained company context and return navigation, and passed desktop overflow checks.

## Product-Wide UI Principles

- [ ] Keep the company context visible on every feature page with a sticky company identity bar: company name, ticker if available, sector, country, latest reviewed date, and a back-to-Company-360 action.
- [ ] Show the answer first, then details. Every feature should start with a short human-readable summary and the most important status cards.
- [x] Move evidence, confidence, source records, and raw review labels into a secondary drawer or expandable source panel unless the user explicitly opens it.
- [ ] Use plain unavailable states. Avoid internal wording such as `planned in Phase 2`, `reviewed payload`, or raw enum names.
- [ ] Prefer timelines, maps, boards, matrices, and relationship graphs over long stacked text rows.
- [ ] Make all pages work for all 20 configured companies, including companies with partial evidence. Missing data should be shown as source gaps, not empty broken layouts.
- [ ] Avoid investment advice, legal conclusions, fake predictions, or implied causation. Use context language where the data is descriptive.

## Shared Company 360 Shell

### UI Name: Research Cockpit Navigation

- [x] Group Company 360 actions into clear categories: Business model, Performance, Strategy, Market position, Risk, Ownership, User workspace.
- [x] Replace the long button wall with grouped cards that explain why each feature matters.
- [x] Add a feature search/filter inside Company 360 so users can type "pricing", "lawsuit", "leadership", or "risk" and jump to the right feature. Browser-tested with the pricing query.
- [x] Add a persistent company/date context strip across all feature pages.
- [x] Add "Back to Company 360", "Change company", and "Compare peer" actions consistently.

### UI Name: Source Lens Drawer

- [x] Create a shared evidence drawer pattern for all Company 360 features.
- [x] Show source title, publisher, source date, source type, and why it was used.
- [x] Deduplicate repeated sources before display.
- [x] Hide internal confidence/review metadata by default; expose it under "Source details" for power users.
- [x] Add source-gap cards that say what is missing and which source type could fill it.

### UI Name: Evidence Gap Card System

- [x] Standardize unavailable states across all Company 360 research features.
- [x] Each unavailable card should show: missing information, why it matters, likely source, and current refresh status.
- [x] Avoid blank panels and avoid treating missing disclosure as zero or false.
- [x] Add "Open related feature" actions when another implemented page may contain adjacent context. The Company 360 evidence strip links to moves, earnings, milestones, and risk signals; the earnings link was browser-tested with live Netflix data.

## 1. Company 360 Profile

### UI Name: Company Dossier

- [x] Redesign the hero into an executive dossier: summary, business identity, coverage score, latest reviewed date, and key source freshness.
- [x] Replace flat section cards with grouped profile blocks: What it sells, Who it serves, How it earns, Where it operates, Who runs it, Who it competes with.
- [x] Add a "Business at a glance" visual using chips for products, customer groups, revenue sources, geographies, leadership, and competitors. Verified with live Netflix data at desktop and mobile widths.
- [x] Add a "What changed recently" strip linking to latest moves, earnings, milestones, and risk signals. The integrated evidence strip uses these direct actions and was browser-tested with live Netflix data.
- [x] Add a "Missing profile evidence" area using the shared Evidence Gap Card System. It now sits in the Company Dossier briefing rather than in a separate activity-rail block.
- [ ] Acceptance: a user should understand the company in under one minute without opening any detail page.

## 2. Business Model Map

### UI Name: Business Model Canvas Graph

- [ ] Keep the current component categories but redesign them as a visual business canvas.
- [ ] Use a movable connected bubble graph for value flow: users, payers, products, delivery channels, monetization, partners, assets, and cost structure.
- [ ] On node hover, highlight only the selected node and its direct relationships; blur unrelated nodes.
- [ ] On connector hover, highlight the relationship and both connected nodes.
- [ ] Remove arrowheads unless the relationship direction is essential and clearly explained.
- [x] Replace long relationship cards with a compact "Flow Details" side panel. Selecting a graph node shows its direct connections; selecting a connector shows its endpoints and relationship. Verified with live Netflix data at desktop and mobile widths.
- [ ] Add a real historical-change timeline that only shows source-backed changes between snapshots.
- [ ] Replace "Related intelligence" wording with plain links: customer groups, products, revenue sources, pricing changes, supplier dependencies.
- [ ] Deduplicate evidence sources and move them into the Source Lens Drawer.
- [ ] Acceptance: the user can visually answer who pays, what is delivered, how it is delivered, and how money flows.

## 3. Operating KPI Tracker

### UI Name: Operating Metrics Workbench

- [x] Group KPI cards by metric family so annual, quarterly, current, and related variants are selected through a compact dropdown inside one card.
- [ ] Keep dropdown labels inside card boundaries with ellipsis and tooltips for long metric names.
- [x] Make "View series" always update the chart for the selected metric variant. Browser-tested against the selected metric action.
- [x] Replace related company event rows with grouped event clusters by category, each expanding into dated events.
- [ ] Remove company-name repetition inside event copy because the page is already company-scoped.
- [x] Redesign peer normalization as a comparison-readiness panel: comparable now, blocked but fixable, not comparable.
- [x] Add a "Why this metric matters" note for operating metrics versus general financial facts.
- [ ] Acceptance: the page should not freeze with large KPI sets and should show useful context without long raw lists.

## 4. Management Promise Tracker

### UI Name: Promise Ledger

- [x] Replace the promise list/detail split with a status board. The board groups reviewed promises into Active, Delivered, At risk, and Unverifiable lanes while keeping full detail on selection. Verified with live Netflix data at desktop and mobile widths.
- [x] Add a promise timeline showing statement date, target window, updates, and final classification. The lifecycle rail preserves missing target dates and update history explicitly; verified with live Ford data at desktop and mobile widths.
- [x] Show the original statement in a quote-style card with speaker and source.
- [x] Show evaluation logic in plain language: what would count as success, failure, or too early.
- [ ] Add linked KPI and milestone context as small relationship cards.
- [ ] Move review metadata and source records into the Source Lens Drawer.
- [ ] Acceptance: a user can quickly see whether management did what it said it would do.

## 5. Earnings Intelligence

### UI Name: Quarterly Intelligence Brief

- [x] Use a quarter selector timeline at the top. The period rail exposes reviewed quarters as selectable visual segments and retains the existing period control as an accessible fallback. Verified with live Netflix data at desktop and mobile widths.
- [x] Redesign each quarter as a briefing: what happened, why management says it happened, what changed in guidance, what risks emerged, and what strategic moves were announced.
- [ ] Add a "Guidance changed?" badge with up, down, reaffirmed, withdrawn, or unavailable.
- [x] Add KPI movement chips linked back to the Operating Metrics Workbench. The earnings browser flow opens the selected KPI series in company scope.
- [x] Add "questions to monitor next quarter" when evidence suggests open items.
- [ ] Acceptance: the page should read like an analyst briefing, not a filing excerpt dump.

## 6. Strategy Milestone Tracker

### UI Name: Strategy Execution Timeline

- [x] Show milestones on a horizontal or vertical execution timeline. Tracks render reviewed start/end dates when known and a dashed track when dates are absent; selected tracks open the execution detail. Verified with live Netflix data at desktop and mobile widths.
- [x] Group milestones by strategic initiative. Execution tracks are grouped by their source-backed strategic-turn or management-promise anchor; unlinked tracks remain explicitly ungrouped. Verified with live Ford milestone data at desktop and mobile widths.
- [ ] Use clear status states: expected, in progress, completed, delayed, missed, cancelled, unverifiable.
- [x] Show expected versus actual dates where available. The execution rail displays source-backed expected windows and the detail view exposes dated status history when supplied.
- [ ] Add linked promises, KPIs, capital allocation, acquisitions, and earnings events.
- [ ] Acceptance: users should see whether a strategic decision is actually progressing.

## 7. Capital Allocation Dashboard

### UI Name: Capital Deployment Map

- [x] Replace dense rows with allocation buckets: acquisitions, buybacks, dividends, debt, capex, R&D, other investments.
- [x] Add a period selector with annual/quarterly toggle. The cadence control reloads the selected reviewed period and was browser-tested with live Netflix data.
- [x] Add a capital-flow visual showing where cash was directed. The allocation mix is now a proportional, category-labelled flow ledger with the reported amount and deployment share visible beside each bar. Verified with live Netflix data at desktop and mobile widths.
- [x] Separate reported cash-flow facts from strategic interpretation.
- [ ] Link large allocations to acquisitions, product launches, geographic expansion, or milestones when available.
- [ ] Acceptance: users should see where management is placing the largest bets.

## 8. Competitive Position Dashboard

### UI Name: Competitive Battlefield Map

- [x] Show competitors as a relationship battlefield that groups source-backed peers by direct, substitute, platform/channel, supplier/customer, and other configured relationship types. Each peer retains its scope, geography, overlap, evidence, and confidence context. Verified with live Netflix data at desktop and mobile widths.
- [ ] Add filters for relationship type, geography, product overlap, and source confidence.
- [x] Add a product/pricing overlap matrix. Source-backed peer intersections now render as a dimension grid for product, customer, geography, scale, and pricing comparisons. Verified with live Netflix data at desktop and mobile widths.
- [ ] Add a competitive response timeline with source-backed actions.
- [ ] Add moat-change cards: strengthening, weakening, mixed, unavailable.
- [ ] Acceptance: users should understand who the company competes with and where the pressure is coming from.

## 9. Product and Pricing History

### UI Name: Product Timeline Studio

- [x] Show product launches, discontinuations, packaging changes, and price changes on one timeline. Each event renders announcement and effective-date markers without implying unavailable dates. Verified with live Netflix data at desktop and mobile widths.
- [x] Add product family cards for current offerings. Offerings are grouped by their reviewed product type and retain availability, geography, customer segment, price-count, and description. Verified with live Netflix data at desktop and mobile widths.
- [x] Use before/after cards for pricing or package changes. Source-backed product and plan comparisons now render as paired prior/revised states.
- [ ] Separate confirmed list prices from missing price-context states.
- [ ] Link product changes to KPI movements, earnings commentary, and competitive responses when available.
- [ ] Acceptance: users should see how the offering changed over time and what evidence supports it.

## 10. Acquisition Lifecycle Tracker

### UI Name: Deal Journey Board

- [x] Show each deal as a lifecycle card: announced, pending approval, closed, integrating, reviewed outcome, unavailable outcome. Verified with live Ford Motor Company data at desktop and mobile widths, including selected-deal interaction.
- [x] Add a selected-deal detail panel with target, price, rationale, synergies, integration progress, and outcome.
- [x] Use a deal timeline for announcement, close, integration updates, impairment/divestiture, or outcome review.
- [x] Add clear unavailable cards for missing price, payment form, approval, synergies, and integration results.
- [ ] Acceptance: users should know what was bought, why, and whether the promised deal logic was later supported.

## 11. Customer and Supplier Dependency

### UI Name: Dependency Risk Map

- [x] Convert dependency rows into a relationship map with customer groups, suppliers, platforms, channels, and partners. It groups only reviewed relationship types returned for the selected company and filters; named counterparties remain explicitly identified as source-backed. Verified with live Netflix data at desktop and mobile widths.
- [ ] Add filters for customer, supplier, platform, distribution, concentration, and contract-risk categories.
- [x] Show named counterparties only when source-backed. Category-only relationships explicitly state that no counterparty is asserted.
- [ ] Add contract-risk cards for renewal, exclusivity, minimum commitment, termination, and critical supplier gaps.
- [ ] Acceptance: users should see where the business may depend on a small group, supplier, platform, or channel.

## 12. Geographic Expansion Map

### UI Name: Market Footprint Atlas

- [x] Use a map-first layout where countries and regions are grouped by current presence, entered, exited, and unavailable detail. The footprint atlas uses only reviewed status fields and places non-classified presence in a separate detail-limited lane. Verified with live Netflix data at desktop and mobile widths.
- [x] Add an expansion timeline for source-backed market entries and exits. The timeline explicitly reports when no dated rows are reviewed.
- [x] Add market detail cards: local partner, regulatory barrier, revenue contribution, outcome, and source gaps. The cards state when these fields are not disclosed rather than treating generic market presence as complete evidence. Verified with live Netflix data at desktop and mobile widths.
- [x] Avoid implying a dated market entry from generic geographic presence.
- [ ] Acceptance: users should understand where the company operates and what expansion evidence is actually known.

## 13. Leadership Decision Record

### UI Name: Leadership Tenure Timeline

- [x] Show executive roles and tenure as timeline bars. Dated roles render as bounded tracks; roles without reviewed dates render as dashed, explicitly undated tracks. Verified with live Ford Motor Company data at desktop and mobile widths.
- [x] Add a leadership-change timeline for appointments, departures, succession, and board changes. Undated records are visibly treated as date-unavailable rather than assigned a false tenure date.
- [ ] Link major decisions and priorities to each leader only when source-backed.
- [ ] Show performance during tenure as context, with non-causation language.
- [ ] Add source gaps for missing tenure dates, compensation, board context, and decision links.
- [ ] Acceptance: users should see who led, when, what priorities were stated, and what cannot be attributed.

## 14. Ownership and Insider Activity

### UI Name: Ownership Control Panel

- [x] Show ownership categories as cards: founder, insider, institution, public float, voting control, unavailable. The coverage board presents source-backed category counts and clear not-reviewed states without inferring ownership.
- [x] Separate economic ownership from voting control. The coverage board and holder table keep the two disclosure types distinct.
- [ ] Add insider activity timeline for source-backed purchases, sales, plans, and holdings changes.
- [x] Add holder table with filters by holder type and transaction type. The responsive holder table follows the existing reviewed holder and transaction filters.
- [ ] Add source gaps for missing ownership percentages, plan details, and holder identity.
- [ ] Acceptance: users should understand who controls or materially owns the company without overreading incomplete disclosure.

## 15. Valuation Context

### UI Name: Valuation Context Lens

- [x] Use measure tabs: market cap, P/S, P/E, EV, EV/revenue, and unavailable inputs. The tabs reload the selected source-backed context and were browser-tested with live Netflix data.
- [x] Show formulas and numerator/denominator inputs in a compact calculation drawer. The calculation ledger groups every reviewed measure with its formula and reported inputs.
- [x] Add peer context cards and event-aligned context around major strategic moves. Peer/range and dated-event context are separate research panels.
- [x] Label everything as context, not investment advice. The route header and research guardrail make this explicit once, without turning the page into advice.
- [x] Add unavailable input cards when market price, share count, debt, cash, or earnings inputs are missing. Missing inputs are named at measure level with their source-backed reason.
- [ ] Acceptance: users should understand the valuation context and data limitations without receiving buy/sell guidance.

## 16. Regulatory and Litigation Calendar

### UI Name: Regulatory Matter Calendar

- [ ] Use a calendar plus matter list layout.
- [ ] Add filters for matter type, status, authority, materiality, and geography.
- [ ] Show matter cards with current status, next known date, potential business exposure when disclosed, and source.
- [ ] Add legal guardrail text once in the page header instead of repeating it in every row.
- [ ] Add source gaps for missing deadline, authority, jurisdiction, or exposure detail.
- [ ] Acceptance: users should know what matters exist, what dates are known, and what is not being concluded.

## 17. Sector and Theme Intelligence

### UI Name: Theme Exposure Radar

- [x] Show themes as a radar or grouped exposure board: AI, cloud, EV, ads, commodities, rates, regulation, consumer demand, and sector-specific themes. The reviewed exposure board is rendered from the configured theme taxonomy and company evidence.
- [ ] Add exposure cards with materiality, direction, related KPIs, related events, and source status. Cards now show the source-backed exposure type, materiality, evidence date, source availability, and available event/KPI/capital links; data does not currently expose a separate directional field.
- [ ] Link themes to capital allocation, earnings commentary, macro sensitivity, and risk signals.
- [ ] Add filters for theme, materiality, source type, and company.
- [ ] Acceptance: users should see which external themes matter to the company and why.

## 18. Macro Sensitivity Profile

### UI Name: Macro Exposure Radar

- [x] Show macro factors as cards: inflation, rates, recession, currency, commodity prices, employment, consumer spending, supply chain. Available reviewed factors now render as directional channel cards rather than rows. Verified with live Netflix data at desktop and mobile widths.
- [x] Add channel labels: revenue, cost, demand, financing, valuation, supply, regulation.
- [x] Show direction only when supported: positive, negative, mixed, unclear.
- [ ] Add stress-period examples where evidence exists.
- [x] Keep relationship limitations visible so users do not confuse correlation with causation.
- [ ] Acceptance: users should understand which economic forces could affect the company and how strong the evidence is.

## 19. Strategy Thesis Workspace

### UI Name: Thesis Evidence Board

- [ ] Redesign the thesis detail page as a board: thesis statement, assumptions, supporting evidence, opposing evidence, milestones, indicators, and confidence history.
- [ ] Add a support-versus-opposition balance visual.
- [ ] Add drag-friendly evidence cards where private notes are clearly separate from source-backed evidence.
- [ ] Add "what would change my mind" prompts for falsifiable milestones and indicators.
- [ ] Add evidence suggestions from ingestion search in a side panel.
- [ ] Acceptance: users should be able to create, monitor, and revise a thesis without mixing private notes with reviewed evidence.

## 20. Watchlists and Alerts

### UI Name: Signal Inbox

- [ ] Replace generic notification lists with an inbox grouped by company, alert category, and severity.
- [ ] Add alert categories: strategic move, guidance change, risk escalation, leadership change, milestone completion, contradiction, source gap resolved.
- [ ] Add follow controls directly on Company 360 and detail pages.
- [ ] Add alert feedback controls: useful, noisy, duplicate, missing context.
- [ ] Acceptance: users should receive meaningful changes, not every new document mention.

## 21. Daily and Weekly Briefings

### UI Name: Executive Briefing Feed

- [ ] Structure each briefing item as: what changed, why it matters, which company, what to watch next.
- [ ] Add priority ranking for followed companies.
- [ ] Add digest filters for daily, weekly, company, theme, risk, and unread.
- [ ] Add archive, useful, too long, and missing context feedback.
- [ ] Acceptance: users should get a quick decision-ready summary of followed companies.

## 22. Scenario Explorer

### UI Name: Scenario Planning Lab

- [ ] Show best case, base case, and worst case as side-by-side scenario boards.
- [ ] Add assumption cards with drivers: KPIs, macro factors, promises, milestones, risks, pricing, and competition.
- [ ] Add indicators to monitor and actual-result comparison when available.
- [ ] Clearly label scenarios as user-created, reviewed, or template-based.
- [ ] Add non-prediction guardrail language in the header.
- [ ] Acceptance: users should compare plausible outcomes and monitor assumptions without treating them as forecasts.

## 23. Contradiction View

### UI Name: Claim Reconciliation Desk

- [ ] Show contradictions as paired claim cards: management statement, filing/result/external evidence, conflict type, materiality, and status.
- [ ] Add filters for conflict type, company, materiality, confidence, review status, and source type.
- [ ] Use neutral language: inconsistent, unsupported, revised, outdated, ambiguous, resolved.
- [ ] Add correction/review path for human review before publishing strong claims.
- [ ] Acceptance: users should understand the inconsistency without the UI accusing the company of deception.

## 24. Strategy Failure Library

### UI Name: Failure Pattern Library

- [ ] Show cases as a searchable library with filters for acquisition, pivot, expansion, pricing, restructuring, product, leadership, and capital allocation.
- [ ] Add failure stage filters: early signal, decision, execution, deterioration, reversal, outcome review.
- [ ] Show each case with management rationale, expected outcome, actual outcome, warning signs, counterexamples, and related evidence.
- [ ] Add links to related promises, milestones, acquisitions, KPIs, and contradictions.
- [ ] Acceptance: users should learn patterns of strategic failure without treating every adverse result as predictable.

## 25. Compare Peers

### UI Name: Peer Comparison Board

- [ ] Keep Company 360 scope when opened from a company page.
- [ ] Show the selected company against same-sector configured peers and reviewed external peers.
- [ ] Use a comparison matrix for business model, KPIs, capital allocation, valuation context, risk signals, and competitive overlap.
- [ ] Show blocked comparisons as reason chips, not raw technical rules.
- [ ] Acceptance: users should know which peer comparisons are valid and why some are unavailable.

## 26. Latest Moves

### UI Name: Strategic Moves Feed

- [ ] Show company-scoped latest moves as an event feed grouped by event type and date.
- [ ] Add filters for product, pricing, acquisition, geography, leadership, regulation, capital allocation, and competitive response.
- [ ] Add "why this matters" snippets that link to the relevant Company 360 feature.
- [ ] Deduplicate repeated source mentions and avoid raw ingestion labels.
- [ ] Acceptance: users should see recent source-backed strategic activity without scanning all dashboards.

## 27. Risk Signals

### UI Name: Risk Watch Panel

- [ ] Group risks by business model, KPI deterioration, competition, regulatory, litigation, macro, dependency, leadership, and valuation context.
- [ ] Add severity and freshness indicators.
- [ ] Link every risk signal to source-backed evidence and related feature pages.
- [ ] Separate observed risk disclosure from inferred impact.
- [ ] Acceptance: users should understand what requires attention and what is only a disclosed uncertainty.

## Suggested Implementation Waves

- [ ] Wave 1: Shared Company 360 shell, Source Lens Drawer, Evidence Gap Card System, Company Dossier, Business Model Canvas Graph, Operating Metrics Workbench.
- [ ] Wave 2: Promise Ledger, Strategy Execution Timeline, Quarterly Intelligence Brief, Capital Deployment Map, Competitive Battlefield Map.
- [ ] Wave 3: Product Timeline Studio, Deal Journey Board, Dependency Risk Map, Market Footprint Atlas, Leadership Tenure Timeline.
- [ ] Wave 4: Ownership Control Panel, Valuation Context Lens, Regulatory Matter Calendar, Theme Exposure Radar, Macro Exposure Radar.
- [ ] Wave 5: Thesis Evidence Board, Signal Inbox, Executive Briefing Feed, Scenario Planning Lab, Claim Reconciliation Desk, Failure Pattern Library.
- [ ] Wave 6: Peer Comparison Board, Strategic Moves Feed, Risk Watch Panel, final cross-company visual consistency pass.

## Per-Feature Acceptance Checklist

- [ ] The page has a clear title, company context, data freshness, and one-sentence purpose.
- [ ] The primary visualization is obvious within the first screen.
- [ ] Dense source/evidence material is hidden behind a drawer or expandable section.
- [ ] Empty and partial states explain the missing source, not just "unavailable".
- [ ] The page remains useful for all 20 configured companies.
- [ ] The page avoids raw enum names and internal implementation language.
- [ ] The layout works on desktop and smaller screens.
- [ ] The feature links to related Company 360 surfaces when context overlaps.
