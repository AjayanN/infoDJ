# InfoDJ Implementation Plan

## Product Direction

InfoDJ starts as a business-event ingestion and curation engine, not as a polished public UI.

The first useful product is an admin-first system where an operator can enter a company, run ingestion jobs, inspect collected sources, review extracted business events, merge duplicates, and approve strategic turns into a structured database.

The first pilot company is Netflix.

## Initial Stack

### Current MVP Stack

- Backend: Django
- Admin interface: Django Admin
- Database: PostgreSQL
- Schema: `infodj`
- Database name: `business`
- Database user: `the_dj`
- Async jobs: Celery
- Broker/cache: Redis
- Source discovery: Wikidata and GDELT
- Article extraction: `trafilatura`, with `readability-lxml` fallback later
- Structured extraction: LLM JSON extraction, added after source collection is stable

### Future Transition Target

The project should be designed so Django Admin is the first internal tool, not the final product UI.

Future target:

- Backend API: FastAPI
- Admin/customer UI: Angular
- Mobile path: Angular PWA first, Ionic/Capacitor later if needed
- Workers: Python services reused from the Django MVP where practical

The important design choice is to keep ingestion, extraction, clustering, and source-client logic in service modules instead of tying it directly to Django Admin. That makes the future FastAPI transition realistic.

## Repository

Project folder:

```text
/home/famei/InfoDJ
```

Git remote:

```text
https://github.com/AjayanN/infoDJ.git
```

The GitHub token must not be committed to files, `.env`, documentation, Git config, or shell scripts.

## Local PostgreSQL Status

Current machine status:

- Native PostgreSQL 16 is installed.
- Local database `business` exists.
- Local user `the_dj` exists.
- Local schema `infodj` exists.
- Django migrations have been applied to PostgreSQL.
- A gitignored local `services/ingestion/.env` file provides the development database URL.

## PostgreSQL Setup

When PostgreSQL is available locally, create the database, user, and schema with:

```sql
CREATE USER the_dj WITH PASSWORD 'change_this_password';
CREATE DATABASE business OWNER the_dj;
\c business
CREATE SCHEMA IF NOT EXISTS infodj AUTHORIZATION the_dj;
ALTER ROLE the_dj SET search_path TO infodj, public;
GRANT ALL PRIVILEGES ON DATABASE business TO the_dj;
GRANT ALL ON SCHEMA infodj TO the_dj;
```

Recommended application environment:

```text
DATABASE_URL=postgres://the_dj:change_this_password@localhost:5432/business
DJANGO_DB_SCHEMA=infodj
DJANGO_SECRET_KEY=local-dev-secret
DJANGO_DEBUG=true
REDIS_URL=redis://localhost:6379/0
```

For Django, the PostgreSQL schema should be set through the connection option:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "business",
        "USER": "the_dj",
        "PASSWORD": "change_this_password",
        "HOST": "localhost",
        "PORT": "5432",
        "OPTIONS": {
            "options": "-c search_path=infodj,public",
        },
    }
}
```

## Django Project Structure

Recommended structure:

```text
InfoDJ/
  services/
    ingestion/
      manage.py
      requirements.txt
      .env.example
      config/
        __init__.py
        settings.py
        urls.py
        celery.py
      apps/
        companies/
          models.py
          admin.py
          services.py
        ingestion/
          models.py
          admin.py
      tasks.py
      services/
        wikidata_client.py
        gdelt_client.py
        query_generator.py
        article_extractor.py
        event_extractor.py
        event_clusterer.py
    curation/
      models.py
      admin.py
      services.py
