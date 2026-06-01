# Sprint 1 Todo

Sprint 1 builds the first usable product/admin surface on top of the existing ingestion system.

Validated decisions:

```text
Auth: token auth for Sprint 1
Payments/subscriptions: Razorpay test mode
Frontend API access: Angular calls main-backend only
Ingestion data access: main-backend calls ingestion APIs internally
Share price feature: start with model/API/provider interface and tested fixture data, then add real provider
Search implementation: Postgres prefix/trigram autocomplete + Postgres full-text search
Testing rule: actually run backend tests, frontend builds, and curl smoke tests for every feature
Agent rule: use a maximum of 3 implementation agents at a time
```

Do not commit Razorpay secrets. Use environment variables:

```text
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
```

## Branch Plan

Use one feature branch per major slice:

```text
feature/sprint1-auth-razorpay-subscriptions
feature/sprint1-dashboard-search
feature/sprint1-company-stages-recommendations
feature/sprint1-market-price-stage-metrics
feature/sprint1-frontend-shell-profile-footer
```

Implementation and merge order:

```text
1. auth + Razorpay subscriptions
2. dashboard + search
3. company stages + recommendations
4. market price metrics
5. frontend shell/profile/footer integration
```

## Testing Standard

Every branch must include:

```text
Backend Django tests
Curl smoke test script
Frontend build test when Angular files change
Docker runtime verification when endpoints are added
```

Standard verification commands:

```bash
sudo docker compose -f infra/docker-compose.yml up -d gateway ingestion main-backend postgres redis
sudo docker compose -f infra/docker-compose.yml exec main-backend python manage.py test
sudo docker compose -f infra/docker-compose.yml run --rm main-frontend npm run build
```

Smoke scripts should live under:

```text
scripts/smoke/
```

## 1. Signup/Login With Subscription Tiers

Branch:

```text
feature/sprint1-auth-razorpay-subscriptions
```

Backend scope:

```text
Add token auth
Add user signup/login/logout/me APIs
Add UserProfile model
Add subscription tier model/fields
Add Razorpay subscription/order integration service
Add subscription audit/history table
```

Initial tiers:

```text
FREE
PRO
ANALYST
ADMIN
```

Proposed endpoints:

```text
POST /api/app/auth/signup
POST /api/app/auth/login
POST /api/app/auth/logout
GET  /api/app/auth/me
GET  /api/app/subscription
POST /api/app/subscription/checkout
POST /api/app/subscription/verify-payment
POST /api/app/subscription/change
GET  /api/app/subscription/history
```

Razorpay environment variables:

```text
RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET
RAZORPAY_WEBHOOK_SECRET
```

Razorpay implementation notes:

```text
Use test mode first.
Create server-side checkout/order endpoint.
Verify payment signatures server-side.
Store Razorpay order/payment/subscription ids.
Never trust frontend payment success without backend verification.
Do not expose key secret to Angular.
```

Backend tests:

```text
signup creates user and FREE profile
login returns token
me requires token
checkout requires token
verify-payment rejects invalid signature
subscription change writes audit history
invalid tier is rejected
```

Curl smoke test:

```text
scripts/smoke/sprint1_auth_subscription.sh
```

Smoke script should:

```text
create user
login
call /me
call /subscription
attempt checkout
verify invalid payment signature fails
```

## 2. Subscription Profile Upgrade/Downgrade

Branch:

```text
feature/sprint1-auth-razorpay-subscriptions
```

This belongs with auth because subscription state is user-owned.

Backend scope:

```text
Track current tier
Track subscription status
Track provider ids
Track upgrade/downgrade audit history
Expose current subscription state to frontend
```

Subscription statuses:

```text
FREE
PENDING_PAYMENT
ACTIVE
PAST_DUE
CANCELLED
DOWNGRADED
```

Tests:

```text
FREE -> PRO pending checkout
PRO -> FREE downgrade
history includes old tier, new tier, reason, provider
unauthenticated requests rejected
```

## 3. Profile, Email Subscribe/Unsubscribe, Footer About

Branch:

```text
feature/sprint1-frontend-shell-profile-footer
```

Backend scope:

```text
Profile API
Email preference fields
About/system info endpoint
```

Profile fields:

```text
display_name
company_name
role
email_updates_enabled
product_updates_enabled
research_digest_enabled
```

Endpoints:

```text
GET   /api/app/profile
PATCH /api/app/profile
POST  /api/app/profile/email-subscribe
POST  /api/app/profile/email-unsubscribe
GET   /api/app/about
```

Frontend scope:

```text
App shell
Top navigation
Footer with About link
Profile page
Email subscription controls
No emojis or smileys
Professional CSS
```

Tests:

```text
profile get/update requires token
email subscribe/unsubscribe toggles fields
about endpoint returns service/version links
Angular build passes
curl smoke test toggles preferences
```

Smoke script:

```text
scripts/smoke/sprint1_profile_footer.sh
```

## 4. Dashboard With Category Classification And Global English Search

Branch:

```text
feature/sprint1-dashboard-search
```

Backend scope:

```text
Main backend calls ingestion API internally
Dashboard groups companies by category/sector
Search companies, business events, and strategic turns
Return English curated text only
Frontend should not call ingestion service directly
Use Postgres full-text search for submitted search queries
Use Postgres prefix/trigram matching for autocomplete/typeahead
Do not use Redis sorted sets as the primary search index in Sprint 1
```

Endpoints:

```text
GET /api/app/dashboard
GET /api/app/categories
GET /api/app/search?q=netflix&language=en
GET /api/app/search/suggest?q=net&language=en
```

Dashboard response should include:

