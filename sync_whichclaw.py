"""Filter the Chinese skills.json down to English-only entries for whichclaw.com.

Design intent (directed by the owner): a one-file-one-truth data pipeline.
We do NOT fetch any external sources here. Instead, whenever the Chinese
site's skills.json is refreshed (python sync.py skills), this filter:

  1. Loads the existing skills.json.
  2. Keeps only skills whose `description` contains no CJK characters —
     i.e. the author's original description is already in English. Skills
     with an empty description or a Chinese original are dropped.
  3. Sorts by downloads desc (same ordering the Chinese site uses).
  4. Writes whichclaw/public/skills.json in the exact same shape
     ({total, featured, skills: [...]}) so the English site can reuse
     the Chinese frontend logic 1:1.
  5. Paginates to whichclaw/public/skills_pages/<N>.json (50 per page).
  6. Mirrors shared leaderboard data + brand assets into whichclaw/.

Zero network calls. Runs in a fraction of a second. Maintaining the
Chinese site automatically maintains the English site.
"""
from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path

HERE = Path(__file__).parent
CN_SKILLS_FILE = HERE / "skills.json"
WC_DIR = HERE / "whichclaw"
WC_PUBLIC = WC_DIR / "public"
WC_SKILLS_FILE = WC_PUBLIC / "skills.json"
WC_PAGES_DIR = WC_PUBLIC / "skills_pages"
WC_FEATURED_FILE = WC_PUBLIC / "featured.json"

CJK_RE = re.compile(r"[\u3000-\u303f\u3040-\u30ff\u4e00-\u9fff\uff00-\uffef]")


def is_english_description(text: str) -> bool:
    """True iff text is non-empty and contains no CJK characters."""
    if not text or not text.strip():
        return False
    if CJK_RE.search(text):
        return False
    # Also require at least one ASCII letter — rule out pure-emoji / pure-punct rows.
    return any("a" <= c.lower() <= "z" for c in text)


def filter_english(cn_skills: list[dict]) -> list[dict]:
    """Keep only skills whose original description is English."""
    out = []
    for s in cn_skills:
        desc = (s.get("description") or "").strip()
        if not is_english_description(desc):
            continue
        # Preserve every upstream field; frontend only reads a known subset.
        # Blank out description_zh so the English page always renders the
        # English `description` field even if some renderer prefers zh.
        row = dict(s)
        row["description_zh"] = ""
        out.append(row)
    out.sort(key=lambda s: (s.get("downloads") or 0, s.get("stars") or 0), reverse=True)
    return out


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
    """Copy shared leaderboard data + icons + brand files into whichclaw/."""
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

    for f in ("ico.png", "logo.png"):
        src = HERE / f
        if src.exists():
            shutil.copy2(src, WC_DIR / f)


def main() -> None:
    if not CN_SKILLS_FILE.exists():
        raise SystemExit(
            f"{CN_SKILLS_FILE} missing — run `python sync.py skills` first."
        )
    with CN_SKILLS_FILE.open("r", encoding="utf-8") as f:
        cn_data = json.load(f)
    cn_skills = cn_data.get("skills", [])
    print(f"Loaded {len(cn_skills)} skills from {CN_SKILLS_FILE.name}")

    en_skills = filter_english(cn_skills)
    pct = 100 * len(en_skills) / max(1, len(cn_skills))
    print(f"English-original skills: {len(en_skills)} ({pct:.1f}%)")

    WC_PUBLIC.mkdir(parents=True, exist_ok=True)
    featured_slugs = [s["slug"] for s in en_skills[:50] if s.get("slug")]
    WC_SKILLS_FILE.write_text(
        json.dumps({"total": len(en_skills), "featured": featured_slugs, "skills": en_skills},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    size_mb = WC_SKILLS_FILE.stat().st_size / 1024 / 1024
    print(f"Wrote {WC_SKILLS_FILE} ({size_mb:.1f} MB)")

    WC_FEATURED_FILE.write_text(
        json.dumps(en_skills[:50], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {WC_FEATURED_FILE} (50 featured)")

    paginate(en_skills)
    mirror_shared_assets()


if __name__ == "__main__":
    main()
