"""자동 전투 판정 (기획서 4.4절): 개입 없이 스탯/쿨타임/확률로만 진행.

시너지 효과(독/화염/버서커/얼음/마나)는 플레이어 캐릭터 → 몬스터 방향으로만 적용된다.
몬스터는 장비/시너지가 없는 순수 스탯 기반 상대로 취급한다.
"""

import random
from typing import Optional

from game.models import Character, Monster, Stats
from game.relics import RelicModifiers, compute_relic_modifiers
from game.synergy import SynergyResult, compute_synergy

MAX_TURNS = 50


FLAT_STAT_FIELDS = {"hp", "atk_phys", "atk_magic", "def_phys", "def_magic", "crit_chance", "crit_damage"}


def _apply_equipment_bonuses(stats: Stats, character: Character) -> Stats:
    result = stats.copy()
    for item in character.equipment.values():
        for key, value in item.stat_bonus.items():
            if key in FLAT_STAT_FIELDS:
                setattr(result, key, getattr(result, key) + value)
    return result


def _apply_synergy_stats(stats: Stats, synergy: SynergyResult) -> Stats:
    result = stats.copy()
    result.atk_phys = int(result.atk_phys * synergy.atk_phys_mult)
    result.atk_magic = int(result.atk_magic * synergy.atk_magic_mult)
    return result


def _cooldown_reduction(character: Character) -> int:
    necklace = character.equipment.get("necklace")
    if necklace is None:
        return 0
    return necklace.stat_bonus.get("cooldown_reduction", 0)


def _apply_relic_stats(stats: Stats, mods: RelicModifiers) -> Stats:
    result = stats.copy()
    result.atk_phys = int(result.atk_phys * mods.atk_phys_mult)
    result.atk_magic = int(result.atk_magic * mods.atk_magic_mult)
    result.def_phys = int(result.def_phys * mods.def_phys_mult)
    result.def_magic = int(result.def_magic * mods.def_magic_mult)
    result.hp = int((result.hp + mods.max_hp_flat) * mods.max_hp_mult)
    result.crit_chance = max(0.0, min(1.0, result.crit_chance + mods.crit_chance_bonus))
    result.crit_damage = max(1.0, result.crit_damage + mods.crit_damage_bonus)
    return result


def _apply_relic_synergy(synergy: SynergyResult, mods: RelicModifiers) -> SynergyResult:
    synergy.poison_proc_chance = max(0.0, min(1.0, synergy.poison_proc_chance + mods.poison_proc_bonus))
    synergy.fire_stack_amount += mods.fire_stack_bonus
    synergy.lifesteal_chance = max(0.0, min(1.0, synergy.lifesteal_chance + mods.lifesteal_chance_bonus))
    synergy.ice_fail_chance = max(0.0, min(1.0, synergy.ice_fail_chance + mods.ice_fail_bonus))
    synergy.shield_regen_chance = max(0.0, min(1.0, synergy.shield_regen_chance + mods.shield_regen_chance_bonus))
    return synergy


def _roll_damage(
    atk_phys: int, atk_magic: int, damage_type: str, multiplier: float,
    defender_def: int, crit_chance: float, crit_damage: float,
) -> tuple[int, bool]:
    """공격력 - 방어력 순. 크리티컬 시엔 물공/마공 중 높은 값에 크리배율을 곱한 뒤 방어력을 뺀다."""
    is_crit = random.random() < crit_chance
    if is_crit:
        base_atk = max(atk_phys, atk_magic) * crit_damage
    else:
        base_atk = atk_phys if damage_type == "phys" else atk_magic
    damage = max(1, int(base_atk * multiplier) - defender_def)
    return damage, is_crit


def _ring_shield(character: Character) -> int:
    ring = character.equipment.get("ring")
    if ring is None:
        return 0
    return ring.stat_bonus.get("shield", 0)


