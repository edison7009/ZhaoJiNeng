"""Sync the lobster-agents leaderboard (ranking.html) from the GitHub API.

Tracked repos are declared in TRACKED below. For each we pull:
  - stargazers_count  (current total stars)
  - 7d commits        (via /commits?since=... Link-header trick)
  - 7d contributors   (via /stats/contributors; GitHub may 202 on first call)

To compute 7-day deltas on stars/contributors/commits we compare the latest
snapshot with the most recent snapshot in public/ranking_history/ that is at
least 6 days old. The first run can't produce deltas — fields come back as
"—" and ranking.html renders a neutral state.

Output:
  public/ranking_snapshot.json        current data, consumed by ranking.html
  public/ranking_history/<date>.json  raw snapshot archive (for next run)

Auth: honors GITHUB_TOKEN (env) to bump rate limit from 60/hr to 5000/hr.
Without a token 11 repos × ~3 requests = 33 calls; fine for a single run but
tight if you re-run in the same hour. Prefer exporting a token.

Run directly:   python ranking_sync.py
Or as part of:  python sync.py
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
SNAPSHOT_FILE = HERE / "public" / "ranking_snapshot.json"
HISTORY_DIR = HERE / "public" / "ranking_history"

# Projects tracked on ranking.html — keep in sync with the PROJECT_* maps there.
TRACKED = [
    ("OpenClaw",     "openclaw/openclaw",          "TypeScript"),
    ("Hermes Agent", "NousResearch/hermes-agent",  "Python"),
    ("Paperclip",    "paperclipai/paperclip",      "TypeScript"),
    ("Nanobot",      "HKUDS/nanobot",              "Python"),
    ("ZeroClaw",     "zeroclaw-labs/zeroclaw",     "Rust"),
    ("PicoClaw",     "sipeed/picoclaw",            "Go"),
    ("NanoClaw",     "qwibitai/nanoclaw",          "TypeScript"),
    ("OpenFang",     "RightNow-AI/openfang",       "Rust"),
    ("IronClaw",     "nearai/ironclaw",            "Rust"),
    ("NullClaw",     "nullclaw/nullclaw",          "Zig"),
    ("TinyClaw",     "TinyAGI/tinyclaw",           "TypeScript"),
]


def _headers() -> dict:
    h = {
        "User-Agent": "ZhaoJiNeng-RankingSync/1.0",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(url: str):
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        return body, dict(resp.headers.items())


def _last_page_count(link_header):
    """Pull `page=N` from rel="last" in a GitHub Link header.

    With per_page=1, the last page number equals the total item count.
    """
    if not link_header:
        return None
    m = re.search(r'<[^>]*[?&]page=(\d+)[^>]*>;\s*rel="last"', link_header)
    return int(m.group(1)) if m else None


def fetch_repo_stats(repo: str, since_iso: str) -> dict:
    base = f"https://api.github.com/repos/{repo}"
    result = {"repo": repo, "error": None}

    try:
        body, _ = _get(base)
        result["stars"] = body.get("stargazers_count", 0)
        result["forks"] = body.get("forks_count", 0)
        result["subscribers"] = body.get("subscribers_count", 0)
        result["default_branch"] = body.get("default_branch", "main")
    except Exception as e:
        result["error"] = f"repo: {e}"
        return result

    try:
        url = f"{base}/commits?since={urllib.parse.quote(since_iso)}&per_page=1"
        body, headers = _get(url)
        link = headers.get("Link") or headers.get("link")
        total = _last_page_count(link)
        if total is None:
            total = len(body) if isinstance(body, list) else 0
        result["commits_7d"] = total
    except urllib.error.HTTPError as e:
        if e.code == 409:
            result["commits_7d"] = 0
        else:
            result["commits_7d"] = None
            result["error"] = f"commits: {e}"
    except Exception as e:
        result["commits_7d"] = None
        result["error"] = f"commits: {e}"

    try:
        body, _ = _get(f"{base}/stats/contributors")
        week_cutoff = int((datetime.now(tz=timezone.utc) - timedelta(days=7)).timestamp())
        active = 0
        if isinstance(body, list):
            for c in body:
                for w in (c.get("weeks") or []):
                    if w.get("w", 0) >= week_cutoff and (w.get("c", 0) or 0) > 0:
                        active += 1
                        break
        result["contribs_7d"] = active
    except Exception:
        result["contribs_7d"] = None

    return result


def load_baseline_snapshot():
    if not HISTORY_DIR.exists():
        return None
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=6)
    candidates = []
    for p in HISTORY_DIR.glob("*.json"):
        try:
            ts = datetime.fromisoformat(p.stem).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ts <= cutoff:
            candidates.append((ts, p))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    try:
        return json.loads(candidates[0][1].read_text(encoding="utf-8"))
    except Exception:
        return None


def _fmt_num(n):
    if n is None:
        return "—"
    return f"{n:,}"


def _fmt_delta(curr, prev):
    if curr is None or prev is None:
        return "—"
    diff = curr - prev
    sign = "+" if diff > 0 else ""
    return f"{sign}{diff:,}"


def _fmt_pct(curr, prev):
    if curr is None or prev is None or prev == 0:
        return "—"
    pct = (curr - prev) / prev * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


def _parse_pct(s):
    m = re.match(r"([+-]?\d+(?:\.\d+)?)%", s or "")
    return float(m.group(1)) if m else None


def _int(s):
    try:
        return int((s or "").replace(",", "").replace("—", "0") or 0)
    except Exception:
        return 0


def build_snapshot(raw_rows, baseline):
    baseline_by_repo = {}
    if baseline:
        for row in baseline.get("_raw", []):
            baseline_by_repo[row["repo"]] = row

    enriched = []
    for (name, repo, lang), raw in zip(TRACKED, raw_rows):
        prev = baseline_by_repo.get(repo)
        stars = raw.get("stars")
        commits7 = raw.get("commits_7d")
        contribs7 = raw.get("contribs_7d")
        prev_stars = prev.get("stars") if prev else None
        prev_commits = prev.get("commits_7d") if prev else None
        prev_contribs = prev.get("contribs_7d") if prev else None

        pct_change = (stars - prev_stars) / prev_stars if (stars and prev_stars) else None
        status = ""
        if pct_change is not None:
            if pct_change >= 0.03:
                status = "RISING"
            elif pct_change <= -0.03:
                status = "COOLING"

        enriched.append({
            "name": name,
            "repo": repo,
            "language": lang,
            "status": status,
            "stars7d": _fmt_delta(stars, prev_stars),
            "stars7dChange": _fmt_pct(stars, prev_stars),
            "contribs7d": _fmt_num(contribs7),
            "contribs7dChange": _fmt_pct(contribs7, prev_contribs),
            "commits7d": _fmt_num(commits7),
            "commits7dChange": _fmt_pct(commits7, prev_commits),
            "totalStars": _fmt_num(stars),
        })

    enriched.sort(key=lambda r: _int(r["totalStars"]), reverse=True)
    for i, r in enumerate(enriched, start=1):
        r["rank"] = i

    total_stars = sum(row.get("stars") or 0 for row in raw_rows)
    prev_total = (
        sum((baseline_by_repo.get(row["repo"], {}) or {}).get("stars", 0) for row in raw_rows)
        if baseline else 0
    )
    growth_val = _fmt_delta(total_stars, prev_total if prev_total else None)
    growth_pct = _fmt_pct(total_stars, prev_total if prev_total else None)

    leader = enriched[0] if enriched else None
    top_growth = max(
        enriched,
        key=lambda r: _parse_pct(r["stars7dChange"]) if _parse_pct(r["stars7dChange"]) is not None else -1e9,
        default=None,
    ) if enriched else None

    return {
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "summary": {
            "leader": {
                "name": leader["name"] if leader else "—",
                "stars": f"{leader['totalStars']} stars" if leader else "—",
            },
            "ecosystemStars": {
                "total": _fmt_num(total_stars),
                "desc": f"Across {len(enriched)} tracked repos",
            },
            "growth7d": {
                "value": growth_val,
                "percentage": f"Stars · {growth_pct}" if growth_pct != "—" else "Stars · —",
            },
            "topGrowth": {
                "name": top_growth["name"] if top_growth else "—",
                "desc": f"{top_growth['stars7dChange']} over 7 days" if top_growth else "—",
            },
        },
        "rankings": enriched,
        "_raw": raw_rows,
    }


def _ts():
    return datetime.now().strftime("%H:%M:%S")


def main():
    since = (datetime.now(tz=timezone.utc) - timedelta(days=7)).isoformat()
    print(f"[{_ts()}] Syncing {len(TRACKED)} repos, 7d window since {since}")

    raw_rows = []
    for name, repo, _lang in TRACKED:
        print(f"[{_ts()}]   fetching {repo} ...")
        raw_rows.append(fetch_repo_stats(repo, since))
        time.sleep(0.2)

    baseline = load_baseline_snapshot()
    if baseline:
        print(f"[{_ts()}] Baseline: {baseline.get('updated_at', 'unknown')} (for 7d deltas)")
    else:
        print(f"[{_ts()}] No eligible baseline yet; deltas render as '—' until next run")

    snapshot = build_snapshot(raw_rows, baseline)

    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_FILE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{_ts()}] Wrote {SNAPSHOT_FILE}")

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    archive = HISTORY_DIR / f"{today}.json"
    archive.write_text(
        json.dumps({"updated_at": snapshot["updated_at"], "_raw": raw_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[{_ts()}] Archived {archive}")


if __name__ == "__main__":
    main()
