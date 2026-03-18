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

## Automatic (GitHub Actions)
// turbo-all

Skills data is automatically synced every day at 11:00 Beijing time via GitHub Actions.

The workflow file is at `.github/workflows/sync-skills.yml`.

The workflow:
1. Fetches featured (top 50) skills from `/api/skills/top`
2. Fetches all skills page by page from `/api/skills?page=N&size=20`
3. Assembles the final `skills.json` with Python
4. Commits and pushes if changed

## Manual Trigger

1. Go to GitHub repo -> Actions tab -> "Sync Skills Data"
2. Click "Run workflow" -> "Run workflow"

## Manual Local Sync (PowerShell)

// turbo
1. Run the sync script:
```powershell
powershell -ExecutionPolicy Bypass -File "C:\tmp\sync-skills.ps1"
```

Or manually step by step:

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
