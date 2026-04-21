---
description: Refresh the LLM leaderboard (models.html) from openrouter.ai/rankings
---

# Sync LLM Leaderboard

## One-shot command

```bash
python sync.py models
```

Single-stage wrapper around `sync_openrouter_models.py`. See
[MAINTAINING.md](../../MAINTAINING.md) for the bigger picture.

## What it does

`sync_openrouter_models.py`:

1. Fetches `https://openrouter.ai/rankings?view={day,week,month}` and extracts
   the inline `rankingData` array from the Next.js RSC payload via regex.
2. Joins with `https://openrouter.ai/api/v1/models` for display names,
   descriptions, context length, pricing.
3. Scrapes author favicon URLs from both the rankings pages and the homepage.
4. Downloads every author icon into `public/models_icons/` (idempotent,
   keyed by author slug). Only **local** relative paths are written to the
   JSON — the runtime has zero outbound URLs.
5. Writes `public/models_ranking.json` with 20 ranked rows per period.

## Output shape

```json
{
  "updated_at": "2026-04-21T13:05:10+00:00",
  "top_n": 20,
  "week": [
    {
      "rank": 1,
      "permaslug": "anthropic/claude-4.6-sonnet-20260217",
      "variant": "standard",
      "author": "anthropic",
      "author_icon": "./public/models_icons/anthropic.svg",
      "short_name": "Claude Sonnet 4.6",
      "description": "...",
      "context_length": 200000,
      "pricing_prompt": "0.000003",
      "pricing_completion": "0.000015",
      "total_tokens": 1393050756216,
      "request_count": 41155663,
      "change": 0.15
    }
  ],
  "day":   [ ... ],
  "month": [ ... ]
}
```

`change` is a float delta (0.15 = +15%). `null` means "new entry".

## Commit

```bash
git add public/models_ranking.json public/models_icons/
git commit -m "data: sync LLM leaderboard $(date +%F)"
git push origin main
```

## Troubleshooting

- **`rankingData not found in HTML`** — OpenRouter changed their frontend.
  Fix the regex in `extract_ranking_data()`. The data source itself (the
  rankings page) is stable.
- **Missing author icon** — the sync writes `author_icon: ""` and the
  frontend falls back to a letter-in-a-colored-circle. If you want a proper
  icon, it usually means OpenRouter no longer renders a `Favicon for <slug>`
  `<img>` on either the rankings page or the homepage for that author.
  Extend `extract_author_icons()` to look in more pages.
