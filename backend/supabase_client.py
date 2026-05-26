import os
from functools import lru_cache
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


@lru_cache
def get_supabase() -> Client:
    """
    Returns a cached Supabase client using the SECRET key *admin use only*
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")

    if not url or not key:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_SECRET_KEY in backend/.env"
        )

    return create_client(url, key)