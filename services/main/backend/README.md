# InfoDJ Main Backend

Django skeleton for the `infodj-main` product backend.

## Intended Apps

- `accounts`: users, teams, roles, and permissions.
- `review`: review assignments and approve/reject/merge/publish workflows.
- `timelines`: published company timelines and strategic-turn APIs.
- `search`: search and filter APIs.

## Local Shape

```text
backend/
  manage.py
  requirements.txt
  config/
    settings.py
    urls.py
    asgi.py
    wsgi.py
  apps/
    accounts/
    review/
    timelines/
    search/
```

## Notes

- This backend should expose public product routes under `/api/app/`.
- Ingestion data should be read through `INGESTION_API_URL`.
- Do not write directly into ingestion-owned tables.
- Dependencies are listed as placeholders only; they have not been installed by this scaffold.
