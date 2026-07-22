"""전투/장비 관련 기본 데이터 구조 (기획서 4장, 5장 참고)."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Stats:
    hp: int
    atk_phys: int
    atk_magic: int
    def_phys: int
    def_magic: int
    crit_chance: float  # 0.0 ~ 1.0
    crit_damage: float  # 1.5 = 150%
    atk_speed: float = 1.0  # 초당 공격 횟수. 1.0 = 1초에 1대 (기존 콘텐츠 기본값, 턴제 시절 페이스와 동일)

    def copy(self) -> "Stats":
        return Stats(**vars(self))


@dataclass
class Skill:
    name: str
    cooldown: float  # 초 단위 (기존 "턴" 수치를 그대로 초로 재해석)
    damage_multiplier: float
    damage_type: str  # "phys" or "magic"
    hits: int = 1  # 다단히트 스킬 (예: 도적 연속 베기)


# 슬롯: helmet(투구) / left_hand(왼손, 방패or무기) / right_hand(오른손, 무기)
# / armor(갑옷) / pants(하의) / boots(신발) / necklace(목걸이) / ring(반지)
EQUIPMENT_SLOTS = ["helmet", "left_hand", "right_hand", "armor", "pants", "boots", "necklace", "ring"]

# 등급별 보유 시너지 태그 개수 (일반 1개 / 희귀 1개 / 유니크 2개 / 레전더리 3개)
RARITY_TAG_COUNT = {"common": 1, "rare": 1, "unique": 2, "legendary": 3}


@dataclass
class Item:
    name: str
    slot: str
    rarity: str  # "common" or "rare"
    tags: list[str]
    stat_bonus: dict[str, int] = field(default_factory=dict)
    image: Optional[str] = None  # assets/images/ 기준 상대 경로, 없으면 None (그래픽 미제작)


@dataclass
class Relic:
    name: str
    description: str
    effect: str  # 코드에서 참조할 효과 식별자 (예: "poison_tick_half", "first_hit_immune", "max_hp_up")
    rarity: str = "common"  # "common" / "rare" / "unique" - 1/2/3장 엘리트 보상 및 상점 등급표에 사용
    image: Optional[str] = None  # assets/images/ 기준 상대 경로, 없으면 None (그래픽 미제작)


@dataclass
class Character:
    name: str
    base_stats: Stats
    skill: Skill
    damage_type: str  # 기본 공격 속성: "phys" or "magic"
    equipment: dict[str, Item] = field(default_factory=dict)
    relics: list[Relic] = field(default_factory=list)
    image: Optional[str] = None  # assets/images/ 기준 상대 경로, 없으면 None (그래픽 미제작)
    trait_mods: object = None  # game.hub.TraitModifiers — 런 시작 시 1회 계산해 부여 (순환참조 방지로 느슨한 타입)

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
    image: Optional[str] = None  # assets/images/ 기준 상대 경로, 없으면 None (그래픽 미제작)
    # 기믹 식별자 (예: "skill_null", "reflect") — 없으면 None. gimmick_value는 기믹별 파라미터
    # 하나를 재사용(회복%, 반사%, 보호막량 등 기믹마다 의미가 다름).
    gimmick: Optional[str] = None
    gimmick_value: int = 0
