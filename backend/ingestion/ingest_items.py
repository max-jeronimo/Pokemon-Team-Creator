import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from tqdm import tqdm
from supabase_client import get_supabase
from ingestion import pokeapi_client as api


def english_effect(entries):
    for e in entries:
        if e.get("language", {}).get("name") == "en":
            return e.get("short_effect") or e.get("effect")
    return None


def ingest_items():
    supabase = get_supabase()
    urls = api.get_all_resource_urls("item")
    print(f"Found {len(urls)} items.")

    batch = []
    for url in tqdm(urls, desc="Items"):
        it = api.get(url)
        category = it.get("category", {}).get("name")
        batch.append({
            "id": it["name"],                                 # 'choice-scarf'
            "name": it["name"].replace("-", " ").title(),
            "description": english_effect(it.get("effect_entries", [])),
            "category": category,
        })
        if len(batch) >= 50:
            supabase.table("items").upsert(batch).execute()
            batch = []

    if batch:
        supabase.table("items").upsert(batch).execute()
    print("Items done.")


if __name__ == "__main__":
    ingest_items()