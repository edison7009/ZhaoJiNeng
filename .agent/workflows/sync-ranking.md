---
description: how to sync ranking data from clawcharts.com to ranking.html
---

# Sync Ranking Data

This workflow scrapes the latest ranking data from clawcharts.com and updates the hardcoded data in ranking.html. Run this every 3 days or when you want fresh data.

## Steps

1. Open https://clawcharts.com/ in the browser and wait for full page load (3-5 seconds)

2. Verify the page has loaded correctly with all 10 projects visible in the ranking table

3. Use the browser tool to scrape all ranking data from the rendered page. The data includes:
   - **Summary cards**: Leader (name + stars), Ecosystem Stars (total + desc), 7D Growth (value + percentage), Top Growth (name + desc)
   - **Rankings table** (10 rows): rank, name, status (RISING/COOLING/""), stars7d, stars7dChange, contribs7d, contribs7dChange, commits7d, commits7dChange, totalStars

4. Update the `RANKING_DATA` object in `d:\ZhaoJiNeng\ranking.html` (search for `// Last synced:` comment):
   - Update the `// Last synced:` date comment
   - Update `summary` object with new card values
   - Update each of the 10 `rankings` array entries with fresh data
   - Also update the default HTML values for the leader and top growth summary cards if they changed

5. Commit and push:
   ```
   git add ranking.html
   git commit -m "data: sync ranking data from clawcharts.com YYYY-MM-DD"
   git push origin main
   ```

6. Wait 1-2 minutes for Cloudflare Pages to deploy, then verify at https://zhaojineng.com/ranking

## Notes
- The ranking page shows "刚刚更新" based on page session time, not actual data freshness
- clawcharts.com syncs from GitHub API hourly
- We deliberately do NOT use a Worker/API to avoid parsing issues with their Next.js RSC payload
