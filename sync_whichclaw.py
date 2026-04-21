"""Aggregate English Claude Skills from curated awesome-claude-skills lists.

Data flow:
  1. Fetch README.md of each repo in AWESOME_REPOS from raw.githubusercontent.com.
  2. Parse markdown list items of the form `- [name](url) — description`.
  3. Dedup by canonical URL; keep the richest metadata across sources.
  4. Classify by nearest preceding Markdown heading (used as `category`).
  5. Emit whichclaw/public/skills.json (same top-level shape as the Chinese
     skills.json: {total, featured, skills: [...]}) so the frontend code path
     can stay almost identical.
  6. Also paginate to whichclaw/public/skills_pages/<N>.json (50 per page)
     for the same first-paint + hydrate story the /all.html page uses.
  7. Mirror shared public/ data (models_ranking.json, ranking_snapshot.json,
     models_icons/, ico/) into whichclaw/public/ so the English site is
     self-contained and can be deployed from the whichclaw/ root directly.

No GitHub token required — raw.githubusercontent.com is anonymous.
"""
from __future__ import annotations

import json
import math
import re
import shutil
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
WC_DIR = HERE / "whichclaw"
WC_PUBLIC = WC_DIR / "public"
WC_SKILLS_FILE = WC_PUBLIC / "skills.json"
WC_PAGES_DIR = WC_PUBLIC / "skills_pages"
WC_FEATURED_FILE = WC_PUBLIC / "featured.json"

# Sources: high-signal, frequently updated awesome lists. Ordered so earlier
# entries "win" when the same URL appears in multiple lists (e.g. canonical
# name + description from Composio preferred over smaller lists).
AWESOME_REPOS = [
    ("ComposioHQ/awesome-claude-skills",        "master"),
    ("hesreallyhim/awesome-claude-code",        "main"),
    ("sickn33/antigravity-awesome-skills",      "main"),
    ("VoltAgent/awesome-agent-skills",          "main"),
    ("travisvn/awesome-claude-skills",          "main"),
    ("BehiSecc/awesome-claude-skills",          "main"),
]

# Section headings we want to skip entirely (not actual skills).
NON_SKILL_HEADINGS = {
    "contributing", "contributors", "license", "table of contents",
    "getting started", "how skills work", "quickstart", "installation",
    "resources", "articles", "videos", "tutorials", "courses", "blogs",
    "podcasts", "communities", "related awesome lists", "related lists",
    "official documentation", "official docs", "references", "contents",
    "credits", "acknowledgements", "acknowledgments",
}

UA = "Mozilla/5.0 (compatible; WhichClaw-Sync/1.0)"

# Markdown bullet with a named link (skills pattern).
# Matches plain `- [name](url) — desc`, bold `- **[name](url)**`, and the
# common "bold name then dash desc" variant `- **[name](url)** - desc`.
LIST_RE = re.compile(
    r"^\s*[-*+]\s+\*{0,2}\[([^\]]+)\]\(([^)]+)\)\*{0,2}\s*(?:[-—–:]\s*(.*))?$",
    re.MULTILINE,
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "skill"


def canonical_url(url: str) -> str:
    url = url.strip().split("#")[0].split("?")[0]
    url = url.rstrip("/")
    m = re.match(r"(https?://github\.com/[^/]+/[^/]+)(?:/tree/[^/]+(?:/.*)?)?$", url)
    if m:
        return m.group(1)
    return url


def parse_readme(repo: str, md: str) -> list[dict]:
    """Return list of {name, url, description, category, source_repo} rows."""
    heading_positions: list[tuple[int, str]] = []
    for m in HEADING_RE.finditer(md):
        heading = m.group(2).strip()
        plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading)
        plain = re.sub(r"[`*_]", "", plain).strip()
        heading_positions.append((m.start(), plain))

    def section_for(pos: int) -> str:
        current = ""
        for h_pos, h_text in heading_positions:
            if h_pos <= pos:
                current = h_text
            else:
                break
        return current

    rows = []
    for m in LIST_RE.finditer(md):
        name = m.group(1).strip()
        url = m.group(2).strip()
        desc = (m.group(3) or "").strip()
        if not name or name.lower() in ("", "source", "link", "repo", "github"):
            continue
        if url.startswith(("#", "mailto:", "javascript:")):
            continue
        if "img.shields.io" in url or "badge" in url.lower():
            continue
        section = section_for(m.start())
        if section.lower() in NON_SKILL_HEADINGS:
            continue
        desc = re.sub(r"`([^`]+)`", r"\1", desc)
        desc = re.sub(r"\*\*([^*]+)\*\*", r"\1", desc)
        desc = re.sub(r"\*([^*]+)\*", r"\1", desc)
        rows.append({
            "name": name,
            "url": url,
            "description": desc,
            "category": section or "Uncategorized",
            "source_repo": repo,
        })
    return rows


