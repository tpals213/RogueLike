"""3개 장 전체 맵/노드 이동 + 상점 콘솔 플레이.

python3 play.py         -> 매 갈림길/상점에서 직접 입력
python3 play.py --auto  -> 전부 무작위 자동 진행 (검증용)
"""

import random
import sys
from pathlib import Path

from game.combat import simulate_battle
from game.content import ACTS, RELIC_POOL, SAMPLE_ITEMS, STARTER_ITEM_NAMES, make_rogue
from game.hub import apply_unlocked_traits
from game.mapgen import generate_act_map, render_map
from game.models import EQUIPMENT_SLOTS
from game.relics import compute_relic_modifiers
from game.save_system import load_meta, save_meta
from game.shop import generate_shop_offer
from game.synergy import SYNERGY_TAGS

SAVE_PATH = Path(__file__).parent / "saves" / "meta_save.json"

GOLD_BASE = {"normal": 15, "elite": 30}
DIAMOND_BASE = {"normal": 2, "elite": 5}
DIAMOND_PER_NODE = 1
DIAMOND_PER_OVERKILL_10 = 1  # 오버킬 10당 다이아 1 (플레이스홀더 가중치)

_TYPE_LABEL = {
    "normal": "일반",
    "elite": "엘리트",
    "shop": "상점",
    "well": "우물",
    "event": "이벤트",
    "blessing": "축복",
    "boss": "보스",
    "relic_room": "유물방",
}


def _grant_relic(character, relic):
    character.relics.append(relic)
    print(f"[유물 획득] {relic.name} - {relic.description}")


