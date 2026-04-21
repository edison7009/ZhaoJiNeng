"""Fast parallel skill sync using asyncio + aiohttp."""
import asyncio, aiohttp, json, math, sys, os

API_BASE = "https://lightmake.site/api/skills"
HEADERS = {
    "Referer": "https://skillhub.tencent.com/",
    "Origin": "https://skillhub.tencent.com",
}
PAGE_SIZE = 20
CONCURRENCY = 50  # parallel requests
OUT_FILE = os.path.join(os.path.dirname(__file__), "skills.json")

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

async def main():
    # First request to get total
    async with aiohttp.ClientSession() as session:
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
