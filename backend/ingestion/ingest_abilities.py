import sys
from pathlib import Path

# allow importing supabase_client from backend/
sys.path.append(str(Path(__file__).resolve().parent.parent))

from tqdm import tqdm
from supabase_client import get_supabase
from ingestion import pokeapi_client as api


def english(entries, key="effect"):
    """Pull the English text from a list of localized entries."""
    for e in entries:
        lang = e.get("language", {}).get("name")
        if lang == "en":
            return e.get(key) or e.get("short_effect") or e.get("flavor_text")
    return None


def ingest_abilities():
    supabase = get_supabase()
    urls = api.get_all_resource_urls("ability")
    print(f"Found {len(urls)} abilities.")

    batch = []
    for url in tqdm(urls, desc="Abilities"):
        a = api.get(url)
        description = english(a.get("effect_entries", []), key="short_effect")
        batch.append({
            "id": a["name"],                    # text PK, e.g. 'intimidate'
            "name": a["name"].replace("-", " ").title(),
            "description": description,
        })
        if len(batch) >= 50:
            supabase.table("abilities").upsert(batch).execute()
            batch = []

    if batch:
        supabase.table("abilities").upsert(batch).execute()
    print("Abilities done.")


if __name__ == "__main__":
    ingest_abilities()