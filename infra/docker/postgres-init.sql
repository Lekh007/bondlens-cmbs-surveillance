-- Runs once against the vichara database on first container init.
-- pgcrypto is enabled for gen_random_uuid() in case a later table needs it;
-- the current schema (Task 9) uses integer identity PKs and doesn't.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
