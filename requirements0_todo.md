# Requirements 0 Todo

This file breaks the first InfoDJ implementation into phases that can be executed by a maximum of three agents.

Primary goal:

```text
Build a Django Admin MVP that can create Netflix as a company, collect source metadata from Wikidata and GDELT, store it in PostgreSQL-ready models, and prepare the path for event extraction and future FastAPI + Angular.
```

## Agent Limits

Use no more than three implementation agents at a time.

### Agent 1: Foundation And Database

Owns:

- Django project setup
- settings
- environment files
- database configuration
- base models
- migrations
- local run commands

Avoids:

- GDELT/Wikidata client logic
- admin polish beyond basic model registration
- future Angular/FastAPI implementation

### Agent 2: Ingestion Services

Owns:

- Wikidata client
- GDELT client
- Netflix query generator
- URL normalization and hashing
- source deduplication helpers
- ingestion task/service orchestration

Avoids:

- changing Django settings unless required
- large admin UI changes
- database schema changes without coordinating with Agent 1

### Agent 3: Admin And Curation

Owns:

- Django Admin configuration
- admin actions
- review statuses
- manual Netflix seed workflow
- strategic turn curation screens
- operator usability inside Django Admin

Avoids:

- source API client internals
- database connection setup
- changing service interfaces without coordinating with Agent 2

## Phase 0: Repository Hygiene

Status: completed

Owner: Agent 1

Tasks:

- [x] Confirm repository root is `/home/famei/InfoDJ`.
- [x] Confirm `origin` points to the intended GitHub repository.
- [x] Keep secrets out of committed files.
- [x] Add `.gitignore` for Python, Django, virtualenv, local DB files, logs, and `.env`.
- [x] Add `.env.example` with placeholder values only.
- [x] Keep `implementation.md` and this todo file tracked.

Acceptance:

- `git status --short` only shows intentional project files.
- No GitHub token, database password, or API key is committed.

## Phase 1: Django Project Foundation

Status: completed

Owner: Agent 1

Tasks:

- [x] Create Python virtual environment instructions.
- [x] Add `requirements.txt`.
- [x] Install/add baseline dependencies:
  - Django
  - psycopg
  - python-dotenv or django-environ
  - requests or httpx
  - celery
  - redis
  - trafilatura
  - readability-lxml
  - beautifulsoup4
- [x] Create Django project under the repo root.
- [x] Create apps:
  - `companies`
  - `ingestion`
  - `curation`
- [x] Configure settings for:
  - PostgreSQL
  - `infodj` schema search path
  - installed apps
  - static files
  - timezone
  - local development debug mode
- [x] Add `config/celery.py`.
- [x] Add basic URL routing for admin.

Acceptance:

- `python manage.py check` passes when dependencies are installed.
- Django admin route exists.
- Project can later connect to database `business` as user `the_dj`.

## Phase 2: PostgreSQL Readiness

Status: completed

Owner: Agent 1

Tasks:

- [x] Document local PostgreSQL status.
- [x] Add SQL setup script for:
  - database: `business`
  - user: `the_dj`
  - schema: `infodj`
- [x] Add Django database config using environment variables.
- [x] Confirm migrations target schema `infodj`.
- [x] Add a fallback note for Docker Postgres if WSL integration is enabled.

Acceptance:

- Setup instructions are executable once PostgreSQL is available.
- No committed password is real.
- Schema search path is explicitly configured.

## Phase 3: Core Models

Status: completed

Owner: Agent 1

Tasks:

- [x] Implement `Company`.
- [x] Implement `SourceDocument`.
- [x] Implement `ArticleExtraction`.
- [x] Implement `BusinessEvent`.
- [x] Implement `StrategicTurn`.
- [x] Implement `StrategicTurnSource`.
- [x] Implement `IngestionJob`.
- [x] Add status/type choices for jobs, sources, extraction, events, and strategic turns.
- [x] Add timestamps.
- [x] Add indexes and uniqueness constraints.
- [x] Create migrations.

Acceptance:

- Models match the fields in `implementation.md`.
- Migrations are generated.
- Models can support Netflix ingestion without schema changes.

## Phase 4: Basic Django Admin

Status: completed

Owner: Agent 3

Tasks:

- [x] Register all models in Django Admin.
- [x] Add list displays for each model.
- [x] Add filters for company, source API, status, event type, review status, and dates.
- [x] Add search fields for names, URLs, titles, decision text, evidence text, and errors.
- [x] Add read-only fields for hashes and timestamps.
- [x] Add inline sources for strategic turns where useful.

Acceptance:

- Admin user can inspect companies, sources, jobs, events, and strategic turns.
- Admin pages are usable without custom frontend code.

## Phase 5: Manual Netflix Seed

Status: completed

