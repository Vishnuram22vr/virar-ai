import re
import copy
from typing import Any, Dict, List, Union

SENSITIVE_KEY_PATTERNS = [
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"auth", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"bearer", re.IGNORECASE),
]

REDACTED_STR = "[REDACTED]"

def redact_sensitive_data(data: Any) -> Any:
    """
    Recursively scans dictionaries, lists, or strings and redacts sensitive keys or values.
    Ensures no credentials or secrets leak into traces, database, or API responses.
    """
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            k_str = str(k)
            # If the key itself looks like a secret, redact value
            if any(p.search(k_str) for p in SENSITIVE_KEY_PATTERNS):
                cleaned[k] = REDACTED_STR
            else:
                cleaned[k] = redact_sensitive_data(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    elif isinstance(data, str):
        # Check for bearer token patterns or long hex/base64 strings that look like secrets
        if "bearer " in data.lower():
            return re.sub(r'(bearer\s+)[A-Za-z0-9_\-\.]{10,}', r'\1[REDACTED]', data, flags=re.IGNORECASE)
        if "sk-" in data:
            return re.sub(r'sk-[A-Za-z0-9]{15,}', 'sk-[REDACTED]', data)
        return data
    else:
        return data
