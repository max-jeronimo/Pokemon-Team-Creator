import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from ingestion.ingest_abilities import ingest_abilities
from ingestion.ingest_moves import ingest_moves
from ingestion.ingest_items import ingest_items
from ingestion.ingest_pokemon import ingest_pokemon


def main():
    print("=== Ingesting abilities ===")
    ingest_abilities()
    print("\n=== Ingesting moves ===")
    ingest_moves()
    print("\n=== Ingesting items ===")
    ingest_items()
    print("\n=== Ingesting pokemon ===")
    ingest_pokemon()
    print("\nAll reference data ingested.")


if __name__ == "__main__":
    main()