def _choose_boss_relic(character, auto):
    choices = random.sample(RELIC_POOL, min(3, len(RELIC_POOL)))
    print("[유물 선택] 처치 보상으로 다음 중 하나를 고르세요:")
    for idx, relic in enumerate(choices, start=1):
        print(f"  {idx}. {relic.name} - {relic.description}")

    if auto:
        pick = random.choice(choices)
        print(f"(자동 선택) -> {pick.name}")
    else:
        while True:
            raw = input("> ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(choices):
                pick = choices[int(raw) - 1]
                break
            print("올바른 번호를 입력하세요.")

    _grant_relic(character, pick)


def resolve_combat(character, state, tier, auto):
    act_content = ACTS[state["act"]]
    key = random.choice(act_content[tier])
    monster = act_content["monsters"][key]()

    if state["trivialize"] > 0:
        monster.stats.hp = 1
        state["trivialize"] -= 1
        print(f"[축복 효과 남음] {monster.name} HP 1로 시작 (남은 적용 {state['trivialize']}회)")

    won, log, ending_hp, overkill, ending_shield = simulate_battle(character, monster, starting_hp=state["hp"])
    print("\n".join(log))
    state["hp"] = ending_hp
    state["shield"] = ending_shield

    if not won:
        state["alive"] = False
        return

    state["nodes_cleared"] += 1
    act = state["act"]

    gold_bonus = compute_relic_modifiers(character).gold_per_win
    if gold_bonus:
        state["gold"] += gold_bonus
        print(f"[유물] 승리 보너스 골드 +{gold_bonus}")

    if tier == "normal":
        state["gold"] += GOLD_BASE["normal"] * act
        state["diamond"] += DIAMOND_BASE["normal"] * act
    elif tier == "elite":
        state["gold"] += GOLD_BASE["elite"] * act
        state["diamond"] += DIAMOND_BASE["elite"] * act
        _grant_relic(character, random.choice(RELIC_POOL))
    elif tier == "boss":
        state["diamond"] += DIAMOND_BASE["elite"] * act * 2
        state["act_cleared"] = True
        print(f"{act}장 보스 처치!")
        _choose_boss_relic(character, auto)

    if overkill:
        bonus = overkill // 10
        if bonus:
            state["diamond"] += bonus
            print(f"[오버킬] {overkill} 초과 피해 -> 다이아 +{bonus}")


BLESSING_OPTIONS = [
    ("item", "무작위 아이템 획득 (빈 슬롯에 자동 장착)"),
    ("trivialize", "이후 3번의 전투, 적 HP 1로 시작"),
    ("relic", "무작위 유물 획득"),
    ("maxhp", "최대 HP +20"),
]


def resolve_blessing(character, state, auto):
    print("[축복] 하나를 선택하세요:")
    for idx, (_, desc) in enumerate(BLESSING_OPTIONS, start=1):
        print(f"  {idx}. {desc}")

    if auto:
        choice = random.randrange(len(BLESSING_OPTIONS))
        print(f"(자동 선택) -> {BLESSING_OPTIONS[choice][1]}")
    else:
        while True:
            raw = input("> ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(BLESSING_OPTIONS):
                choice = int(raw) - 1
                break
            print("올바른 번호를 입력하세요.")

    effect = BLESSING_OPTIONS[choice][0]
    if effect == "item":
        empty_slots = [s for s in EQUIPMENT_SLOTS if s not in character.equipment]
        candidates = [i for i in SAMPLE_ITEMS if i.slot in empty_slots]
        if candidates:
            item = random.choice(candidates)
            character.equip(item)
            print(f"[축복] 랜덤 아이템 획득 및 즉시 장착: {item.name}")
        else:
            print("[축복] 빈 슬롯이 없어 효과가 발동하지 않았습니다.")
    elif effect == "trivialize":
        state["trivialize"] = 3
        print("[축복] 이후 3번의 전투는 적 HP가 1로 시작합니다.")
    elif effect == "relic":
        _grant_relic(character, random.choice(RELIC_POOL))
    elif effect == "maxhp":
        character.base_stats.hp += 20
        state["hp"] += 20
        print(f"[축복] 최대 HP +20 (현재 {state['hp']}/{character.base_stats.hp})")


def resolve_relic_room(character, state):
    relic = random.choice(RELIC_POOL)
    print("[유물방] 무조건 유물을 획득합니다.")
    _grant_relic(character, relic)


def resolve_well(character, state, auto):
    common_items = [item for item in character.equipment.values() if item.rarity == "common"]

    print("[우물] 하나를 선택하세요:")
    print("  1. HP 40% 회복")
    if common_items:
        print("  2. 장비 하나 업그레이드 (일반 -> 희귀)")

    option_count = 2 if common_items else 1
    if auto:
        choice = random.randrange(option_count) + 1
    else:
        while True:
            raw = input("> ").strip()
            if raw.isdigit() and 1 <= int(raw) <= option_count:
                choice = int(raw)
                break
            print("올바른 번호를 입력하세요.")

    if choice == 1:
        heal = int(character.base_stats.hp * 0.4)
        state["hp"] = min(character.base_stats.hp, state["hp"] + heal)
        print(f"[우물] HP {heal} 회복 (현재 {state['hp']}/{character.base_stats.hp})")
    else:
        item = random.choice(common_items)
        item.rarity = "rare"
        available_tags = [t for t in SYNERGY_TAGS if t not in item.tags]
        if available_tags:
            item.tags.append(random.choice(available_tags))
        print(f"[우물] {item.name} 희귀 등급으로 업그레이드! (태그: {item.tags})")


def resolve_shop(character, state, auto):
    offer = generate_shop_offer(character)
    entries = [("item", item, price) for item, price in offer.items] + [("relic", relic, price) for relic, price in offer.relics]

    print(f"[상점] 보유 골드: {state['gold']}G")
    for idx, (kind, obj, price) in enumerate(entries, start=1):
        if kind == "item":
            print(f"  {idx}. [장비/{obj.slot}] {obj.name} ({obj.rarity}, {obj.tags}) - {price}G")
        else:
            print(f"  {idx}. [유물] {obj.name} - {obj.description} - {price}G")
    print("  0. 나가기")

    while True:
        affordable = [i for i, (_, _, price) in enumerate(entries, start=1) if price <= state["gold"]]
        if auto:
            if not affordable or random.random() < 0.3:
                print("(자동) 상점을 나갑니다.")
                return
            choice = random.choice(affordable)
        else:
            raw = input("> ").strip()
            if raw == "0":
                return
            if not raw.isdigit() or not (1 <= int(raw) <= len(entries)):
                print("올바른 번호를 입력하세요.")
                continue
            choice = int(raw)
            if choice not in affordable:
                print("골드가 부족합니다.")
                continue

        kind, obj, price = entries[choice - 1]
        state["gold"] -= price
        if kind == "item":
            character.equip(obj)
            print(f"구매: {obj.name} 장착 완료 (남은 골드 {state['gold']}G)")
        else:
            character.relics.append(obj)
            print(f"구매: {obj.name} 획득 (남은 골드 {state['gold']}G)")


def resolve_event(character, state, auto):
    def curse_altar():
        loss = int(state["hp"] * 0.15)
        state["hp"] = max(1, state["hp"] - loss)
        print(f"[저주받은 제단] HP {loss} 소모")
        _grant_relic(character, random.choice(RELIC_POOL))

    def treasure_chest():
        if random.random() < 0.5:
            state["gold"] += 20
            print("[버려진 보물상자] 골드 +20")
        else:
            loss = int(state["hp"] * 0.1)
            state["hp"] = max(1, state["hp"] - loss)
            print(f"[버려진 보물상자] 함정 발동! HP {loss} 소모")

    def mystic_spring():
        if random.random() < 0.5:
            character.base_stats.hp += 15
            state["hp"] += 15
            print(f"[신비한 샘] 최대 HP +15 (현재 {state['hp']}/{character.base_stats.hp})")
        else:
            character.base_stats.hp = max(1, character.base_stats.hp - 10)
            state["hp"] = min(state["hp"], character.base_stats.hp)
            print(f"[신비한 샘] 실패, 최대 HP -10 (현재 {state['hp']}/{character.base_stats.hp})")

    def short_rest():
        if random.random() < 0.5:
            state["gold"] += 15
            print("[짧은 휴식] 골드 +15")
        else:
            heal = int(character.base_stats.hp * 0.2)
            state["hp"] = min(character.base_stats.hp, state["hp"] + heal)
            print(f"[짧은 휴식] HP {heal} 회복")

    def ambush():
        print("[매복] 적이 나타났다!")
        resolve_combat(character, state, "normal", auto)

    def challenge():
        print("[도전장] 강한 상대가 도전을 걸어왔다!")
        resolve_combat(character, state, "elite", auto)

    def sealed_ward():
        print("[봉인된 결계] 위험을 무릅쓰고 결계를 개방한다 (조기 보스 도전)!")
        resolve_combat(character, state, "boss", auto)
        state["act_cleared"] = False  # 조기 도전은 정식 클리어로 치지 않음, 이동은 계속된다

    events = [curse_altar, treasure_chest, mystic_spring, short_rest, ambush, challenge, sealed_ward]
    random.choice(events)()


def resolve_node(node, character, state, auto):
    print(f"\n--- [{node.id}] {_TYPE_LABEL[node.node_type]} ---")
    if node.node_type == "blessing":
        resolve_blessing(character, state, auto)
    elif node.node_type == "well":
        resolve_well(character, state, auto)
    elif node.node_type == "shop":
        resolve_shop(character, state, auto)
    elif node.node_type == "event":
        resolve_event(character, state, auto)
    elif node.node_type == "relic_room":
        resolve_relic_room(character, state)
    elif node.node_type in ("normal", "elite", "boss"):
        resolve_combat(character, state, node.node_type, auto)


def choose_next(act_map, current_id, auto):
    node = act_map.nodes[current_id]
    options = node.next_ids
    if not options:
        return None
    print("\n다음 노드를 선택하세요:")
    for idx, nid in enumerate(options):
        n = act_map.nodes[nid]
        print(f"  {idx + 1}. [{nid}] {_TYPE_LABEL[n.node_type]}")

    if auto:
        choice = random.choice(options)
        print(f"(자동 선택) -> {choice}")
        return choice

    while True:
        raw = input("> ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("올바른 번호를 입력하세요.")


def main() -> None:
    auto = "--auto" in sys.argv

    meta = load_meta(SAVE_PATH)

    character = make_rogue()
    apply_unlocked_traits(character, meta["unlocked_traits"])
    if meta["unlocked_traits"]:
        print(f"[허브 특성 적용] {meta['unlocked_traits']}")
    for item in SAMPLE_ITEMS:
        if item.name in STARTER_ITEM_NAMES:
            character.equip(item)

    state = {
        "hp": character.base_stats.hp,
        "shield": 0,
        "gold": 0,
        "diamond": 0,
        "trivialize": 0,
        "alive": True,
        "act_cleared": False,
        "nodes_cleared": 0,
        "act": 1,
    }

    final_act_cleared = False
    relic_room_act = random.choice([1, 2, 3])  # 유물방은 런 전체에서 이 장(act)에만 등장

    for act_num in (1, 2, 3):
        if not state["alive"]:
            break

        state["act"] = act_num
        state["act_cleared"] = False
        act_map = generate_act_map(act_num, include_relic_room=(act_num == relic_room_act))
        print(f"\n{'#' * 12} {act_num}장 진입 ({ACTS[act_num]['theme']}) {'#' * 12}")
        print(render_map(act_map))

        current_id = act_map.start_id
        resolve_node(act_map.nodes[current_id], character, state, auto)

        while state["alive"] and not state["act_cleared"]:
            next_id = choose_next(act_map, current_id, auto)
            if next_id is None:
                break
            current_id = next_id
            resolve_node(act_map.nodes[current_id], character, state, auto)

        if not state["alive"] or not state["act_cleared"]:
            break
        if act_num == 3:
            final_act_cleared = True

    print("\n" + "=" * 40)
    if final_act_cleared:
        print("결과: 런 클리어! 3장 보스까지 전부 격파했습니다.")
    elif not state["alive"]:
        print(f"결과: {state['act']}장에서 사망. 런 종료.")
    else:
        print(f"결과: {state['act']}장 진행 중 더 이상 이동할 노드가 없어 런 종료.")

    diamond_total = state["diamond"] + state["nodes_cleared"] * DIAMOND_PER_NODE
    print(f"골드(런 한정, 소멸): {state['gold']}")
    print(f"획득 유물: {[r.name for r in character.relics]}")

    meta["total_diamond"] += diamond_total
    save_meta(SAVE_PATH, meta)
    print(f"다이아 정산: +{diamond_total} (누적 {meta['total_diamond']})")
    print(f"저장 위치: {SAVE_PATH}")


if __name__ == "__main__":
    main()
