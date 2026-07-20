"""메타 자원 저장/로드 (기획서 7장): 로컬 JSON 파일만 사용.

골드는 런 한정 자원이라 저장 대상이 아니며, 다이아만 영구 저장된다.
유물은 런 한정이라 마찬가지로 저장하지 않는다.
"""

import json
from pathlib import Path

DEFAULT_META = {
    "total_diamond": 0,
    "unlocked_traits": [],
    "unlocked_classes": ["rogue"],
    "unlocked_themes": [],
}


def load_meta(path: Path) -> dict:
    if not path.exists():
        return dict(DEFAULT_META)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_meta(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
