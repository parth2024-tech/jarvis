# AI Deal Agent

Daily autonomous agent that hunts AI tool deals, credits, and grants across 30+ sources, verifies them with live URL checks and LLM grounding, and delivers a curated digest by email + instant Telegram alerts for high-value finds.

## Architecture (10 Layers)

1. **Trigger & Health** — GitHub Actions cron @ 08:00 UTC + watchdog @ 09:00 UTC
2. **Intelligence Sources** — 6 categories, 30+ sources (official pages, partners, search, community, newsletters, Discord)
3. **Anti-Bot Bypass** — Firecrawl API for JS-rendered / Cloudflare-protected pages
4. **Dedup** — SHA-256 + fuzzy URL/text matching before LLM
5. **LLM Pass 1** — Claude Sonnet candidate extraction (GPT-4o-mini fallback)
6. **Live URL Verifier** — HTTP HEAD checks kill hallucinated/dead URLs
7. **LLM Pass 2** — Source-grounded confidence scoring (1-10) + status
8. **Postgres + Change Detector** — Supabase; NEW / UPDATED / EXPIRED / RETURNED
9. **Email Composer** — HTML digest + CSV attachments
10. **Dual Delivery** — SendGrid email + instant Telegram alert for $500+ verified deals

## Quick Start

```bash
cd ai-deal-agent
pip install -r requirements.txt
cp .env.example .env   # fill in secrets
python agent.py
```

For production: push to GitHub, add all secrets in repo Settings → Secrets, the workflows in `.github/workflows/` will run automatically.

## Secrets

See `.env.example` for the full list. All are required except `DISCORD_BOT_TOKEN` (optional, for Discord monitoring) and `OPENAI_API_KEY` (only used as Claude fallback).

## Supabase Setup

Run `modules/storage/schema.sql` against your Supabase project to create the `deals` and `agent_runs` tables.

## Cost

~$13–17/month total. One captured $500+ deal pays for 30+ months.

## File Layout

See the directory tree — every layer maps to a module under `modules/`.
