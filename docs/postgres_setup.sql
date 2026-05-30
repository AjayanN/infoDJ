-- Run as a PostgreSQL superuser or another role allowed to create roles/databases.
-- Replace the placeholder password before running locally. Do not commit real secrets.

CREATE USER the_dj WITH PASSWORD 'change_this_password';
CREATE DATABASE business OWNER the_dj;

\connect business

CREATE SCHEMA IF NOT EXISTS infodj AUTHORIZATION the_dj;
ALTER ROLE the_dj SET search_path TO infodj, public;
GRANT ALL PRIVILEGES ON DATABASE business TO the_dj;
GRANT ALL ON SCHEMA infodj TO the_dj;
