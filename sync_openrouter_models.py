"""
Sync real LLM leaderboard data from openrouter.ai/rankings.

Data flow:
  1. Call the Next.js Server Action `getModelRankingsCached` via POST to
     https://openrouter.ai/rankings with header `Next-Action: <RANKINGS_ACTION_ID>`
     and body `["day"|"week"|"month"]`. The response is an RSC stream whose
     second line (`1:`) is the JSON array of rankings rows. OpenRouter's page
     bailed out to client-side rendering in 2026, so the previous HTML scrape
     of `rankingData` from `__next_f.push(...)` no longer works.
  2. Each row: date, model_permaslug, variant, total_prompt_tokens,
     total_completion_tokens, count, change (percent delta as a float, e.g.
     0.15 == +15%), variant_permaslug.
  3. Fetch https://openrouter.ai/api/v1/models for metadata (display name,
     description, context_length, pricing).
  4. Build per-author icon URLs from `AUTHOR_ICON_HOMEPAGES`. Unknown
     authors fall back to the gstatic favicon proxy keyed on a best-guess
     homepage. Already-cached icons in ICON_DIR are reused unchanged.
  5. Emit public/models_ranking.json consumed by models.html.

No API keys required. Safe to run as a scheduled workflow.

Maintenance note: if Server Action calls start returning 404, the action
ID hash changed in an OpenRouter deploy. Reproduce by curl-ing
https://openrouter.ai/rankings, grep the loaded JS chunks for
`getModelRankingsCached` to find the new hash, and update
RANKINGS_ACTION_ID below.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

MODELS_API = "https://openrouter.ai/api/v1/models"
RANKINGS_PAGE = "https://openrouter.ai/rankings"
RANKINGS_ACTION_ID = "40824635c5eb77626bdf6795ffbf382c0862b321e1"
FAVICON_PROXY = (
    "https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON"
    "&fallback_opts=TYPE,SIZE,URL&url={url}&size=256"
)
VIEWS = ["day", "week", "month"]
OUTPUT_FILE = "public/models_ranking.json"
ICON_DIR = "public/models_icons"
ICON_WEB_PREFIX = "./public/models_icons"
TOP_N = 20
UA = "Mozilla/5.0 (compatible; ZhaoJiNeng-Sync/1.0)"

# Author slug → homepage URL used by OpenRouter's RemoteFavicon component.
# Transcribed from the `getAuthorIconInfo` map in the openrouter web chunks.
# Unmapped authors fall back to https://<slug>.com.
AUTHOR_ICON_HOMEPAGES = {
    "openai": "https://openai.com/",
    "anthropic": "https://anthropic.com/",
    "google": "https://gemini.google.com/",
    "mistralai": "https://mistral.ai/",
    "meta-llama": "https://www.llama.com/",
    "deepseek": "https://www.deepseek.com/",
    "qwen": "https://qwenlm.ai/",
    "moonshotai": "https://www.moonshot.cn/",
    "x-ai": "https://x.ai/",
    "perplexity": "https://www.perplexity.ai/",
    "cohere": "https://cohere.com/",
    "amazon": "https://nova.amazon.com/",
    "microsoft": "https://www.microsoft.com/",
    "nousresearch": "https://nousresearch.com/",
    "nvidia": "https://nvidia.com/",
    "ai21": "https://ai21.com/",
    "allenai": "https://allenai.org/",
    "huggingface": "https://huggingface.co/",
    "together": "https://www.together.ai/",
    "infermatic": "https://infermatic.ai/",
    "inflection": "https://inflection.ai/",
    "featherless": "https://featherless.ai/",
    "minimax": "https://minimaxi.com/",
    "liquid": "https://www.liquid.ai/",
    "inception": "https://www.inceptionlabs.ai/",
    "arcee-ai": "https://www.arcee.ai/",
    "z-ai": "https://z.ai/",
    "morph": "https://morphllm.com/",
    "databricks": "https://databricks.com/",
    "openrouter": "https://openrouter.ai/",
    "baidu": "https://www.baidu.com/",
    "tencent": "https://www.tencent.com/",
    "alibaba": "https://www.alibabacloud.com/",
    "bytedance": "https://seed.bytedance.com/",
    "bytedance-seed": "https://seed.bytedance.com/",
    "stepfun": "https://stepfun.ai/",
    "stepfun-ai": "https://stepfun.ai/",
    "writer": "https://writer.com/",
    "xiaomi": "https://www.mi.com/",
    "black-forest-labs": "https://bfl.ai/",
    "prime-intellect": "https://www.primeintellect.ai/",
    "essentialai": "https://www.essential.ai/",
    "deepcogito": "https://www.deepcogito.com/",
    "aion-labs": "https://www.aionlabs.ai/",
    "switchpoint": "https://switchpoint.dev/",
    "inclusionai": "https://www.inclusion-ai.org/",
    "byteplus": "https://www.byteplus.com/",
    "recraft": "https://www.recraft.ai/",
    "relace": "https://www.relace.ai/",
    "sourceful": "https://www.sourceful.com/",
    "perceptron": "https://www.perceptron.inc/",
    "kwaipilot": "https://www.kuaishou.com/",
    "kwaivgi": "https://www.kuaishou.com/",
    "thedrummer": "https://huggingface.co/TheDrummer",
    "nex-agi": "https://huggingface.co/",
    "ibm-granite": "https://www.ibm.com/granite",
}


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def call_rankings_action(view: str) -> list:
    """POST the Next.js Server Action for `getModelRankingsCached`.

    Response is an RSC stream where line `0:` is the action envelope and
    line `1:` is the JSON-encoded rows array.
    """
    body = json.dumps([view]).encode("utf-8")
    req = urllib.request.Request(
        RANKINGS_PAGE,
        data=body,
        method="POST",
        headers={
            "User-Agent": UA,
            "Next-Action": RANKINGS_ACTION_ID,
            "Content-Type": "text/plain;charset=UTF-8",
            "Accept": "text/x-component",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    for line in text.splitlines():
        if line.startswith("1:"):
            payload = json.loads(line[2:])
            if isinstance(payload, list):
                return payload
            raise RuntimeError(
                f"rankings action returned non-list payload for view={view}: {type(payload).__name__}"
            )
    raise RuntimeError(
        f"rankings action returned no `1:` payload for view={view} — action ID may have rotated"
    )


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


def build_author_icon_urls(rows_by_view: dict) -> dict:
    """Return {author_slug: remote_icon_url} for every author seen in rankings.

    Uses the gstatic favicon proxy (same one OpenRouter uses) keyed on the
    author homepage. Author → homepage mapping comes from AUTHOR_ICON_HOMEPAGES;
    unknown authors fall back to `https://<slug>.com`. The localize step is
    idempotent: existing icons in ICON_DIR are reused regardless of the URL
    we return here.
    """
    authors: set = set()
    for rows in rows_by_view.values():
        for row in rows:
            slug = row.get("model_permaslug") or ""
            if "/" in slug:
                authors.add(slug.split("/", 1)[0].lower())
            elif slug:
                authors.add(slug.lower())
    icons: dict = {}
    for author in authors:
        homepage = AUTHOR_ICON_HOMEPAGES.get(author, f"https://{author}.com/")
        icons[author] = FAVICON_PROXY.format(url=urllib.parse.quote(homepage, safe=""))
    return icons


def _guess_ext(url: str, content_type: str) -> str:
    """Pick a file extension from URL or Content-Type."""
    low = url.lower()
    for ext in (".svg", ".png", ".jpg", ".jpeg", ".ico", ".webp"):
        if ext in low:
            return ext
    ct = (content_type or "").lower()
    if "svg" in ct: return ".svg"
    if "png" in ct: return ".png"
    if "jpeg" in ct or "jpg" in ct: return ".jpg"
    if "webp" in ct: return ".webp"
    if "icon" in ct: return ".ico"
    return ".png"


def localize_icons(remote_icons: dict) -> dict:
    """Download each author icon into ICON_DIR. Return {author: local_path}.

    Idempotent: existing files with the same author + extension are reused.
    """
    os.makedirs(ICON_DIR, exist_ok=True)
    existing = {}
    for fname in os.listdir(ICON_DIR):
        stem, dot, ext = fname.partition(".")
        if dot:
            existing[stem] = f"{ICON_WEB_PREFIX}/{fname}"
    local_map: dict = dict(existing)
    for author, url in remote_icons.items():
        if author in existing:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                ct = resp.headers.get("Content-Type", "")
                ext = _guess_ext(url, ct)
                data = resp.read()
            fname = f"{author}{ext}"
            with open(os.path.join(ICON_DIR, fname), "wb") as fh:
                fh.write(data)
            local_map[author] = f"{ICON_WEB_PREFIX}/{fname}"
            print(f"[{_now()}] icon saved: {fname} ({len(data)} bytes)")
        except Exception as exc:
            print(f"[{_now()}] icon skipped for {author}: {exc}")
    return local_map


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

    for view in VIEWS:
        print(f"[{_now()}] Fetching rankings view={view} ...")
        rows = call_rankings_action(view)
        print(f"[{_now()}] view={view}: {len(rows)} raw rows")
        ranking_by_view[view] = rows

    icon_accumulator = build_author_icon_urls(ranking_by_view)
    print(f"[{_now()}] author icon URLs derived for {len(icon_accumulator)} authors")
    local_icons = localize_icons(icon_accumulator)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "top_n": TOP_N,
    }
    for view, rows in ranking_by_view.items():
        output[view] = build_period_ranking(rows, meta_index, local_icons)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    print(f"[{_now()}] Wrote {OUTPUT_FILE} ({sum(len(output[v]) for v in VIEWS)} ranked entries)")


if __name__ == "__main__":
    main()
