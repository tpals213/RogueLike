"""허브 - 공용 특성 트리 (기획서 6.3절: 다이아로 해금하는 영구 스탯 강화).

라인(hp/atk/def/gold)별로 1~3단계는 일직선, 4~5단계는 3갈래로 분기, 6단계는 5단계
중 아무 갈래나 하나만 있으면 열리는 캡스톤(각 라인의 정체성을 압축한 유니크 효과) 하나로
다시 수렴한다. requires는 리스트이며 "그 중 하나라도" 보유하면 구매 가능(OR).
캐릭터별 특성은 이번 범위에서 제외. 가격/수치는 초기 플레이스홀더이며 밸런싱은 추후 조정 대상.
"""

from dataclasses import dataclass, field
from typing import Optional

from game.content import SAMPLE_ITEMS


@dataclass
class TraitNode:
    id: str
    line: str
    tier: int
    name: str
    desc: str
    cost: int
    requires: list[str] = field(default_factory=list)  # 비어있으면 최하위. 여러 개면 OR.
    stat_bonus: dict[str, int] = field(default_factory=dict)  # Stats 필드명 -> 증가량
    effect: Optional[str] = None  # 특수효과 식별자 (TraitModifiers 참고)
    effect_value: float = 0.0


_LINE_LABEL = {"hp": "체력", "atk": "공격력", "def": "방어력", "gold": "재화"}

