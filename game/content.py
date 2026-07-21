"""3개 장(Act) 컨텐츠: 도적 스타터 클래스, 7슬롯 장비 풀, 장별 몬스터 로스터.

전사/마법사는 이름만 등록된 스텁 — 스킬/스탯/밸런스는 추후 개발.
장별 스탯은 1장 기준 x1.0 / 2장 x1.6 / 3장 x2.5 배율의 플레이스홀더이며 밸런싱은 추후 조정 대상.
"""

from game.models import EQUIPMENT_SLOTS, Character, Item, Monster, Relic, Skill, Stats

# ---------------------------------------------------------------------------
# 캐릭터 클래스
# ---------------------------------------------------------------------------


def make_rogue() -> Character:
    return Character(
        name="도적",
        base_stats=Stats(hp=90, atk_phys=16, atk_magic=3, def_phys=6, def_magic=4, crit_chance=0.25, crit_damage=1.6),
        skill=Skill(name="연속 베기", cooldown=3, damage_multiplier=1.0, damage_type="phys", hits=2),
        damage_type="phys",
    )


def make_warrior_stub() -> Character:
    """미완성 스텁: 추후 스킬/밸런스 작업 예정."""
    return Character(
        name="전사",
        base_stats=Stats(hp=120, atk_phys=18, atk_magic=4, def_phys=10, def_magic=4, crit_chance=0.1, crit_damage=1.5),
        skill=Skill(name="파워 스트라이크", cooldown=3, damage_multiplier=2.0, damage_type="phys"),
        damage_type="phys",
    )


def make_mage_stub() -> Character:
    """미완성 스텁: 추후 스킬/밸런스 작업 예정."""
    return Character(
        name="마법사",
        base_stats=Stats(hp=80, atk_phys=6, atk_magic=20, def_phys=4, def_magic=8, crit_chance=0.15, crit_damage=1.6),
        skill=Skill(name="파이어볼", cooldown=2, damage_multiplier=2.2, damage_type="magic"),
        damage_type="magic",
    )


STARTER_CLASSES = {"rogue": make_rogue}  # 시작부터 사용 가능
LOCKED_CLASSES = {"warrior": make_warrior_stub, "mage": make_mage_stub}  # 다이아 해금 대상 (해금 기능은 추후 오픈)


# ---------------------------------------------------------------------------
# 1장 몬스터 로스터 (숲/폐허) — 난이도 배율은 1장 기준 x1.0
# ---------------------------------------------------------------------------