Owner: Agent 3

Tasks:

- [x] Add a Django management command or admin action to create Netflix manually.
- [x] Seed:
  - name: `Netflix`
  - slug: `netflix`
  - aliases: `Netflix`, `Netflix Inc.`, `Netflix.com`
  - country: `United States`
  - Wikidata ID: `Q907311`
  - website: `https://www.netflix.com`
- [x] Add one manually curated sample strategic turn for local review.
- [x] Add one or more sample source documents if no live ingestion has run yet.

Acceptance:

- Admin can show a Netflix company page with related records.
- The project demonstrates the expected final data shape before automation is complete.

## Phase 6: Wikidata Resolver

Status: completed

Owner: Agent 2

Tasks:

- [x] Add `wikidata_client.py`.
- [x] Implement company search using `wbsearchentities`.
- [x] Implement entity detail lookup using `wbgetentities`.
- [x] Normalize useful fields:
  - Wikidata ID
  - label/name
  - description
  - aliases
  - website where available
  - country where available
  - industry where available
- [x] Add service function to update a `Company`.
- [x] Add admin action to resolve selected companies from Wikidata.
- [x] Add ingestion job tracking for metadata sync.

Acceptance:

- Running the resolver for Netflix updates the company record.
- Failures are captured in `IngestionJob.error_message`.

## Phase 7: Netflix Query Generator

Status: completed

Owner: Agent 2

Tasks:

- [x] Add `query_generator.py`.
- [x] Generate default Netflix business-history queries:
  - `Netflix DVD rental business model`
  - `Netflix streaming launch`
  - `Netflix subscription pricing change`
  - `Netflix original content strategy`
  - `Netflix international expansion`
  - `Netflix advertising tier launch`
  - `Netflix password sharing crackdown`
  - `Netflix subscriber growth decline response`
  - `Netflix partnership strategy`
  - `Netflix acquisition strategy`
- [x] Make the generator accept company aliases.
- [x] Keep query definitions easy to edit.

Acceptance:

- Netflix produces a predictable query list.
- Query generation is independent from GDELT.

## Phase 8: GDELT Source Collector

Status: completed

Owner: Agent 2

Tasks:

- [x] Add `gdelt_client.py`.
- [x] Query GDELT DOC 2.0 API.
- [x] Use `mode=ArtList`.
- [x] Use JSON response format.
- [x] Limit first run to a safe number of records per query.
- [x] Normalize returned source metadata:
  - title
  - URL
  - publisher/domain
  - published date
  - snippet if available
  - language
  - source API
- [x] Store results as `SourceDocument`.
- [x] Track job counters.

Acceptance:

- Running source discovery for Netflix creates `SourceDocument` rows.
- The collector stores metadata first and does not fetch full article bodies yet.

## Phase 9: Deduplication

Status: completed

Owner: Agent 2

Tasks:

- [x] Add URL normalization.
- [x] Remove common tracking params.
- [x] Create stable `url_hash`.
- [x] Create normalized `title_hash`.
- [x] Detect exact URL duplicates.
- [x] Detect basic same-company same-publisher same-date title duplicates.
- [x] Mark duplicates instead of deleting them.

Acceptance:

- Re-running Netflix source discovery does not create repeated source rows.
- Duplicates can be reviewed in admin.

## Phase 10: Admin Actions For Ingestion

Status: completed

Owner: Agent 3

Tasks:

- [x] Add admin action: run full Netflix source discovery.
- [x] Add admin action: resolve selected companies through Wikidata.
- [x] Add admin action: approve selected source documents.
- [x] Add admin action: ignore selected source documents.
- [x] Add admin action: recalculate source hashes.
- [x] Show job status and counters clearly.

Acceptance:

- An admin user can trigger the Netflix metadata and GDELT workflow without shell access.
- Failed jobs are inspectable in admin.

## Phase 11: Article Extraction

Status: pending

Owner: Agent 2

Tasks:

- [ ] Add `article_extractor.py`.
- [ ] Use `trafilatura` first.
- [ ] Add `readability-lxml` or BeautifulSoup fallback later.
- [ ] Extract only approved or selected sources.
- [ ] Store:
  - clean text
  - word count
  - extractor name
  - extraction status
  - extraction error
- [ ] Never delete source records when extraction fails.

Acceptance:

- Selected Netflix source documents can produce `ArticleExtraction` rows.
- Admin can inspect extraction quality.

## Phase 12: Event Extraction Contract

Status: pending

Owner: Agent 2

Tasks:

- [ ] Add `event_extractor.py`.
- [ ] Define strict JSON output schema.
- [ ] Add validation before creating `BusinessEvent`.
- [ ] Store raw extraction JSON.
- [ ] Add support for unknown/null fields.
- [ ] Keep the LLM provider behind a small interface for future replacement.

