import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from tqdm import tqdm
from supabase_client import get_supabase
from ingestion import pokeapi_client as api


def english_flavor(entries):
    for e in entries:
        if e.get("language", {}).get("name") == "en":
            return e.get("flavor_text", "").replace("\n", " ").replace("\f", " ")
    return None


def ingest_moves():
    supabase = get_supabase()
    urls = api.get_all_resource_urls("move")
    print(f"Found {len(urls)} moves.")

    batch = []
    for url in tqdm(urls, desc="Moves"):
        m = api.get(url)
        batch.append({
            "id": m["name"],                                  # 'flare-blitz'
            "name": m["name"].replace("-", " ").title(),
            "type": m["type"]["name"],
            "category": m["damage_class"]["name"],            # physical/special/status
            "power": m.get("power"),
            "accuracy": m.get("accuracy"),
            "pp": m.get("pp") or 0,
            "priority": m.get("priority", 0),
            "description": english_flavor(m.get("flavor_text_entries", [])),
        })
        if len(batch) >= 50:
            supabase.table("moves").upsert(batch).execute()
            batch = []

    if batch:
        supabase.table("moves").upsert(batch).execute()
    print("Moves done.")


if __name__ == "__main__":
    ingest_moves()