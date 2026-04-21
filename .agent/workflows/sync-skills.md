---
description: Refresh skills.json, public/featured.json, and public/skills_pages/*.json from SkillHub
---

# Sync Skills Data

## One-shot command

```bash
python sync.py skills
```

That runs `scratch_sync.py` then `generate_pages.py`. See
[MAINTAINING.md](../../MAINTAINING.md) for the unified entry.

## What each script does

1. `scratch_sync.py`
   - `GET https://lightmake.site/api/skills/top` → `public/featured.json` (50 full skill objects)
   - `GET https://lightmake.site/api/skills?page=N&size=20` (≈685 pages, concurrency 50) → `skills.json`
   - Required headers: `Referer: https://skillhub.tencent.com/`, `Origin: https://skillhub.tencent.com`

2. `generate_pages.py`
   - Reads `skills.json`
   - Sorts by `(stars, downloads)` descending
   - Writes `public/skills_pages/1.json` .. `public/skills_pages/<N>.json`, 50 items per page
   - Frontend (`all.html`) loads page 1 for first paint, hydrates the rest in the background

## Skill object schema

```json
{
  "slug": "skill-name",
  "name": "Skill Name",
  "description": "English description",
  "description_zh": "中文描述",
  "version": "1.0.0",
  "homepage": "https://clawhub.ai/skill-name",
  "tags": [],
  "downloads": 1000,
  "stars": 50,
  "installs": 100,
  "score": 12345.6,
  "category": "ai-intelligence",
  "ownerName": "author",
  "updated_at": 1772065840450
}
```

Categories: `ai-intelligence`, `developer-tools`, `productivity`, `data-analysis`, `content-creation`, `security-compliance`, `communication-collaboration`.

## Commit

```bash
git add skills.json public/featured.json public/skills_pages/
git commit -m "data: sync skills $(date +%F)"
git push origin main
```

`skills.json` is ≈25 MB — don't churn it.

## First-time setup

```bash
pip install -r requirements.txt    # installs aiohttp
```
