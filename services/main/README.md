# InfoDJ Main Service

This directory is the initial scaffold for `infodj-main`, the product service described in `docs/service_architecture_format.md`.

The main service owns user-facing product workflows and reads curated ingestion data through APIs. It must not write directly into ingestion-owned tables.

## Layout

```text
services/main/
  backend/     Django product backend skeleton
  frontend/    Angular admin/product UI skeleton
  .env.example Main service environment example
```

## Responsibilities

- Users, teams, roles, and permissions.
- Review assignments and review workflow APIs.
- Published company profile APIs.
- Search and filter APIs.
- Optional local projections of curated ingestion data.

## Integration Boundary

The main service should read ingestion data through the gateway:

```text
main service -> gateway -> ingestion internal API -> ingestion DB
```

Initial expected ingestion API base:

```text
INGESTION_API_URL=http://gateway/api/ingestion
```

## Status

This is a lightweight scaffold only. It intentionally does not include installed dependencies, generated framework output, migrations, Docker build files, or production settings.
