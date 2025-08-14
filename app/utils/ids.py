import hashlib
from datetime import datetime

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def urn(namespace: str, *parts: str) -> str:
    base = "|".join(parts)
    return f"urn:mna:{namespace}:{sha256_str(base)}"

def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