def merge(rows_by_repo: list[list[dict]]) -> list[dict]:
    """Dedup by canonical URL. Earlier repos win. Later repos enrich empty fields."""
    out: dict[str, dict] = {}
    for rows in rows_by_repo:
        for r in rows:
            key = canonical_url(r["url"])
            if key not in out:
                out[key] = {**r, "canonical_url": key, "sources": [r["source_repo"]]}
                continue
            existing = out[key]
            if r["source_repo"] not in existing["sources"]:
                existing["sources"].append(r["source_repo"])
            if not existing.get("description") and r.get("description"):
                existing["description"] = r["description"]
    merged = list(out.values())
    merged.sort(key=lambda x: (-len(x["sources"]), x["name"].lower()))
    return merged


def enrich_for_frontend(merged: list[dict]) -> list[dict]:
    """Shape rows to match the Chinese skills.json schema the frontend expects."""
    prepared = []
    for i, r in enumerate(merged):
        url = r["canonical_url"]
        owner = ""
        if url.startswith("https://github.com/"):
            parts = url.split("/", 5)
            if len(parts) >= 5:
                owner = parts[3]
        slug = slugify(r["name"])
        prepared.append({
            "slug": slug,
            "name": r["name"],
            "description": r.get("description", ""),
            "description_zh": "",
            "homepage": url,
            "tags": [r["category"]] if r.get("category") and r["category"] != "Uncategorized" else [],
            "category": r.get("category", "Uncategorized"),
            "ownerName": owner,
            "sources": r.get("sources", []),
            # Ranking proxy: more awesome lists listing this skill → higher score.
            "score": len(r.get("sources", [])) * 100 + max(0, 1000 - i),
            "downloads": 0,
            "stars": 0,
            "installs": 0,
            "version": "",
            "updated_at": 0,
        })
    return prepared


def paginate(skills: list[dict], page_size: int = 50) -> None:
    WC_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for p in WC_PAGES_DIR.glob("*.json"):
        p.unlink()
    total_pages = max(1, math.ceil(len(skills) / page_size))
    for page in range(1, total_pages + 1):
        start = (page - 1) * page_size
        slice_ = skills[start:start + page_size]
        out = {
            "page": page,
            "total_pages": total_pages,
            "total": len(skills),
            "skills": slice_,
        }
        (WC_PAGES_DIR / f"{page}.json").write_text(
            json.dumps(out, ensure_ascii=False), encoding="utf-8"
        )
    print(f"  paginated: {total_pages} pages ({page_size} per page)")


def mirror_shared_assets() -> None:
    """Copy shared leaderboard data + icons into whichclaw/public/."""
    for rel in ("public/models_ranking.json", "public/ranking_snapshot.json"):
        src = HERE / rel
        if not src.exists():
            continue
        dst = WC_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  mirrored {rel} -> whichclaw/{rel}")

    for sub in ("public/models_icons", "public/ico"):
        src = HERE / sub
        if not src.exists():
            continue
        dst = WC_DIR / sub
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"  mirrored {sub}/ -> whichclaw/{sub}/")

    # Brand assets (ico.png, logo.png) — referenced by every whichclaw page
    for f in ("ico.png", "logo.png"):
        src = HERE / f
        if src.exists():
            shutil.copy2(src, WC_DIR / f)


def main() -> None:
    all_rows: list[list[dict]] = []
    for repo, branch in AWESOME_REPOS:
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
        try:
            md = http_get(url)
        except Exception as e:
            print(f"  WARN {repo}@{branch}: {e}")
            continue
        rows = parse_readme(repo, md)
        print(f"  {repo}@{branch}: {len(rows)} candidate rows")
        all_rows.append(rows)

    merged = merge(all_rows)
    print(f"Merged unique skills: {len(merged)}")
    skills = enrich_for_frontend(merged)

    WC_PUBLIC.mkdir(parents=True, exist_ok=True)

    featured_slugs = [s["slug"] for s in skills[:50]]
    WC_SKILLS_FILE.write_text(
        json.dumps({"total": len(skills), "featured": featured_slugs, "skills": skills},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    size_kb = WC_SKILLS_FILE.stat().st_size / 1024
    print(f"Wrote {WC_SKILLS_FILE} ({size_kb:.1f} KB, {len(skills)} skills)")

    WC_FEATURED_FILE.write_text(
        json.dumps(skills[:50], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {WC_FEATURED_FILE} (50 featured)")

    paginate(skills)
    mirror_shared_assets()


if __name__ == "__main__":
    main()
