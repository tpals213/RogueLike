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
        image="characters/rogue.png",
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
        image="monsters/goblin.png",
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
        gimmick="skill_null",
    )


def make_ruin_witch() -> Monster:
    return Monster(
        name="폐허의 마녀",
        stats=Stats(hp=85, atk_phys=4, atk_magic=18, def_phys=4, def_magic=8, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="저주의 구슬", cooldown=3, damage_multiplier=2.1, damage_type="magic"),
        damage_type="magic",
        tier="elite",
        gimmick="synergy_null",
    )


def make_forest_guardian() -> Monster:
    return Monster(
        name="숲의 파수꾼",
        stats=Stats(hp=220, atk_phys=16, atk_magic=14, def_phys=10, def_magic=8, crit_chance=0.1, crit_damage=1.6),
        skill=Skill(name="파수꾼의 분노", cooldown=3, damage_multiplier=2.2, damage_type="phys"),
        damage_type="phys",
        tier="boss",
    )


def make_forest_wolf() -> Monster:
    return Monster(
        name="숲 늑대",
        stats=Stats(hp=45, atk_phys=9, atk_magic=0, def_phys=3, def_magic=2, crit_chance=0.08, crit_damage=1.5),
        skill=Skill(name="물어뜯기", cooldown=3, damage_multiplier=1.7, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_bandit() -> Monster:
    return Monster(
        name="산적",
        stats=Stats(hp=50, atk_phys=10, atk_magic=0, def_phys=4, def_magic=2, crit_chance=0.1, crit_damage=1.5),
        skill=Skill(name="기습", cooldown=3, damage_multiplier=1.9, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_giant_spider() -> Monster:
    return Monster(
        name="거대 거미",
        stats=Stats(hp=38, atk_phys=7, atk_magic=0, def_phys=2, def_magic=2, crit_chance=0.1, crit_damage=1.6),
        skill=Skill(name="맹독 침", cooldown=3, damage_multiplier=1.6, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_rotting_zombie() -> Monster:
    return Monster(
        name="부패한 좀비",
        stats=Stats(hp=55, atk_phys=8, atk_magic=0, def_phys=5, def_magic=2, crit_chance=0.03, crit_damage=1.5),
        skill=Skill(name="감염된 발톱", cooldown=4, damage_multiplier=1.9, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_stone_troll() -> Monster:
    return Monster(
        name="돌 트롤",
        stats=Stats(hp=130, atk_phys=15, atk_magic=0, def_phys=11, def_magic=5, crit_chance=0.06, crit_damage=1.5),
        skill=Skill(name="바위 주먹", cooldown=3, damage_multiplier=2.1, damage_type="phys"),
        damage_type="phys",
        tier="elite",
        gimmick="healer",
        gimmick_value=10,
    )


def make_corrupted_druid() -> Monster:
    return Monster(
        name="타락한 드루이드",
        stats=Stats(hp=100, atk_phys=3, atk_magic=17, def_phys=5, def_magic=8, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="가시덩굴", cooldown=3, damage_multiplier=2.0, damage_type="magic"),
        damage_type="magic",
        tier="elite",
        gimmick="shield_tank",
    )


ACT1_MONSTERS = {
    "goblin": make_goblin,
    "poison_frog": make_poison_frog,
    "forest_wolf": make_forest_wolf,
    "bandit": make_bandit,
    "giant_spider": make_giant_spider,
    "rotting_zombie": make_rotting_zombie,
    "orc_warrior": make_orc_warrior,
    "ruin_witch": make_ruin_witch,
    "stone_troll": make_stone_troll,
    "corrupted_druid": make_corrupted_druid,
    "forest_guardian": make_forest_guardian,
}

ACT1_NORMAL_KEYS = ["goblin", "poison_frog", "forest_wolf", "bandit", "giant_spider", "rotting_zombie"]
ACT1_ELITE_KEYS = ["orc_warrior", "ruin_witch", "stone_troll", "corrupted_druid"]
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
        gimmick="inflict_status",
        gimmick_value=20,
    )


def make_ice_spirit() -> Monster:
    return Monster(
        name="얼음 정령",
        stats=Stats(hp=140, atk_phys=0, atk_magic=24, def_phys=5, def_magic=10, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="서리 폭발", cooldown=3, damage_multiplier=2.1, damage_type="magic"),
        damage_type="magic",
        tier="elite",
        gimmick="reflect",
        gimmick_value=15,
    )


def make_frost_queen() -> Monster:
    return Monster(
        name="빙결의 여왕",
        stats=Stats(hp=360, atk_phys=18, atk_magic=22, def_phys=12, def_magic=12, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="절대영도", cooldown=3, damage_multiplier=2.3, damage_type="magic"),
        damage_type="magic",
        tier="boss",
    )


def make_ice_bat() -> Monster:
    return Monster(
        name="얼음 박쥐",
        stats=Stats(hp=58, atk_phys=12, atk_magic=0, def_phys=4, def_magic=4, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="초음파", cooldown=3, damage_multiplier=1.8, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_cave_bear() -> Monster:
    return Monster(
        name="동굴 곰",
        stats=Stats(hp=75, atk_phys=15, atk_magic=0, def_phys=6, def_magic=3, crit_chance=0.06, crit_damage=1.5),
        skill=Skill(name="휘두르기", cooldown=3, damage_multiplier=1.9, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_frost_bandit() -> Monster:
    return Monster(
        name="서리 도적",
        stats=Stats(hp=65, atk_phys=14, atk_magic=0, def_phys=5, def_magic=4, crit_chance=0.1, crit_damage=1.6),
        skill=Skill(name="냉기 일격", cooldown=3, damage_multiplier=1.9, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_crystal_slime() -> Monster:
    return Monster(
        name="수정 슬라임",
        stats=Stats(hp=70, atk_phys=0, atk_magic=16, def_phys=6, def_magic=7, crit_chance=0.05, crit_damage=1.5),
        skill=Skill(name="수정 파편", cooldown=3, damage_multiplier=1.8, damage_type="magic"),
        damage_type="magic",
        tier="normal",
    )


def make_yeti_chieftain() -> Monster:
    return Monster(
        name="예티 족장",
        stats=Stats(hp=210, atk_phys=20, atk_magic=0, def_phys=14, def_magic=6, crit_chance=0.08, crit_damage=1.5),
        skill=Skill(name="눈사태", cooldown=3, damage_multiplier=2.1, damage_type="phys"),
        damage_type="phys",
        tier="elite",
        gimmick="glass_shield",
        gimmick_value=60,
    )


def make_ice_wraith() -> Monster:
    return Monster(
        name="얼음 망령",
        stats=Stats(hp=170, atk_phys=0, atk_magic=26, def_phys=8, def_magic=11, crit_chance=0.13, crit_damage=1.6),
        skill=Skill(name="영혼 서리", cooldown=3, damage_multiplier=2.2, damage_type="magic"),
        damage_type="magic",
        tier="elite",
        gimmick="skill_null",
    )


ACT2_MONSTERS = {
    "frost_wolf": make_frost_wolf,
    "skeleton_mage": make_skeleton_mage,
    "ice_bat": make_ice_bat,
    "cave_bear": make_cave_bear,
    "frost_bandit": make_frost_bandit,
    "crystal_slime": make_crystal_slime,
    "frost_golem": make_frost_golem,
    "ice_spirit": make_ice_spirit,
    "yeti_chieftain": make_yeti_chieftain,
    "ice_wraith": make_ice_wraith,
    "frost_queen": make_frost_queen,
}
ACT2_NORMAL_KEYS = ["frost_wolf", "skeleton_mage", "ice_bat", "cave_bear", "frost_bandit", "crystal_slime"]
ACT2_ELITE_KEYS = ["frost_golem", "ice_spirit", "yeti_chieftain", "ice_wraith"]
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
        gimmick="synergy_null",
    )


def make_dark_mage() -> Monster:
    return Monster(
        name="흑마법사",
        stats=Stats(hp=200, atk_phys=0, atk_magic=30, def_phys=7, def_magic=12, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="암흑파동", cooldown=3, damage_multiplier=2.1, damage_type="magic"),
        damage_type="magic",
        tier="elite",
        gimmick="healer",
        gimmick_value=12,
    )


def make_demon_king() -> Monster:
    return Monster(
        name="마왕",
        stats=Stats(hp=550, atk_phys=30, atk_magic=30, def_phys=18, def_magic=18, crit_chance=0.15, crit_damage=1.7),
        skill=Skill(name="파멸의 일격", cooldown=3, damage_multiplier=2.4, damage_type="phys"),
        damage_type="phys",
        tier="boss",
    )


def make_lava_hound() -> Monster:
    return Monster(
        name="용암 사냥개",
        stats=Stats(hp=85, atk_phys=0, atk_magic=22, def_phys=6, def_magic=8, crit_chance=0.12, crit_damage=1.6),
        skill=Skill(name="용암 숨결", cooldown=3, damage_multiplier=1.9, damage_type="magic"),
        damage_type="magic",
        tier="normal",
    )


def make_cursed_knight() -> Monster:
    return Monster(
        name="저주받은 기사",
        stats=Stats(hp=95, atk_phys=24, atk_magic=0, def_phys=10, def_magic=5, crit_chance=0.1, crit_damage=1.6),
        skill=Skill(name="저주의 검", cooldown=3, damage_multiplier=2.0, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_obsidian_golem() -> Monster:
    return Monster(
        name="흑요석 골렘",
        stats=Stats(hp=110, atk_phys=20, atk_magic=0, def_phys=16, def_magic=8, crit_chance=0.04, crit_damage=1.5),
        skill=Skill(name="분쇄", cooldown=4, damage_multiplier=2.1, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_hellhound() -> Monster:
    return Monster(
        name="지옥견",
        stats=Stats(hp=80, atk_phys=26, atk_magic=0, def_phys=7, def_magic=5, crit_chance=0.16, crit_damage=1.6),
        skill=Skill(name="화염 이빨", cooldown=3, damage_multiplier=1.9, damage_type="phys"),
        damage_type="phys",
        tier="normal",
    )


def make_inferno_juggernaut() -> Monster:
    return Monster(
        name="인페르노 저거넛",
        stats=Stats(hp=260, atk_phys=32, atk_magic=0, def_phys=16, def_magic=10, crit_chance=0.1, crit_damage=1.6),
        skill=Skill(name="용암 돌진", cooldown=3, damage_multiplier=2.2, damage_type="phys"),
        damage_type="phys",
        tier="elite",
        gimmick="shield_tank",
    )


def make_shadow_assassin() -> Monster:
    return Monster(
        name="그림자 암살자",
        stats=Stats(hp=220, atk_phys=28, atk_magic=0, def_phys=10, def_magic=8, crit_chance=0.22, crit_damage=1.8),
        skill=Skill(name="암습", cooldown=2, damage_multiplier=1.9, damage_type="phys"),
        damage_type="phys",
        tier="elite",
        gimmick="inflict_status",
        gimmick_value=25,
    )


ACT3_MONSTERS = {
    "fire_imp": make_fire_imp,
    "death_knight": make_death_knight,
    "lava_hound": make_lava_hound,
    "cursed_knight": make_cursed_knight,
    "obsidian_golem": make_obsidian_golem,
    "hellhound": make_hellhound,
    "fire_elemental": make_fire_elemental,
    "dark_mage": make_dark_mage,
    "inferno_juggernaut": make_inferno_juggernaut,
    "shadow_assassin": make_shadow_assassin,
    "demon_king": make_demon_king,
}
ACT3_NORMAL_KEYS = ["fire_imp", "death_knight", "lava_hound", "cursed_knight", "obsidian_golem", "hellhound"]
ACT3_ELITE_KEYS = ["fire_elemental", "dark_mage", "inferno_juggernaut", "shadow_assassin"]
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
# 유물 풀 (엘리트/보스/축복/이벤트 보상으로 랜덤 지급) — 효과는 game/relics.py에서 전투 로직에 연동됨
# ---------------------------------------------------------------------------

RELIC_POOL = [
    # === 일반(common) - 소소하고 안정적인 효과 ===
    Relic(name="낡은 지갑", description="전투 승리 시 골드 +5", effect="worn_wallet", rarity="common"),
    Relic(name="여행자의 부적", description="전투 시작 시 HP 5% 회복", effect="travelers_charm", rarity="common"),
    Relic(name="무딘 숫돌", description="물리공격력 +5%", effect="dull_whetstone", rarity="common"),
    Relic(name="낡은 지팡이", description="마법공격력 +5%", effect="worn_staff", rarity="common"),
    Relic(name="튼튼한 허리띠", description="물방/마방 +5%", effect="sturdy_belt", rarity="common"),
    Relic(name="행운의 부적", description="크리티컬 확률 +5%p", effect="lucky_charm", rarity="common"),
    Relic(name="독아의 인장", description="독 시너지 중독 부여 확률 +10%p", effect="poison_proc_boost", rarity="common"),
    Relic(name="화염 심장", description="화염 시너지 화상 부여 스택 +5", effect="fire_stack_boost", rarity="common"),
    Relic(name="광전사의 표식", description="버서커 시너지 흡혈 확률 +10%p", effect="berserker_lifesteal_boost", rarity="common"),
    Relic(name="서리 파편", description="얼음 상태이상 행동불가 확률 +10%p", effect="ice_fail_boost", rarity="common"),
    Relic(name="현자의 돌", description="마나 시너지 보호막 재생 확률 +10%p", effect="mana_shield_boost", rarity="common"),
    Relic(name="가벼운 신발", description="공격속도 +0.10", effect="light_boots", rarity="common"),
    Relic(name="동전 주머니", description="몬스터 처치 시 획득 골드 +10%", effect="coin_pouch", rarity="common"),
    # === 희귀(rare) - 중간 강도, 개성 있는 효과 ===
    Relic(name="야수의 발톱", description="물리공격력 +8% (버서커 시너지 무관)", effect="beast_claw", rarity="rare"),
    Relic(name="현자의 렌즈", description="마법공격력 +8% (마나 시너지 무관)", effect="sage_lens", rarity="rare"),
    Relic(name="불굴의 심장", description="전투 중 첫 피격 데미지 무효", effect="first_hit_immune", rarity="rare"),
    Relic(name="거인의 뼈", description="최대 HP +30 (이번 런 한정)", effect="max_hp_up", rarity="rare"),
    Relic(name="도박사의 주사위", description="크리티컬 확률 +20%p, 대신 크리티컬 데미지 -25%p", effect="gamblers_dice", rarity="rare"),
    Relic(name="검은 낙인", description="스킬 쿨타임 -1초, 대신 최대 HP -15%", effect="black_brand", rarity="rare"),
    Relic(name="구원의 반지", description="전투 시작 시 HP 20% 회복, 대신 매턴 시작 시 HP 1% 자해", effect="ring_of_salvation", rarity="rare"),
    Relic(name="질풍의 목걸이", description="공격속도 +0.25", effect="windwalker_amulet", rarity="rare"),
    Relic(name="탐욕의 저울", description="몬스터 처치 시 획득 골드 +25%", effect="greed_scale", rarity="rare"),
    Relic(name="적응하는 인장", description="보유 시너지 중 가장 높은 것 +1 (장비를 바꾸면 그때그때 다시 계산됨)", effect="adaptive_signet", rarity="rare"),
    Relic(name="가시 갑주", description="피격 시 받은 피해의 8% 반사", effect="thorn_plate", rarity="rare"),
    # === 유니크(unique) - 강력하고 빌드를 정의하는 효과 ===
    Relic(name="악마의 계약", description="물공/마공 +25%, 대신 매턴 시작 시 현재 HP 3% 자해", effect="demons_pact", rarity="unique", image="relics/demons_pact.png"),
    Relic(name="폭주의 흉갑", description="물공/마공 +30%, 대신 물방/마방 -20%", effect="berserk_plate", rarity="unique"),
    Relic(name="피의 서약", description="크리티컬 데미지 +40%p, 대신 최대 HP -20%", effect="blood_oath", rarity="unique"),
    Relic(name="침묵의 룬", description="스킬을 사용할 수 없는 대신 물공/마공 +40%", effect="silent_rune", rarity="unique"),
    Relic(name="불사의 부적", description="전투당 1회 부활 (부활 시 HP 50%로 회복)", effect="undying_charm", rarity="unique"),
    Relic(name="마력 증폭 건틀릿", description="마법공격력의 60%를 물리공격력에 추가", effect="arcane_amplifier", rarity="unique"),
    Relic(name="비전 각인 건틀릿", description="물리공격력의 60%를 마법공격력에 추가", effect="arcane_engraving", rarity="unique"),
    Relic(name="폭풍우의 심장", description="공격속도 +0.40, 대신 물방/마방 -15%", effect="tempest_heart", rarity="unique"),
    Relic(name="황금의 손", description="몬스터 처치 시 획득 골드 +50%", effect="golden_touch", rarity="unique"),
]

# 1/2/3장 엘리트 처치 보상은 이 등급으로 고정 (밸런싱: 장이 오를수록 강한 유물)
ELITE_RELIC_RARITY_BY_ACT = {1: "common", 2: "rare", 3: "unique"}


def relics_by_rarity(rarity: str) -> list[Relic]:
    return [r for r in RELIC_POOL if r.rarity == rarity]


# ---------------------------------------------------------------------------
# 장비 풀 — 슬롯별 보장 스탯 + 등급별 태그 개수(일반 1 / 희귀 1 / 유니크 2 / 레전더리 3).
# 희귀는 기존 2태그에서 1개로 낮추면서 슬롯당 2종은 번개/출혈(신규 시너지)로 재배정했다.
# 등급별 스탯은 슬롯 기준값 대비 대략 희귀 x1.4 / 유니크 x1.8 / 레전더리 x2.4 스케일.
# ---------------------------------------------------------------------------

SAMPLE_ITEMS = [
    # 투구 - HP 증가 (일반4 / 희귀4 / 유니크3 / 레전더리3)
    Item(name="가죽 두건", slot="helmet", rarity="common", tags=["poison"], stat_bonus={"hp": 15}),
    Item(name="철 투구", slot="helmet", rarity="common", tags=["berserker"], stat_bonus={"hp": 20}),
    Item(name="얼음 투구", slot="helmet", rarity="common", tags=["ice"], stat_bonus={"hp": 18}),
    Item(name="감전 두건", slot="helmet", rarity="common", tags=["lightning"], stat_bonus={"hp": 17}),
    Item(name="독사냥꾼의 투구", slot="helmet", rarity="rare", tags=["poison"], stat_bonus={"hp": 25}),
    Item(name="현자의 로브 두건", slot="helmet", rarity="rare", tags=["mana"], stat_bonus={"hp": 22}),
    Item(name="감전의 투구", slot="helmet", rarity="rare", tags=["lightning"], stat_bonus={"hp": 24}),
    Item(name="출혈 마녀의 관", slot="helmet", rarity="rare", tags=["bleed"], stat_bonus={"hp": 26}),
    Item(name="폭풍 지배자의 투구", slot="helmet", rarity="unique", tags=["lightning", "mana"], stat_bonus={"hp": 32}),
    Item(name="혈투의 투구", slot="helmet", rarity="unique", tags=["bleed", "berserker"], stat_bonus={"hp": 30}),
    Item(name="삼원소 투구", slot="helmet", rarity="unique", tags=["ice", "fire"], stat_bonus={"hp": 34}),
    Item(name="폭풍의 제왕관", slot="helmet", rarity="legendary", tags=["lightning", "bleed", "berserker"], stat_bonus={"hp": 42}),
    Item(name="심연의 대투구", slot="helmet", rarity="legendary", tags=["poison", "ice", "mana"], stat_bonus={"hp": 40}),
    Item(name="용맹의 왕관", slot="helmet", rarity="legendary", tags=["fire", "berserker", "lightning"], stat_bonus={"hp": 46}),
    # 왼손 - 방패 또는 무기 (일반4 / 희귀4 / 유니크3 / 레전더리3)
    Item(name="가시 방패", slot="left_hand", rarity="common", tags=["berserker"], stat_bonus={"def_phys": 4}),
    Item(name="냉기의 방패", slot="left_hand", rarity="common", tags=["ice"], stat_bonus={"def_phys": 5}),
    Item(name="화염 방패", slot="left_hand", rarity="common", tags=["fire"], stat_bonus={"def_phys": 4}),
    Item(name="마나의 방패", slot="left_hand", rarity="common", tags=["mana"], stat_bonus={"def_phys": 4}),
    Item(name="독날 단검", slot="left_hand", rarity="rare", tags=["poison"], stat_bonus={"atk_phys": 5}),
    Item(name="화염의 대거", slot="left_hand", rarity="rare", tags=["fire"], stat_bonus={"atk_phys": 8}),
    Item(name="감전의 단검", slot="left_hand", rarity="rare", tags=["lightning"], stat_bonus={"atk_phys": 6}),
    Item(name="출혈의 대거", slot="left_hand", rarity="rare", tags=["bleed"], stat_bonus={"atk_phys": 7}),
    Item(name="뇌전 방패", slot="left_hand", rarity="unique", tags=["lightning", "ice"], stat_bonus={"def_phys": 10}),
    Item(name="출혈 단검", slot="left_hand", rarity="unique", tags=["bleed", "poison"], stat_bonus={"atk_phys": 10}),
    Item(name="폭풍의 대거", slot="left_hand", rarity="unique", tags=["lightning", "berserker"], stat_bonus={"atk_phys": 11}),
    Item(name="심판자의 방패", slot="left_hand", rarity="legendary", tags=["lightning", "bleed", "mana"], stat_bonus={"def_phys": 14}),
    Item(name="원소지배 단검", slot="left_hand", rarity="legendary", tags=["fire", "ice", "poison"], stat_bonus={"atk_phys": 15}),
    Item(name="종말의 대거", slot="left_hand", rarity="legendary", tags=["berserker", "bleed", "lightning"], stat_bonus={"atk_phys": 16}),
    # 오른손 - 무기 (일반4 / 희귀4 / 유니크3 / 레전더리3)
    Item(name="녹슨 단검", slot="right_hand", rarity="common", tags=["poison"], stat_bonus={"atk_phys": 5}, image="items/rusty_dagger.png"),
    Item(name="부족의 도끼", slot="right_hand", rarity="common", tags=["berserker"], stat_bonus={"atk_phys": 6}),
    Item(name="출혈 단도", slot="right_hand", rarity="common", tags=["bleed"], stat_bonus={"atk_phys": 5}),
    Item(name="마나의 지팡이", slot="right_hand", rarity="common", tags=["mana"], stat_bonus={"atk_phys": 5}),
    Item(name="맹독의 쌍검", slot="right_hand", rarity="rare", tags=["poison"], stat_bonus={"atk_phys": 9}, image="items/venomous_twin_swords.png"),
    Item(name="얼음 창", slot="right_hand", rarity="rare", tags=["ice"], stat_bonus={"atk_phys": 10}),
    Item(name="감전의 대검", slot="right_hand", rarity="rare", tags=["lightning"], stat_bonus={"atk_phys": 9}),
    Item(name="출혈의 지팡이", slot="right_hand", rarity="rare", tags=["bleed"], stat_bonus={"atk_phys": 9}),
    Item(name="뇌전검", slot="right_hand", rarity="unique", tags=["lightning", "berserker"], stat_bonus={"atk_phys": 13}),
    Item(name="출혈의 쌍검", slot="right_hand", rarity="unique", tags=["bleed", "poison"], stat_bonus={"atk_phys": 13}),
    Item(name="삼재의 지팡이", slot="right_hand", rarity="unique", tags=["fire", "mana"], stat_bonus={"atk_phys": 14}),
    Item(name="폭풍출혈검", slot="right_hand", rarity="legendary", tags=["lightning", "bleed", "berserker"], stat_bonus={"atk_phys": 19}),
    Item(name="대현자의 지팡이", slot="right_hand", rarity="legendary", tags=["mana", "fire", "ice"], stat_bonus={"atk_phys": 18}),
    Item(name="심연의 대검", slot="right_hand", rarity="legendary", tags=["poison", "bleed", "lightning"], stat_bonus={"atk_phys": 20}),
    # 갑옷 - 물방/마방 증가 (일반4 / 희귀4 / 유니크3 / 레전더리3)
    Item(name="가죽 갑옷", slot="armor", rarity="common", tags=["ice"], stat_bonus={"def_phys": 3, "def_magic": 3}),
    Item(name="가시 갑옷", slot="armor", rarity="common", tags=["berserker"], stat_bonus={"def_phys": 4}),
    Item(name="독저항 갑옷", slot="armor", rarity="common", tags=["poison"], stat_bonus={"def_phys": 3, "def_magic": 3}),
    Item(name="마법사의 로브", slot="armor", rarity="common", tags=["mana"], stat_bonus={"def_phys": 2, "def_magic": 4}),
    Item(name="서리 갑옷", slot="armor", rarity="rare", tags=["ice"], stat_bonus={"def_phys": 6, "def_magic": 6}),
    Item(name="용의 비늘 갑옷", slot="armor", rarity="rare", tags=["fire"], stat_bonus={"def_phys": 7, "def_magic": 7}),
    Item(name="감전 갑옷", slot="armor", rarity="rare", tags=["lightning"], stat_bonus={"def_phys": 6, "def_magic": 6}),
    Item(name="출혈전사 갑옷", slot="armor", rarity="rare", tags=["bleed"], stat_bonus={"def_phys": 7, "def_magic": 5}),
    Item(name="폭풍갑주", slot="armor", rarity="unique", tags=["lightning", "ice"], stat_bonus={"def_phys": 9, "def_magic": 9}),
    Item(name="유혈갑주", slot="armor", rarity="unique", tags=["bleed", "berserker"], stat_bonus={"def_phys": 10, "def_magic": 8}),
    Item(name="마나실드 갑옷", slot="armor", rarity="unique", tags=["mana", "fire"], stat_bonus={"def_phys": 9, "def_magic": 10}),
    Item(name="심연의 전신갑주", slot="armor", rarity="legendary", tags=["lightning", "bleed", "poison"], stat_bonus={"def_phys": 13, "def_magic": 13}),
    Item(name="용맹의 성갑", slot="armor", rarity="legendary", tags=["berserker", "fire", "ice"], stat_bonus={"def_phys": 14, "def_magic": 12}),
    Item(name="대현자의 로브", slot="armor", rarity="legendary", tags=["mana", "lightning", "bleed"], stat_bonus={"def_phys": 12, "def_magic": 14}),
    # 하의 - 공격속도 (일반4 / 희귀4 / 유니크3 / 레전더리3)
    Item(name="가죽 각반", slot="pants", rarity="common", tags=["poison"], stat_bonus={"atk_speed": 0.04}),
    Item(name="강철 각반", slot="pants", rarity="common", tags=["berserker"], stat_bonus={"atk_speed": 0.05}),
    Item(name="서리 각반", slot="pants", rarity="common", tags=["ice"], stat_bonus={"atk_speed": 0.04}),
    Item(name="감전 각반", slot="pants", rarity="common", tags=["lightning"], stat_bonus={"atk_speed": 0.05}),
    Item(name="사냥꾼의 각반", slot="pants", rarity="rare", tags=["poison"], stat_bonus={"atk_speed": 0.09}),
    Item(name="화염 각반", slot="pants", rarity="rare", tags=["fire"], stat_bonus={"atk_speed": 0.10}),
    Item(name="감전의 각반", slot="pants", rarity="rare", tags=["lightning"], stat_bonus={"atk_speed": 0.10}),
    Item(name="출혈의 각반", slot="pants", rarity="rare", tags=["bleed"], stat_bonus={"atk_speed": 0.09}),
    Item(name="폭풍질주 각반", slot="pants", rarity="unique", tags=["lightning", "berserker"], stat_bonus={"atk_speed": 0.16}),
    Item(name="유혈질주 각반", slot="pants", rarity="unique", tags=["bleed", "poison"], stat_bonus={"atk_speed": 0.15}),
    Item(name="서리감전 각반", slot="pants", rarity="unique", tags=["ice", "lightning"], stat_bonus={"atk_speed": 0.17}),
    Item(name="광휘의 각반", slot="pants", rarity="legendary", tags=["lightning", "bleed", "berserker"], stat_bonus={"atk_speed": 0.24}),
    Item(name="삼재 각반", slot="pants", rarity="legendary", tags=["fire", "ice", "poison"], stat_bonus={"atk_speed": 0.23}),
    Item(name="폭군의 각반", slot="pants", rarity="legendary", tags=["berserker", "fire", "lightning"], stat_bonus={"atk_speed": 0.25}),
    # 신발 - 크리율/크리데미지 (일반4 / 희귀4 / 유니크3 / 레전더리3)
    Item(name="사냥꾼의 부츠", slot="boots", rarity="common", tags=["berserker"], stat_bonus={"crit_chance": 0.05}),
    Item(name="독안개 신발", slot="boots", rarity="common", tags=["poison"], stat_bonus={"crit_chance": 0.04}),
    Item(name="냉기의 신발", slot="boots", rarity="common", tags=["ice"], stat_bonus={"crit_chance": 0.04}),
    Item(name="마나의 신발", slot="boots", rarity="common", tags=["mana"], stat_bonus={"crit_chance": 0.04}),
    Item(name="질풍의 부츠", slot="boots", rarity="rare", tags=["berserker"], stat_bonus={"crit_chance": 0.1, "crit_damage": 0.1}),
    Item(name="화염 질주화", slot="boots", rarity="rare", tags=["fire"], stat_bonus={"crit_chance": 0.08, "crit_damage": 0.15}),
    Item(name="감전 부츠", slot="boots", rarity="rare", tags=["lightning"], stat_bonus={"crit_chance": 0.09, "crit_damage": 0.1}),
    Item(name="출혈 슬리퍼", slot="boots", rarity="rare", tags=["bleed"], stat_bonus={"crit_chance": 0.07, "crit_damage": 0.12}),
    Item(name="폭풍질주화", slot="boots", rarity="unique", tags=["lightning", "berserker"], stat_bonus={"crit_chance": 0.13, "crit_damage": 0.18}),
    Item(name="유혈부츠", slot="boots", rarity="unique", tags=["bleed", "poison"], stat_bonus={"crit_chance": 0.12, "crit_damage": 0.2}),
    Item(name="서리감전화", slot="boots", rarity="unique", tags=["lightning", "ice"], stat_bonus={"crit_chance": 0.14, "crit_damage": 0.19}),
    Item(name="종말의 부츠", slot="boots", rarity="legendary", tags=["lightning", "bleed", "berserker"], stat_bonus={"crit_chance": 0.18, "crit_damage": 0.26}),
    Item(name="삼재화", slot="boots", rarity="legendary", tags=["fire", "ice", "poison"], stat_bonus={"crit_chance": 0.17, "crit_damage": 0.25}),
    Item(name="폭군의 신발", slot="boots", rarity="legendary", tags=["berserker", "fire", "lightning"], stat_bonus={"crit_chance": 0.19, "crit_damage": 0.28}),
    # 목걸이 - 스킬 쿨다운 감소 (일반4 / 희귀4 / 유니크3 / 레전더리3)
    Item(name="집중의 목걸이", slot="necklace", rarity="common", tags=["mana"], stat_bonus={"cooldown_reduction": 1}),
    Item(name="맹독의 목걸이", slot="necklace", rarity="common", tags=["poison"], stat_bonus={"cooldown_reduction": 1}),
    Item(name="서리의 목걸이", slot="necklace", rarity="common", tags=["ice"], stat_bonus={"cooldown_reduction": 1}),
    Item(name="화염의 목걸이", slot="necklace", rarity="common", tags=["fire"], stat_bonus={"cooldown_reduction": 1}),
    Item(name="현자의 목걸이", slot="necklace", rarity="rare", tags=["mana"], stat_bonus={"cooldown_reduction": 2}),
    Item(name="전투의 부적", slot="necklace", rarity="rare", tags=["berserker"], stat_bonus={"cooldown_reduction": 2}),
    Item(name="감전 목걸이", slot="necklace", rarity="rare", tags=["lightning"], stat_bonus={"cooldown_reduction": 2}),
    Item(name="출혈 목걸이", slot="necklace", rarity="rare", tags=["bleed"], stat_bonus={"cooldown_reduction": 2}),
    Item(name="폭풍의 부적", slot="necklace", rarity="unique", tags=["lightning", "mana"], stat_bonus={"cooldown_reduction": 3}),
    Item(name="유혈의 목걸이", slot="necklace", rarity="unique", tags=["bleed", "berserker"], stat_bonus={"cooldown_reduction": 3}),
    Item(name="원소의 목걸이", slot="necklace", rarity="unique", tags=["fire", "ice"], stat_bonus={"cooldown_reduction": 3}),
    Item(name="시공의 목걸이", slot="necklace", rarity="legendary", tags=["lightning", "bleed", "mana"], stat_bonus={"cooldown_reduction": 4}),
    Item(name="대재앙의 부적", slot="necklace", rarity="legendary", tags=["poison", "fire", "berserker"], stat_bonus={"cooldown_reduction": 4}),
    Item(name="심연의 목걸이", slot="necklace", rarity="legendary", tags=["ice", "bleed", "lightning"], stat_bonus={"cooldown_reduction": 4}),
    # 반지 - 방어막 제공 (일반4 / 희귀4 / 유니크3 / 레전더리3)
    Item(name="수호의 반지", slot="ring", rarity="common", tags=["mana"], stat_bonus={"shield": 10}),
    Item(name="불꽃 반지", slot="ring", rarity="common", tags=["fire"], stat_bonus={"shield": 8}),
    Item(name="독저항 반지", slot="ring", rarity="common", tags=["poison"], stat_bonus={"shield": 8}),
    Item(name="전사의 반지", slot="ring", rarity="common", tags=["berserker"], stat_bonus={"shield": 9}),
    Item(name="대마법사의 인장", slot="ring", rarity="rare", tags=["mana"], stat_bonus={"shield": 20}),
    Item(name="서리 인장", slot="ring", rarity="rare", tags=["ice"], stat_bonus={"shield": 18}),
    Item(name="감전의 인장", slot="ring", rarity="rare", tags=["lightning"], stat_bonus={"shield": 19}),
    Item(name="출혈의 인장", slot="ring", rarity="rare", tags=["bleed"], stat_bonus={"shield": 20}),
    Item(name="폭풍의 인장", slot="ring", rarity="unique", tags=["lightning", "mana"], stat_bonus={"shield": 27}),
    Item(name="유혈의 반지", slot="ring", rarity="unique", tags=["bleed", "poison"], stat_bonus={"shield": 26}),
    Item(name="삼원소 인장", slot="ring", rarity="unique", tags=["fire", "berserker"], stat_bonus={"shield": 28}),
    Item(name="심연의 인장", slot="ring", rarity="legendary", tags=["lightning", "bleed", "mana"], stat_bonus={"shield": 36}),
    Item(name="종말의 반지", slot="ring", rarity="legendary", tags=["poison", "fire", "berserker"], stat_bonus={"shield": 34}),
    Item(name="태초의 인장", slot="ring", rarity="legendary", tags=["ice", "lightning", "bleed"], stat_bonus={"shield": 38}),
]

assert {item.slot for item in SAMPLE_ITEMS} == set(EQUIPMENT_SLOTS)

# 런 시작 시 기본 지급 장비 (오른손 무기 1개만)
STARTER_ITEM_NAMES = ["녹슨 단검"]
