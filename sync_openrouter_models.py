"""
Sync real LLM leaderboard data from openrouter.ai/rankings.

Data flow:
  1. Scrape https://openrouter.ai/rankings?view={day|week|month} — Next.js SSR
     embeds the leaderboard into __next_f.push("45:...rankingData:[...]...") RSC
     payload inline in the HTML. OpenRouter exposes no public ranking API, so
     the page HTML is the source of truth.
  2. Each rankingData row: date, model_permaslug, variant,
     total_prompt_tokens, total_completion_tokens, count, change (percent
     delta as a float, e.g. 0.15 == +15%).
  3. Fetch https://openrouter.ai/api/v1/models for metadata (display name,
     description, context_length, pricing).
  4. Scrape author icon URLs per author from the rendered HTML (OpenRouter
     uses /images/icons/<Vendor>.svg for big brands and a gstatic favicon
     proxy for smaller ones).
  5. Emit public/models_ranking.json consumed by models.html.

No API keys required. Safe to run as a scheduled workflow.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

MODELS_API = "https://openrouter.ai/api/v1/models"
RANKINGS_URL = "https://openrouter.ai/rankings?view={view}"
VIEWS = ["day", "week", "month"]
OUTPUT_FILE = "public/models_ranking.json"
TOP_N = 20
UA = "Mozilla/5.0 (compatible; ZhaoJiNeng-Sync/1.0)"


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_models_metadata() -> dict:
    """Return {permaslug_or_id: metadata} from the public models API.

    The rankings stream uses `model_permaslug` that often matches either the
    API's `id` or `canonical_slug`. We index by both for resilience.
    """
    print(f"[{_now()}] Fetching /api/v1/models ...")
    raw = http_get(MODELS_API)
    data = json.loads(raw).get("data", [])
    index: dict = {}
    for m in data:
        meta = {
            "id": m.get("id"),
            "name": m.get("name", ""),
            "description": (m.get("description") or "").strip(),
            "context_length": m.get("context_length") or 0,
            "pricing_prompt": (m.get("pricing") or {}).get("prompt", "0"),
            "pricing_completion": (m.get("pricing") or {}).get("completion", "0"),
            "created": m.get("created") or 0,
        }
        for key in (m.get("id"), m.get("canonical_slug")):
            if key:
                index[key] = meta
    print(f"[{_now()}] Indexed {len(index)} model keys from metadata API")
    return index


def extract_ranking_data(html: str) -> list:
    """Extract the inline `rankingData` array from the RSC payload.

    The stream chunk looks like:
        self.__next_f.push([1,"45:[\\"$\\",\\"$L55\\",null,{\\"rankingData\\":[ ... ]}]"])
    Every `"` inside is doubled to `\\"`. We capture the JSON array text and
    unescape it once before parsing.
    """
    m = re.search(r'\\"rankingData\\":(\[.+?\])(?:,\\"|\})', html, re.DOTALL)
    if not m:
        raise RuntimeError("rankingData not found in HTML — OpenRouter page layout changed")
    escaped = m.group(1)
    decoded = escaped.encode("utf-8").decode("unicode_escape")
    return json.loads(decoded)


def extract_author_icons(html: str) -> dict:
    """Return {author_slug: icon_url}. Uses OpenRouter's rendered icons."""
    icons: dict = {}
    pattern = re.compile(r'alt="Favicon for ([a-z0-9][a-z0-9\-]*)"\s+src="([^"]+)"')
    for slug, src in pattern.findall(html):
        if slug in icons:
            continue
        if src.startswith("/"):
            src = f"https://openrouter.ai{src}"
        src = src.replace("&amp;", "&")
        icons[slug] = src
    return icons


def build_period_ranking(rows: list, meta_index: dict, icon_map: dict) -> list:
    """Sort rows by total tokens, keep top N, enrich with metadata."""
    enriched = []
    for row in rows:
        slug = row.get("model_permaslug") or ""
        if not slug:
            continue
        variant = (row.get("variant") or "standard").lower()
        prompt_tokens = int(row.get("total_prompt_tokens") or 0)
        completion_tokens = int(row.get("total_completion_tokens") or 0)
        total_tokens = prompt_tokens + completion_tokens
        if total_tokens <= 0:
            continue
        change = row.get("change")
        author = slug.split("/", 1)[0] if "/" in slug else slug
        variant_slug = row.get("variant_permaslug") or slug
        meta = (
            meta_index.get(variant_slug)
            or meta_index.get(slug)
            or _best_effort_meta_lookup(slug, meta_index)
        )
        short = _short_name(meta, slug)
        if variant and variant != "standard":
            short = f"{short} ({variant})"
        enriched.append({
            "permaslug": slug,
            "variant": variant,
            "variant_permaslug": variant_slug,
            "author": author,
            "author_icon": icon_map.get(author, ""),
            "name": _display_name(meta, slug),
            "short_name": short,
            "description": (meta or {}).get("description", "")[:180],
            "context_length": (meta or {}).get("context_length", 0),
            "pricing_prompt": (meta or {}).get("pricing_prompt", "0"),
            "pricing_completion": (meta or {}).get("pricing_completion", "0"),
            "total_tokens": total_tokens,
            "request_count": int(row.get("count") or 0),
            "change": change,
        })
    enriched.sort(key=lambda r: r["total_tokens"], reverse=True)
    top = enriched[:TOP_N]
    for i, item in enumerate(top, start=1):
        item["rank"] = i
    return top


def _best_effort_meta_lookup(slug: str, meta_index: dict) -> dict:
    """Try fuzzy matches when the dated permaslug is missing from the API."""
    if slug in meta_index:
        return meta_index[slug]
    stripped = re.sub(r"-\d{8}$", "", slug)
    if stripped in meta_index:
        return meta_index[stripped]
    for key in meta_index:
        if key.startswith(stripped):
            return meta_index[key]
    return {}


def _display_name(meta: dict, slug: str) -> str:
    if meta and meta.get("name"):
        return meta["name"]
    last = slug.split("/", 1)[-1]
    return last.replace("-", " ").title()


def _short_name(meta: dict, slug: str) -> str:
    full = _display_name(meta, slug)
    return re.sub(r"^[^:]+:\s*", "", full)


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def main() -> None:
    meta_index = fetch_models_metadata()
    ranking_by_view: dict = {}
    icon_accumulator: dict = {}

    for view in VIEWS:
        url = RANKINGS_URL.format(view=view)
        print(f"[{_now()}] Fetching rankings view={view} ...")
        html = http_get(url)
        rows = extract_ranking_data(html)
        icon_accumulator.update(extract_author_icons(html))
        print(f"[{_now()}] view={view}: {len(rows)} raw rows")
        ranking_by_view[view] = rows

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "https://openrouter.ai/rankings",
        "top_n": TOP_N,
    }
    for view, rows in ranking_by_view.items():
        output[view] = build_period_ranking(rows, meta_index, icon_accumulator)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    print(f"[{_now()}] Wrote {OUTPUT_FILE} ({sum(len(output[v]) for v in VIEWS)} ranked entries)")


if __name__ == "__main__":
    main()
