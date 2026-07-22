"""상점 판매 목록 생성.

장비 5개 + 유물 3개를 제공한다. 5개 중 하나는 반드시 플레이어가 현재 가장 많이 보유한(=가장 높은
시너지 단계에 있는) 태그를 가진 장비로 보장한다 — 이미 장착한 부위와 슬롯이 겹쳐도 무방하다(교체 구매용).

장비 등급(일반/희귀/유니크/레전더리)은 장(act)별 확률표로 슬롯마다 독립적으로 굴린다 — 3장으로
갈수록 유니크/레전더리 비중이 커진다. 일반전투 보상도 같은 표를 쓰고, 엘리트 전투 보상은 더 높은
등급 쪽으로 치우친 별도 표를 쓴다.

가격/확률은 초기 플레이스홀더 수치이며 밸런싱은 추후 조정 대상.
"""

import random
from dataclasses import dataclass

from game.content import RELIC_POOL, SAMPLE_ITEMS
from game.models import Character, Item, Relic

PRICE_BY_RARITY = {"common": 25, "rare": 55, "unique": 100, "legendary": 180}
RELIC_PRICE = 45
REROLL_COST = 20  # 상점 진열을 통째로 새로 뽑는 데 드는 골드 (품절 여부 무관)

# 장(act)별 등급 드롭률 — 상점 진열과 일반전투 보상이 공유한다.
ITEM_RARITY_WEIGHTS = {
    1: {"common": 70, "rare": 25, "unique": 5, "legendary": 0},
    2: {"common": 45, "rare": 35, "unique": 18, "legendary": 2},
    3: {"common": 25, "rare": 35, "unique": 30, "legendary": 10},
}

# 엘리트 전투 보상 전용 — 일반 표보다 상급 등급 쪽으로 치우친다.
ELITE_ITEM_RARITY_WEIGHTS = {
    1: {"common": 30, "rare": 50, "unique": 20, "legendary": 0},
    2: {"common": 10, "rare": 45, "unique": 35, "legendary": 10},
    3: {"common": 0, "rare": 35, "unique": 40, "legendary": 25},
}


def roll_item_rarity(act: int, elite: bool = False) -> str:
    table = ELITE_ITEM_RARITY_WEIGHTS if elite else ITEM_RARITY_WEIGHTS
    weights = table[act]
    return random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]


@dataclass
class ShopOffer:
    items: list[tuple[Item, int]]
    relics: list[tuple[Relic, int]]


def _dominant_tag(character: Character):
    tags = character.equipped_tags()
    if not tags:
        return None
    counts: dict[str, int] = {}
    for tag in tags:
        counts[tag] = counts.get(tag, 0) + 1
    top_count = max(counts.values())
    top_tags = [tag for tag, count in counts.items() if count == top_count]
    return random.choice(top_tags)


def _pick_item_by_rarity(rarity: str, exclude_names: set) -> Item:
    candidates = [i for i in SAMPLE_ITEMS if i.rarity == rarity and i.name not in exclude_names]
    if not candidates:
        candidates = [i for i in SAMPLE_ITEMS if i.name not in exclude_names] or SAMPLE_ITEMS
    return random.choice(candidates)


ITEM_SLOT_COUNT = 5


def generate_shop_offer(character: Character, act: int) -> ShopOffer:
    dominant = _dominant_tag(character)
    guaranteed = None
    if dominant:
        candidates = [i for i in SAMPLE_ITEMS if dominant in i.tags]
        if candidates:
            rarity = roll_item_rarity(act)
            rarity_candidates = [i for i in candidates if i.rarity == rarity] or candidates
            guaranteed = random.choice(rarity_candidates)

    selected: list[Item] = [guaranteed] if guaranteed else []
    for _ in range(ITEM_SLOT_COUNT - len(selected)):
        exclude = {i.name for i in selected}
        rarity = roll_item_rarity(act)
        selected.append(_pick_item_by_rarity(rarity, exclude))

    priced_items = [(item, PRICE_BY_RARITY[item.rarity]) for item in selected]
    relic_choices = random.sample(RELIC_POOL, min(3, len(RELIC_POOL)))
    priced_relics = [(relic, RELIC_PRICE) for relic in relic_choices]

    return ShopOffer(items=priced_items, relics=priced_relics)


def build_shop_entries(offer: ShopOffer) -> list[dict]:
    """ShopOffer를 구매/품절 상태를 담을 수 있는 가변 항목 목록으로 변환한다."""
    entries = [{"kind": "item", "obj": item, "price": price, "sold": False} for item, price in offer.items]
    entries += [{"kind": "relic", "obj": relic, "price": price, "sold": False} for relic, price in offer.relics]
    return entries


def reroll_all_entries(entries: list[dict], act: int) -> None:
    """상점 진열을 품절 여부와 무관하게 전부 새로 뽑는다 (등급도 장 확률표로 다시 굴림)."""
    for entry in entries:
        current_names = {e["obj"].name for e in entries}
        if entry["kind"] == "item":
            rarity = roll_item_rarity(act)
            new_obj = _pick_item_by_rarity(rarity, current_names)
            entry["obj"] = new_obj
            entry["price"] = PRICE_BY_RARITY[new_obj.rarity]
        else:
            pool = [r for r in RELIC_POOL if r.name not in current_names] or RELIC_POOL
            new_obj = random.choice(pool)
            entry["obj"] = new_obj
            entry["price"] = RELIC_PRICE
        entry["sold"] = False