TRAIT_TREE: dict[str, list[TraitNode]] = {
    "hp": [
        TraitNode("hp_1", "hp", 1, "체력 강화 1", "최대HP +15", 30, [], {"hp": 15}),
        TraitNode("hp_2", "hp", 2, "체력 강화 2", "최대HP +20", 60, ["hp_1"], {"hp": 20}),
        TraitNode("hp_3", "hp", 3, "체력 강화 3", "최대HP +30", 100, ["hp_2"], {"hp": 30}),
        TraitNode("hp_4a", "hp", 4, "굳건함", "최대HP +45", 150, ["hp_3"], {"hp": 45}),
        TraitNode("hp_4b", "hp", 4, "수호의 결계", "전투 시작 시 보호막 +20", 150, ["hp_3"],
                   effect="shield_on_start_flat", effect_value=20),
        TraitNode("hp_4c", "hp", 4, "이중 방벽", "물리방어 +4, 마법방어 +4", 150, ["hp_3"],
                   {"def_phys": 4, "def_magic": 4}),
        TraitNode("hp_5a", "hp", 5, "불굴의 육체", "최대HP +60", 220, ["hp_4a"], {"hp": 60}),
        TraitNode("hp_5b", "hp", 5, "생명의 고동", "매턴 시작 시 최대HP 2% 회복", 220, ["hp_4b"],
                   effect="regen_percent_per_turn", effect_value=0.02),
        TraitNode("hp_5c", "hp", 5, "가시 오라", "피격 시 받은 피해의 5% 반사", 220, ["hp_4c"],
                   effect="thorns_percent", effect_value=0.05),
        TraitNode("hp_6", "hp", 6, "불사조의 심장",
                   "전투 중 1회 부활 (부활 시 최대HP 50% 회복, 이후 3턴간 받는 피해 30% 감소)",
                   500, ["hp_5a", "hp_5b", "hp_5c"], effect="phoenix_heart"),
    ],
    "atk": [
        TraitNode("atk_1", "atk", 1, "공격력 강화 1", "물공/마공 +3", 30, [], {"atk_phys": 3, "atk_magic": 3}),
        TraitNode("atk_2", "atk", 2, "공격력 강화 2", "물공/마공 +4", 60, ["atk_1"], {"atk_phys": 4, "atk_magic": 4}),
        TraitNode("atk_3", "atk", 3, "공격력 강화 3", "물공/마공 +6", 100, ["atk_2"], {"atk_phys": 6, "atk_magic": 6}),
        TraitNode("atk_4a", "atk", 4, "예리한 감각", "치명타 확률 +5%", 150, ["atk_3"], {"crit_chance": 0.05}),
        TraitNode("atk_4b", "atk", 4, "신속한 손놀림", "스킬 쿨타임 -1", 150, ["atk_3"],
                   effect="cooldown_reduction", effect_value=1),
        TraitNode("atk_4c", "atk", 4, "쾌속 검술", "공격속도 +0.15", 150, ["atk_3"], {"atk_speed": 0.15}),
        TraitNode("atk_5a", "atk", 5, "숙련된 일격", "치명타 피해 +20%", 220, ["atk_4a"], {"crit_damage": 0.20}),
        TraitNode("atk_5b", "atk", 5, "쌍수 연격", "공격 시 5% 확률로 즉시 추가공격 1회", 220, ["atk_4b"],
                   effect="double_attack_chance", effect_value=0.05),
        TraitNode("atk_5c", "atk", 5, "관통 타격", "방어력 10% 무시", 220, ["atk_4c"],
                   effect="armor_pen_percent", effect_value=0.10),
        TraitNode("atk_6", "atk", 6, "필멸의 검",
                   "치명타 확률 +15%, 치명타 피해 +35% / 치명타 발생 시 30% 확률로 즉시 추가공격 1회",
                   500, ["atk_5a", "atk_5b", "atk_5c"], {"crit_chance": 0.15, "crit_damage": 0.35},
                   effect="mortal_blade"),
    ],
    "def": [
        TraitNode("def_1", "def", 1, "방어력 강화 1", "물방/마방 +3", 30, [], {"def_phys": 3, "def_magic": 3}),
        TraitNode("def_2", "def", 2, "방어력 강화 2", "물방/마방 +5", 60, ["def_1"], {"def_phys": 5, "def_magic": 5}),
        TraitNode("def_3", "def", 3, "방어력 강화 3", "물방/마방 +8", 100, ["def_2"], {"def_phys": 8, "def_magic": 8}),
        TraitNode("def_4a", "def", 4, "중장갑", "물방/마방 +12", 150, ["def_3"], {"def_phys": 12, "def_magic": 12}),
        TraitNode("def_4b", "def", 4, "완강함", "받는 모든 피해 5% 감소", 150, ["def_3"],
                   effect="flat_damage_reduction_percent", effect_value=0.05),
        TraitNode("def_4c", "def", 4, "냉정함", "받는 치명타 피해 15% 감소", 150, ["def_3"],
                   effect="incoming_crit_damage_reduction", effect_value=0.15),
        TraitNode("def_5a", "def", 5, "수호자의 가호", "전투 첫 피격 무효 1회", 220, ["def_4a"],
                   effect="first_hit_immune", effect_value=1),
        TraitNode("def_5b", "def", 5, "마나의 잔재", "매턴 20% 확률로 보호막(최대HP 5%) 생성", 220, ["def_4b"],
                   effect="shield_regen_flat_chance", effect_value=0.20),
        TraitNode("def_5c", "def", 5, "위기 감지", "몬스터 기믹 발동 확률 20% 감소", 220, ["def_4c"],
                   effect="gimmick_resist_percent", effect_value=0.20),
        TraitNode("def_6", "def", 6, "철옹성",
                   "받는 모든 피해 10% 감소 + 전투 시작 시 보호막(최대HP 15%) + 첫 피격 무효 1회",
                   500, ["def_5a", "def_5b", "def_5c"], effect="fortress"),
    ],
    "gold": [
        TraitNode("gold_1", "gold", 1, "재화 감각 1", "시작 골드 +50", 30, [], effect="starting_gold", effect_value=50),
        TraitNode("gold_2", "gold", 2, "재화 감각 2", "시작 골드 +80", 60, ["gold_1"], effect="starting_gold", effect_value=80),
        TraitNode("gold_3", "gold", 3, "재화 감각 3", "시작 골드 +120", 100, ["gold_2"], effect="starting_gold", effect_value=120),
        TraitNode("gold_4a", "gold", 4, "든든한 자본", "시작 골드 +150", 150, ["gold_3"],
                   effect="starting_gold", effect_value=150),
        TraitNode("gold_4b", "gold", 4, "여행의 준비", "시작 아이템 1개 추가 지급", 150, ["gold_3"],
                   effect="starting_item", effect_value=1),
        TraitNode("gold_4c", "gold", 4, "단골 손님", "상점 아이템 가격 10% 할인", 150, ["gold_3"],
                   effect="shop_discount", effect_value=0.10),
        TraitNode("gold_5a", "gold", 5, "약탈 본능", "몬스터 처치 시 획득 골드 +15%", 220, ["gold_4a"],
                   effect="gold_on_kill_percent", effect_value=0.15),
        TraitNode("gold_5b", "gold", 5, "흥정의 달인", "상점 무료 리롤 +1회", 220, ["gold_4b"],
                   effect="shop_free_reroll", effect_value=1),
        TraitNode("gold_5c", "gold", 5, "감정안", "상점/보상 레어 이상 등장확률 +10%", 220, ["gold_4c"],
                   effect="rarity_bonus", effect_value=0.10),
        TraitNode("gold_6", "gold", 6, "미다스의 축복",
                   "보유 시너지 전부 +1 + 처치 시 20% 확률로 추가 골드 10% + 상점 유물 진열 +1개",
                   500, ["gold_5a", "gold_5b", "gold_5c"], effect="midas"),
    ],
}


