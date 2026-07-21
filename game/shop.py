"""상점 판매 목록 생성.

장비 5개(일반 4 / 희귀 1) + 유물 3개를 제공한다.
5개 중 하나는 반드시 플레이어가 현재 가장 많이 보유한(=가장 높은 시너지 단계에 있는)
태그를 가진 장비로 보장한다 — 이미 장착한 부위와 슬롯이 겹쳐도 무방하다(교체 구매용).

가격은 초기 플레이스홀더 수치이며 밸런싱은 추후 조정 대상.
"""

import random
from dataclasses import dataclass

from game.content import RELIC_POOL, SAMPLE_ITEMS
from game.models import Character, Item, Relic

COMMON_PRICE = 25
RARE_PRICE = 55
RELIC_PRICE = 45
REROLL_COST = 20  # 품절(구매 완료)된 슬롯을 새 무작위 항목으로 채우는 데 드는 골드


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


def generate_shop_offer(character: Character) -> ShopOffer:
    commons = [i for i in SAMPLE_ITEMS if i.rarity == "common"]
    rares = [i for i in SAMPLE_ITEMS if i.rarity == "rare"]

    dominant = _dominant_tag(character)
    guaranteed = None
    if dominant:
        candidates = [i for i in SAMPLE_ITEMS if dominant in i.tags]
        if candidates:
            guaranteed = random.choice(candidates)

    selected: list[Item] = [guaranteed] if guaranteed else []
    remaining_commons = [i for i in commons if i is not guaranteed]
    remaining_rares = [i for i in rares if i is not guaranteed]

    if guaranteed and guaranteed.rarity == "rare":
        selected += random.sample(remaining_commons, min(4, len(remaining_commons)))
    elif guaranteed and guaranteed.rarity == "common":
        selected += random.sample(remaining_commons, min(3, len(remaining_commons)))
        if remaining_rares:
            selected.append(random.choice(remaining_rares))
    else:
        selected += random.sample(commons, min(4, len(commons)))
        if rares:
            selected.append(random.choice(rares))

    priced_items = [(item, RARE_PRICE if item.rarity == "rare" else COMMON_PRICE) for item in selected]
    relic_choices = random.sample(RELIC_POOL, min(3, len(RELIC_POOL)))
    priced_relics = [(relic, RELIC_PRICE) for relic in relic_choices]

    return ShopOffer(items=priced_items, relics=priced_relics)


def build_shop_entries(offer: ShopOffer) -> list[dict]:
    """ShopOffer를 구매/품절 상태를 담을 수 있는 가변 항목 목록으로 변환한다."""
    entries = [{"kind": "item", "obj": item, "price": price, "sold": False} for item, price in offer.items]
    entries += [{"kind": "relic", "obj": relic, "price": price, "sold": False} for relic, price in offer.relics]
    return entries


def refill_sold_entries(entries: list[dict]) -> None:
    """품절(구매 완료) 처리된 슬롯을 그 자리에서 새 무작위 항목으로 채운다.
    아직 구매하지 않은 슬롯은 그대로 유지된다."""
    for entry in entries:
        if not entry["sold"]:
            continue
        current_names = {e["obj"].name for e in entries}
        if entry["kind"] == "item":
            pool = [i for i in SAMPLE_ITEMS if i.name not in current_names] or SAMPLE_ITEMS
            new_obj = random.choice(pool)
            entry["obj"] = new_obj
            entry["price"] = RARE_PRICE if new_obj.rarity == "rare" else COMMON_PRICE
        else:
            pool = [r for r in RELIC_POOL if r.name not in current_names] or RELIC_POOL
            new_obj = random.choice(pool)
            entry["obj"] = new_obj
            entry["price"] = RELIC_PRICE
        entry["sold"] = False