def compute_effective_stats(
    character: Character, tags_override: Optional[list[str]] = None
) -> tuple[Stats, SynergyResult, RelicModifiers, int]:
    """장비/시너지/유물을 전부 반영한 플레이어 유효 스탯 계산 — 전투 시뮬레이션과 UI 표시(전투
    화면 스탯 패널)가 공유하는 헬퍼. tags_override를 주면(예: 시너지 무효화 기믹) 실제 장착 태그
    대신 그 목록으로 시너지를 계산한다.
    반환: (유효 스탯, 시너지 결과, 유물 보정치, 실제 스킬 쿨다운)
    """
    tags = character.equipped_tags() if tags_override is None else tags_override
    synergy = compute_synergy(tags)
    relic_mods = compute_relic_modifiers(character)
    synergy = _apply_relic_synergy(synergy, relic_mods)

    stats = _apply_equipment_bonuses(character.base_stats, character)
    stats = _apply_synergy_stats(stats, synergy)
    stats = _apply_relic_stats(stats, relic_mods)
    skill_cooldown = max(1, character.skill.cooldown - _cooldown_reduction(character) - relic_mods.cooldown_reduction_bonus)
    return stats, synergy, relic_mods, skill_cooldown


def _dominant_tag(tags: list[str]) -> Optional[str]:
    if not tags:
        return None
    counts: dict[str, int] = {}
    for t in tags:
        counts[t] = counts.get(t, 0) + 1
    return max(counts, key=lambda t: counts[t])


GIMMICK_HEAL_INTERVAL = 3  # healer 기믹 자힐 주기(턴)
GIMMICK_STATUS_CHANCE = 0.3  # inflict_status 기믹 발동 확률


