"""One-click entry to refresh every data source the site consumes.

Running stages (each is a separate subprocess so a failure in one stage does
not abort the others — every stage prints its own log):

  1. scratch_sync.py          skills + featured list     -> skills.json, public/featured.json
  2. generate_pages.py        paginated skills JSON      -> public/skills_pages/*.json
  3. sync_openrouter_models   LLM leaderboard + icons    -> public/models_ranking.json, public/models_icons/
  4. ranking_sync.py          lobster-agents leaderboard -> public/ranking_snapshot.json, public/ranking_history/
  5. sync_whichclaw.py        English site aggregator    -> whichclaw/public/skills.json, paginated + mirrors (3)+(4)

Usage:
    python sync.py             # run everything
    python sync.py skills      # only stages 1 & 2
    python sync.py models      # only stage 3
    python sync.py ranking     # only stage 4
    python sync.py whichclaw   # only stage 5 (run after stages 3 and 4 so mirrors are fresh)

Each stage exits non-zero on error but we keep going so you can still commit
whatever got refreshed. The final line reports which stages failed.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

STAGES = {
    # Refreshing Chinese skills also refreshes the English side — the
    # filter step reads the freshly-written skills.json. One command,
    # two sites.
    "skills":    [("scratch_sync.py",           "fetch skills"),
                  ("generate_pages.py",         "paginate skills"),
                  ("sync_whichclaw.py",         "english filter + mirror")],
    "models":    [("sync_openrouter_models.py", "LLM leaderboard")],
    "ranking":   [("ranking_sync.py",           "lobster ranking")],
    "whichclaw": [("sync_whichclaw.py",         "english filter + mirror")],
    # Manual-only: rewrites whichclaw/*.html from Chinese HTML via a
    # translation dictionary. Destructive, so it is NOT chained.
    # Run with: python sync_html.py   (after editing Chinese HTML)
}


def run_stage(script: str, label: str) -> bool:
    print(f"\n===== {label} ({script}) =====")
    script_path = HERE / script
    if not script_path.exists():
        print(f"  SKIP: {script_path} not found")
        return False
    try:
        subprocess.run([sys.executable, str(script_path)], check=True, cwd=HERE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  FAIL: exit code {e.returncode}")
        return False


def main() -> int:
    requested = [a.lower() for a in sys.argv[1:]] or list(STAGES.keys())
    unknown = [r for r in requested if r not in STAGES]
    if unknown:
        print(f"Unknown stage(s): {unknown}. Valid: {list(STAGES.keys())}")
        return 2

    failures = []
    for group in requested:
        for script, label in STAGES[group]:
            if not run_stage(script, label):
                failures.append(script)

    print("\n===== summary =====")
    if failures:
        print(f"  Failed: {failures}")
        return 1
    print("  All stages OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
