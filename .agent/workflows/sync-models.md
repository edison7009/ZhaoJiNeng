---
description: Refresh the LLM capability leaderboard (models.html) from the Artificial Analysis API
---

# Sync LLM Leaderboard

## One-shot command

```bash
# needs a free Artificial Analysis API key:
export AA_API_KEY=<key>           # PowerShell: $env:AA_API_KEY="<key>"
python sync.py models
```

Single-stage wrapper around `sync_artificialanalysis_models.py`. See
[MAINTAINING.md](../../MAINTAINING.md) for the bigger picture.

## What it does

`sync_artificialanalysis_models.py`:

1. `GET https://artificialanalysis.ai/api/v2/data/llms/models` with header
   `x-api-key: <AA_API_KEY>` — a documented, versioned REST API (it does not
   move under us the way OpenRouter's internal Server Action hash did).
2. Builds three Top-20 capability rankings from each model's `evaluations`:
   `intelligence` (Intelligence Index), `coding` (Coding Index), `math`
   (Math Index). Each entry also carries the other two indices plus blended
   price and output speed.
3. Downloads every creator icon into `public/models_icons/` (idempotent,
   keyed by creator slug). Only **local** relative paths are written to the
   JSON — the runtime has zero outbound URLs.
4. Writes `public/models_ranking.json`.

## Output shape

```json
{
  "updated_at": "2026-06-04T06:00:00+00:00",
  "top_n": 20,
  "source": "artificialanalysis.ai",
  "intelligence": [
    {
      "rank": 1,
      "model_id": "claude-opus-4.8",
      "name": "Claude Opus 4.8",
      "short_name": "Claude Opus 4.8",
      "author": "anthropic",
      "author_name": "Anthropic",
      "author_icon": "./public/models_icons/anthropic.png",
      "score": 73.1,
      "intelligence": 73.1,
      "coding": 71.2,
      "math": 88.0,
      "price_blended": 15.0,
      "output_speed": 82.0
    }
  ],
  "coding": [ ... ],
  "math":   [ ... ]
}
```

`score` is the index for the active view; the frontend shows it big, with
`price_blended` ($/1M blended tokens) and `output_speed` (tok/s) as the
secondary stat.

## Commit

```bash
git add public/models_ranking.json public/models_icons/
git commit -m "data: sync LLM leaderboard $(date +%F)"
git push origin main
```

## Troubleshooting

- **`AA_API_KEY is not set` / HTTP 401** — the key is missing or invalid.
  Check the env var locally, or the repo secret `AA_API_KEY` in GitHub
  Actions. Get a free key at https://artificialanalysis.ai/.
- **Want a different ranking dimension** — edit the `VIEWS` map at the top of
  `sync_artificialanalysis_models.py`; each value is a field name inside the
  API's `evaluations` object (e.g. `artificial_analysis_math_index`).
- **Missing creator icon** — the sync writes `author_icon: ""` and the
  frontend falls back to a letter-in-a-colored-circle. Add the creator's
  homepage to `CREATOR_ICON_HOMEPAGES` for a proper favicon.
