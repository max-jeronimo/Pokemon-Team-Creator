"""Ingests Smogon chaos usage-stat JSON into usage_stats, teammate_correlations, counter_correlations."""
import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from tqdm import tqdm
from supabase_client import get_supabase
from ingestion import pokeapi_client as http
from ingestion.name_resolver import NameResolver

STATS_MONTH_BASE = "https://www.smogon.com/stats"

FORMATS_TO_INGEST = [
    {"format_id": "vgc-reg-i-bo3",  "month_dir": "2026-04",
     "file": "gen9vgc2026regibo3-1760.json",          "db_month": "2026-04-01"},
    {"format_id": "vgc-reg-f-bo3",  "month_dir": "2026-04",
     "file": "gen9vgc2026regfbo3-1760.json",           "db_month": "2026-04-01"},
    {"format_id": "vgc-reg-ma-bo3", "month_dir": "2026-04",
     "file": "gen9championsvgc2026regmabo3-1760.json", "db_month": "2026-04-01"},
]

def _dedupe_rows(rows, key_fields, sum_field):
    """Collapse rows sharing the same key (because two Smogon names mapped to
    one pokemon_id). Sums the numeric field; keeps first row's other values."""
    merged = {}
    for r in rows:
        key = tuple(r[k] for k in key_fields)
        if key in merged:
            merged[key][sum_field] = round(merged[key][sum_field] + r[sum_field], 3)
        else:
            merged[key] = dict(r)
    return list(merged.values())


def _top_n_as_pct(counts: dict, n: int = 12) -> list[dict]:
    total = sum(counts.values())
    if total <= 0:
        return []
    items = sorted(counts.items(), key=lambda kv: -kv[1])[:n]
    return [{"name": k, "pct": round(100.0 * v / total, 3)} for k, v in items]


def _fetch_chaos(month_dir: str, filename: str) -> dict:
    url = f"{STATS_MONTH_BASE}/{month_dir}/chaos/{filename}"
    print(f"Fetching {url}")
    return http.get(url)


def ingest_one_format(cfg, supabase, resolver, dry_run):
    chaos = _fetch_chaos(cfg["month_dir"], cfg["file"])
    data = chaos.get("data", {})
    fmt = cfg["format_id"]
    month = cfg["db_month"]
    print(f"  {len(data)} pokemon entries in {cfg['file']}")

    usage_rows, teammate_rows, counter_rows = [], [], []
    ranked = sorted(data.items(), key=lambda kv: -kv[1].get("usage", 0))

    for rank, (smogon_name, entry) in enumerate(tqdm(ranked, desc=f"  {fmt}"), start=1):
        pid = resolver.resolve(smogon_name)
        if pid is None:
            continue
        usage_rows.append({
            "pokemon_id": pid, "format_id": fmt, "month": month, "rank": rank,
            "usage_pct": round(100.0 * entry.get("usage", 0), 3),
            "raw_count": entry.get("Raw count"),
            "common_items": _top_n_as_pct(entry.get("Items", {})),
            "common_abilities": _top_n_as_pct(entry.get("Abilities", {})),
            "common_moves": _top_n_as_pct(entry.get("Moves", {}), n=16),
            "common_spreads": _top_n_as_pct(entry.get("Spreads", {})),
            "common_tera_types": _top_n_as_pct(entry.get("Tera Types", {})),
        })
        teammates = entry.get("Teammates", {})
        t_total = sum(v for v in teammates.values() if v > 0) or 1
        for mate_name, w in teammates.items():
            if w <= 0:
                continue
            mate_id = resolver.resolve(mate_name)
            if mate_id is None or mate_id == pid:
                continue
            teammate_rows.append({
                "pokemon_id": pid, "teammate_id": mate_id, "format_id": fmt,
                "month": month, "correlation": round(100.0 * w / t_total, 3),
            })
        counters = entry.get("Checks and Counters", {})
        for opp_name, arr in counters.items():
            if not isinstance(arr, list) or len(arr) < 2:
                continue
            opp_id = resolver.resolve(opp_name)
            if opp_id is None or opp_id == pid:
                continue
            win_rate = round(100.0 * arr[1], 3) if arr[1] is not None else None
            extra = round(100.0 * arr[2], 3) if len(arr) > 2 and arr[2] is not None else None
            counter_rows.append({
                "pokemon_id": pid, "opponent_id": opp_id, "format_id": fmt,
                "month": month, "win_rate": win_rate, "ko_rate": extra, "switch_rate": None,
            })

    print(f"  resolved -> {len(usage_rows)} usage, {len(teammate_rows)} teammate, {len(counter_rows)} counter rows")
    usage_rows = _dedupe_rows(usage_rows, ["pokemon_id", "format_id", "month"], "usage_pct")
    teammate_rows = _dedupe_rows(teammate_rows, ["pokemon_id", "teammate_id", "format_id", "month"], "correlation")
    counter_rows = _dedupe_rows(counter_rows, ["pokemon_id", "opponent_id", "format_id", "month"], "win_rate")

    print(f"  after dedupe -> {len(usage_rows)} usage, "
          f"{len(teammate_rows)} teammate, {len(counter_rows)} counter rows")

    if dry_run:
        print("  [dry-run] no writes performed.")
        return
    _upsert_batched(supabase, "usage_stats", usage_rows, "pokemon_id,format_id,month")
    _upsert_batched(supabase, "teammate_correlations", teammate_rows, "pokemon_id,teammate_id,format_id,month")
    _upsert_batched(supabase, "counter_correlations", counter_rows, "pokemon_id,opponent_id,format_id,month")
    print(f"  wrote {fmt}.")


def _upsert_batched(supabase, table, rows, on_conflict, size=500):
    for i in range(0, len(rows), size):
        supabase.table(table).upsert(rows[i:i + size], on_conflict=on_conflict).execute()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    supabase = get_supabase()
    resolver = NameResolver(supabase)
    for cfg in FORMATS_TO_INGEST:
        print(f"\n=== {cfg['format_id']} ({cfg['file']}) ===")
        ingest_one_format(cfg, supabase, resolver, dry_run=args.dry_run)
    resolver.report()
    print("\nDone.")


if __name__ == "__main__":
    main()