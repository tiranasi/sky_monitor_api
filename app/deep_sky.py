from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "deep_sky_catalog.json"
DEEP_SKY_OBJECTS: List[Dict[str, Any]] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def get_deep_sky_objects() -> List[Dict[str, Any]]:
    return [dict(item) for item in DEEP_SKY_OBJECTS]
