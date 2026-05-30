# infoDJ
all info on business and what changed

## Services

```text
services/
  ingestion/   Django ingestion and curation service
  gateway/     Kong API gateway scaffold
  main/        Angular + Django product service scaffold
```

The ingestion service is the current working backend:

```bash
.venv/bin/python services/ingestion/manage.py check
.venv/bin/python services/ingestion/manage.py daily_company_update --skip-gdelt
```
