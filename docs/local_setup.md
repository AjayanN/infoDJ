# Local Setup

## Python

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py check
```

## PostgreSQL

This project is configured for:

- database: `business`
- user: `the_dj`
- schema: `infodj`

When PostgreSQL is available, copy `.env.example` to `.env`, replace placeholder secrets locally, and run:

```bash
psql -U postgres -f docs/postgres_setup.sql
python manage.py migrate
```

Django sets the PostgreSQL search path through `DJANGO_DB_SCHEMA`, defaulting to `infodj`, with `public` second.

## Current Local Status

Native PostgreSQL 16 is installed in this environment. The local database, user, and schema have been created for development:

- database: `business`
- user: `the_dj`
- schema: `infodj`

The local `.env` file is gitignored and should contain the real development password. Do not commit `.env`.

Docker fallback once WSL integration is available:

```bash
docker run --name infodj-postgres \
  -e POSTGRES_DB=business \
  -e POSTGRES_USER=the_dj \
  -e POSTGRES_PASSWORD=change_this_password \
  -p 5432:5432 \
  -d postgres:16
```

Then create the `infodj` schema inside the container:

```bash
psql postgres://the_dj:change_this_password@localhost:5432/business \
  -c "CREATE SCHEMA IF NOT EXISTS infodj AUTHORIZATION the_dj;"
```
