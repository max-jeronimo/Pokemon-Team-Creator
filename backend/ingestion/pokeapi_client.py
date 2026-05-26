import time
import httpx

BASE_URL = "https://pokeapi.co/api/v2"

# Politeness: small delay between calls, retry on transient failures
REQUEST_DELAY = 0.05      # seconds between requests
MAX_RETRIES = 4
RETRY_BACKOFF = 2.0       # exponential: 2s, 4s, 8s, ...

_client = httpx.Client(timeout=30.0)


def get(endpoint: str) -> dict:
    """
    GET a PokeAPI endpoint (relative path or full URL).
    Retries on network errors and 5xx/429 with exponential backoff.
    """
    url = endpoint if endpoint.startswith("http") else f"{BASE_URL}/{endpoint}"

    for attempt in range(MAX_RETRIES):
        try:
            resp = _client.get(url)
            if resp.status_code == 200:
                time.sleep(REQUEST_DELAY)
                return resp.json()
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = RETRY_BACKOFF ** attempt
                print(f"  [{resp.status_code}] retrying in {wait:.0f}s: {url}")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except httpx.RequestError as e:
            wait = RETRY_BACKOFF ** attempt
            print(f"  [network error] {e} — retrying in {wait:.0f}s")
            time.sleep(wait)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries: {url}")

def get_bytes(endpoint: str) -> bytes:
    """
    GET raw bytes from a URL (for downloading .gz files).
    Same retry/backoff behavior as get().
    """
    url = endpoint if endpoint.startswith("http") else f"{BASE_URL}/{endpoint}"

    for attempt in range(MAX_RETRIES):
        try:
            resp = _client.get(url)
            if resp.status_code == 200:
                time.sleep(REQUEST_DELAY)
                return resp.content
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = RETRY_BACKOFF ** attempt
                print(f"  [{resp.status_code}] retrying in {wait:.0f}s: {url}")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except httpx.RequestError as e:
            wait = RETRY_BACKOFF ** attempt
            print(f"  [network error] {e} — retrying in {wait:.0f}s")
            time.sleep(wait)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries: {url}")

def get_all_resource_urls(endpoint: str) -> list[str]:
    """
    Walk a paginated list endpoint (e.g. 'move', 'ability') and return
    every resource's detail URL.
    """
    urls = []
    next_url = f"{endpoint}?limit=200"
    while next_url:
        data = get(next_url)
        urls.extend(item["url"] for item in data["results"])
        next_url = data.get("next")
    return urls