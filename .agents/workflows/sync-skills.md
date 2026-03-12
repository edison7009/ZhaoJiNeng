---
description: how to manually sync skills data from SkillHub
---

# Sync Skills Data

## Automatic (GitHub Actions)
// turbo-all

Skills data is automatically synced every day at 11:00 Beijing time via GitHub Actions.

The workflow file is at `.github/workflows/sync-skills.yml`.

## Manual Trigger

1. Go to GitHub repo → Actions tab → "Sync Skills Data"
2. Click "Run workflow" → "Run workflow"

## Manual Local Sync

1. Download the latest skills.json:
```bash
curl -fsSL -o skills.json "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills.json"
```

2. Commit and push:
```bash
git add skills.json
git commit -m "chore: manual sync skills.json"
git push
```

## Data Source URLs

| Resource | URL |
|----------|-----|
| Skills Index | `https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills.json` |
| Skill Download | `https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills/{slug}.zip` |
| CLI Installer | `https://skillhub-1251783334.cos.ap-guangzhou.myqcloud.com/install/install.sh` |
| CLI Version | `https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/version.json` |
