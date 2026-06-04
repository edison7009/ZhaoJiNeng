"""
Sync the LLM *capability* leaderboard from Artificial Analysis.

Data source — the official, documented Artificial Analysis API:
    GET https://artificialanalysis.ai/api/v2/data/llms/models
    Auth: header `x-api-key: <AA_API_KEY>`

Get a free key at https://artificialanalysis.ai/ (account -> API). Put it in
the environment as AA_API_KEY (GitHub Actions: repository secret AA_API_KEY).

Why this replaced the old OpenRouter scrape: the previous source called an
internal Next.js Server Action addressed by a hash that OpenRouter rotated on
every deploy, so the sync 404'd and failed several times a day. A versioned
REST API does not move under us — it stays valid across the provider's
redeploys, which is the whole point of switching.

Output — public/models_ranking.json, three Top-N capability rankings:
    intelligence : Artificial Analysis Intelligence Index (overall ability)
    coding       : Artificial Analysis Coding Index
    math         : Artificial Analysis Math Index
Each entry also carries the other two indices plus blended price and output
speed, so the frontend can show a secondary stat without a second request.

Author icons are localized into public/models_icons/ via the gstatic favicon
proxy keyed on each creator's homepage — the same idempotent scheme the old
script used, so already-cached icons are reused untouched.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
OUTPUT_FILE = "public/models_ranking.json"
ICON_DIR = "public/models_icons"
ICON_WEB_PREFIX = "./public/models_icons"
TOP_N = 20
UA = "Mozilla/5.0 (compatible; ZhaoJiNeng-Sync/1.0)"

# view key -> evaluations field on each model. Order here is display order.
VIEWS = {
    "intelligence": "artificial_analysis_intelligence_index",
    "coding": "artificial_analysis_coding_index",
    "math": "artificial_analysis_math_index",
}

FAVICON_PROXY = (
    "https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON"
    "&fallback_opts=TYPE,SIZE,URL&url={url}&size=256"
)

# Creator slug -> homepage used for the favicon proxy. Unmapped creators fall
# back to https://<slug>.com. (Artificial Analysis creator slugs, e.g.
# "openai", "anthropic", "google", "meta", "mistral", "xai", "deepseek".)
CREATOR_ICON_HOMEPAGES = {
    "openai": "https://openai.com/",
    "anthropic": "https://anthropic.com/",
    "google": "https://gemini.google.com/",
    "google-deepmind": "https://deepmind.google/",
    "meta": "https://www.llama.com/",
    "meta-llama": "https://www.llama.com/",
    "mistral": "https://mistral.ai/",
    "mistralai": "https://mistral.ai/",
    "deepseek": "https://www.deepseek.com/",
    "qwen": "https://qwenlm.ai/",
    "alibaba": "https://www.alibabacloud.com/",
    "moonshot": "https://www.moonshot.cn/",
    "moonshotai": "https://www.moonshot.cn/",
    "xai": "https://x.ai/",
    "x-ai": "https://x.ai/",
    "perplexity": "https://www.perplexity.ai/",
    "cohere": "https://cohere.com/",
    "amazon": "https://nova.amazon.com/",
    "microsoft": "https://www.microsoft.com/",
    "microsoft-azure": "https://www.microsoft.com/",
    "nvidia": "https://nvidia.com/",
    "ai21-labs": "https://ai21.com/",
    "ai21": "https://ai21.com/",
    "allen-institute-for-ai": "https://allenai.org/",
    "reka-ai": "https://www.reka.ai/",
    "databricks": "https://databricks.com/",
    "minimax": "https://www.minimaxi.com/",
    "zhipu": "https://z.ai/",
    "zhipu-ai": "https://z.ai/",
    "z-ai": "https://z.ai/",
    "01-ai": "https://www.01.ai/",
    "tencent": "https://www.tencent.com/",
    "baidu": "https://www.baidu.com/",
    "bytedance": "https://seed.bytedance.com/",
    "stepfun": "https://stepfun.ai/",
    "xiaomi": "https://www.mi.com/",
    "liquid-ai": "https://www.liquid.ai/",
    "nous-research": "https://nousresearch.com/",
    "ibm": "https://www.ibm.com/granite",
}


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def fetch_models(api_key: str) -> list:
    """Return the `data` list from the Artificial Analysis models endpoint."""
    print(f"[{_now()}] Fetching {API_URL} ...")
    req = urllib.request.Request(
        API_URL, headers={"User-Agent": UA, "x-api-key": api_key}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    data = payload.get("data", [])
    if not isinstance(data, list) or not data:
        raise RuntimeError(
            f"API returned no models (status={payload.get('status')}); "
            "check AA_API_KEY and the endpoint."
        )
    print(f"[{_now()}] Received {len(data)} models")
    return data


def _creator(model: dict) -> tuple:
    """Return (slug, display_name) for a model's creator."""
    mc = model.get("model_creator") or {}
    slug = (mc.get("slug") or "").strip().lower()
    name = (mc.get("name") or slug or "").strip()
    return slug, name