def make_goblin() -> Monster:
    return Monster(
        name="고블린",
        stats=Stats(hp=40, atk_phys=8, atk_magic=0, def_phys=3, def_magic=2, crit_chance=0.05, crit_damage=1.5),
        skill=Skill(name="찌르기", cooldown=4, damage_multiplier=1.8, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_poison_frog() -> Monster:
    return Monster(
        name="독개구리",
        stats=Stats(hp=32, atk_phys=6, atk_magic=0, def_phys=2, def_magic=2, crit_chance=0.05, crit_damage=1.5),
        skill=Skill(name="혀 채찍", cooldown=3, damage_multiplier=1.6, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_orc_warrior() -> Monster:
    return Monster(
        name="오크 전사",
        stats=Stats(hp=110, atk_phys=14, atk_magic=0, def_phys=9, def_magic=4, crit_chance=0.08, crit_damage=1.5),
        skill=Skill(name="대지 강타", cooldown=3, damage_multiplier=2.0, damage_type="phys"),
        damage_type="phys",
        tier="elite",
    )


def make_ruin_witch() -> Monster:
    return Monster(
        name="폐허의 마녀",
        stats=Stats(hp=85, atk_phys=4, atk_magic=18, def_phys=4, def_magic=8, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="저주의 구슬", cooldown=3, damage_multiplier=2.1, damage_type="magic"),
        damage_type="magic",
        tier="elite",
    )


def make_forest_guardian() -> Monster:
    return Monster(
        name="숲의 파수꾼",
        stats=Stats(hp=220, atk_phys=16, atk_magic=14, def_phys=10, def_magic=8, crit_chance=0.1, crit_damage=1.6),
        skill=Skill(name="파수꾼의 분노", cooldown=3, damage_multiplier=2.2, damage_type="phys"),
        damage_type="phys",
        tier="boss",
    )


ACT1_MONSTERS = {
    "goblin": make_goblin,
    "poison_frog": make_poison_frog,
    "orc_warrior": make_orc_warrior,
    "ruin_witch": make_ruin_witch,
    "forest_guardian": make_forest_guardian,
}

ACT1_NORMAL_KEYS = ["goblin", "poison_frog"]
ACT1_ELITE_KEYS = ["orc_warrior", "ruin_witch"]
ACT1_BOSS_KEYS = ["forest_guardian"]


# ---------------------------------------------------------------------------
# 2장 몬스터 로스터 (설산/동굴) — 난이도 배율 x1.6
# ---------------------------------------------------------------------------


def make_frost_wolf() -> Monster:
    return Monster(
        name="서리 늑대",
        stats=Stats(hp=60, atk_phys=13, atk_magic=0, def_phys=5, def_magic=3, crit_chance=0.08, crit_damage=1.5),
        skill=Skill(name="물어뜯기", cooldown=3, damage_multiplier=1.8, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_skeleton_mage() -> Monster:
    return Monster(
        name="스켈레톤 메이지",
        stats=Stats(hp=55, atk_phys=0, atk_magic=16, def_phys=3, def_magic=5, crit_chance=0.1, crit_damage=1.6),
        skill=Skill(name="저주탄", cooldown=3, damage_multiplier=1.9, damage_type="magic"),
        damage_type="magic",
        tier="normal",
    )


def make_frost_golem() -> Monster:
    return Monster(
        name="서리 골렘",
        stats=Stats(hp=190, atk_phys=18, atk_magic=0, def_phys=15, def_magic=6, crit_chance=0.05, crit_damage=1.5),
        skill=Skill(name="빙결 강타", cooldown=4, damage_multiplier=2.0, damage_type="phys"),
        damage_type="phys",
        tier="elite",
    )


def make_ice_spirit() -> Monster:
    return Monster(
        name="얼음 정령",
        stats=Stats(hp=140, atk_phys=0, atk_magic=24, def_phys=5, def_magic=10, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="서리 폭발", cooldown=3, damage_multiplier=2.1, damage_type="magic"),
        damage_type="magic",
        tier="elite",
    )


def make_frost_queen() -> Monster:
    return Monster(
        name="빙결의 여왕",
        stats=Stats(hp=360, atk_phys=18, atk_magic=22, def_phys=12, def_magic=12, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="절대영도", cooldown=3, damage_multiplier=2.3, damage_type="magic"),
        damage_type="magic",
        tier="boss",
    )


ACT2_MONSTERS = {
    "frost_wolf": make_frost_wolf,
    "skeleton_mage": make_skeleton_mage,
    "frost_golem": make_frost_golem,
    "ice_spirit": make_ice_spirit,
    "frost_queen": make_frost_queen,
}
ACT2_NORMAL_KEYS = ["frost_wolf", "skeleton_mage"]
ACT2_ELITE_KEYS = ["frost_golem", "ice_spirit"]
ACT2_BOSS_KEYS = ["frost_queen"]


# ---------------------------------------------------------------------------
# 3장 몬스터 로스터 (화산/성채) — 난이도 배율 x2.5, 최종장
# ---------------------------------------------------------------------------


def make_fire_imp() -> Monster:
    return Monster(
        name="화염 임프",
        stats=Stats(hp=70, atk_phys=0, atk_magic=20, def_phys=4, def_magic=6, crit_chance=0.1, crit_damage=1.6),
        skill=Skill(name="화염구", cooldown=3, damage_multiplier=1.9, damage_type="magic"),
        damage_type="magic",
        tier="normal",
    )


def make_death_knight() -> Monster:
    return Monster(
        name="데스나이트",
        stats=Stats(hp=90, atk_phys=22, atk_magic=0, def_phys=9, def_magic=5, crit_chance=0.1, crit_damage=1.6),
        skill=Skill(name="죽음의 일격", cooldown=3, damage_multiplier=2.0, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_fire_elemental() -> Monster:
    return Monster(
        name="화염 정령",
        stats=Stats(hp=230, atk_phys=0, atk_magic=34, def_phys=8, def_magic=14, crit_chance=0.14, crit_damage=1.6),
        skill=Skill(name="대화염", cooldown=3, damage_multiplier=2.2, damage_type="magic"),
        damage_type="magic",
        tier="elite",
    )


def make_dark_mage() -> Monster:
    return Monster(
        name="흑마법사",
        stats=Stats(hp=200, atk_phys=0, atk_magic=30, def_phys=7, def_magic=12, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="암흑파동", cooldown=3, damage_multiplier=2.1, damage_type="magic"),
        damage_type="magic",
        tier="elite",
    )


def make_demon_king() -> Monster:
    return Monster(
        name="마왕",
        stats=Stats(hp=550, atk_phys=30, atk_magic=30, def_phys=18, def_magic=18, crit_chance=0.15, crit_damage=1.7),
        skill=Skill(name="파멸의 일격", cooldown=3, damage_multiplier=2.4, damage_type="phys"),
        damage_type="phys",
        tier="boss",
    )


ACT3_MONSTERS = {
    "fire_imp": make_fire_imp,
    "death_knight": make_death_knight,
    "fire_elemental": make_fire_elemental,
    "dark_mage": make_dark_mage,
    "demon_king": make_demon_king,
}
ACT3_NORMAL_KEYS = ["fire_imp", "death_knight"]
ACT3_ELITE_KEYS = ["fire_elemental", "dark_mage"]
ACT3_BOSS_KEYS = ["demon_king"]


# 장(Act) 공통 조회용 레지스트리
ACTS = {
    1: {
        "theme": "숲/폐허",
        "monsters": ACT1_MONSTERS,
        "normal": ACT1_NORMAL_KEYS,
        "elite": ACT1_ELITE_KEYS,
        "boss": ACT1_BOSS_KEYS,
    },
    2: {
        "theme": "설산/동굴",
        "monsters": ACT2_MONSTERS,
        "normal": ACT2_NORMAL_KEYS,
        "elite": ACT2_ELITE_KEYS,
        "boss": ACT2_BOSS_KEYS,
    },
    3: {
        "theme": "화산/성채",
        "monsters": ACT3_MONSTERS,
        "normal": ACT3_NORMAL_KEYS,
        "elite": ACT3_ELITE_KEYS,
        "boss": ACT3_BOSS_KEYS,
    },
}


# ---------------------------------------------------------------------------
# 유물 풀 (엘리트/보스/축복/이벤트 보상으로 랜덤 지급) — 효과는 설명 텍스트 수준,
# 전투 로직 연동은 추후 작업 대상
# ---------------------------------------------------------------------------

RELIC_POOL = [
    # 일반 유물 - 소소한 효과
    Relic(name="낡은 지갑", description="전투 승리 시 골드 +5", effect="worn_wallet"),
    Relic(name="여행자의 부적", description="전투 시작 시 HP 5% 회복", effect="travelers_charm"),
    Relic(name="무딘 숫돌", description="물리공격력 +5%", effect="dull_whetstone"),
    Relic(name="낡은 지팡이", description="마법공격력 +5%", effect="worn_staff"),
    # 시너지 보조형
    Relic(name="독아의 인장", description="독 시너지 중독 부여 확률 +10%p", effect="poison_proc_boost"),
    Relic(name="화염 심장", description="화염 시너지 화상 부여 스택 +5", effect="fire_stack_boost"),
    Relic(name="광전사의 표식", description="버서커 시너지 흡혈 확률 +10%p", effect="berserker_lifesteal_boost"),
    Relic(name="서리 파편", description="얼음 상태이상 행동불가 확률 +10%p", effect="ice_fail_boost"),
    Relic(name="현자의 돌", description="마나 시너지 보호막 재생 확률 +10%p", effect="mana_shield_boost"),
    # 강력형 (부작용 없음)
    Relic(name="불굴의 심장", description="전투 중 첫 피격 데미지 무효", effect="first_hit_immune"),
    Relic(name="거인의 뼈", description="최대 HP +30 (이번 런 한정)", effect="max_hp_up"),
    # 하이리스크 강력형 (부작용 동반)
    Relic(name="악마의 계약", description="물공/마공 +25%, 대신 매턴 시작 시 현재 HP 3% 자해", effect="demons_pact"),
    Relic(name="폭주의 흉갑", description="물공/마공 +30%, 대신 물방/마방 -20%", effect="berserk_plate"),
    Relic(name="도박사의 주사위", description="크리티컬 확률 +20%p, 대신 크리티컬 데미지 -25%p", effect="gamblers_dice"),
    Relic(name="검은 낙인", description="스킬 쿨타임 -1, 대신 최대 HP -15%", effect="black_brand"),
    # 일반 유물 추가
    Relic(name="튼튼한 허리띠", description="물방/마방 +5%", effect="sturdy_belt"),
    Relic(name="행운의 부적", description="크리티컬 확률 +5%p", effect="lucky_charm"),
    # 시너지 무관 스탯 강화형 (태그 투자 없이도 적용)
    Relic(name="야수의 발톱", description="물리공격력 +8% (버서커 시너지 무관)", effect="beast_claw"),
    Relic(name="현자의 렌즈", description="마법공격력 +8% (마나 시너지 무관)", effect="sage_lens"),
    # 하이리스크 강력형 추가
    Relic(name="피의 서약", description="크리티컬 데미지 +40%p, 대신 최대 HP -20%", effect="blood_oath"),
    Relic(name="구원의 반지", description="전투 시작 시 HP 20% 회복, 대신 매턴 시작 시 HP 1% 자해", effect="ring_of_salvation"),
]


# ---------------------------------------------------------------------------
# 장비 풀 — 슬롯별 보장 스탯 + 등급별 태그 개수(일반 1개 / 희귀 2개)
# ---------------------------------------------------------------------------

SAMPLE_ITEMS = [
    # 투구 - HP 증가 (일반 4 / 희귀 4)
    Item(name="가죽 두건", slot="helmet", rarity="common", tags=["poison"], stat_bonus={"hp": 15}),
    Item(name="독사냥꾼의 투구", slot="helmet", rarity="rare", tags=["poison", "fire"], stat_bonus={"hp": 25}),
    Item(name="철 투구", slot="helmet", rarity="common", tags=["berserker"], stat_bonus={"hp": 20}),
    Item(name="얼음 투구", slot="helmet", rarity="common", tags=["ice"], stat_bonus={"hp": 18}),
    Item(name="현자의 로브 두건", slot="helmet", rarity="rare", tags=["mana", "fire"], stat_bonus={"hp": 22}),
    Item(name="화염 두건", slot="helmet", rarity="common", tags=["fire"], stat_bonus={"hp": 17}),
    Item(name="버서커의 투구", slot="helmet", rarity="rare", tags=["berserker", "ice"], stat_bonus={"hp": 24}),
    Item(name="얼음 여왕의 관", slot="helmet", rarity="rare", tags=["ice", "mana"], stat_bonus={"hp": 26}),
    # 왼손 - 방패 또는 무기 (일반 4 / 희귀 4)
    Item(name="가시 방패", slot="left_hand", rarity="common", tags=["berserker"], stat_bonus={"def_phys": 4}),
    Item(name="독날 단검", slot="left_hand", rarity="rare", tags=["poison", "berserker"], stat_bonus={"atk_phys": 5}),
    Item(name="냉기의 방패", slot="left_hand", rarity="common", tags=["ice"], stat_bonus={"def_phys": 5}),
    Item(name="화염의 대거", slot="left_hand", rarity="rare", tags=["fire", "mana"], stat_bonus={"atk_phys": 8}),
    Item(name="화염 방패", slot="left_hand", rarity="common", tags=["fire"], stat_bonus={"def_phys": 4}),
    Item(name="마나의 방패", slot="left_hand", rarity="common", tags=["mana"], stat_bonus={"def_phys": 4}),
    Item(name="서리 단검", slot="left_hand", rarity="rare", tags=["ice", "poison"], stat_bonus={"atk_phys": 6}),
    Item(name="광전사의 대거", slot="left_hand", rarity="rare", tags=["berserker", "fire"], stat_bonus={"atk_phys": 7}),
    # 오른손 - 무기 (일반 4 / 희귀 4)
    Item(name="녹슨 단검", slot="right_hand", rarity="common", tags=["poison"], stat_bonus={"atk_phys": 5}),
    Item(name="맹독의 쌍검", slot="right_hand", rarity="rare", tags=["poison", "fire"], stat_bonus={"atk_phys": 9}),
    Item(name="부족의 도끼", slot="right_hand", rarity="common", tags=["berserker"], stat_bonus={"atk_phys": 6}),
    Item(name="얼음 창", slot="right_hand", rarity="rare", tags=["ice", "berserker"], stat_bonus={"atk_phys": 10}),
    Item(name="얼음 단검", slot="right_hand", rarity="common", tags=["ice"], stat_bonus={"atk_phys": 5}),
    Item(name="마나의 지팡이", slot="right_hand", rarity="common", tags=["mana"], stat_bonus={"atk_phys": 5}),
    Item(name="화염의 대검", slot="right_hand", rarity="rare", tags=["fire", "berserker"], stat_bonus={"atk_phys": 9}),
    Item(name="현자의 지팡이", slot="right_hand", rarity="rare", tags=["mana", "poison"], stat_bonus={"atk_phys": 9}),
    # 갑옷 - 물방/마방 증가 (일반 4 / 희귀 4)
    Item(name="가죽 갑옷", slot="armor", rarity="common", tags=["ice"], stat_bonus={"def_phys": 3, "def_magic": 3}),
    Item(name="서리 갑옷", slot="armor", rarity="rare", tags=["ice", "mana"], stat_bonus={"def_phys": 6, "def_magic": 6}),
    Item(name="가시 갑옷", slot="armor", rarity="common", tags=["berserker"], stat_bonus={"def_phys": 4}),
    Item(name="용의 비늘 갑옷", slot="armor", rarity="rare", tags=["fire", "berserker"], stat_bonus={"def_phys": 7, "def_magic": 7}),
    Item(name="독저항 갑옷", slot="armor", rarity="common", tags=["poison"], stat_bonus={"def_phys": 3, "def_magic": 3}),
    Item(name="마법사의 로브", slot="armor", rarity="common", tags=["mana"], stat_bonus={"def_phys": 2, "def_magic": 4}),
    Item(name="독룡의 갑옷", slot="armor", rarity="rare", tags=["poison", "fire"], stat_bonus={"def_phys": 6, "def_magic": 6}),
    Item(name="얼음전사 갑옷", slot="armor", rarity="rare", tags=["ice", "berserker"], stat_bonus={"def_phys": 7, "def_magic": 5}),
    # 신발 - 크리율/크리데미지 (일반 4 / 희귀 4)
    Item(name="사냥꾼의 부츠", slot="boots", rarity="common", tags=["berserker"], stat_bonus={"crit_chance": 0.05}),
    Item(name="질풍의 부츠", slot="boots", rarity="rare", tags=["berserker", "ice"], stat_bonus={"crit_chance": 0.1, "crit_damage": 0.1}),
    Item(name="독안개 신발", slot="boots", rarity="common", tags=["poison"], stat_bonus={"crit_chance": 0.04}),
    Item(name="화염 질주화", slot="boots", rarity="rare", tags=["fire", "mana"], stat_bonus={"crit_chance": 0.08, "crit_damage": 0.15}),
    Item(name="냉기의 신발", slot="boots", rarity="common", tags=["ice"], stat_bonus={"crit_chance": 0.04}),
    Item(name="마나의 신발", slot="boots", rarity="common", tags=["mana"], stat_bonus={"crit_chance": 0.04}),
    Item(name="독개구리 부츠", slot="boots", rarity="rare", tags=["poison", "berserker"], stat_bonus={"crit_chance": 0.09, "crit_damage": 0.1}),
    Item(name="현자의 슬리퍼", slot="boots", rarity="rare", tags=["mana", "ice"], stat_bonus={"crit_chance": 0.07, "crit_damage": 0.12}),
    # 목걸이 - 스킬 쿨다운 감소 (일반 4 / 희귀 4)
    Item(name="집중의 목걸이", slot="necklace", rarity="common", tags=["mana"], stat_bonus={"cooldown_reduction": 1}),
    Item(name="현자의 목걸이", slot="necklace", rarity="rare", tags=["mana", "fire"], stat_bonus={"cooldown_reduction": 2}),
    Item(name="맹독의 목걸이", slot="necklace", rarity="common", tags=["poison"], stat_bonus={"cooldown_reduction": 1}),
    Item(name="전투의 부적", slot="necklace", rarity="rare", tags=["berserker", "ice"], stat_bonus={"cooldown_reduction": 2}),
    Item(name="서리의 목걸이", slot="necklace", rarity="common", tags=["ice"], stat_bonus={"cooldown_reduction": 1}),
    Item(name="화염의 목걸이", slot="necklace", rarity="common", tags=["fire"], stat_bonus={"cooldown_reduction": 1}),
    Item(name="독아의 목걸이", slot="necklace", rarity="rare", tags=["poison", "berserker"], stat_bonus={"cooldown_reduction": 2}),
    Item(name="얼음마법사의 목걸이", slot="necklace", rarity="rare", tags=["ice", "mana"], stat_bonus={"cooldown_reduction": 2}),
    # 반지 - 방어막 제공 (일반 4 / 희귀 4)
    Item(name="수호의 반지", slot="ring", rarity="common", tags=["mana"], stat_bonus={"shield": 10}),
    Item(name="대마법사의 인장", slot="ring", rarity="rare", tags=["mana", "poison"], stat_bonus={"shield": 20}),
    Item(name="불꽃 반지", slot="ring", rarity="common", tags=["fire"], stat_bonus={"shield": 8}),
    Item(name="서리 인장", slot="ring", rarity="rare", tags=["ice", "berserker"], stat_bonus={"shield": 18}),
    Item(name="독저항 반지", slot="ring", rarity="common", tags=["poison"], stat_bonus={"shield": 8}),
    Item(name="전사의 반지", slot="ring", rarity="common", tags=["berserker"], stat_bonus={"shield": 9}),
    Item(name="화염군주의 반지", slot="ring", rarity="rare", tags=["fire", "berserker"], stat_bonus={"shield": 19}),
    Item(name="얼음현자의 반지", slot="ring", rarity="rare", tags=["ice", "mana"], stat_bonus={"shield": 20}),
]

assert {item.slot for item in SAMPLE_ITEMS} == set(EQUIPMENT_SLOTS)

# 런 시작 시 기본 지급 장비 (오른손 무기 1개만)
STARTER_ITEM_NAMES = ["녹슨 단검"]
