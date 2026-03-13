---
description: how to manually sync skills data from SkillHub
---

# Sync Skills Data

## Automatic (GitHub Actions)
// turbo-all

Skills data is automatically synced every day at 11:00 Beijing time via GitHub Actions.

The workflow file is at `.github/workflows/sync-skills.yml`.

The workflow dynamically discovers the latest skills data URL by:
1. Fetching `https://skillhub.tencent.com/` to find the hashed JS bundle
2. Parsing the JS bundle to extract the skills data hash
3. Downloading from `https://cloudcache.tencentcs.com/qcloud/tea/app/data/skills.{hash}.json`

## Manual Trigger

1. Go to GitHub repo → Actions tab → "Sync Skills Data"
2. Click "Run workflow" → "Run workflow"

## Manual Local Sync

1. Get the latest hash from skillhub.tencent.com:
```bash
PAGE=$(curl -fsSL https://skillhub.tencent.com/)
JS_NAME=$(echo "$PAGE" | grep -oP 'skill-hub\.[A-Za-z0-9_-]+\.js' | head -1)
JS=$(curl -fsSL "https://cloudcache.tencent-cloud.com/qcloud/tea/app/assets/$JS_NAME")
HASH=$(echo "$JS" | grep -oP 'skills\.[a-f0-9]+\.json' | head -1 | grep -oP '[a-f0-9]+(?=\.json)')
echo "Hash: $HASH"
```

2. Download using the discovered URL:
```bash
curl -fsSL -o skills.json "https://cloudcache.tencentcs.com/qcloud/tea/app/data/skills.${HASH}.json?max_age=31536000"
```

3. Commit and push:
```bash
git add skills.json
git commit -m "chore: manual sync skills.json"
git push
```

## Data Source URLs

| Resource | URL |
|----------|-----|
| Skills Data (dynamic) | `https://cloudcache.tencentcs.com/qcloud/tea/app/data/skills.{hash}.json` |
| Skills Data (alt CDN) | `https://cloudcache.tencent-cloud.com/qcloud/tea/app/data/skills.{hash}.json` |
| Skill Download | `https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills/{slug}.zip` |
| CLI Installer | `https://skillhub-1251783334.cos.ap-guangzhou.myqcloud.com/install/install.sh` |
| CLI Version | `https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/version.json` |
