# Plan To Fetch Company Details

InfoDJ should not use one fixed collector for every company. It should route source discovery by company stage, year range, public/private status, and jurisdiction.

## Goal

Given a company, create a source plan that answers:

- which years matter
- which stage the company was in during each year range
- which sources are best for each stage
- which collectors should run first
- which sources should be treated as official, supporting, or noisy

The output should guide ingestion before any crawler or API collector runs.

## Generic Company Stages

### Founding / Private Early Stage

Use this stage when the company is newly founded, private, or pre-revenue.

Best sources:

- Wikidata
- Wikipedia page and references
- company website/about page
- founder interviews
- archived webpages
- early press
- funding announcements
- product launch pages

Look for:

- founding story
- first product
- first customer segment
- first pricing model
- first distribution channel
- early pivot
- early partnerships

Avoid relying on:

- SEC EDGAR
- broad recent-news search

### Growth / Pre-IPO / Private Scale

Use this stage when the company is private but has market traction, funding, expansion, or visible product changes.

Best sources:

- company blog/newsroom
- funding announcements
- product launch pages
- founder interviews
- trade publications
- Wikipedia references
- targeted news search
- archived webpages

Look for:

- business model changes
- product expansion
- geographic expansion
- customer segment shifts
- channel changes
- funding events
- partnerships
- early acquisitions

### Public Company

Use this stage when the company is publicly listed.

For U.S. public companies, use:

- SEC EDGAR submissions
- 10-K
- 10-Q
- 8-K
- S-1 and amended S-1 for IPO history
- DEF 14A where governance/leadership matters
- investor relations pages
- annual reports
- earnings releases
- company newsroom
- targeted news validation

For non-U.S. public companies, use:

- local exchange filings
- local securities regulator filings
- annual reports
- investor relations pages
- company newsroom
- targeted news validation

Look for:

- official strategic language
- risk-factor changes
- revenue model shifts
- segment reporting changes
- product categories
- geographic mix
- acquisitions
- partnerships
- restructuring
- leadership changes
- regulatory responses

### Recent / Live Monitoring

Use this stage for the last three years or for ongoing monitoring.

Best sources:

- company newsroom
- investor relations updates
- SEC/local filings
- GDELT
- trusted business news
- official social/product feeds where useful

Look for:

- fresh product launches
- pricing changes
- leadership changes
- acquisitions
- partnerships
- regulatory events
- crisis response
- competitive response

GDELT should be treated as supporting discovery, not primary truth.

## Year-Based Routing Rules

### Rule 1: Before Public Listing

If:

```text
target_year < public_listing_year
```

Use:

```text
WIKIDATA
WIKIPEDIA_REFERENCES
COMPANY_HISTORY_PAGE
COMPANY_NEWSROOM
ARCHIVED_WEB
FOUNDER_INTERVIEWS
TARGETED_NEWS
```

Do not use SEC EDGAR as the primary source for this period.

### Rule 2: After Public Listing

If:

```text
target_year >= public_listing_year
```

Use:

```text
SEC_EDGAR or LOCAL_FILINGS
INVESTOR_RELATIONS
ANNUAL_REPORTS
COMPANY_NEWSROOM
TARGETED_NEWS
GDELT_SUPPORTING
```

For U.S. public companies, EDGAR becomes the backbone source.

### Rule 3: Recent Years

If:

```text
target_year >= current_year - 3
```

Use:

```text
FILINGS
COMPANY_NEWSROOM
INVESTOR_RELATIONS
GDELT_SUPPORTING
TRUSTED_BUSINESS_NEWS
```

Recent sources should still be reviewed because they are noisy and can overstate events before official confirmation.

### Rule 4: Private Companies

If the company is private:

```text
skip SEC_EDGAR unless it has public debt or related filings
```

Use:

```text
WIKIDATA
WIKIPEDIA_REFERENCES
COMPANY_WEBSITE
COMPANY_BLOG
FUNDING_NEWS
FOUNDER_INTERVIEWS
TARGETED_NEWS
ARCHIVED_WEB
```

### Rule 5: Unknown Listing Status

If public/private status is unknown:

1. Try Wikidata metadata.
2. Try ticker/CIK lookup for U.S. companies.
3. Try company investor relations page.
4. Fall back to private-company routing until listing evidence is found.

## Source Reliability

### Official Sources

Highest weight:

- SEC EDGAR
- exchange/regulator filings
- annual reports
- investor relations releases
- company newsroom
- official product/blog announcements

### Structured Public Knowledge

Medium weight:

- Wikidata
- Wikipedia
- Wikipedia references

Use for discovery and timeline seeds, then validate with source links.

### News And Web Sources

Supporting weight:

- GDELT
- trusted business news
- trade publications
- archived web

Useful for evidence and context, but noisy.

## Source Router Output

The source router should output rows like:

```json
{
  "stage": "PUBLIC_COMPANY",
  "year_start": 2002,
  "year_end": 2026,
  "primary_sources": ["SEC_EDGAR", "INVESTOR_RELATIONS", "ANNUAL_REPORTS"],
  "supporting_sources": ["COMPANY_NEWSROOM", "TARGETED_NEWS", "GDELT_SUPPORTING"],
  "collector_priority": ["sec_edgar", "investor_relations", "company_newsroom", "gdelt"],
  "notes": "Use filings as backbone from listing year onward."
}
```

## Data Needed On Company

Current fields:

- name
- slug
- aliases
- industry
- country
- wikidata_id
- sec_cik
- website
- founded_date

Needed soon:

- ticker
- is_public
- public_listing_date
- public_listing_exchange
- filing_jurisdiction
- filing_identifier
- investor_relations_url
- newsroom_url

Until these fields exist, the router can infer from:

- `sec_cik` present means U.S. public-company filing route is available
- `founded_date` gives pre-public starting point
- known ticker input can resolve EDGAR CIK

## Netflix Example

Known facts for routing:

```text
founded year: 1997
public listing year: 2002
country: United States
ticker: NFLX
SEC CIK: 0001065280
```

Generic routing result:

```text
1997-2001:
  stage: PRIVATE_EARLY_AND_GROWTH
  primary: Wikipedia references, company history, archived web, founder interviews
  supporting: targeted news

2002-2022:
  stage: PUBLIC_COMPANY
  primary: SEC EDGAR, annual reports, investor relations
  supporting: company newsroom, targeted news, Wikipedia references

2023-2026:
  stage: RECENT_PUBLIC_COMPANY
  primary: SEC EDGAR, investor relations, company newsroom
  supporting: GDELT, trusted business news
```

This is generic: another U.S. public company follows the same pattern with different years and ticker/CIK. A private company skips the public-company stage unless a filing source is discovered.

## Implementation Steps

1. Add a `source_router` service.
2. Add a command to print a source plan for a company.
3. Extend company metadata with listing fields.
4. Implement full-history EDGAR ingestion by following `filings.files[]`.
5. Implement Wikipedia/Wikidata reference ingestion for pre-public history.
6. Implement company website/newsroom discovery.
7. Keep GDELT as supporting evidence with strict language and pacing filters.
