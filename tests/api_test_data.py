from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parent.parent / "test_data" / "fakestore.json"


def _load() -> dict[str, Any]:
    return json.loads(_DATA_PATH.read_text())


API_TEST_DATA = _load()
