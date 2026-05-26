"""Diagnostic: resolve all names in the chaos files against the real pokemon
table and report match rate + every miss. Uses the shared chaos_loader
(local cache, else fetch from Smogon). No DB writes.

Run from backend/ with venv active:
    python -m ingestion.diagnose_matching
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from supabase_client import get_supabase
from ingestion.chaos_loader import load_chaos


# Names where a hyphen is intrinsic to the name, NOT a form separator.
INTRINSIC = {"chiyu", "chienpao", "wochien", "hooh", "kommoo", "porygonz"}


def norm(s: str) -> str:
    """Lowercase, strip punctuation/spaces/hyphens so spellings converge."""
    s = s.lower().replace("\u2019", "'")
    return re.sub(r"[\s\-_.':]", "", s)


def load_db(supabase):
    """Load pokemon table into two lookups:
       - by_norm: normalized full name -> id
       - by_base_default: normalized base_name -> id (default form only)
    """
    by_norm, by_base_default = {}, {}
    rows = []
    page, size = 0, 1000
    while True:
        resp = (
            supabase.table("pokemon")
            .select("id,name,is_default,base_name")
            .range(page * size, page * size + size - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < size:
            break
        page += 1

    for r in rows:
        by_norm[norm(r["name"])] = r["id"]
        if r.get("is_default") and r.get("base_name"):
            by_base_default[norm(r["base_name"])] = r["id"]

    return by_norm, by_base_default, len(rows)


def main():
    sb = get_supabase()
    by_norm, by_base_default, n = load_db(sb)
    print(f"Loaded {n} pokemon. {len(by_base_default)} have base_name+is_default set.\n")

    # (month_dir, filename) pairs — loader reads local cache or fetches
    FORMATS = [
        ("2026-04", "gen9vgc2026regibo3-1760.json"),
        ("2026-04", "gen9vgc2026regfbo3-1760.json"),
        ("2026-04", "gen9championsvgc2026regmabo3-1760.json"),
    ]

    names = set()
    for month_dir, fn in FORMATS:
        d = load_chaos(month_dir, fn)
        names |= set(d["data"].keys())
        for e in d["data"].values():
            names |= set(e.get("Teammates", {}).keys())

    if not names:
        print("No names loaded — check the chaos files / loader.")
        return

    matched, missed = 0, []
    for nm in sorted(names):
        nn = norm(nm)
        if nn in by_norm or nn in by_base_default:
            matched += 1
        else:
            missed.append(nm)

    print(f"MATCHED {matched}/{len(names)}  ({100 * matched / len(names):.1f}%)")
    print(f"\nMISSED ({len(missed)}):")
    for m in missed:
        print(f"  {m}   (norm: {norm(m)})")


if __name__ == "__main__":
    main()