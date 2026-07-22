"""허브 콘솔: 다이아로 공용 특성(HP/물공/마공) 영구 해금.

python3 hub.py         -> 번호로 직접 구매
python3 hub.py --auto  -> 구매 가능한 특성을 무작위로 사들임 (검증용)
"""

import random
import sys
from pathlib import Path

from game.hub import TRAIT_TREE, all_traits, is_purchasable
from game.save_system import load_meta, save_meta

SAVE_PATH = Path(__file__).parent / "saves" / "meta_save.json"

_LINE_LABEL = {"hp": "체력", "atk": "공격력", "def": "방어력", "gold": "재화"}


def render_tree(owned: set) -> None:
    for line_key, ranks in TRAIT_TREE.items():
        print(f"\n[{_LINE_LABEL[line_key]}]")
        for rank in ranks:
            if rank.id in owned:
                status = "보유"
            elif is_purchasable(rank, owned):
                status = "구매 가능"
            else:
                status = "잠김 (이전 단계 필요)"
            print(f"  {rank.id} ({rank.tier}단계) {rank.name}: {rank.desc} - {rank.cost} 다이아 [{status}]")


def main() -> None:
    auto = "--auto" in sys.argv
    meta = load_meta(SAVE_PATH)
    owned = set(meta["unlocked_traits"])
    diamond = meta["total_diamond"]

    print(f"보유 다이아: {diamond}")
    render_tree(owned)

    if auto:
        traits = all_traits()
        random.shuffle(traits)
        changed = True
        while changed:
            changed = False
            for trait in traits:
                if is_purchasable(trait, owned) and trait.cost <= diamond:
                    diamond -= trait.cost
                    owned.add(trait.id)
                    print(f"(자동 구매) {trait.name} - {trait.cost} 다이아 소모 (잔여 {diamond})")
                    changed = True
    else:
        print("\n구매할 특성 id를 입력하세요 (예: hp_1), 종료는 q")
        while True:
            raw = input("> ").strip()
            if raw.lower() == "q":
                break
            trait = next((t for t in all_traits() if t.id == raw), None)
            if trait is None:
                print("존재하지 않는 특성 id입니다.")
                continue
            if not is_purchasable(trait, owned):
                print("구매할 수 없는 특성입니다 (이미 보유했거나 선행 단계가 없습니다).")
                continue
            if trait.cost > diamond:
                print("다이아가 부족합니다.")
                continue
            diamond -= trait.cost
            owned.add(trait.id)
            print(f"구매 완료: {trait.name} (잔여 다이아 {diamond})")
            render_tree(owned)

    meta["total_diamond"] = diamond
    meta["unlocked_traits"] = sorted(owned)
    save_meta(SAVE_PATH, meta)
    print(f"\n저장 완료. 보유 다이아 {diamond}, 해금 특성 {len(owned)}개")
    print(f"저장 위치: {SAVE_PATH}")


if __name__ == "__main__":
    main()
