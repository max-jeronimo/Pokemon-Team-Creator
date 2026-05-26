import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from tqdm import tqdm
from supabase_client import get_supabase
from ingestion import pokeapi_client as api

STAT_KEYS = {
    "hp": "hp",
    "attack": "atk",
    "defense": "def",
    "special-attack": "spa",
    "special-defense": "spd",
    "speed": "spe",
}


def build_row(p: dict, species: dict) -> dict:
    stats = {STAT_KEYS[s["stat"]["name"]]: s["base_stat"]
             for s in p["stats"] if s["stat"]["name"] in STAT_KEYS}

    types = sorted(p["types"], key=lambda t: t["slot"])
    type1 = types[0]["type"]["name"]
    type2 = types[1]["type"]["name"] if len(types) > 1 else None

    abilities = [a["ability"]["name"].replace("-", " ").title()
                 for a in p["abilities"]]

    sprite = (p.get("sprites", {})
              .get("other", {})
              .get("official-artwork", {})
              .get("front_default")) or p.get("sprites", {}).get("front_default")

    return {
        "id": p["id"],
        "name": p["name"].replace("-", " ").title(),
        "type1": type1,
        "type2": type2,
        "hp": stats.get("hp", 0),
        "atk": stats.get("atk", 0),
        "def": stats.get("def", 0),
        "spa": stats.get("spa", 0),
        "spd": stats.get("spd", 0),
        "spe": stats.get("spe", 0),
        "abilities": abilities,
        "is_legendary": species.get("is_legendary", False),
        "is_mythical": species.get("is_mythical", False),
        "is_paradox": False,
        "sprite_url": sprite,
        "is_default": p.get("is_default", False),                 
        "base_name": species["name"].replace("-", " ").title(),  
    }


def ingest_pokemon():
    supabase = get_supabase()
    urls = api.get_all_resource_urls("pokemon")
    print(f"Found {len(urls)} pokemon entries (including forms).")

    batch = []
    default_count = 0
    for url in tqdm(urls, desc="Pokemon"):
        p = api.get(url)
        species = api.get(p["species"]["url"])
        row = build_row(p, species)
        if row["is_default"]:
            default_count += 1
        batch.append(row)
        if len(batch) >= 25:
            supabase.table("pokemon").upsert(batch).execute()
            batch = []

    if batch:
        supabase.table("pokemon").upsert(batch).execute()
    print(f"Pokemon done. {default_count} marked is_default=true.")


if __name__ == "__main__":
    ingest_pokemon()