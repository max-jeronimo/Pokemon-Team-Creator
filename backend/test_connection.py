from supabase_client import get_supabase


def test_connection():
    supabase = get_supabase()
    print("Client created successfully.\n")

    # 1. READ test: your formats table already has VGC Reg I seeded
    print("Reading from 'formats' table...")
    result = supabase.table("formats").select("*").execute()
    print(f"  Found {len(result.data)} format(s):")
    for fmt in result.data:
        print(f"    - {fmt['id']}: {fmt['name']}")
    print()

    # 2. WRITE + READ + DELETE test on a throwaway abilities row
    print("Testing write/read/delete on 'abilities'...")
    test_id = "test-connection-ability"

    # Insert
    supabase.table("abilities").insert({
        "id": test_id,
        "name": "Test Connection Ability",
        "description": "Temporary row to verify write access. Safe to delete.",
    }).execute()
    print("  Insert OK")

    # Read it back
    read_back = supabase.table("abilities").select("*").eq("id", test_id).execute()
    assert len(read_back.data) == 1, "Could not read back inserted row"
    print(f"  Read OK: {read_back.data[0]['name']}")

    # Clean up
    supabase.table("abilities").delete().eq("id", test_id).execute()
    print("  Delete OK (cleaned up test row)")
    print()

    print("✅ Connection fully verified — read, write, and delete all work.")


if __name__ == "__main__":
    test_connection()