def build_creator_icon_urls(models: list) -> dict:
    """Return {creator_slug: remote_favicon_url} for every creator present."""
    icons: dict = {}
    for model in models:
        slug, _ = _creator(model)
        if not slug or slug in icons:
            continue
        homepage = CREATOR_ICON_HOMEPAGES.get(slug, f"https://{slug}.com/")
        icons[slug] = FAVICON_PROXY.format(url=urllib.parse.quote(homepage, safe=""))
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
    """Download each creator icon into ICON_DIR. Return {creator: local_path}.

    Idempotent: an existing file with the same creator + extension is reused.
    """
    os.makedirs(ICON_DIR, exist_ok=True)
    existing = {}
    for fname in os.listdir(ICON_DIR):
        stem, dot, _ext = fname.partition(".")
        if dot:
            existing[stem] = f"{ICON_WEB_PREFIX}/{fname}"
    local_map: dict = dict(existing)
    for creator, url in remote_icons.items():
        if creator in existing:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                ct = resp.headers.get("Content-Type", "")
                ext = _guess_ext(url, ct)
                data = resp.read()
            fname = f"{creator}{ext}"
            with open(os.path.join(ICON_DIR, fname), "wb") as fh:
                fh.write(data)
            local_map[creator] = f"{ICON_WEB_PREFIX}/{fname}"
            print(f"[{_now()}] icon saved: {fname} ({len(data)} bytes)")
        except Exception as exc:
            print(f"[{_now()}] icon skipped for {creator}: {exc}")
    return local_map


def _num(value):
    """Coerce to float, or None if missing/non-numeric."""
    if isinstance(value, (int, float)):
        return float(value)
    return None


_VARIANT_SUFFIX = re.compile(r"\s*\([^()]*\)\s*$")


def _base_name(name: str) -> str:
    """Strip a trailing '(...)' reasoning/effort qualifier for display + dedup.

    AA lists effort variants as separate rows ('GPT-5.5 (high)', 'GPT-5.5
    (xhigh)', ...). For a public board we collapse them to one row per model
    under the clean base name, keeping the best-scoring variant.
    """
    base = _VARIANT_SUFFIX.sub("", name).strip()
    return base or name


def build_view(models: list, field: str, icon_map: dict) -> list:
    """Rank by `field` (desc), collapse effort variants, keep Top-N."""
    scored = []
    for model in models:
        evals = model.get("evaluations") or {}
        score = _num(evals.get(field))
        if score is None:
            continue  # model not evaluated on this dimension
        slug, name = _creator(model)
        pricing = model.get("pricing") or {}
        full_name = model.get("name") or model.get("slug") or ""
        scored.append({
            "model_id": model.get("slug") or model.get("id") or "",
            "name": full_name,
            "short_name": _base_name(full_name),
            "author": slug,
            "author_name": name,
            "author_icon": icon_map.get(slug, ""),
            "score": round(score, 1),
            "intelligence": _num(evals.get("artificial_analysis_intelligence_index")),
            "coding": _num(evals.get("artificial_analysis_coding_index")),
            "math": _num(evals.get("artificial_analysis_math_index")),
            "price_blended": _num(pricing.get("price_1m_blended_3_to_1")),
            "output_speed": _num(model.get("median_output_tokens_per_second")),
        })
    scored.sort(key=lambda r: r["score"], reverse=True)
    # Keep the best-scoring variant per (creator, base name); take Top-N.
    seen = set()
    top = []
    for entry in scored:
        key = (entry["author"], entry["short_name"].lower())
        if key in seen:
            continue
        seen.add(key)
        top.append(entry)
        if len(top) >= TOP_N:
            break
    for i, item in enumerate(top, start=1):
        item["rank"] = i
    return top


def main() -> None:
    api_key = os.environ.get("AA_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "AA_API_KEY is not set. Get a free key at "
            "https://artificialanalysis.ai/ and export AA_API_KEY=<key> "
            "(GitHub Actions: add repository secret AA_API_KEY)."
        )

    models = fetch_models(api_key)
    icon_map = localize_icons(build_creator_icon_urls(models))

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "top_n": TOP_N,
        "source": "artificialanalysis.ai",
    }
    for view, field in VIEWS.items():
        output[view] = build_view(models, field, icon_map)
        print(f"[{_now()}] view={view}: {len(output[view])} ranked entries")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    print(f"[{_now()}] Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