```text
sector counts
company counts
source/event/turn counts
latest ingestion job summary
top companies by event count
```

Search response should include grouped results:

```text
companies
events
strategic_turns
```

Search implementation:

```text
/api/app/search
  -> Postgres full-text search over curated company/event/turn fields
  -> rank with SearchRank where available
  -> filter to English-facing curated text

/api/app/search/suggest
  -> Postgres prefix search for company names and common fields
  -> trigram similarity for fuzzy suggestions
  -> return compact typeahead results
```

Redis search rule:

```text
Redis can be added later for caching popular queries or suggestions.
Redis should not be the source of truth for search in Sprint 1.
```

Tests:

```text
dashboard returns grouped sectors
search requires q
search defaults to English
search does not expose non-English source rows
search/suggest returns prefix matches
search/suggest returns fuzzy trigram matches where available
main-backend handles ingestion service failures gracefully
```

Smoke script:

```text
scripts/smoke/sprint1_dashboard_search.sh
```

## 5. Bubble-Themed Individual Company Stages

Branch:

```text
feature/sprint1-company-stages-recommendations
```

Backend scope:

```text
Company detail API
Company stage API
Stages derived from strategic turns and business events
Group by lifecycle_stage, event_type, and chronology
```

Endpoints:

```text
GET /api/app/companies/{slug}
GET /api/app/companies/{slug}/stages
```

Stage response shape:

```text
stage_id
stage_label
event_type
start_date
end_date
summary
specific_company_action
source_count
confidence_score
review_status
```

Frontend scope:

```text
Company detail page
Bubble/timeline stage visualization
Category filters
Stage detail drawer/panel
Readable responsive layout
No decorative clutter
```

Tests:

```text
Netflix stages endpoint returns stage list
unknown company returns 404
stages are sorted chronologically
Angular build passes
curl smoke test for Netflix stages
```

Smoke script:

```text
scripts/smoke/sprint1_company_stages.sh
```

## 6. Recommendations From Existing Company Data

Branch:

```text
feature/sprint1-company-stages-recommendations
```

Backend scope:

```text
Rule-based recommendation generator
Use existing business_events and strategic_turns
Return generalized theme plus specific company evidence
```

Endpoint:

```text
GET /api/app/companies/{slug}/recommendations
```

Recommendation response shape:

```text
theme
recommendation
specific_company_action
why_it_matters
stage
event_type
source_event_ids
source_turn_ids
confidence_score
```

Example:

```text
Theme: Expand monetization after usage maturity
Specific detail: Netflix introduced an ad-supported tier after subscription scale matured.
Recommendation: Consider a second revenue model only after core product usage is stable enough to avoid weakening the original offer.
```

Tests:

```text
recommendations include generalized theme
recommendations include specific company action
recommendations reference source events/turns
empty company data returns empty recommendation list, not 500
```

Smoke script:

```text
scripts/smoke/sprint1_recommendations.sh
```

## 7. Share Price At Each Stage

Branch:

```text
feature/sprint1-market-price-stage-metrics
```

Backend scope:

```text
Add market price metric model
Add provider interface
Add fixture/test provider first
Map strategic turn date to nearest market close
Calculate 30/180/365 day return where data exists
```

Model:

```text
CompanyStageMarketMetric
company_slug
ticker
stage_id
stage_date
close_price
currency
return_30d
return_180d
return_365d
provider
status
error_message
```

Endpoints:

```text
GET  /api/app/companies/{slug}/stage-market-metrics
POST /api/app/market-prices/backfill
```

Provider rule:

```text
Start with fixture/provider interface in tests.
Add real provider only after validating source reliability and limits.
Do not block Sprint 1 UI on external finance API instability.
```

Tests:

```text
fixture provider maps prices to stage dates
returns are calculated correctly
missing ticker returns useful status
curl smoke test retrieves metrics for Netflix after fixture backfill
```

Smoke script:

```text
scripts/smoke/sprint1_market_metrics.sh
```

## Frontend Build Expectations

Angular UI should include:

```text
Login/signup page
Subscription page
Dashboard page
Global search
Company list
Company detail stages
Recommendations panel
Profile page
Footer/about
```

Design requirements:

```text
No emojis or smileys
Professional CSS
Responsive layout
Readable dense dashboard
No marketing landing page
No oversized hero section
No decorative bloat
```

Frontend tests for Sprint 1:

```text
npm run build
curl main-backend APIs through Kong
manual browser check at http://localhost:4200
```

## Runtime Verification Checklist

Before a branch is considered done:

```bash
sudo docker compose -f infra/docker-compose.yml up -d \
  gateway ingestion main-backend postgres redis

sudo docker compose -f infra/docker-compose.yml exec main-backend python manage.py migrate
sudo docker compose -f infra/docker-compose.yml exec main-backend python manage.py test

curl http://localhost:8080/api/app/health
curl http://localhost:8080/api/ingestion/health

sudo docker compose -f infra/docker-compose.yml run --rm main-frontend npm run build
```

Run the relevant smoke scripts:

```bash
bash scripts/smoke/sprint1_auth_subscription.sh
bash scripts/smoke/sprint1_profile_footer.sh
bash scripts/smoke/sprint1_dashboard_search.sh
bash scripts/smoke/sprint1_company_stages.sh
bash scripts/smoke/sprint1_recommendations.sh
bash scripts/smoke/sprint1_market_metrics.sh
```

## Notes Before Implementation

Razorpay API work should be checked against official Razorpay documentation before implementation.

The frontend should only call:

```text
/api/app/*
```

It should not call:

```text
/api/ingestion/*
```

The main backend owns product-facing APIs and should call ingestion internally.
