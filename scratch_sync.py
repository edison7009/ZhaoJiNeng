"""Fast parallel skill sync using asyncio + aiohttp.

Data flow:
  1. Pull the "featured top 50" list from /api/skills/top and persist it to
     public/featured.json (full skill objects consumed by index.html).
  2. Fan out concurrent page fetches (page 1..N, size=20) from /api/skills
     and collect every skill into skills.json.
  3. Embed the featured slugs into skills.json so the frontend can cross-
     reference them without a second fetch.

Run directly:   python scratch_sync.py
Or as part of:  python sync.py
"""
import asyncio, aiohttp, json, math, os

API_BASE = "https://lightmake.site/api/skills"
TOP_API = "https://lightmake.site/api/skills/top"
HEADERS = {
    "Referer": "https://skillhub.tencent.com/",
    "Origin": "https://skillhub.tencent.com",
}
PAGE_SIZE = 20
CONCURRENCY = 50  # parallel requests
OUT_FILE = os.path.join(os.path.dirname(__file__), "skills.json")
FEATURED_FILE = os.path.join(os.path.dirname(__file__), "public", "featured.json")

async def fetch_page(session, sem, page, results, errors):
    url = f"{API_BASE}?page={page}&size={PAGE_SIZE}"
    async with sem:
        for attempt in range(3):
            try:
                async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json(content_type=None)
                    skills = data["data"]["skills"]
                    results[page] = skills
                    return
            except Exception as e:
                if attempt == 2:
                    errors.append((page, str(e)))
                await asyncio.sleep(0.5 * (attempt + 1))

async def fetch_featured(session):
    """Refresh public/featured.json with the current top-50 list."""
    try:
        async with session.get(TOP_API, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            payload = await resp.json(content_type=None)
        featured = (payload or {}).get("data", {}).get("skills") or payload.get("data") or []
        if not isinstance(featured, list) or not featured:
            print(f"  WARN: featured list empty or unexpected shape; skipping featured.json update")
            return None
        os.makedirs(os.path.dirname(FEATURED_FILE), exist_ok=True)
        with open(FEATURED_FILE, "w", encoding="utf-8") as f:
            json.dump(featured, f, ensure_ascii=False, indent=2)
        print(f"  Featured refreshed: {len(featured)} skills -> public/featured.json")
        return featured
    except Exception as e:
        print(f"  WARN: featured fetch failed ({e}); keeping existing public/featured.json")
        return None


async def main():
    async with aiohttp.ClientSession() as session:
        # Refresh featured list first (independent of main skills dump)
        print("Fetching featured top 50 ...")
        await fetch_featured(session)

        # First request to get total
        async with session.get(f"{API_BASE}?page=1&size={PAGE_SIZE}", headers=HEADERS) as resp:
            data = await resp.json(content_type=None)
            total = data["data"]["total"]
            total_pages = math.ceil(total / PAGE_SIZE)
            print(f"Total skills: {total}, pages: {total_pages}")

        results = {}
        errors = []
        sem = asyncio.Semaphore(CONCURRENCY)

        # Fetch all pages in parallel batches
        batch_size = 200
        for batch_start in range(1, total_pages + 1, batch_size):
            batch_end = min(batch_start + batch_size, total_pages + 1)
            tasks = [fetch_page(session, sem, p, results, errors) for p in range(batch_start, batch_end)]
            await asyncio.gather(*tasks)
            fetched = sum(len(v) for v in results.values())
            print(f"  Batch {batch_start}-{batch_end-1} done, fetched {fetched}/{total} skills so far")

        if errors:
            print(f"WARNING: {len(errors)} pages failed: {errors[:5]}")

        # Merge in page order
        all_skills = []
        for p in sorted(results.keys()):
            all_skills.extend(results[p])

        print(f"Total fetched: {len(all_skills)} skills")

        # Build featured slugs from featured.json
        featured_path = os.path.join(os.path.dirname(__file__), "public", "featured.json")
        featured_slugs = []
        if os.path.exists(featured_path):
            with open(featured_path, "r", encoding="utf-8-sig") as f:
                featured_data = json.load(f)
                featured_slugs = [s["slug"] for s in featured_data if "slug" in s]

        # Write skills.json
        output = {
            "total": len(all_skills),
            "featured": featured_slugs,
            "skills": all_skills
        }
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False)
        
        size_mb = os.path.getsize(OUT_FILE) / 1024 / 1024
        print(f"Saved {OUT_FILE} ({size_mb:.1f} MB)")

if __name__ == "__main__":
    asyncio.run(main())
