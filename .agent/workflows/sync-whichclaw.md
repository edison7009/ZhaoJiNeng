---
description: Aggregate the English site (whichclaw.com) from awesome-claude-skills GitHub lists
---

# Sync WhichClaw (English site)

## One-shot command

```bash
python sync.py whichclaw
```

Single-stage wrapper around `sync_whichclaw.py`. See
[MAINTAINING.md](../../MAINTAINING.md) for the bigger picture.

⚠️ This stage *mirrors* `public/models_ranking.json` and `public/ranking_snapshot.json`
into `whichclaw/public/`, so always run `python sync.py models` and
`python sync.py ranking` **before** this stage if you want the English site to
show fresh leaderboard data.

## What it does

`sync_whichclaw.py`:

1. Fetches `README.md` from each repo in `AWESOME_REPOS` via
   `raw.githubusercontent.com` (anonymous, no rate limits in practice):
   - `ComposioHQ/awesome-claude-skills`
   - `hesreallyhim/awesome-claude-code`
   - `sickn33/antigravity-awesome-skills`
   - `VoltAgent/awesome-agent-skills`
   - `travisvn/awesome-claude-skills`
   - `BehiSecc/awesome-claude-skills`
2. Parses markdown list items of the form `- [name](url) — description`, tagging
   each row with the nearest preceding heading as its `category`.
3. Dedupes by canonical URL (GitHub `owner/repo` normalized). Each skill
   remembers which awesome lists it came from in a `sources[]` array; more
   sources = higher `score`, which drives the homepage ranking.
4. Writes `whichclaw/public/skills.json` with the same `{total, featured, skills}`
   shape the Chinese site uses, so the frontend rendering code stays similar.
5. Writes `whichclaw/public/featured.json` (top 50 full objects) and
   `whichclaw/public/skills_pages/<N>.json` (50/page, for progressive hydration).
6. Mirrors shared leaderboard data and brand assets into `whichclaw/public/`
   and `whichclaw/` so the English site is self-contained and deployable
   from the `whichclaw/` directory directly.

## Output shape

```json
{
  "total": 325,
  "featured": ["slug-1", "slug-2", "..."],
  "skills": [
    {
      "slug": "example-skill",
      "name": "Example Skill",
      "description": "Does X when Y happens",
      "description_zh": "",
      "homepage": "https://github.com/owner/repo",
      "tags": ["Category"],
      "category": "Category",
      "ownerName": "owner",
      "sources": ["ComposioHQ/awesome-claude-skills", "travisvn/awesome-claude-skills"],
      "score": 1100,
      "downloads": 0, "stars": 0, "installs": 0,
      "version": "", "updated_at": 0
    }
  ]
}
```

`downloads`/`stars`/`installs` are zero because markdown lists don't carry that
data. If you want real GitHub stars, extend `sync_whichclaw.py` to hit
`api.github.com/repos/{owner}/{repo}` for each canonical URL — but respect rate
limits (60/hr anon, 5000/hr with `GITHUB_TOKEN`).

## Adding a new awesome list

Edit the `AWESOME_REPOS` list at the top of `sync_whichclaw.py`:

```python
AWESOME_REPOS = [
    ("ComposioHQ/awesome-claude-skills", "master"),
    ...
    ("newuser/awesome-new-list",         "main"),  # <-- append here
]
```

Earlier entries win when the same URL appears in multiple lists (that's the
order of trust — put the biggest / most curated list first).

## Commit

```bash
git add whichclaw/public whichclaw/*.html whichclaw/*.png
git commit -m "data: sync whichclaw $(date +%F)"
git push origin main
```

The whichclaw Cloudflare Pages project picks up the push and redeploys.