```

## Core Admin Workflows

### 1. Company Setup

Admin can:

- create a company manually
- resolve company metadata from Wikidata
- edit aliases, industry, country, website, Wikidata ID, and SEC CIK
- mark a company as active/inactive for ingestion

For Netflix, expected company metadata:

```text
name: Netflix
slug: netflix
aliases: Netflix, Netflix Inc., Netflix.com
country: United States
wikidata_id: Q907311
website: https://www.netflix.com
```

SEC CIK should be resolved from SEC EDGAR later for public-company filings.

### 2. Ingestion Job

Admin can create an ingestion job for a company.

Job fields:

- company
- job type
- query
- source
- status
- started at
- finished at
- error message
- counters for sources found, sources inserted, duplicates skipped, extractions completed, events extracted

Job types:

```text
COMPANY_METADATA_SYNC
SOURCE_DISCOVERY
ARTICLE_EXTRACTION
EVENT_EXTRACTION
EVENT_CLUSTERING
FULL_COMPANY_PIPELINE
```

Job statuses:

```text
PENDING
RUNNING
SUCCEEDED
FAILED
PARTIAL
CANCELLED
```

### 3. Source Review

Admin can inspect collected source documents before full extraction.

Useful filters:

- company
- source API
- publisher
- language
- published date
- status
- duplicate status
- extraction status

Useful admin actions:

- mark selected sources as approved
- mark selected sources as ignored
- run article extraction for selected sources
- run event extraction for selected sources
- recalculate duplicate hashes

### 4. Article Extraction Review

Admin can inspect extracted text quality.

Admin should show:

- source title
- URL
- publisher
- extraction status
- word count
- short clean-text preview
- extraction error

The system should not rely on storing full article text forever as the product value. Long-term storage should focus on metadata, extracted facts, short evidence excerpts, and source links.

### 5. Business Event Review

Admin can inspect extracted structured business events.

Admin should allow editing:

- event type
- lifecycle stage
- event date
- before state
- after state
- trigger
- decision
- outcome
- evidence text
- confidence score
- review status

Review statuses:

```text
DRAFT
NEEDS_REVIEW
APPROVED
REJECTED
MERGED
```

### 6. Strategic Turn Curation

Admin can group multiple business events into one strategic turn.

Example:

```text
Strategic turn: Netflix launches ad-supported subscription tier
Turn type: BUSINESS_MODEL_EXPANSION
Company: Netflix
Start date: 2022-04-01
End date: 2022-11-30
Before: Subscription-only streaming revenue model
After: Subscription plus advertising-supported tier
Trigger: Subscriber growth pressure and market saturation
Decision: Introduce a lower-priced ad-supported plan
Outcome: Opened advertising as a new revenue channel
Founder lesson: When the core model matures, add a complementary revenue model without abandoning the main one.
```

Admin actions:

- create turn from selected events
- attach source documents
- merge turns
- mark turn as approved
- publish/unpublish turn

## Database Model Plan

### Company

Fields:

- `id`
- `name`
- `slug`
- `aliases`
- `industry`
- `country`
- `wikidata_id`
- `sec_cik`
- `website`
- `founded_date`
- `description`
- `is_active`
- `created_at`
- `updated_at`

Indexes:

- unique `slug`
- indexed `wikidata_id`
- indexed `sec_cik`

### SourceDocument

Fields:

- `id`
- `company_id`
- `source_api`
- `url`
- `canonical_url`
- `title`
- `publisher`
- `published_date`
- `snippet`
- `language`
- `url_hash`
- `title_hash`
- `status`
- `duplicate_of_id`
- `created_at`
- `updated_at`

Statuses:

```text
DISCOVERED
APPROVED
IGNORED
DUPLICATE
EXTRACTION_PENDING
EXTRACTED
EXTRACTION_FAILED
```

Indexes:

- unique `url_hash`
- indexed `company_id`
- indexed `published_date`
- indexed `source_api`
- indexed `status`

### ArticleExtraction

Fields:

- `id`
- `source_document_id`
- `clean_text`
- `word_count`
- `extraction_status`
- `extraction_error`
- `extractor_name`
- `created_at`
- `updated_at`

Statuses:

```text
PENDING
SUCCEEDED
FAILED
SKIPPED
```

### BusinessEvent

Fields:

- `id`
- `company_id`
- `source_document_id`
- `article_extraction_id`
- `event_date`
- `event_type`
- `lifecycle_stage`
- `before_state`
- `after_state`
- `trigger`
- `decision`
- `outcome`
- `evidence_text`
- `confidence_score`
- `review_status`
- `raw_extraction_json`
- `created_at`
- `updated_at`

Event types:

```text
BUSINESS_MODEL_PIVOT
PRICING_CHANGE
PRODUCT_EXPANSION
GEOGRAPHIC_EXPANSION
CUSTOMER_SEGMENT_SHIFT
DISTRIBUTION_CHANNEL_SHIFT
FUNDING_EVENT
ACQUISITION
PARTNERSHIP
LEADERSHIP_CHANGE
REGULATORY_RESPONSE
CRISIS_RESPONSE
COMPETITIVE_RESPONSE
BRAND_REPOSITIONING
REVENUE_MODEL_EXPANSION
```

Lifecycle stages:

```text
IDEA
LAUNCH
EARLY_GROWTH
SCALE
MATURITY
TURNAROUND
DECLINE
REINVENTION
```

### StrategicTurn

Fields:

- `id`
- `company_id`
- `title`
- `turn_type`
- `start_date`
- `end_date`
- `lifecycle_stage`
- `summary`
- `before_state`
- `after_state`
- `trigger`
- `decision`
- `outcome`
- `founder_lesson`
- `confidence_score`
- `review_status`
- `is_published`
- `created_at`
- `updated_at`

Indexes:

- indexed `company_id`
- indexed `turn_type`
- indexed `start_date`
- indexed `review_status`
- indexed `is_published`

### StrategicTurnSource

Fields:

- `id`
- `strategic_turn_id`
- `source_document_id`
- `business_event_id`
- `evidence_text`
- `created_at`

Purpose:

This preserves traceability from a curated strategic turn back to the sources and extracted events that support it.

### IngestionJob

Fields:

- `id`
- `job_type`
- `company_id`
- `query`
- `source`
- `status`
- `started_at`
- `finished_at`
- `error_message`
- `sources_found`
- `sources_inserted`
- `duplicates_skipped`
- `articles_extracted`
- `events_extracted`
- `turns_created`
- `created_at`
- `updated_at`

## Netflix First Pipeline

### Step 1: Create Netflix Company

Admin creates or resolves:

```text
Netflix
```

The Wikidata resolver should search for the company and save:

- Wikidata ID
- official name
- aliases
- country
- industry
- website
- description

Wikidata endpoint:

```text
https://www.wikidata.org/w/api.php
```

Initial search parameters:

```text
action=wbsearchentities
search=Netflix
language=en
format=json
```

Entity detail parameters:

```text
action=wbgetentities
ids=Q907311
props=claims|descriptions|aliases|sitelinks
languages=en
format=json
```

### Step 2: Generate Netflix Queries

The query generator should create focused business-history search queries.

Initial Netflix query set:

```text
Netflix DVD rental business model
Netflix streaming launch
Netflix subscription pricing change
Netflix original content strategy
Netflix international expansion
Netflix advertising tier launch
Netflix password sharing crackdown
Netflix subscriber growth decline response
Netflix partnership strategy
Netflix acquisition strategy
```

Each query becomes one `IngestionJob` child task or one tracked query row in the job payload.

### Step 3: Fetch GDELT Documents

Use GDELT DOC 2.0 API for source discovery.

Endpoint:

```text
https://api.gdeltproject.org/api/v2/doc/doc
```

Example request:

```text
query="Netflix streaming launch"
mode=ArtList
format=json
maxrecords=25
sort=HybridRel
```

For each returned article, store:

- title
- URL
- publisher/domain
- published date
- snippet if available
- language
- source API as `GDELT`

Do not extract article text during this step. First store source metadata and deduplicate.

### Step 4: Deduplicate Sources

For each source:

- normalize URL
- remove tracking query parameters
- create `url_hash`
- create normalized lowercase `title_hash`
- check existing `url_hash`
- check same company + same publisher + same date + similar title

Duplicates should be marked as `DUPLICATE` and linked through `duplicate_of`.

### Step 5: Extract Article Text

Only extract from approved or high-confidence source documents.

First extractor:

```text
trafilatura
```

Store:

- clean text
- word count
- extractor name
- extraction status
- extraction error

If extraction fails, leave the source in the database with `EXTRACTION_FAILED`; do not delete it.

### Step 6: Extract Business Events

The event extractor should request structured JSON, not summaries.

Prompt shape:

```text
Extract business strategy events from this article.
Return only valid JSON.

