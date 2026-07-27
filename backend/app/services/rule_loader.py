import json
from functools import lru_cache
from pathlib import Path
from typing import Any

RULES_DIR = Path(__file__).resolve().parents[1] / "data" / "rules"


@lru_cache
def load_rule_file(file_name: str) -> Any:
    with (RULES_DIR / file_name).open(encoding="utf-8") as rule_file:
        return json.load(rule_file)