def all_traits() -> list[TraitNode]:
    return [node for line in TRAIT_TREE.values() for node in line]


def get_trait(trait_id: str) -> Optional[TraitNode]:
    for node in all_traits():
        if node.id == trait_id:
            return node
    return None


def is_purchasable(node: TraitNode, owned_ids: set) -> bool:
    if node.id in owned_ids:
        return False
    return not node.requires or any(r in owned_ids for r in node.requires)


def apply_unlocked_traits(character, owned_ids: list) -> None:
    owned = set(owned_ids)
    for node in all_traits():
        if node.id in owned:
            for stat, amount in node.stat_bonus.items():
                current = getattr(character.base_stats, stat)
                setattr(character.base_stats, stat, current + amount)


# --- 전투/런 중 특수효과 --------------------------------------------------

SHIELD_REGEN_FLAT_PERCENT = 0.05  # def_5b: 발동 시 보호막량 (최대HP 대비)


@dataclass
class TraitModifiers:
    revive_charges: int = 0
    revive_heal_percent: float = 0.0
    revive_shield_turns: int = 0
    revive_shield_reduction: float = 0.0
    shield_on_start_flat: int = 0
    shield_on_start_percent: float = 0.0
    regen_percent_per_turn: float = 0.0
    thorns_percent: float = 0.0
    cooldown_reduction: int = 0
    double_attack_chance: float = 0.0
    armor_pen_percent: float = 0.0
    crit_extra_attack_chance: float = 0.0
    first_hit_immune: bool = False
    incoming_crit_damage_reduction: float = 0.0
    flat_damage_reduction_percent: float = 0.0
    shield_regen_flat_chance: float = 0.0
    gimmick_resist_percent: float = 0.0
    synergy_boost_highest: int = 0
    synergy_boost_all: int = 0
    bonus_starting_gold: int = 0
    bonus_starting_items: int = 0
    shop_discount_percent: float = 0.0
    shop_free_reroll: int = 0
    rarity_bonus_percent: float = 0.0
    gold_on_kill_percent: float = 0.0
    gold_on_kill_bonus_chance: float = 0.0
    gold_on_kill_bonus_percent: float = 0.0
    shop_bonus_relic_slots: int = 0