def simulate_battle(
    character: Character, monster: Monster, starting_hp: Optional[int] = None
) -> tuple[bool, list[str], int, int, int]:
    """플레이어 캐릭터 vs 몬스터 1:1 자동전투.

    starting_hp를 넘기면 (맵 이동 중 누적된 HP 등) 그 값에서 전투를 시작한다.
    오버킬 = 마지막으로 가한 피해량 - 몬스터 사망 직전 체력 (= 사망 시점 몬스터 HP의 음수값).
    보호막은 HP보다 먼저 차감되며, 전투 종료 시점 잔여값을 반환한다 (다음 전투에서는 링 기준으로 다시 채워짐).
    반환값: (승리 여부, 로그, 전투 종료 시점 HP, 오버킬, 전투 종료 시점 보호막)

    몬스터 기믹(Monster.gimmick)이 있으면 아래 규칙으로 전투에 반영된다:
    skill_null(스킬 봉인) / synergy_null(최다 보유 태그 시너지 1개 무효화) / healer(자힐) /
    inflict_status(피격 시 확률로 플레이어 공격력 영구 약화) / reflect(받은 피해 반사) /
    glass_shield(HP는 낮지만 별도 보호막 보유). shield_tank는 그룹전투에서만 의미가 있다.
    """
    log: list[str] = []
    tags = character.equipped_tags()

    dominant = _dominant_tag(tags)
    if monster.gimmick == "synergy_null" and dominant:
        tags = [t for t in tags if t != dominant]

    p_stats, synergy, relic_mods, p_skill_cooldown = compute_effective_stats(character, tags_override=tags)
    m_stats = monster.stats.copy()

    skill_sealed = monster.gimmick == "skill_null"
    m_shield = monster.gimmick_value if monster.gimmick == "glass_shield" else 0
    status_inflicted = False

    p_hp = p_stats.hp if starting_hp is None else min(starting_hp, p_stats.hp)
    if relic_mods.heal_on_start_percent > 0:
        heal = int(p_stats.hp * relic_mods.heal_on_start_percent)
        p_hp = min(p_stats.hp, p_hp + heal)
        log.append(f"[유물] 전투 시작 회복 +{heal}")
    p_shield = _ring_shield(character)
    m_hp = m_stats.hp
    p_cd, m_cd = p_skill_cooldown, monster.skill.cooldown
    m_poison_stacks = 0
    m_fire_stacks = 0
    m_bleed_stacks = 0
    m_iced = False
    first_hit_immune_available = relic_mods.first_hit_immune

    log.append(f"전투 시작: {character.name} vs {monster.name}")
    for tag_name, chance in [
        ("poison", synergy.poison_proc_chance),
        ("fire", synergy.fire_proc_chance),
        ("berserker", synergy.atk_phys_mult > 1.0),
        ("ice", synergy.ice_proc_chance),
        ("mana", synergy.atk_magic_mult > 1.0),
        ("lightning", synergy.lightning_proc_chance),
        ("bleed", synergy.bleed_proc_chance),
    ]:
        if chance:
            log.append(f"[시너지] {tag_name} 활성화")

    if monster.gimmick == "synergy_null" and dominant:
        log.append(f"[기믹] {monster.name}이(가) {dominant} 시너지를 무효화했다!")
    elif monster.gimmick == "skill_null":
        log.append(f"[기믹] {monster.name} 주변에서는 스킬을 사용할 수 없다!")
    elif monster.gimmick == "glass_shield":
        log.append(f"[기믹] {monster.name}은(는) 보호막 {m_shield}을(를) 두르고 있다 (기본 체력은 낮음)")

    def deal_player_damage(damage_type: str, multiplier: float, def_: int, count: int) -> int:
        nonlocal m_hp, m_shield, p_hp
        total = 0
        for _ in range(count):
            dmg, is_crit = _roll_damage(
                p_stats.atk_phys, p_stats.atk_magic, damage_type, multiplier,
                def_, p_stats.crit_chance, p_stats.crit_damage,
            )
            if m_shield > 0:
                absorbed = min(m_shield, dmg)
                m_shield -= absorbed
                dmg -= absorbed
            m_hp -= dmg
            total += dmg
            shield_note = f" (보호막 {m_shield} 남음)" if monster.gimmick == "glass_shield" else ""
            log.append(f"  - {dmg} 피해{' (크리티컬)' if is_crit else ''}{shield_note}")
            if monster.gimmick == "reflect" and dmg > 0:
                reflected = max(0, int(dmg * monster.gimmick_value / 100))
                if reflected:
                    p_hp -= reflected
                    log.append(f"  [기믹] {monster.name}이(가) {reflected} 피해를 반사했다!")
        return total

    for turn in range(1, MAX_TURNS + 1):
        # --- 몬스터 상태이상 (턴 시작) ---
        if m_poison_stacks > 0:
            tick = max(1, int(m_stats.hp * synergy.poison_tick_percent * m_poison_stacks))
            m_hp -= tick
            log.append(f"[턴{turn}] 중독 피해 {tick} ({m_poison_stacks}스택)")
            if m_hp <= 0:
                log.append(f"[턴{turn}] {monster.name} 중독으로 사망. {character.name} 승리!")
                return True, log, p_hp, max(0, -m_hp), p_shield

        if relic_mods.self_damage_percent_per_turn > 0:
            self_dmg = max(1, int(p_hp * relic_mods.self_damage_percent_per_turn))
            p_hp -= self_dmg
            log.append(f"[턴{turn}] [유물] 반동 피해 {self_dmg}")
            if p_hp <= 0:
                log.append(f"[턴{turn}] {character.name} 유물 반동으로 사망.")
                return False, log, 0, 0, 0

        # --- 회복형 기믹 (턴 시작) ---
        if monster.gimmick == "healer" and turn % GIMMICK_HEAL_INTERVAL == 0 and m_hp > 0:
            heal = int(m_stats.hp * monster.gimmick_value / 100)
            if heal:
                m_hp = min(m_stats.hp, m_hp + heal)
                log.append(f"[턴{turn}] [기믹] {monster.name} 자힐 +{heal}")

        # --- 캐릭터 턴 ---
        if p_cd <= 0 and not skill_sealed:
            def_ = m_stats.def_phys if character.skill.damage_type == "phys" else m_stats.def_magic
            log.append(f"[턴{turn}] {character.name}의 스킬 '{character.skill.name}'!")
            dealt = deal_player_damage(character.skill.damage_type, character.skill.damage_multiplier, def_, character.skill.hits)
            p_cd = p_skill_cooldown
        else:
            def_ = m_stats.def_phys if character.damage_type == "phys" else m_stats.def_magic
            log.append(f"[턴{turn}] {character.name} 기본 공격.")
            dealt = deal_player_damage(character.damage_type, 1.0, def_, 1)
            if not skill_sealed:
                p_cd -= 1

        if p_hp <= 0:
            log.append(f"[턴{turn}] {character.name} 사망 (반사 피해).")
            return False, log, 0, 0, 0

        if m_hp > 0:
            if synergy.poison_proc_chance and random.random() < synergy.poison_proc_chance:
                m_poison_stacks += 1
                log.append(f"[턴{turn}] {monster.name} 중독 스택 +1 (총 {m_poison_stacks})")
            if synergy.fire_proc_chance and random.random() < synergy.fire_proc_chance:
                m_fire_stacks += synergy.fire_stack_amount
                log.append(f"[턴{turn}] {monster.name} 화상 스택 +{synergy.fire_stack_amount} (총 {m_fire_stacks})")
            if synergy.ice_proc_chance and not m_iced and random.random() < synergy.ice_proc_chance:
                m_iced = True
                log.append(f"[턴{turn}] {monster.name} 빙결 부여")
            if synergy.lifesteal_chance and random.random() < synergy.lifesteal_chance:
                heal = int(dealt * synergy.lifesteal_ratio)
                p_hp = min(p_stats.hp, p_hp + heal)
                log.append(f"[턴{turn}] 흡혈 {heal}")
            if synergy.shield_regen_chance and random.random() < synergy.shield_regen_chance:
                regen = int(dealt * synergy.shield_regen_ratio)
                p_shield += regen
                log.append(f"[턴{turn}] 보호막 재생 +{regen} (총 {p_shield})")
            if synergy.lightning_proc_chance and random.random() < synergy.lightning_proc_chance:
                burst = synergy.lightning_burst_flat
                m_hp -= burst
                log.append(f"[턴{turn}] {monster.name} 감전 피해 {burst} (방어 무시)")
                if synergy.lightning_chain_chance and random.random() < synergy.lightning_chain_chance:
                    m_hp -= burst
                    log.append(f"[턴{turn}] 번개 연쇄! 추가 감전 피해 {burst}")
            if synergy.bleed_proc_chance and random.random() < synergy.bleed_proc_chance:
                m_bleed_stacks += 1
                log.append(f"[턴{turn}] {monster.name} 출혈 스택 +1 (총 {m_bleed_stacks})")

        # --- 화염 / 출혈 (턴 종료) ---
        if m_fire_stacks > 0 and m_hp > 0:
            tick = synergy.fire_tick_flat * m_fire_stacks
            m_hp -= tick
            log.append(f"[턴{turn}] 화상 피해 {tick} ({m_fire_stacks}스택)")

        if m_bleed_stacks > 0 and m_hp > 0:
            tick = synergy.bleed_tick_flat * m_bleed_stacks
            m_hp -= tick
            log.append(f"[턴{turn}] 출혈 피해 {tick} ({m_bleed_stacks}스택)")
            if synergy.bleed_decays:
                m_bleed_stacks -= 1

        if m_hp <= 0:
            log.append(f"[턴{turn}] {monster.name} 처치. {character.name} 승리!")
            return True, log, p_hp, max(0, -m_hp), p_shield

        # --- 몬스터 턴 ---
        if m_iced and random.random() < synergy.ice_fail_chance:
            log.append(f"[턴{turn}] {monster.name}은(는) 빙결로 행동 불가")
        else:
            if m_cd <= 0:
                def_ = p_stats.def_phys if monster.skill.damage_type == "phys" else p_stats.def_magic
                dmg, is_crit = _roll_damage(
                    m_stats.atk_phys, m_stats.atk_magic, monster.skill.damage_type, monster.skill.damage_multiplier,
                    def_, m_stats.crit_chance, m_stats.crit_damage,
                )
                m_cd = monster.skill.cooldown
                label = f"스킬 '{monster.skill.name}'"
            else:
                def_ = p_stats.def_phys if monster.damage_type == "phys" else p_stats.def_magic
                dmg, is_crit = _roll_damage(
                    m_stats.atk_phys, m_stats.atk_magic, monster.damage_type, 1.0,
                    def_, m_stats.crit_chance, m_stats.crit_damage,
                )
                m_cd -= 1
                label = "기본 공격"

            if p_shield > 0:
                absorbed = min(p_shield, dmg)
                p_shield -= absorbed
                dmg -= absorbed
            if first_hit_immune_available and dmg > 0:
                dmg = 0
                first_hit_immune_available = False
                log.append(f"[턴{turn}] [유물] 불굴의 심장 발동 - 피해 무효화")
            p_hp -= dmg
            log.append(f"[턴{turn}] {monster.name} {label}! {dmg} 피해{' (크리티컬)' if is_crit else ''} (보호막 {p_shield} 남음)")

            if monster.gimmick == "inflict_status" and not status_inflicted and random.random() < GIMMICK_STATUS_CHANCE:
                status_inflicted = True
                p_stats.atk_phys = int(p_stats.atk_phys * (1 - monster.gimmick_value / 100))
                p_stats.atk_magic = int(p_stats.atk_magic * (1 - monster.gimmick_value / 100))
                log.append(f"[턴{turn}] [기믹] {monster.name}이(가) 상태이상을 걸었다! 공격력 -{monster.gimmick_value}%")

        if p_hp <= 0:
            log.append(f"[턴{turn}] {character.name} 사망. {monster.name} 승리!")
            return False, log, 0, 0, 0

    log.append("[시간 초과] 무승부 처리 - 패배로 간주")
    return False, log, max(0, p_hp), 0, p_shield


