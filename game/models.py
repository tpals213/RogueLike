"""전투/장비 관련 기본 데이터 구조 (기획서 4장, 5장 참고)."""

from dataclasses import dataclass, field


@dataclass
class Stats:
    hp: int
    atk_phys: int
    atk_magic: int
    def_phys: int
    def_magic: int
    crit_chance: float  # 0.0 ~ 1.0
    crit_damage: float  # 1.5 = 150%

    def copy(self) -> "Stats":
        return Stats(**vars(self))


@dataclass
class Skill:
    name: str
    cooldown: int  # 턴 단위
    damage_multiplier: float
    damage_type: str  # "phys" or "magic"
    hits: int = 1  # 다단히트 스킬 (예: 도적 연속 베기)


# 슬롯: helmet(투구) / left_hand(왼손, 방패or무기) / right_hand(오른손, 무기)
# / armor(갑옷) / boots(신발) / necklace(목걸이) / ring(반지)
EQUIPMENT_SLOTS = ["helmet", "left_hand", "right_hand", "armor", "boots", "necklace", "ring"]

# 등급별 보유 시너지 태그 개수 (기획서: 일반 1개, 희귀 2개)
RARITY_TAG_COUNT = {"common": 1, "rare": 2}


@dataclass
class Item:
    name: str
    slot: str
    rarity: str  # "common" or "rare"
    tags: list[str]
    stat_bonus: dict[str, int] = field(default_factory=dict)


@dataclass
class Relic:
    name: str
    description: str
    effect: str  # 코드에서 참조할 효과 식별자 (예: "poison_tick_half", "first_hit_immune", "max_hp_up")


@dataclass
class Character:
    name: str
    base_stats: Stats
    skill: Skill
    damage_type: str  # 기본 공격 속성: "phys" or "magic"
    equipment: dict[str, Item] = field(default_factory=dict)
    relics: list[Relic] = field(default_factory=list)

    def equip(self, item: Item) -> None:
        self.equipment[item.slot] = item

    def equipped_tags(self) -> list[str]:
        tags: list[str] = []
        for item in self.equipment.values():
            tags.extend(item.tags)
        return tags


@dataclass
class Monster:
    name: str
    stats: Stats
    skill: Skill
    damage_type: str
    tier: str  # "normal" or "elite" or "boss"
