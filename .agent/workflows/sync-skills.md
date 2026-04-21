---
description: how to manually sync skills data from SkillHub
---

# Sync Skills Data

## Architecture (Updated 2026-03)

SkillHub (skillhub.tencent.com) migrated from static CDN JSON files to a backend API:
- **API Base**: `https://lightmake.site`
- **Featured (Top 50)**: `GET /api/skills/top`
- **All Skills (paginated)**: `GET /api/skills?page=N&size=20` (max 20 per page)
- **Skill Download**: `http://lightmake.site/api/v1/download?slug={slug}`
- **Required Headers**: `Referer: https://skillhub.tencent.com/` and `Origin: https://skillhub.tencent.com`

The old static `skills.{hash}.json` CDN approach no longer works.

## How to Sync

Run this workflow manually when skills data needs updating. No auto-trigger — all syncs are manual.

## Steps

// turbo
1. Run the sync script (fetches all 25000+ skills paginated):
```powershell
powershell -ExecutionPolicy Bypass -File "C:\tmp\sync-skills.ps1"
```

// turbo
2. Update the 50 featured skills from SkillHub API:
```powershell
python C:\tmp\update-featured.py
```
This fetches the latest top 50 from `GET /api/skills/top` and updates both `public/featured.json` (full skill objects for the homepage) and the `featured` slugs array in `skills.json`.

3. Generate paginated JSON files for frontend loading (to prevent 15MB huge file lag):
```powershell
python d:\ZhaoJiNeng\generate_pages.py
```
This splits the skills into 50-item chunks inside `public/skills_pages`.

4. Commit and push:
```bash
git add skills.json public/featured.json public/skills_pages/
git commit -m "chore: sync skills data YYYY-MM-DD"
git push origin main
```

// turbo
2. Fetch featured skills:
```powershell
$headers = @{"Referer"="https://skillhub.tencent.com/";"Origin"="https://skillhub.tencent.com"}
$resp = Invoke-WebRequest -Uri "https://lightmake.site/api/skills/top" -UseBasicParsing -Headers $headers
$json = [System.Text.Encoding]::UTF8.GetString($resp.RawContentStream.ToArray()) | ConvertFrom-Json
Write-Host "Got $($json.data.skills.Count) featured skills"
```

// turbo
3. Fetch all skills (paginated, 20 per page):
```powershell
# Loop through pages 1..N until all skills fetched
$page = 1; $all = @()
do {
  $r = Invoke-WebRequest -Uri "https://lightmake.site/api/skills?page=$page&size=20" -UseBasicParsing -Headers $headers
  $j = [System.Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray()) | ConvertFrom-Json
  $all += $j.data.skills; $page++
  Start-Sleep -Milliseconds 100
} while ($all.Count -lt $j.data.total)
```

4. Commit and push:
```bash
git add skills.json
git commit -m "chore: manual sync skills.json"
git push
```

## API Endpoints

| Resource | URL |
|----------|-----|
| Featured Top 50 | `https://lightmake.site/api/skills/top` |
| All Skills (paginated) | `https://lightmake.site/api/skills?page=N&size=20` |
| Skill Download | `http://lightmake.site/api/v1/download?slug={slug}` |
| SkillHub Frontend | `https://skillhub.tencent.com/` |

## Data Format

Each skill object from the API:
```json
{
  "slug": "skill-name",
  "name": "Skill Name",
  "description": "English description",
  "description_zh": "Chinese description",
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

Categories: `ai-intelligence`, `developer-tools`, `productivity`, `data-analysis`, `content-creation`, `security-compliance`, `communication-collaboration`
