"""Resolves Smogon chaos-file Pokemon names to integer pokemon.id values.

Resolution order:
  1. Direct normalized match on full name.
  2. Explicit suffix-translation override (form-name mismatches).
  3. Default-form fallback: match base_name where is_default=true.
  4. Skip known non-Pokemon keys (e.g. 'empty').
  Otherwise: record as unmatched.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from supabase_client import get_supabase  # noqa: E402

# Smogon name keys that are NOT pokemon — skip silently.
SKIP_KEYS = {"empty", "nothing"}

# Explicit overrides: normalized Smogon name -> normalized DB full name.
# Only for cases that don't resolve via direct match or base-name default.
OVERRIDES = {
    "necrozmaduskmane": "necrozmadusk",
    "necrozmadawnwings": "necrozmadawn",
    "taurospaldeaaqua": "taurospaldeaaquabreed",
    "taurospaldeablaze": "taurospaldeablazebreed",
    "taurospaldeacombat": "taurospaldeacombatbreed",
    "basculegionf": "basculegionfemale",
    "oinkolognef": "oinkolognefemale",
    "indeedeef": "indeedeefemale",
    "meowsticmmega": "meowsticmega",
    "meowsticfmega": "meowsticmega",
     "ogerponwellspring": "ogerponwellspringmask",      
    "ogerponhearthflame": "ogerponhearthflamemask",    
    "ogerponcornerstone": "ogerponcornerstonemask",    
}


def _normalize(name: str) -> str:
    name = name.lower().replace("\u2019", "'")
    return re.sub(r"[\s\-_.':]", "", name)


class NameResolver:
    def __init__(self, supabase):
        self.supabase = supabase
        self._by_norm: dict[str, int] = {}        # normalized full name -> id
        self._by_base_default: dict[str, int] = {}  # normalized base_name -> id (default form)
        self._unmatched: dict[str, int] = {}
        self._build_lookup()

    def _build_lookup(self):
        rows = []
        page, size = 0, 1000
        while True:
            resp = (
                self.supabase.table("pokemon")
                .select("id,name,is_default,base_name")
                .range(page * size, page * size + size - 1)
                .execute()
            )
            batch = resp.data or []
            rows.extend(batch)
            if len(batch) < size:
                break
            page += 1

        for r in rows:
            self._by_norm[_normalize(r["name"])] = r["id"]
            if r.get("is_default") and r.get("base_name"):
                self._by_base_default[_normalize(r["base_name"])] = r["id"]

        print(f"NameResolver: {len(self._by_norm)} names, "
              f"{len(self._by_base_default)} default-form base names.")

    def resolve(self, smogon_name: str) -> int | None:
        norm = _normalize(smogon_name)

        if norm in SKIP_KEYS:
            return None  # non-pokemon key, skip silently (not counted as miss)

        # 1. direct match
        if norm in self._by_norm:
            return self._by_norm[norm]

        # 2. explicit override
        if norm in OVERRIDES:
            target = OVERRIDES[norm]
            if target in self._by_norm:
                return self._by_norm[target]

        # 3. default-form fallback (bare species name -> default form)
        if norm in self._by_base_default:
            return self._by_base_default[norm]

        # miss
        self._unmatched[smogon_name] = self._unmatched.get(smogon_name, 0) + 1
        return None

    def report(self):
        if not self._unmatched:
            print("NameResolver: all names resolved, no misses.")
            return
        print(f"\nNameResolver: {len(self._unmatched)} unmatched:")
        for name, count in sorted(self._unmatched.items(), key=lambda kv: -kv[1]):
            print(f"  {count:>5}x  {name}  (norm: {_normalize(name)})")


if __name__ == "__main__":
    sb = get_supabase()
    r = NameResolver(sb)
    for t in ["Incineroar", "Urshifu", "Urshifu-Rapid-Strike", "Landorus",
              "Necrozma-Dusk-Mane", "Tauros-Paldea-Aqua", "Indeedee-F",
              "Meowstic-F-Mega", "empty"]:
        print(f"  {t:24} -> {r.resolve(t)}")
    r.report()