# Company Data Source Strategy

## Decision

InfoDJ should not present a single vendor as the source of all company data. No
such API provides complete, timely, auditable coverage across financials,
ownership, products, contracts, competition, and regulation. The data platform
should use original disclosures as its evidence spine, specialist APIs for
commoditised market data, and a reviewable document-extraction workflow for
unstructured claims.

Every displayed fact must retain its source URL, publisher, source date,
extraction method, and confidence. A missing field is preferable to a guessed
field.

## Current Baseline

The active universe is U.S. listed companies and already has SEC CIK support.
The existing database has SEC financial facts, source documents, and Company
360 domain models. The current audit found these material gaps:

| Data set | Current rows | Consequence |
| --- | ---: | --- |
| Equity market prices | 1,336 rows across 14/20 companies, latest 2025-05-01 | Existing bars are stale and six companies have no coverage. |
| Product PriceObservation | 0 | Product and service price history is unavailable. |
| DependencyContractTerm | 0 | Supplier/customer contract detail is unavailable. |
| InsiderTransaction | 66 rows across all 20 companies after the initial two-filing backfill | A 2,627-filing historical backlog remains and should be processed in controlled batches. |

The source inventory also found 4,500 documents, 432 text extractions (420
successful), and 2,627 already-discovered Forms 3/4/5. That last group is a
high-value source-to-model gap: the evidence exists locally and should be
parsed before adding another insider-data vendor.

## Coverage by Category

| Company 360 category | Canonical source | Secondary source | Automation level | Important limit |
| --- | --- | --- | --- | --- |
| Identity, listing, filing timeline | SEC submissions API | Exchange/IR site | High | U.S. issuers only. |
| Financial statements and selected KPIs | SEC Company Facts and filing XBRL | Annual report tables | High | Company Facts only exposes reported XBRL concepts. |
| Market price, volume, returns | Licensed market-data vendor | Stooq EOD fallback | High | Free sources are not a real-time or redistribution licence. |
| Insider transactions | SEC Forms 3, 4, 5 XML | FMP/Finnhub/Polygon convenience feed | High for U.S. | Form 4 reflects reported insider transactions, not all economic ownership. |
| Ownership and voting control | DEF 14A, Schedules 13D/13G, 13F | Licensed ownership vendor | Medium | 13F is delayed and manager-centric; it is not a complete shareholder register. |
| Capital allocation, segments, geography | 10-K/10-Q XBRL and notes | Earnings releases | Medium | Segment and geography disclosures vary by issuer. |
| Acquisitions, strategy, leadership | 8-K, 10-K, DEF 14A, IR releases | Reputable licensed news | Medium | Requires date-aware extraction and review. |
| Product catalogue and pricing | Official product pages, price sheets, filings | Vertical product-data provider | Medium/low | No cross-industry universal product API exists. |
| Customer/supplier concentration and contract terms | 10-K concentration disclosures, Exhibit 10 agreements | Procurement/vertical licensed data | Low/medium | Most contracts are private; extracted terms must be explicitly evidenced. |
| Competitive position | Company filings and peer disclosures | Licensed industry datasets | Medium | Market-share data is sector-specific and often licensed. |
| Litigation and regulation | SEC filings, regulator/court primary records | Licensed legal/news feed | Medium | Jurisdiction and industry determine coverage. |

## Source Tiers

### Tier 1: original and authoritative

Use SEC EDGAR as the default U.S. public-company spine. Its submissions and
XBRL APIs require no API key, return JSON, and are updated as filings are
disseminated. The Company Facts endpoint provides reported XBRL facts in one
company-level call. Relevant forms are 10-K, 10-Q, 8-K, S-1, DEF 14A, 3/4/5,
13D, and 13G. Fetch document content from the filing archive only after the
metadata record is stored.

Use government and regulator sources per vertical: FDA and ClinicalTrials.gov
for healthcare, NHTSA for vehicle recalls, FTC/DOJ for competition matters, and
court records where their terms and coverage permit.

### Tier 2: licensed normalised feeds

FMP is a practical optional provider for historical prices, quotes, statements,
and insider-trading convenience data. It requires an API key and requests may
be rate limited. Alpha Vantage is a viable optional price provider; its daily
adjusted endpoint contains OHLCV, adjusted close, dividends, and splits, but
the endpoint is premium. Use either only behind an adapter and retain the
provider and raw response metadata.

For production redistribution, choose and contract with one market-data vendor
after confirming exchange coverage, latency, historical rights, and user-count
licensing. Do not represent an unaudited free EOD fallback as real-time data.

### Tier 3: document-derived evidence

Use official IR pages, product pages, pricing pages, earnings releases, and
filing exhibits where Tier 1 data is structurally absent. Extraction can propose
records, but publication requires a source excerpt, source document, and
review status. This tier is the correct path for product pricing, supplier
terms, competitive claims, and private-company history.

## Operating Model

1. Discover and store filing metadata first.
2. Ingest structured records where the source defines them: Company Facts,
   market bars, and Form 4 transactions.
3. Derive Company 360 snapshots only from cited records.
4. Send ambiguous or unstructured claims to a review queue rather than filling
   a dashboard with defaults.
5. Record a visible coverage/gap state for every category and route the next
   collection job from that gap.

## Delivery Sequence

1. Complete the SEC spine for every active U.S. issuer: CIK resolution,
   submissions, Company Facts, 10-K/10-Q/8-K and ownership-form metadata.
2. Backfill end-of-day market data, then build valuation contexts and event
   price windows.
3. Parse Forms 4/3/5 into auditable insider transactions and use DEF 14A plus
   13D/13G for ownership percentages.
4. Add industry-specific regulatory adapters before expanding generic news.
5. Implement evidence-first extractors for product/pricing, contracts, and
   competitive position; keep all resulting rows in review until verified.

## References

- [SEC EDGAR data APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC ownership XML technical specification](https://www.sec.gov/info/edgar/ownershipxmltechspec-v3.pdf)
- [FMP API quickstart](https://site.financialmodelingprep.com/developer/docs/quickstart)
- [Alpha Vantage API documentation](https://www.alphavantage.co/documentation/)
