"""Shared loader for Smogon chaos files: local .json cache, else fetch .gz,
decompress, cache, return parsed dict."""
import gzip
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from ingestion import pokeapi_client as http

CHAOS_DIR = Path(__file__).resolve().parent.parent / "CHAOS_FILES"
STATS_BASE = "https://www.smogon.com/stats"


def load_chaos(month_dir: str, filename: str) -> dict:
    """Return parsed chaos JSON. Reads local cache if present, else fetches
    the .gz from Smogon, decompresses, caches the .json, and returns it."""
    CHAOS_DIR.mkdir(parents=True, exist_ok=True)
    local_json = CHAOS_DIR / filename

    if local_json.exists():
        with open(local_json, "r", encoding="utf-8") as fh:
            return json.load(fh)

    gz_url = f"{STATS_BASE}/{month_dir}/chaos/{filename}.gz"
    print(f"  cache miss -> fetching {gz_url}")
    raw_gz = http.get_bytes(gz_url)
    text = gzip.decompress(raw_gz).decode("utf-8")

    with open(local_json, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"  cached -> {local_json}")

    return json.loads(text)