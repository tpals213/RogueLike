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


def simulate_battle(
    character: Character, monster: Monster, starting_hp: Optional[int] = None
) -> tuple[bool, list[str], int, int, int]:
    """플레이어 캐릭터 vs 몬스터 1:1 자동전투.

    starting_hp를 넘기면 (맵 이동 중 누적된 HP 등) 그 값에서 전투를 시작한다.
    오버킬 = 마지막으로 가한 피해량 - 몬스터 사망 직전 체력 (= 사망 시점 몬스터 HP의 음수값).
    보호막은 HP보다 먼저 차감되며, 전투 종료 시점 잔여값을 반환한다 (다음 전투에서는 링 기준으로 다시 채워짐).
    반환값: (승리 여부, 로그, 전투 종료 시점 HP, 오버킬, 전투 종료 시점 보호막)
    """
    log: list[str] = []
    tags = character.equipped_tags()
    synergy = compute_synergy(tags)
    relic_mods = compute_relic_modifiers(character)
    synergy = _apply_relic_synergy(synergy, relic_mods)

    p_stats = _apply_equipment_bonuses(character.base_stats, character)
    p_stats = _apply_synergy_stats(p_stats, synergy)
    p_stats = _apply_relic_stats(p_stats, relic_mods)
    m_stats = monster.stats.copy()

    p_skill_cooldown = max(1, character.skill.cooldown - _cooldown_reduction(character) - relic_mods.cooldown_reduction_bonus)
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
    m_iced = False
    first_hit_immune_available = relic_mods.first_hit_immune

    log.append(f"전투 시작: {character.name} vs {monster.name}")
    for tag_name, chance in [
        ("poison", synergy.poison_proc_chance),
        ("fire", synergy.fire_proc_chance),
        ("berserker", synergy.atk_phys_mult > 1.0),
        ("ice", synergy.ice_proc_chance),
        ("mana", synergy.atk_magic_mult > 1.0),
    ]:
        if chance:
            log.append(f"[시너지] {tag_name} 활성화")

    def deal_player_damage(damage_type: str, multiplier: float, def_: int, count: int) -> int:
        nonlocal m_hp
        total = 0
        for _ in range(count):
            dmg, is_crit = _roll_damage(
                p_stats.atk_phys, p_stats.atk_magic, damage_type, multiplier,
                def_, p_stats.crit_chance, p_stats.crit_damage,
            )
            m_hp -= dmg
            total += dmg
            log.append(f"  - {dmg} 피해{' (크리티컬)' if is_crit else ''}")
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

        # --- 캐릭터 턴 ---
        if p_cd <= 0:
            def_ = m_stats.def_phys if character.skill.damage_type == "phys" else m_stats.def_magic
            log.append(f"[턴{turn}] {character.name}의 스킬 '{character.skill.name}'!")
            dealt = deal_player_damage(character.skill.damage_type, character.skill.damage_multiplier, def_, character.skill.hits)
            p_cd = p_skill_cooldown
        else:
            def_ = m_stats.def_phys if character.damage_type == "phys" else m_stats.def_magic
            log.append(f"[턴{turn}] {character.name} 기본 공격.")
            dealt = deal_player_damage(character.damage_type, 1.0, def_, 1)
            p_cd -= 1

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

        # --- 화염 (턴 종료) ---
        if m_fire_stacks > 0 and m_hp > 0:
            tick = synergy.fire_tick_flat * m_fire_stacks
            m_hp -= tick
            log.append(f"[턴{turn}] 화상 피해 {tick} ({m_fire_stacks}스택)")

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

        if p_hp <= 0:
            log.append(f"[턴{turn}] {character.name} 사망. {monster.name} 승리!")
            return False, log, 0, 0, 0

    log.append("[시간 초과] 무승부 처리 - 패배로 간주")
    return False, log, max(0, p_hp), 0, p_shield