Fields:
- company
- event_date
- event_type
- lifecycle_stage
- before_state
- after_state
- trigger
- decision
- outcome
- evidence_text
- confidence_score

Rules:
- Use only information supported by the article text.
- If a field is unknown, return null.
- evidence_text must be a short excerpt.
- confidence_score must be between 0 and 1.
```

Store the raw JSON in `raw_extraction_json` for auditability.

### Step 7: Cluster Into Strategic Turns

Initial rule-based clustering:

- same company
- same event type or compatible event type
- event dates within 30 to 90 days
- similar decision text
- overlapping source titles

Later clustering:

- embeddings for title, decision, before state, after state, and evidence
- vector search
- reviewer-assisted merge suggestions

### Step 8: Admin Review

Admin reviews:

- source documents
- extraction quality
- extracted business events
- generated strategic turns

Only approved strategic turns should be shown in the future Angular product.

## Django Admin Configuration

### Company Admin

Display columns:

- name
- industry
- country
- wikidata_id
- sec_cik
- is_active
- updated_at

Search:

- name
- aliases
- wikidata_id
- sec_cik

Filters:

- industry
- country
- is_active

Actions:

- resolve selected companies from Wikidata
- run full ingestion for selected companies

### SourceDocument Admin

Display columns:

- title
- company
- publisher
- published_date
- source_api
- status
- language

Search:

- title
- url
- canonical_url
- publisher
- snippet

Filters:

- company
- source_api
- status
- publisher
- language
- published_date

Actions:

- approve selected sources
- ignore selected sources
- run extraction for selected sources
- recalculate hashes

### ArticleExtraction Admin

Display columns:

- source document
- extraction_status
- word_count
- extractor_name
- updated_at

Search:

- source document title
- clean_text
- extraction_error

Filters:

- extraction_status
- extractor_name
- word_count

### BusinessEvent Admin

Display columns:

- company
- event_type
- event_date
- lifecycle_stage
- confidence_score
- review_status

Search:

- before_state
- after_state
- trigger
- decision
- outcome
- evidence_text

Filters:

- company
- event_type
- lifecycle_stage
- review_status
- event_date

Actions:

- approve selected events
- reject selected events
- create strategic turn from selected events

### StrategicTurn Admin

Display columns:

- title
- company
- turn_type
- start_date
- confidence_score
- review_status
- is_published

Search:

- title
- summary
- before_state
- after_state
- trigger
- decision
- outcome
- founder_lesson

Filters:

- company
- turn_type
- lifecycle_stage
- review_status
- is_published
- start_date

Actions:

- approve selected turns
- publish selected turns
- unpublish selected turns
- merge selected turns

### IngestionJob Admin

Display columns:

- id
- job_type
- company
- source
- status
- started_at
- finished_at
- sources_inserted
- articles_extracted
- events_extracted
- turns_created

Search:

- query
- error_message

Filters:

- job_type
- source
- status
- company
- started_at

Actions:

- retry failed jobs
- cancel pending jobs

## First Build Milestones

### Milestone 1: Project Foundation

- Create Django project.
- Connect to PostgreSQL using database `business`, user `the_dj`, schema `infodj`.
- Add `.env.example`.
- Add core apps: `companies`, `ingestion`, `curation`.
- Add initial models and migrations.
- Register admin screens.

Acceptance:

- Django admin loads.
- Admin user can log in.
- Database tables are created in schema `infodj`.

### Milestone 2: Manual Netflix Admin Data

- Add Netflix company record.
- Add a few manually created source documents.
- Add a manually curated strategic turn.

Acceptance:

- Admin can display Netflix timeline records from structured DB rows.

### Milestone 3: Wikidata Resolver

- Add service to search Wikidata by company name.
- Save Netflix metadata.
- Add admin action to resolve company metadata.

Acceptance:

- Admin action populates Netflix Wikidata fields.

### Milestone 4: GDELT Collector

- Add GDELT client.
- Generate Netflix query set.
- Store source documents.
- Deduplicate by URL and title hash.

Acceptance:

- Running a Netflix ingestion job inserts source documents into the database.
- Duplicate articles are skipped or marked as duplicates.

### Milestone 5: Article Extraction

- Add `trafilatura`.
- Extract clean text from approved source documents.
- Store extraction status and word count.

Acceptance:

- Admin can inspect extracted article text quality.

### Milestone 6: Business Event Extraction

- Add structured JSON extraction.
- Store events as `BusinessEvent` rows.
- Keep raw JSON for review.

Acceptance:

- Netflix source documents produce editable business-event rows.

### Milestone 7: Strategic Turn Curation

- Add rule-based clustering.
- Add admin action to create strategic turns from selected events.
- Attach sources through `StrategicTurnSource`.

Acceptance:

- Admin can approve a Netflix strategic turn with traceable source evidence.

## API Design For Future FastAPI And Angular

Django Admin is the first interface, but the data model should support these future endpoints:

```text
GET /api/companies
GET /api/companies/{slug}
GET /api/companies/{slug}/sources
GET /api/companies/{slug}/events
GET /api/companies/{slug}/strategic-turns
POST /api/ingestion/company
GET /api/ingestion/jobs/{id}
POST /api/curation/strategic-turns/{id}/approve
POST /api/curation/strategic-turns/{id}/publish
```

Angular admin screens later:

- Company list
- Company detail
- Ingestion job monitor
- Source review table
- Article extraction review
- Business event review
- Strategic turn timeline
- Strategic turn editor

## Risk Notes

### Source Legality And Terms

The system should prefer public APIs and metadata-first ingestion. It should avoid storing or displaying full copyrighted article content as product content.

Store:

- metadata
- source links
- short evidence excerpts
- extracted structured facts

Avoid:

- republishing full article bodies
- bypassing paywalls
- aggressive crawling
- ignoring robots.txt for direct crawlers

### Data Quality

LLM extraction will produce mistakes. Admin review is required before publishing strategic turns.

Every strategic turn must preserve source traceability.

### Scalability

The first MVP should avoid Common Crawl WARC processing. Add it only after the GDELT and Wikidata workflow produces useful structured Netflix records.

## Immediate Next Step

Implement the Django project foundation, then create the database once PostgreSQL is available.

If native PostgreSQL is installed later, run:

```bash
sudo service postgresql start
sudo -u postgres psql
```

Then execute the SQL from the PostgreSQL setup section.

If Docker Desktop WSL integration is enabled later, a local container can be used instead:

```bash
docker run --name infodj-postgres \
  -e POSTGRES_DB=business \
  -e POSTGRES_USER=the_dj \
  -e POSTGRES_PASSWORD=change_this_password \
  -p 5432:5432 \
  -d postgres:16
```

After the database is available, run Django migrations and create the first superuser.
