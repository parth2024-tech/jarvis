-- Run this once in Supabase SQL editor.

create extension if not exists "pgcrypto";

create table if not exists deals (
  id uuid primary key default gen_random_uuid(),
  tool_name text not null,
  plan_name text,
  discount_type text,
  value_usd numeric,
  discounted_value text,
  eligibility text,
  claim_url text,
  website_url text,
  expiry_date date,
  verification_status text,
  confidence_score integer,
  source_type text,
  source_url text,
  raw_snippet text,
  region text default 'global',
  first_seen timestamptz not null default now(),
  last_confirmed timestamptz not null default now(),
  last_updated timestamptz not null default now(),
  consecutive_misses integer not null default 0,
  is_active boolean not null default true,
  status text default 'NEW',  -- NEW / UPDATED / EXPIRED / RETURNED / UNCHANGED
  prev_value text,
  unique (tool_name, plan_name)
);

create index if not exists idx_deals_active on deals(is_active);
create index if not exists idx_deals_region on deals(region);
create index if not exists idx_deals_status on deals(status);
create index if not exists idx_deals_value on deals(value_usd desc);

create table if not exists agent_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text default 'running',  -- running / success / failed
  sources_scanned integer default 0,
  candidates_extracted integer default 0,
  deals_verified integer default 0,
  errors jsonb default '[]'::jsonb
);

create index if not exists idx_runs_finished on agent_runs(finished_at desc);
