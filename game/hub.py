"""허브 - 공용 특성 트리 (기획서 6.3절: 다이아로 해금하는 영구 스탯 강화).

라인(hp/atk_phys/atk_magic)별로 랭크가 순차 배치되며, 하위 랭크를 먼저 사야
다음 랭크가 구매 가능해진다. 캐릭터별 특성은 이번 범위에서 제외.
가격/수치는 초기 플레이스홀더이며 밸런싱은 추후 조정 대상.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TraitRank:
    id: str
    name: str
    stat: str  # Stats 필드명 (hp / atk_phys / atk_magic)
    amount: int
    cost: int
    requires: Optional[str]  # 선행 랭크 id (None이면 최하위)


def _line(prefix: str, label: str, stat: str, steps: list[tuple[int, int]]) -> list[TraitRank]:
    ranks = []
    prev_id = None
    for idx, (amount, cost) in enumerate(steps, start=1):
        rank_id = f"{prefix}_{idx}"
        ranks.append(TraitRank(id=rank_id, name=f"{label} {idx}단계", stat=stat, amount=amount, cost=cost, requires=prev_id))
        prev_id = rank_id
    return ranks


TRAIT_TREE: dict[str, list[TraitRank]] = {
    "hp": _line("hp", "체력 강화", "hp", [(15, 30), (20, 60), (30, 100), (40, 160), (60, 250)]),
    "atk_phys": _line("atk_phys", "물리공격력 강화", "atk_phys", [(3, 30), (4, 60), (6, 100), (8, 160), (12, 250)]),
    "atk_magic": _line("atk_magic", "마법공격력 강화", "atk_magic", [(3, 30), (4, 60), (6, 100), (8, 160), (12, 250)]),
}


def all_traits() -> list[TraitRank]:
    return [rank for line in TRAIT_TREE.values() for rank in line]


def get_trait(trait_id: str) -> Optional[TraitRank]:
    for rank in all_traits():
        if rank.id == trait_id:
            return rank
    return None


def is_purchasable(trait: TraitRank, owned_ids: set) -> bool:
    if trait.id in owned_ids:
        return False
    return trait.requires is None or trait.requires in owned_ids


def apply_unlocked_traits(character, owned_ids: list) -> None:
    owned = set(owned_ids)
    for trait in all_traits():
        if trait.id in owned:
            current = getattr(character.base_stats, trait.stat)
            setattr(character.base_stats, trait.stat, current + trait.amount)
