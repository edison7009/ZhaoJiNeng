---
description: Refresh the lobster-agents leaderboard (ranking.html) from the GitHub API
---

# Sync Lobster Ranking Data

## One-shot command

```bash
python sync.py ranking
```

Single-stage wrapper around `ranking_sync.py`. See
[MAINTAINING.md](../../MAINTAINING.md) for the bigger picture.

## What it does

`ranking_sync.py` pulls current stats for every repo in the `TRACKED` list
at the top of the script using the GitHub REST API, then computes 7-day
deltas by comparing with the most recent snapshot in
`public/ranking_history/` that is at least 6 days old.

Per repo it fetches:

- `GET api.github.com/repos/<owner>/<repo>` → `stargazers_count` etc.
- `GET .../commits?since=<7d-ago>&per_page=1` → pulls `rel="last"` from the
  Link header to count the last-7-days commits cheaply.
- `GET .../stats/contributors` → active contributors in the 7d window
  (GitHub may return 202 while computing; treated as 0 for this run).

### Outputs

| Path | Role |
|---|---|
| `public/ranking_snapshot.json` | Consumed by `ranking.html` at runtime |
| `public/ranking_history/<YYYY-MM-DD>.json` | Archive; next run uses it for 7d deltas |

### Output shape

```json
{
  "updated_at": "2026-04-21T14:21:59+00:00",
  "summary": {
    "leader": { "name": "OpenClaw", "stars": "361,670 stars" },
    "ecosystemStars": { "total": "700,000", "desc": "Across 11 tracked repos" },
    "growth7d": { "value": "+5,000", "percentage": "Stars · +0.7%" },
    "topGrowth": { "name": "Hermes Agent", "desc": "+3.1% over 7 days" }
  },
  "rankings": [
    {
      "rank": 1,
      "name": "OpenClaw",
      "repo": "openclaw/openclaw",
      "language": "TypeScript",
      "status": "",
      "stars7d": "+4,158",
      "stars7dChange": "+1.2%",
      "contribs7d": "125",
      "contribs7dChange": "+21.4%",
      "commits7d": "1,691",
      "commits7dChange": "+29.5%",
      "totalStars": "361,411"
    }
  ],
  "_raw": [ ... ]
}
```

Numbers are pre-formatted strings so the frontend can render them directly.
Missing deltas (e.g. first run before any historical baseline) render as `—`.

## Frontend fallback

`ranking.html` prefers the live snapshot. If the fetch fails or returns
something unexpected, the hardcoded `RANKING_DATA` inside the HTML renders
instead, so the page never breaks.

## Rate limits

| Auth | Rate |
|---|---|
| Anonymous | 60 requests/hour — enough for one run (11 repos × ~3 requests = 33) but tight for repeated debugging |
| With `GITHUB_TOKEN` env var | 5000 requests/hour |

```bash
export GITHUB_TOKEN=ghp_...
python sync.py ranking
```

A fine-grained token with **public repo read-only** scope is enough.

## Adding or removing a tracked project

Edit the `TRACKED` list at the top of `ranking_sync.py`, and keep the
`PROJECT_COLORS`, `PROJECT_DATA`, `PROJECT_ICONS` maps in `ranking.html`
aligned — add local icons under `public/ico/`.

## Commit

```bash
git add public/ranking_snapshot.json public/ranking_history/
git commit -m "data: sync lobster ranking $(date +%F)"
git push origin main
```