Acceptance:

- Event extraction code can be implemented without changing the database model.
- Bad JSON does not crash the ingestion pipeline silently.

## Phase 13: Business Event Admin Review

Status: pending

Owner: Agent 3

Tasks:

- [ ] Add strong admin list filters for `BusinessEvent`.
- [ ] Add review statuses:
  - `DRAFT`
  - `NEEDS_REVIEW`
  - `APPROVED`
  - `REJECTED`
  - `MERGED`
- [ ] Add actions:
  - approve selected events
  - reject selected events
  - create strategic turn from selected events
- [ ] Show source document and evidence traceability.

Acceptance:

- Admin can review and correct extracted Netflix events.
- Approved events can become strategic turns.

## Phase 14: Strategic Turn Curation

Status: pending

Owner: Agent 3

Tasks:

- [ ] Add strategic turn admin editor.
- [ ] Add `StrategicTurnSource` inline.
- [ ] Add actions:
  - approve selected turns
  - publish selected turns
  - unpublish selected turns
  - merge selected turns
- [ ] Add fields for:
  - summary
  - before state
  - after state
  - trigger
  - decision
  - outcome
  - founder lesson
  - confidence score

Acceptance:

- Admin can create an approved Netflix strategic turn backed by one or more source documents.

## Phase 15: Rule-Based Clustering

Status: pending

Owner: Agent 2

Tasks:

- [ ] Add `event_clusterer.py`.
- [ ] Group candidate events by:
  - same company
  - compatible event type
  - dates within 30 to 90 days
  - similar decision text
  - overlapping source titles
- [ ] Produce suggested strategic turns, not auto-published turns.
- [ ] Preserve source/event traceability.

Acceptance:

- Similar Netflix events can be grouped into a draft strategic turn.
- Admin still makes the final approval decision.

## Phase 16: Smoke Tests

Status: pending

Owner: Agent 1

Tasks:

- [ ] Add model tests for core constraints.
- [ ] Add service tests for URL normalization and hashing.
- [ ] Add query generator tests.
- [ ] Add basic admin registration smoke checks where practical.
- [ ] Add command or documented smoke path:
  - create Netflix
  - resolve metadata
  - collect GDELT sources
  - review sources in admin

Acceptance:

- Tests cover the highest-risk early behavior.
- The Netflix path is reproducible.

## Phase 17: Future FastAPI And Angular Prep

Status: pending

Owner: Agent 1

Tasks:

- [ ] Keep ingestion logic out of Django Admin classes.
- [ ] Keep source clients framework-light.
- [ ] Keep Pydantic-compatible schemas in mind for extraction contracts.
- [ ] Document future API endpoints:
  - companies
  - sources
  - events
  - strategic turns
  - ingestion jobs
- [ ] Do not build Angular yet.
- [ ] Do not build FastAPI yet.

Acceptance:

- The Django MVP can later expose the same data through FastAPI without rewriting ingestion logic.

## First Implementation Order

Execute in this order:

1. Phase 0: Repository Hygiene
2. Phase 1: Django Project Foundation
3. Phase 2: PostgreSQL Readiness
4. Phase 3: Core Models
5. Phase 4: Basic Django Admin
6. Phase 5: Manual Netflix Seed
7. Phase 6: Wikidata Resolver
8. Phase 7: Netflix Query Generator
9. Phase 8: GDELT Source Collector
10. Phase 9: Deduplication
11. Phase 10: Admin Actions For Ingestion
12. Phase 11: Article Extraction
13. Phase 12: Event Extraction Contract
14. Phase 13: Business Event Admin Review
15. Phase 14: Strategic Turn Curation
16. Phase 15: Rule-Based Clustering
17. Phase 16: Smoke Tests
18. Phase 17: Future FastAPI And Angular Prep

## First Usable Demo Target

The first demo is not the final product UI.

Demo target:

```text
Open Django Admin
  -> see Netflix company
  -> run Wikidata metadata sync
  -> run GDELT source discovery
  -> inspect collected source documents
  -> approve useful sources
  -> manually create or review a strategic turn
```

## Do Not Build Yet

- Angular frontend
- FastAPI service
- payment system
- user accounts
- public landing page
- Common Crawl ingestion
- full web crawler
- graph visualization
- multi-company automation at scale
- mobile app

## Definition Of Done For Requirements 0

Requirements 0 is done when:

- Django project exists.
- PostgreSQL-ready models and migrations exist.
- Django Admin exposes the core data.
- Netflix can be created.
- Wikidata metadata sync can run.
- GDELT source discovery can collect source metadata.
- Duplicate source records are handled.
- Admin can inspect and approve sources.
- At least one Netflix strategic turn can be curated and linked to sources.