def _pick_target(states: list[dict]) -> Optional[dict]:
    """생존한 몬스터 중 공격 대상을 고른다 - shield_tank 기믹이 있으면 살아있는 한 항상 우선."""
    alive = [s for s in states if s["alive"]]
    if not alive:
        return None
    tanks = [s for s in alive if s["monster"].gimmick == "shield_tank"]
    return tanks[0] if tanks else alive[0]


def simulate_group_battle(
    character: Character, monsters: list[Monster], starting_hp: Optional[int] = None
) -> tuple[bool, list[str], int, int, int]:
    """플레이어 캐릭터 vs 몬스터 여럿(1:2~1:3) 자동전투.

    플레이어는 항상 "맨 앞의 생존 몬스터"(shield_tank 기믹이 있으면 그쪽을 우선)만 공격 대상으로
    삼고, 시너지 프록(독/화염/출혈/번개 등)도 그 대상에게만 적용된다 — 대상이 죽으면 다음 생존
    몬스터로 자연히 넘어간다. 몬스터는 각자 자기 쿨다운으로 매턴 개별적으로 플레이어를 공격한다.
    반환 형식은 simulate_battle과 동일하되, 오버킬은 이번 전투에서 죽은 몬스터들의 합산치.
    """
    log: list[str] = []
    tags = character.equipped_tags()

    dominant = _dominant_tag(tags)
    any_synergy_null = any(m.gimmick == "synergy_null" for m in monsters)
    if any_synergy_null and dominant:
        tags = [t for t in tags if t != dominant]

    p_stats, synergy, relic_mods, p_skill_cooldown = compute_effective_stats(character, tags_override=tags)

    states = []
    for m in monsters:
        m_stats = m.stats.copy()
        states.append({
            "monster": m,
            "stats": m_stats,
            "hp": m_stats.hp,
            "shield": m.gimmick_value if m.gimmick == "glass_shield" else 0,
            "cd": m.skill.cooldown,
            "poison": 0,
            "fire": 0,
            "bleed": 0,
            "iced": False,
            "alive": True,
            "status_inflicted": False,
        })

    p_hp = p_stats.hp if starting_hp is None else min(starting_hp, p_stats.hp)
    if relic_mods.heal_on_start_percent > 0:
        heal = int(p_stats.hp * relic_mods.heal_on_start_percent)
        p_hp = min(p_stats.hp, p_hp + heal)
        log.append(f"[유물] 전투 시작 회복 +{heal}")
    p_shield = _ring_shield(character)
    first_hit_immune_available = relic_mods.first_hit_immune
    total_overkill = 0
    p_cd = p_skill_cooldown

    names = ", ".join(m.name for m in monsters)
    log.append(f"전투 시작: {character.name} vs {names} ({len(monsters)}마리)")
    for tag_name, chance in [
        ("poison", synergy.poison_proc_chance),
        ("fire", synergy.fire_proc_chance),
        ("berserker", synergy.atk_phys_mult > 1.0),
        ("ice", synergy.ice_proc_chance),
        ("mana", synergy.atk_magic_mult > 1.0),
        ("lightning", synergy.lightning_proc_chance),
        ("bleed", synergy.bleed_proc_chance),
    ]:
        if chance:
            log.append(f"[시너지] {tag_name} 활성화")
    if any_synergy_null and dominant:
        log.append(f"[기믹] 그룹 내 몬스터가 {dominant} 시너지를 무효화했다!")
    for s in states:
        if s["monster"].gimmick == "glass_shield":
            log.append(f"[기믹] {s['monster'].name}은(는) 보호막 {s['shield']}을(를) 두르고 있다 (기본 체력은 낮음)")

    def deal_player_damage(target: dict, damage_type: str, multiplier: float, def_: int, count: int) -> int:
        nonlocal p_hp
        total = 0
        for _ in range(count):
            dmg, is_crit = _roll_damage(
                p_stats.atk_phys, p_stats.atk_magic, damage_type, multiplier,
                def_, p_stats.crit_chance, p_stats.crit_damage,
            )
            if target["shield"] > 0:
                absorbed = min(target["shield"], dmg)
                target["shield"] -= absorbed
                dmg -= absorbed
            target["hp"] -= dmg
            total += dmg
            shield_note = f" (보호막 {target['shield']} 남음)" if target["monster"].gimmick == "glass_shield" else ""
            log.append(f"  - {target['monster'].name}에게 {dmg} 피해{' (크리티컬)' if is_crit else ''}{shield_note}")
            if target["monster"].gimmick == "reflect" and dmg > 0:
                reflected = max(0, int(dmg * target["monster"].gimmick_value / 100))
                if reflected:
                    p_hp -= reflected
                    log.append(f"  [기믹] {target['monster'].name}이(가) {reflected} 피해를 반사했다!")
        return total

    for turn in range(1, MAX_TURNS + 1):
        # --- 몬스터 상태이상 / 회복형 기믹 (턴 시작) ---
        for s in states:
            if not s["alive"]:
                continue
            if s["poison"] > 0:
                tick = max(1, int(s["stats"].hp * synergy.poison_tick_percent * s["poison"]))
                s["hp"] -= tick
                log.append(f"[턴{turn}] {s['monster'].name} 중독 피해 {tick} ({s['poison']}스택)")
            if s["monster"].gimmick == "healer" and turn % GIMMICK_HEAL_INTERVAL == 0 and s["hp"] > 0:
                heal = int(s["stats"].hp * s["monster"].gimmick_value / 100)
                if heal:
                    s["hp"] = min(s["stats"].hp, s["hp"] + heal)
                    log.append(f"[턴{turn}] [기믹] {s['monster'].name} 자힐 +{heal}")
            if s["hp"] <= 0 and s["alive"]:
                s["alive"] = False
                total_overkill += max(0, -s["hp"])
                log.append(f"[턴{turn}] {s['monster'].name} 처치!")

        if relic_mods.self_damage_percent_per_turn > 0:
            self_dmg = max(1, int(p_hp * relic_mods.self_damage_percent_per_turn))
            p_hp -= self_dmg
            log.append(f"[턴{turn}] [유물] 반동 피해 {self_dmg}")
            if p_hp <= 0:
                log.append(f"[턴{turn}] {character.name} 유물 반동으로 사망.")
                return False, log, 0, 0, 0

        if all(not s["alive"] for s in states):
            log.append(f"[턴{turn}] 전원 처치! {character.name} 승리!")
            return True, log, p_hp, total_overkill, p_shield

        # --- 캐릭터 턴 ---
        target = _pick_target(states)
        skill_sealed = any(s["alive"] and s["monster"].gimmick == "skill_null" for s in states)

        if p_cd <= 0 and not skill_sealed:
            def_ = target["stats"].def_phys if character.skill.damage_type == "phys" else target["stats"].def_magic
            log.append(f"[턴{turn}] {character.name}의 스킬 '{character.skill.name}'! (대상: {target['monster'].name})")
            dealt = deal_player_damage(target, character.skill.damage_type, character.skill.damage_multiplier, def_, character.skill.hits)
            p_cd = p_skill_cooldown
        else:
            def_ = target["stats"].def_phys if character.damage_type == "phys" else target["stats"].def_magic
            log.append(f"[턴{turn}] {character.name} 기본 공격. (대상: {target['monster'].name})")
            dealt = deal_player_damage(target, character.damage_type, 1.0, def_, 1)
            if not skill_sealed:
                p_cd -= 1

        if p_hp <= 0:
            log.append(f"[턴{turn}] {character.name} 사망 (반사 피해).")
            return False, log, 0, 0, 0

        if target["hp"] > 0:
            if synergy.poison_proc_chance and random.random() < synergy.poison_proc_chance:
                target["poison"] += 1
                log.append(f"[턴{turn}] {target['monster'].name} 중독 스택 +1 (총 {target['poison']})")
            if synergy.fire_proc_chance and random.random() < synergy.fire_proc_chance:
                target["fire"] += synergy.fire_stack_amount
                log.append(f"[턴{turn}] {target['monster'].name} 화상 스택 +{synergy.fire_stack_amount} (총 {target['fire']})")
            if synergy.ice_proc_chance and not target["iced"] and random.random() < synergy.ice_proc_chance:
                target["iced"] = True
                log.append(f"[턴{turn}] {target['monster'].name} 빙결 부여")
            if synergy.lifesteal_chance and random.random() < synergy.lifesteal_chance:
                heal = int(dealt * synergy.lifesteal_ratio)
                p_hp = min(p_stats.hp, p_hp + heal)
                log.append(f"[턴{turn}] 흡혈 {heal}")
            if synergy.shield_regen_chance and random.random() < synergy.shield_regen_chance:
                regen = int(dealt * synergy.shield_regen_ratio)
                p_shield += regen
                log.append(f"[턴{turn}] 보호막 재생 +{regen} (총 {p_shield})")
            if synergy.lightning_proc_chance and random.random() < synergy.lightning_proc_chance:
                burst = synergy.lightning_burst_flat
                target["hp"] -= burst
                log.append(f"[턴{turn}] {target['monster'].name} 감전 피해 {burst} (방어 무시)")
                if synergy.lightning_chain_chance and random.random() < synergy.lightning_chain_chance:
                    target["hp"] -= burst
                    log.append(f"[턴{turn}] 번개 연쇄! 추가 감전 피해 {burst}")
            if synergy.bleed_proc_chance and random.random() < synergy.bleed_proc_chance:
                target["bleed"] += 1
                log.append(f"[턴{turn}] {target['monster'].name} 출혈 스택 +1 (총 {target['bleed']})")

        # --- 화염 / 출혈 (턴 종료, 현재 대상만) ---
        if target["fire"] > 0 and target["hp"] > 0:
            tick = synergy.fire_tick_flat * target["fire"]
            target["hp"] -= tick
            log.append(f"[턴{turn}] {target['monster'].name} 화상 피해 {tick} ({target['fire']}스택)")

        if target["bleed"] > 0 and target["hp"] > 0:
            tick = synergy.bleed_tick_flat * target["bleed"]
            target["hp"] -= tick
            log.append(f"[턴{turn}] {target['monster'].name} 출혈 피해 {tick} ({target['bleed']}스택)")
            if synergy.bleed_decays:
                target["bleed"] -= 1

        if target["hp"] <= 0 and target["alive"]:
            target["alive"] = False
            total_overkill += max(0, -target["hp"])
            log.append(f"[턴{turn}] {target['monster'].name} 처치!")

        if all(not s["alive"] for s in states):
            log.append(f"[턴{turn}] 전원 처치! {character.name} 승리!")
            return True, log, p_hp, total_overkill, p_shield

        # --- 몬스터 턴 (생존한 몬스터가 각자 개별 공격) ---
        for s in states:
            if not s["alive"]:
                continue
            m_stats = s["stats"]
            monster = s["monster"]
            if s["iced"] and random.random() < synergy.ice_fail_chance:
                log.append(f"[턴{turn}] {monster.name}은(는) 빙결로 행동 불가")
                continue

            if s["cd"] <= 0:
                def_ = p_stats.def_phys if monster.skill.damage_type == "phys" else p_stats.def_magic
                dmg, is_crit = _roll_damage(
                    m_stats.atk_phys, m_stats.atk_magic, monster.skill.damage_type, monster.skill.damage_multiplier,
                    def_, m_stats.crit_chance, m_stats.crit_damage,
                )
                s["cd"] = monster.skill.cooldown
                label = f"스킬 '{monster.skill.name}'"
            else:
                def_ = p_stats.def_phys if monster.damage_type == "phys" else p_stats.def_magic
                dmg, is_crit = _roll_damage(
                    m_stats.atk_phys, m_stats.atk_magic, monster.damage_type, 1.0,
                    def_, m_stats.crit_chance, m_stats.crit_damage,
                )
                s["cd"] -= 1
                label = "기본 공격"

            if p_shield > 0:
                absorbed = min(p_shield, dmg)
                p_shield -= absorbed
                dmg -= absorbed
            if first_hit_immune_available and dmg > 0:
                dmg = 0
                first_hit_immune_available = False
                log.append(f"[턴{turn}] [유물] 불굴의 심장 발동 - 피해 무효화")
            p_hp -= dmg
            log.append(f"[턴{turn}] {monster.name} {label}! {dmg} 피해{' (크리티컬)' if is_crit else ''} (보호막 {p_shield} 남음)")

            if monster.gimmick == "inflict_status" and not s["status_inflicted"] and random.random() < GIMMICK_STATUS_CHANCE:
                s["status_inflicted"] = True
                p_stats.atk_phys = int(p_stats.atk_phys * (1 - monster.gimmick_value / 100))
                p_stats.atk_magic = int(p_stats.atk_magic * (1 - monster.gimmick_value / 100))
                log.append(f"[턴{turn}] [기믹] {monster.name}이(가) 상태이상을 걸었다! 공격력 -{monster.gimmick_value}%")

            if p_hp <= 0:
                log.append(f"[턴{turn}] {character.name} 사망. {monster.name} 승리!")
                return False, log, 0, 0, 0

    log.append("[시간 초과] 무승부 처리 - 패배로 간주")
    return False, log, max(0, p_hp), 0, p_shield