def compute_trait_modifiers(owned_ids: list) -> TraitModifiers:
    owned = set(owned_ids)
    mods = TraitModifiers()
    for node in all_traits():
        if node.id not in owned or node.effect is None:
            continue
        effect, value = node.effect, node.effect_value

        if effect == "shield_on_start_flat":
            mods.shield_on_start_flat += int(value)
        elif effect == "regen_percent_per_turn":
            mods.regen_percent_per_turn += value
        elif effect == "thorns_percent":
            mods.thorns_percent += value
        elif effect == "phoenix_heart":
            mods.revive_charges += 1
            mods.revive_heal_percent = max(mods.revive_heal_percent, 0.5)
            mods.revive_shield_turns = max(mods.revive_shield_turns, 3)
            mods.revive_shield_reduction = max(mods.revive_shield_reduction, 0.3)
        elif effect == "cooldown_reduction":
            mods.cooldown_reduction += int(value)
        elif effect == "double_attack_chance":
            mods.double_attack_chance += value
        elif effect == "armor_pen_percent":
            mods.armor_pen_percent += value
        elif effect == "mortal_blade":
            mods.crit_extra_attack_chance += 0.30
        elif effect == "first_hit_immune":
            mods.first_hit_immune = True
        elif effect == "shield_regen_flat_chance":
            mods.shield_regen_flat_chance += value
        elif effect == "gimmick_resist_percent":
            mods.gimmick_resist_percent += value
        elif effect == "flat_damage_reduction_percent":
            mods.flat_damage_reduction_percent += value
        elif effect == "incoming_crit_damage_reduction":
            mods.incoming_crit_damage_reduction += value
        elif effect == "fortress":
            mods.flat_damage_reduction_percent += 0.10
            mods.shield_on_start_percent += 0.15
            mods.first_hit_immune = True
        elif effect == "starting_gold":
            mods.bonus_starting_gold += int(value)
        elif effect == "starting_item":
            mods.bonus_starting_items += int(value)
        elif effect == "shop_discount":
            mods.shop_discount_percent += value
        elif effect == "gold_on_kill_percent":
            mods.gold_on_kill_percent += value
        elif effect == "shop_free_reroll":
            mods.shop_free_reroll += int(value)
        elif effect == "rarity_bonus":
            mods.rarity_bonus_percent += value
        elif effect == "midas":
            mods.synergy_boost_all += 1
            mods.gold_on_kill_bonus_chance = max(mods.gold_on_kill_bonus_chance, 0.20)
            mods.gold_on_kill_bonus_percent = max(mods.gold_on_kill_bonus_percent, 0.10)
            mods.shop_bonus_relic_slots += 1

    return mods


def apply_gold_kill_bonus(trait_mods: "TraitModifiers", base_gold: int) -> int:
    """gold_5a(약탈 본능)/gold_6(미다스의 축복)를 처치 보상 골드에 반영."""
    import random

    gold = int(base_gold * (1 + trait_mods.gold_on_kill_percent))
    if trait_mods.gold_on_kill_bonus_chance and random.random() < trait_mods.gold_on_kill_bonus_chance:
        gold = int(gold * (1 + trait_mods.gold_on_kill_bonus_percent))
    return gold


def grant_bonus_starting_items(character, count: int) -> list:
    """gold_4b(여행의 준비) 등으로 늘어난 시작 아이템 지급분 — 아직 빈 슬롯에 무작위 common 아이템을 채운다."""
    import random

    from game.models import EQUIPMENT_SLOTS

    granted = []
    empty_slots = [s for s in EQUIPMENT_SLOTS if s not in character.equipment]
    random.shuffle(empty_slots)
    for slot in empty_slots[:count]:
        candidates = [i for i in SAMPLE_ITEMS if i.slot == slot and i.rarity == "common"]
        if not candidates:
            candidates = [i for i in SAMPLE_ITEMS if i.slot == slot]
        if not candidates:
            continue
        item = random.choice(candidates)
        character.equip(item)
        granted.append(item)
    return granted
