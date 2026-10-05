import json
from typing import Any


def parse_portkey_config(value: str | None) -> dict[str, Any] | None:
    if not value or not value.strip():
        return None

    try:
        config = json.loads(value)
    except json.JSONDecodeError:
        return None

    return config if isinstance(config, dict) and config else None