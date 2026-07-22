"""자동 전투 판정 (기획서 4.4절): 개입 없이 스탯/쿨타임/확률로만 진행.

시너지 효과(독/화염/버서커/얼음/마나)는 플레이어 캐릭터 → 몬스터 방향으로만 적용된다.
몬스터는 장비/시너지가 없는 순수 스탯 기반 상대로 취급한다.
"""

import random
from typing import Optional

from game.hub import SHIELD_REGEN_FLAT_PERCENT, TraitModifiers
from game.models import Character, Monster, Stats
from game.relics import RelicModifiers, compute_relic_modifiers
from game.synergy import SynergyResult, compute_synergy

MAX_TIME = 50.0  # 전투 시간 제한(초) - 기존 MAX_TURNS(턴제 시절) 수치를 그대로 재해석


FLAT_STAT_FIELDS = {"hp", "atk_phys", "atk_magic", "def_phys", "def_magic", "crit_chance", "crit_damage", "atk_speed"}


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
    orig_atk_phys, orig_atk_magic = result.atk_phys, result.atk_magic
    if mods.magic_to_phys_percent:
        result.atk_phys += int(orig_atk_magic * mods.magic_to_phys_percent)
    if mods.phys_to_magic_percent:
        result.atk_magic += int(orig_atk_phys * mods.phys_to_magic_percent)
    result.def_phys = int(result.def_phys * mods.def_phys_mult)
    result.def_magic = int(result.def_magic * mods.def_magic_mult)
    result.hp = int((result.hp + mods.max_hp_flat) * mods.max_hp_mult)
    result.crit_chance = max(0.0, min(1.0, result.crit_chance + mods.crit_chance_bonus))
    result.crit_damage = max(1.0, result.crit_damage + mods.crit_damage_bonus)
    result.atk_speed = max(0.1, result.atk_speed + mods.atk_speed_bonus)
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


def _reduce_incoming_damage(dmg: int, is_crit: bool, trait_mods: TraitModifiers, revive_shield_active: bool) -> int:
    """방어형 특성(완강함/철옹성/냉정함/불사조의 심장 부활 후 보호)을 몬스터의 직접 공격 피해에 반영."""
    reduction = trait_mods.flat_damage_reduction_percent
    if revive_shield_active and trait_mods.revive_shield_reduction:
        reduction = 1 - (1 - reduction) * (1 - trait_mods.revive_shield_reduction)
    if is_crit and trait_mods.incoming_crit_damage_reduction:
        reduction = 1 - (1 - reduction) * (1 - trait_mods.incoming_crit_damage_reduction)
    if reduction <= 0:
        return dmg
    return int(dmg * (1 - reduction))


def compute_effective_stats(
    character: Character, tags_override: Optional[list[str]] = None
) -> tuple[Stats, SynergyResult, RelicModifiers, int]:
    """장비/시너지/유물/특성을 전부 반영한 플레이어 유효 스탯 계산 — 전투 시뮬레이션과 UI 표시(전투
    화면 스탯 패널)가 공유하는 헬퍼. tags_override를 주면(예: 시너지 무효화 기믹) 실제 장착 태그
    대신 그 목록으로 시너지를 계산한다.
    반환: (유효 스탯, 시너지 결과, 유물 보정치, 실제 스킬 쿨다운)
    """
    trait_mods = character.trait_mods or TraitModifiers()
    relic_mods = compute_relic_modifiers(character)
    tags = character.equipped_tags() if tags_override is None else tags_override
    synergy = compute_synergy(
        tags,
        boost_all=trait_mods.synergy_boost_all,
        boost_highest=trait_mods.synergy_boost_highest + relic_mods.synergy_boost_highest,
    )
    synergy = _apply_relic_synergy(synergy, relic_mods)

    stats = _apply_equipment_bonuses(character.base_stats, character)
    stats = _apply_synergy_stats(stats, synergy)
    stats = _apply_relic_stats(stats, relic_mods)
    skill_cooldown = max(
        1,
        character.skill.cooldown - _cooldown_reduction(character) - relic_mods.cooldown_reduction_bonus - trait_mods.cooldown_reduction,
    )
    return stats, synergy, relic_mods, skill_cooldown


def _dominant_tag(tags: list[str]) -> Optional[str]:
    if not tags:
        return None
    counts: dict[str, int] = {}
    for t in tags:
        counts[t] = counts.get(t, 0) + 1
    return max(counts, key=lambda t: counts[t])


GIMMICK_HEAL_INTERVAL = 3  # healer 기믹 자힐 주기(턴)
GIMMICK_STATUS_CHANCE = 0.3  # inflict_status 기믹 발동 확률 (특성 "위기 감지"로 감소 가능)


def simulate_battle(
    character: Character, monster: Monster, starting_hp: Optional[int] = None
) -> tuple[bool, list[str], int, int, int]:
    """플레이어 캐릭터 vs 몬스터 1:1 자동전투 - 실시간(초) 기반, 양측 공격속도(Stats.atk_speed)로 독립 진행.

    양측 모두 1/atk_speed초 간격으로 스스로 행동한다. 스킬 쿨다운도 초 단위이며, 쿨다운이 다 찼어도
    실제 발동은 그 주체의 다음 공격 시점에 이루어진다 (예: 쿨다운 3초·공속 1.2면 0/0.83/1.67/2.5초는
    기본공격, 3초를 넘긴 다음 틱인 3.33초에 비로소 스킬 발동).

    "매턴" 계열 주기 효과는 이제 그 효과가 붙는 쪽의 "자기 행동 시점"에 발동한다: 중독/화상/출혈처럼
    몬스터를 갉아먹는 효과는 몬스터가 행동할 때, 생명의 고동처럼 플레이어를 회복시키는 효과는 플레이어가
    행동할 때 틱한다 (회복형 몬스터 기믹의 "3턴마다"도 "자기 행동 3회마다"로 재해석). 지속시간/쿨다운
    수치(스킬 쿨다운, 불사조의 심장 보호 지속시간, 시간 제한)는 예전 "턴" 수치를 그대로 "초"로 재해석한다.

    starting_hp를 넘기면 (맵 이동 중 누적된 HP 등) 그 값에서 전투를 시작한다.
    오버킬 = 마지막으로 가한 피해량 - 몬스터 사망 직전 체력 (= 사망 시점 몬스터 HP의 음수값).
    보호막은 HP보다 먼저 차감되며, 전투 종료 시점 잔여값을 반환한다 (다음 전투에서는 링 기준으로 다시 채워짐).
    반환값: (승리 여부, 로그, 전투 종료 시점 HP, 오버킬, 전투 종료 시점 보호막)

    몬스터 기믹(Monster.gimmick)이 있으면 아래 규칙으로 전투에 반영된다:
    skill_null(스킬 봉인) / synergy_null(최다 보유 태그 시너지 1개 무효화) / healer(자힐) /
    inflict_status(피격 시 확률로 플레이어 공격력 영구 약화) / reflect(받은 피해 반사) /
    glass_shield(HP는 낮지만 별도 보호막 보유). shield_tank는 그룹전투에서만 의미가 있다.

    허브 특성(game.hub.TraitModifiers)도 여기서 함께 반영된다: 부활(불사조의 심장), 가시 오라,
    생명의 고동, 보호막 계열, 방어형 감소(완강함/철옹성/냉정함), 공격형 확률형(쌍수 연격/필멸의 검),
    관통(관통 타격), 기믹 저항(위기 감지).
    """
    log: list[str] = []
    tags = character.equipped_tags()
    trait_mods = character.trait_mods or TraitModifiers()

    dominant = _dominant_tag(tags)
    if monster.gimmick == "synergy_null" and dominant:
        tags = [t for t in tags if t != dominant]

    p_stats, synergy, relic_mods, p_skill_cooldown = compute_effective_stats(character, tags_override=tags)
    m_stats = monster.stats.copy()

    skill_sealed = monster.gimmick == "skill_null" or relic_mods.skill_sealed
    m_shield = monster.gimmick_value if monster.gimmick == "glass_shield" else 0
    status_inflicted = False
    thorns_percent = trait_mods.thorns_percent + relic_mods.thorns_percent

    p_hp = p_stats.hp if starting_hp is None else min(starting_hp, p_stats.hp)
    if relic_mods.heal_on_start_percent > 0:
        heal = int(p_stats.hp * relic_mods.heal_on_start_percent)
        p_hp = min(p_stats.hp, p_hp + heal)
        log.append(f"[유물] 전투 시작 회복 +{heal}")
    p_shield = _ring_shield(character) + trait_mods.shield_on_start_flat + int(p_stats.hp * trait_mods.shield_on_start_percent)
    m_hp = m_stats.hp
    m_poison_stacks = 0
    m_fire_stacks = 0
    m_bleed_stacks = 0
    m_iced = False
    m_action_count = 0
    first_hit_immune_available = relic_mods.first_hit_immune or trait_mods.first_hit_immune
    revive_shield_until = -1.0
    relic_revive_used = False

    p_interval = 1.0 / max(0.1, p_stats.atk_speed)
    m_interval = 1.0 / max(0.1, m_stats.atk_speed)
    p_skill_ready_at = float(p_skill_cooldown)
    m_skill_ready_at = float(monster.skill.cooldown)
    p_next_time = 0.0
    m_next_time = 0.0

    def _try_revive() -> bool:
        nonlocal p_hp, revive_shield_until, relic_revive_used
        if trait_mods.revive_charges > 0:
            trait_mods.revive_charges -= 1
            p_hp = max(1, int(p_stats.hp * trait_mods.revive_heal_percent))
            revive_shield_until = t + trait_mods.revive_shield_turns
            log.append(f"[{t:.2f}초] [특성] 불사조의 심장 발동! {character.name} 부활 (HP {p_hp})")
            return True
        if relic_mods.revive_charges > 0 and not relic_revive_used:
            relic_revive_used = True
            p_hp = max(1, int(p_stats.hp * relic_mods.revive_heal_percent))
            log.append(f"[{t:.2f}초] [유물] 불사의 부적 발동! {character.name} 부활 (HP {p_hp})")
            return True
        return False

    log.append(f"전투 시작: {character.name} vs {monster.name} (공속 {p_stats.atk_speed:.2f} vs {m_stats.atk_speed:.2f})")
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
        def_eff = int(def_ * (1 - trait_mods.armor_pen_percent))

        def _hit() -> tuple[int, bool]:
            nonlocal m_hp, m_shield, p_hp
            dmg, is_crit = _roll_damage(
                p_stats.atk_phys, p_stats.atk_magic, damage_type, multiplier,
                def_eff, p_stats.crit_chance, p_stats.crit_damage,
            )
            if m_shield > 0:
                absorbed = min(m_shield, dmg)
                m_shield -= absorbed
                dmg -= absorbed
            m_hp -= dmg
            shield_note = f" (보호막 {m_shield} 남음)" if monster.gimmick == "glass_shield" else ""
            log.append(f"  - {dmg} 피해{' (크리티컬)' if is_crit else ''}{shield_note}")
            if monster.gimmick == "reflect" and dmg > 0:
                reflected = max(0, int(dmg * monster.gimmick_value / 100))
                if reflected:
                    p_hp -= reflected
                    log.append(f"  [기믹] {monster.name}이(가) {reflected} 피해를 반사했다!")
            return dmg, is_crit

        total = 0
        for _ in range(count):
            dmg, is_crit = _hit()
            total += dmg
            if trait_mods.double_attack_chance and random.random() < trait_mods.double_attack_chance:
                log.append("  [특성] 쌍수 연격 발동!")
                extra_dmg, _ = _hit()
                total += extra_dmg
            if is_crit and trait_mods.crit_extra_attack_chance and random.random() < trait_mods.crit_extra_attack_chance:
                log.append("  [특성] 필멸의 검 발동!")
                extra_dmg, _ = _hit()
                total += extra_dmg
        return total

    while True:
        t = p_next_time if p_next_time <= m_next_time else m_next_time
        if t > MAX_TIME:
            log.append("[시간 초과] 무승부 처리 - 패배로 간주")
            return False, log, max(0, p_hp), 0, p_shield

        if p_next_time <= m_next_time:
            # --- 플레이어 행동 시점 ---
            if trait_mods.regen_percent_per_turn and p_hp > 0:
                heal = int(p_stats.hp * trait_mods.regen_percent_per_turn)
                before = p_hp
                p_hp = min(p_stats.hp, p_hp + heal)
                if p_hp > before:
                    log.append(f"[{t:.2f}초] [특성] 생명의 고동 회복 +{p_hp - before}")
            if trait_mods.shield_regen_flat_chance and random.random() < trait_mods.shield_regen_flat_chance:
                regen = int(p_stats.hp * SHIELD_REGEN_FLAT_PERCENT)
                p_shield += regen
                log.append(f"[{t:.2f}초] [특성] 마나의 잔재 발동 - 보호막 +{regen} (총 {p_shield})")

            if relic_mods.self_damage_percent_per_turn > 0:
                self_dmg = max(1, int(p_hp * relic_mods.self_damage_percent_per_turn))
                p_hp -= self_dmg
                log.append(f"[{t:.2f}초] [유물] 반동 피해 {self_dmg}")
                if p_hp <= 0:
                    if not _try_revive():
                        log.append(f"[{t:.2f}초] {character.name} 유물 반동으로 사망.")
                        return False, log, 0, 0, 0

            if t >= p_skill_ready_at and not skill_sealed:
                def_ = m_stats.def_phys if character.skill.damage_type == "phys" else m_stats.def_magic
                log.append(f"[{t:.2f}초] {character.name}의 스킬 '{character.skill.name}'!")
                dealt = deal_player_damage(character.skill.damage_type, character.skill.damage_multiplier, def_, character.skill.hits)
                p_skill_ready_at = t + p_skill_cooldown
            else:
                def_ = m_stats.def_phys if character.damage_type == "phys" else m_stats.def_magic
                log.append(f"[{t:.2f}초] {character.name} 기본 공격.")
                dealt = deal_player_damage(character.damage_type, 1.0, def_, 1)

            if p_hp <= 0:
                if not _try_revive():
                    log.append(f"[{t:.2f}초] {character.name} 사망 (반사 피해).")
                    return False, log, 0, 0, 0

            if m_hp > 0:
                if synergy.poison_proc_chance and random.random() < synergy.poison_proc_chance:
                    m_poison_stacks += 1
                    log.append(f"[{t:.2f}초] {monster.name} 중독 스택 +1 (총 {m_poison_stacks})")
                if synergy.fire_proc_chance and random.random() < synergy.fire_proc_chance:
                    m_fire_stacks += synergy.fire_stack_amount
                    log.append(f"[{t:.2f}초] {monster.name} 화상 스택 +{synergy.fire_stack_amount} (총 {m_fire_stacks})")
                if synergy.ice_proc_chance and not m_iced and random.random() < synergy.ice_proc_chance:
                    m_iced = True
                    log.append(f"[{t:.2f}초] {monster.name} 빙결 부여")
                if synergy.lifesteal_chance and random.random() < synergy.lifesteal_chance:
                    heal = int(dealt * synergy.lifesteal_ratio)
                    p_hp = min(p_stats.hp, p_hp + heal)
                    log.append(f"[{t:.2f}초] 흡혈 {heal}")
                if synergy.shield_regen_chance and random.random() < synergy.shield_regen_chance:
                    regen = int(dealt * synergy.shield_regen_ratio)
                    p_shield += regen
                    log.append(f"[{t:.2f}초] 보호막 재생 +{regen} (총 {p_shield})")
                if synergy.lightning_proc_chance and random.random() < synergy.lightning_proc_chance:
                    burst = synergy.lightning_burst_flat
                    m_hp -= burst
                    log.append(f"[{t:.2f}초] {monster.name} 감전 피해 {burst} (방어 무시)")
                    if synergy.lightning_chain_chance and random.random() < synergy.lightning_chain_chance:
                        m_hp -= burst
                        log.append(f"[{t:.2f}초] 번개 연쇄! 추가 감전 피해 {burst}")
                if synergy.bleed_proc_chance and random.random() < synergy.bleed_proc_chance:
                    m_bleed_stacks += 1
                    log.append(f"[{t:.2f}초] {monster.name} 출혈 스택 +1 (총 {m_bleed_stacks})")

            if m_hp <= 0:
                log.append(f"[{t:.2f}초] {monster.name} 처치. {character.name} 승리!")
                return True, log, p_hp, max(0, -m_hp), p_shield

            p_next_time = t + p_interval

        else:
            # --- 몬스터 행동 시점 ---
            m_action_count += 1

            if m_poison_stacks > 0:
                tick = max(1, int(m_stats.hp * synergy.poison_tick_percent * m_poison_stacks))
                m_hp -= tick
                log.append(f"[{t:.2f}초] 중독 피해 {tick} ({m_poison_stacks}스택)")
                if m_hp <= 0:
                    log.append(f"[{t:.2f}초] {monster.name} 중독으로 사망. {character.name} 승리!")
                    return True, log, p_hp, max(0, -m_hp), p_shield
            if m_fire_stacks > 0:
                tick = synergy.fire_tick_flat * m_fire_stacks
                m_hp -= tick
                log.append(f"[{t:.2f}초] 화상 피해 {tick} ({m_fire_stacks}스택)")
                if m_hp <= 0:
                    log.append(f"[{t:.2f}초] {monster.name} 화상으로 사망. {character.name} 승리!")
                    return True, log, p_hp, max(0, -m_hp), p_shield
            if m_bleed_stacks > 0:
                tick = synergy.bleed_tick_flat * m_bleed_stacks
                m_hp -= tick
                log.append(f"[{t:.2f}초] 출혈 피해 {tick} ({m_bleed_stacks}스택)")
                if synergy.bleed_decays:
                    m_bleed_stacks -= 1
                if m_hp <= 0:
                    log.append(f"[{t:.2f}초] {monster.name} 출혈로 사망. {character.name} 승리!")
                    return True, log, p_hp, max(0, -m_hp), p_shield

            if monster.gimmick == "healer" and m_action_count % GIMMICK_HEAL_INTERVAL == 0 and m_hp > 0:
                heal = int(m_stats.hp * monster.gimmick_value / 100)
                if heal:
                    m_hp = min(m_stats.hp, m_hp + heal)
                    log.append(f"[{t:.2f}초] [기믹] {monster.name} 자힐 +{heal}")

            if m_iced and random.random() < synergy.ice_fail_chance:
                log.append(f"[{t:.2f}초] {monster.name}은(는) 빙결로 행동 불가")
            else:
                if t >= m_skill_ready_at:
                    def_ = p_stats.def_phys if monster.skill.damage_type == "phys" else p_stats.def_magic
                    dmg, is_crit = _roll_damage(
                        m_stats.atk_phys, m_stats.atk_magic, monster.skill.damage_type, monster.skill.damage_multiplier,
                        def_, m_stats.crit_chance, m_stats.crit_damage,
                    )
                    m_skill_ready_at = t + monster.skill.cooldown
                    label = f"스킬 '{monster.skill.name}'"
                else:
                    def_ = p_stats.def_phys if monster.damage_type == "phys" else p_stats.def_magic
                    dmg, is_crit = _roll_damage(
                        m_stats.atk_phys, m_stats.atk_magic, monster.damage_type, 1.0,
                        def_, m_stats.crit_chance, m_stats.crit_damage,
                    )
                    label = "기본 공격"

                dmg = _reduce_incoming_damage(dmg, is_crit, trait_mods, t < revive_shield_until)
                if p_shield > 0:
                    absorbed = min(p_shield, dmg)
                    p_shield -= absorbed
                    dmg -= absorbed
                if first_hit_immune_available and dmg > 0:
                    dmg = 0
                    first_hit_immune_available = False
                    log.append(f"[{t:.2f}초] [유물] 불굴의 심장 발동 - 피해 무효화")
                p_hp -= dmg
                log.append(f"[{t:.2f}초] {monster.name} {label}! {dmg} 피해{' (크리티컬)' if is_crit else ''} (보호막 {p_shield} 남음)")

                if p_hp <= 0:
                    if not _try_revive():
                        log.append(f"[{t:.2f}초] {character.name} 사망. {monster.name} 승리!")
                        return False, log, 0, 0, 0

                if thorns_percent and dmg > 0:
                    reflect = max(0, int(dmg * thorns_percent))
                    if reflect:
                        m_hp -= reflect
                        log.append(f"[{t:.2f}초] [특성] 가시 오라 반사 {reflect}")
                        if m_hp <= 0:
                            log.append(f"[{t:.2f}초] {monster.name} 가시 반사로 사망. {character.name} 승리!")
                            return True, log, p_hp, max(0, -m_hp), p_shield

                if monster.gimmick == "inflict_status" and not status_inflicted and random.random() < GIMMICK_STATUS_CHANCE * (1 - trait_mods.gimmick_resist_percent):
                    status_inflicted = True
                    p_stats.atk_phys = int(p_stats.atk_phys * (1 - monster.gimmick_value / 100))
                    p_stats.atk_magic = int(p_stats.atk_magic * (1 - monster.gimmick_value / 100))
                    log.append(f"[{t:.2f}초] [기믹] {monster.name}이(가) 상태이상을 걸었다! 공격력 -{monster.gimmick_value}%")

            m_next_time = t + m_interval


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
    """플레이어 캐릭터 vs 몬스터 여럿(1:2~1:3) 자동전투 - 실시간(초) 기반, 전원이 각자 공격속도로 독립 행동.

    simulate_battle과 동일하게 각 주체(플레이어 + 몬스터마다 개별)가 1/atk_speed초 간격으로 스스로
    행동하는 이벤트 큐 구조다. 몬스터별로 스킬 쿨다운/공속/행동 횟수를 독립적으로 관리한다.
    플레이어는 항상 "맨 앞의 생존 몬스터"(shield_tank 기믹이 있으면 그쪽을 우선)만 공격 대상으로
    삼고, 시너지 프록(독/화염/출혈/번개 등)도 그 대상에게만 적용된다 — 대상이 죽으면 다음 생존
    몬스터로 자연히 넘어간다. 반환 형식은 simulate_battle과 동일하되, 오버킬은 이번 전투에서 죽은
    몬스터들의 합산치.

    "매턴" 계열 주기 효과의 처리 방식은 simulate_battle과 동일: 중독/화상/출혈처럼 몬스터를 갉아먹는
    효과는 그 몬스터 자신이 행동할 때, 생명의 고동처럼 플레이어를 회복시키는 효과는 플레이어가
    행동할 때 틱한다. 허브 특성(game.hub.TraitModifiers) 반영도 simulate_battle과 동일
    (부활/가시 오라/재생/보호막/방어감소/공격형 확률/관통/기믹저항).
    """
    log: list[str] = []
    tags = character.equipped_tags()
    trait_mods = character.trait_mods or TraitModifiers()

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
            "skill_ready_at": float(m.skill.cooldown),
            "interval": 1.0 / max(0.1, m_stats.atk_speed),
            "next_time": 0.0,
            "action_count": 0,
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
    p_shield = _ring_shield(character) + trait_mods.shield_on_start_flat + int(p_stats.hp * trait_mods.shield_on_start_percent)
    first_hit_immune_available = relic_mods.first_hit_immune or trait_mods.first_hit_immune
    thorns_percent = trait_mods.thorns_percent + relic_mods.thorns_percent
    revive_shield_until = -1.0
    relic_revive_used = False
    total_overkill = 0

    p_interval = 1.0 / max(0.1, p_stats.atk_speed)
    p_skill_ready_at = float(p_skill_cooldown)
    p_next_time = 0.0

    def _try_revive() -> bool:
        nonlocal p_hp, revive_shield_until, relic_revive_used
        if trait_mods.revive_charges > 0:
            trait_mods.revive_charges -= 1
            p_hp = max(1, int(p_stats.hp * trait_mods.revive_heal_percent))
            revive_shield_until = t + trait_mods.revive_shield_turns
            log.append(f"[{t:.2f}초] [특성] 불사조의 심장 발동! {character.name} 부활 (HP {p_hp})")
            return True
        if relic_mods.revive_charges > 0 and not relic_revive_used:
            relic_revive_used = True
            p_hp = max(1, int(p_stats.hp * relic_mods.revive_heal_percent))
            log.append(f"[{t:.2f}초] [유물] 불사의 부적 발동! {character.name} 부활 (HP {p_hp})")
            return True
        return False

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
        def_eff = int(def_ * (1 - trait_mods.armor_pen_percent))

        def _hit() -> tuple[int, bool]:
            nonlocal p_hp
            dmg, is_crit = _roll_damage(
                p_stats.atk_phys, p_stats.atk_magic, damage_type, multiplier,
                def_eff, p_stats.crit_chance, p_stats.crit_damage,
            )
            if target["shield"] > 0:
                absorbed = min(target["shield"], dmg)
                target["shield"] -= absorbed
                dmg -= absorbed
            target["hp"] -= dmg
            shield_note = f" (보호막 {target['shield']} 남음)" if target["monster"].gimmick == "glass_shield" else ""
            log.append(f"  - {target['monster'].name}에게 {dmg} 피해{' (크리티컬)' if is_crit else ''}{shield_note}")
            if target["monster"].gimmick == "reflect" and dmg > 0:
                reflected = max(0, int(dmg * target["monster"].gimmick_value / 100))
                if reflected:
                    p_hp -= reflected
                    log.append(f"  [기믹] {target['monster'].name}이(가) {reflected} 피해를 반사했다!")
            return dmg, is_crit

        total = 0
        for _ in range(count):
            dmg, is_crit = _hit()
            total += dmg
            if trait_mods.double_attack_chance and random.random() < trait_mods.double_attack_chance:
                log.append("  [특성] 쌍수 연격 발동!")
                extra_dmg, _ = _hit()
                total += extra_dmg
            if is_crit and trait_mods.crit_extra_attack_chance and random.random() < trait_mods.crit_extra_attack_chance:
                log.append("  [특성] 필멸의 검 발동!")
                extra_dmg, _ = _hit()
                total += extra_dmg
        return total

    while True:
        candidates = [("player", p_next_time)] + [(idx, s["next_time"]) for idx, s in enumerate(states) if s["alive"]]
        t = min(time for _, time in candidates)
        if t > MAX_TIME:
            log.append("[시간 초과] 무승부 처리 - 패배로 간주")
            return False, log, max(0, p_hp), 0, p_shield
        actor_key = next(key for key, time in candidates if time == t)

        if actor_key == "player":
            # --- 플레이어 행동 시점 ---
            if trait_mods.regen_percent_per_turn and p_hp > 0:
                heal = int(p_stats.hp * trait_mods.regen_percent_per_turn)
                before = p_hp
                p_hp = min(p_stats.hp, p_hp + heal)
                if p_hp > before:
                    log.append(f"[{t:.2f}초] [특성] 생명의 고동 회복 +{p_hp - before}")
            if trait_mods.shield_regen_flat_chance and random.random() < trait_mods.shield_regen_flat_chance:
                regen = int(p_stats.hp * SHIELD_REGEN_FLAT_PERCENT)
                p_shield += regen
                log.append(f"[{t:.2f}초] [특성] 마나의 잔재 발동 - 보호막 +{regen} (총 {p_shield})")

            if relic_mods.self_damage_percent_per_turn > 0:
                self_dmg = max(1, int(p_hp * relic_mods.self_damage_percent_per_turn))
                p_hp -= self_dmg
                log.append(f"[{t:.2f}초] [유물] 반동 피해 {self_dmg}")
                if p_hp <= 0:
                    if not _try_revive():
                        log.append(f"[{t:.2f}초] {character.name} 유물 반동으로 사망.")
                        return False, log, 0, 0, 0

            target = _pick_target(states)
            skill_sealed = relic_mods.skill_sealed or any(s["alive"] and s["monster"].gimmick == "skill_null" for s in states)

            if t >= p_skill_ready_at and not skill_sealed:
                def_ = target["stats"].def_phys if character.skill.damage_type == "phys" else target["stats"].def_magic
                log.append(f"[{t:.2f}초] {character.name}의 스킬 '{character.skill.name}'! (대상: {target['monster'].name})")
                dealt = deal_player_damage(target, character.skill.damage_type, character.skill.damage_multiplier, def_, character.skill.hits)
                p_skill_ready_at = t + p_skill_cooldown
            else:
                def_ = target["stats"].def_phys if character.damage_type == "phys" else target["stats"].def_magic
                log.append(f"[{t:.2f}초] {character.name} 기본 공격. (대상: {target['monster'].name})")
                dealt = deal_player_damage(target, character.damage_type, 1.0, def_, 1)

            if p_hp <= 0:
                if not _try_revive():
                    log.append(f"[{t:.2f}초] {character.name} 사망 (반사 피해).")
                    return False, log, 0, 0, 0

            if target["hp"] > 0:
                if synergy.poison_proc_chance and random.random() < synergy.poison_proc_chance:
                    target["poison"] += 1
                    log.append(f"[{t:.2f}초] {target['monster'].name} 중독 스택 +1 (총 {target['poison']})")
                if synergy.fire_proc_chance and random.random() < synergy.fire_proc_chance:
                    target["fire"] += synergy.fire_stack_amount
                    log.append(f"[{t:.2f}초] {target['monster'].name} 화상 스택 +{synergy.fire_stack_amount} (총 {target['fire']})")
                if synergy.ice_proc_chance and not target["iced"] and random.random() < synergy.ice_proc_chance:
                    target["iced"] = True
                    log.append(f"[{t:.2f}초] {target['monster'].name} 빙결 부여")
                if synergy.lifesteal_chance and random.random() < synergy.lifesteal_chance:
                    heal = int(dealt * synergy.lifesteal_ratio)
                    p_hp = min(p_stats.hp, p_hp + heal)
                    log.append(f"[{t:.2f}초] 흡혈 {heal}")
                if synergy.shield_regen_chance and random.random() < synergy.shield_regen_chance:
                    regen = int(dealt * synergy.shield_regen_ratio)
                    p_shield += regen
                    log.append(f"[{t:.2f}초] 보호막 재생 +{regen} (총 {p_shield})")
                if synergy.lightning_proc_chance and random.random() < synergy.lightning_proc_chance:
                    burst = synergy.lightning_burst_flat
                    target["hp"] -= burst
                    log.append(f"[{t:.2f}초] {target['monster'].name} 감전 피해 {burst} (방어 무시)")
                    if synergy.lightning_chain_chance and random.random() < synergy.lightning_chain_chance:
                        target["hp"] -= burst
                        log.append(f"[{t:.2f}초] 번개 연쇄! 추가 감전 피해 {burst}")
                if synergy.bleed_proc_chance and random.random() < synergy.bleed_proc_chance:
                    target["bleed"] += 1
                    log.append(f"[{t:.2f}초] {target['monster'].name} 출혈 스택 +1 (총 {target['bleed']})")

            if target["hp"] <= 0 and target["alive"]:
                target["alive"] = False
                total_overkill += max(0, -target["hp"])
                log.append(f"[{t:.2f}초] {target['monster'].name} 처치!")

            if not any(s["alive"] for s in states):
                log.append(f"[{t:.2f}초] 전원 처치! {character.name} 승리!")
                return True, log, p_hp, total_overkill, p_shield

            p_next_time = t + p_interval

        else:
            # --- 몬스터(actor_key번째) 행동 시점 ---
            s = states[actor_key]
            monster = s["monster"]
            m_stats = s["stats"]
            s["action_count"] += 1

            if s["alive"] and s["poison"] > 0:
                tick = max(1, int(m_stats.hp * synergy.poison_tick_percent * s["poison"]))
                s["hp"] -= tick
                log.append(f"[{t:.2f}초] {monster.name} 중독 피해 {tick} ({s['poison']}스택)")
                if s["hp"] <= 0:
                    s["alive"] = False
                    total_overkill += max(0, -s["hp"])
                    log.append(f"[{t:.2f}초] {monster.name} 중독으로 처치!")

            if s["alive"] and s["fire"] > 0:
                tick = synergy.fire_tick_flat * s["fire"]
                s["hp"] -= tick
                log.append(f"[{t:.2f}초] {monster.name} 화상 피해 {tick} ({s['fire']}스택)")
                if s["hp"] <= 0:
                    s["alive"] = False
                    total_overkill += max(0, -s["hp"])
                    log.append(f"[{t:.2f}초] {monster.name} 화상으로 처치!")

            if s["alive"] and s["bleed"] > 0:
                tick = synergy.bleed_tick_flat * s["bleed"]
                s["hp"] -= tick
                log.append(f"[{t:.2f}초] {monster.name} 출혈 피해 {tick} ({s['bleed']}스택)")
                if synergy.bleed_decays:
                    s["bleed"] -= 1
                if s["hp"] <= 0:
                    s["alive"] = False
                    total_overkill += max(0, -s["hp"])
                    log.append(f"[{t:.2f}초] {monster.name} 출혈로 처치!")

            if not any(st["alive"] for st in states):
                log.append(f"[{t:.2f}초] 전원 처치! {character.name} 승리!")
                return True, log, p_hp, total_overkill, p_shield

            if s["alive"] and monster.gimmick == "healer" and s["action_count"] % GIMMICK_HEAL_INTERVAL == 0 and s["hp"] > 0:
                heal = int(m_stats.hp * monster.gimmick_value / 100)
                if heal:
                    s["hp"] = min(m_stats.hp, s["hp"] + heal)
                    log.append(f"[{t:.2f}초] [기믹] {monster.name} 자힐 +{heal}")

            if s["alive"]:
                if s["iced"] and random.random() < synergy.ice_fail_chance:
                    log.append(f"[{t:.2f}초] {monster.name}은(는) 빙결로 행동 불가")
                else:
                    if t >= s["skill_ready_at"]:
                        def_ = p_stats.def_phys if monster.skill.damage_type == "phys" else p_stats.def_magic
                        dmg, is_crit = _roll_damage(
                            m_stats.atk_phys, m_stats.atk_magic, monster.skill.damage_type, monster.skill.damage_multiplier,
                            def_, m_stats.crit_chance, m_stats.crit_damage,
                        )
                        s["skill_ready_at"] = t + monster.skill.cooldown
                        label = f"스킬 '{monster.skill.name}'"
                    else:
                        def_ = p_stats.def_phys if monster.damage_type == "phys" else p_stats.def_magic
                        dmg, is_crit = _roll_damage(
                            m_stats.atk_phys, m_stats.atk_magic, monster.damage_type, 1.0,
                            def_, m_stats.crit_chance, m_stats.crit_damage,
                        )
                        label = "기본 공격"

                    dmg = _reduce_incoming_damage(dmg, is_crit, trait_mods, t < revive_shield_until)
                    if p_shield > 0:
                        absorbed = min(p_shield, dmg)
                        p_shield -= absorbed
                        dmg -= absorbed
                    if first_hit_immune_available and dmg > 0:
                        dmg = 0
                        first_hit_immune_available = False
                        log.append(f"[{t:.2f}초] [유물] 불굴의 심장 발동 - 피해 무효화")
                    p_hp -= dmg
                    log.append(f"[{t:.2f}초] {monster.name} {label}! {dmg} 피해{' (크리티컬)' if is_crit else ''} (보호막 {p_shield} 남음)")

                    if p_hp <= 0:
                        if not _try_revive():
                            log.append(f"[{t:.2f}초] {character.name} 사망. {monster.name} 승리!")
                            return False, log, 0, 0, 0

                    if thorns_percent and dmg > 0:
                        reflect = max(0, int(dmg * thorns_percent))
                        if reflect:
                            s["hp"] -= reflect
                            log.append(f"[{t:.2f}초] [특성] 가시 오라 반사 {reflect} ({monster.name})")
                            if s["hp"] <= 0 and s["alive"]:
                                s["alive"] = False
                                total_overkill += max(0, -s["hp"])
                                log.append(f"[{t:.2f}초] {monster.name} 가시 반사로 처치!")
                                if not any(st["alive"] for st in states):
                                    log.append(f"[{t:.2f}초] 전원 처치! {character.name} 승리!")
                                    return True, log, p_hp, total_overkill, p_shield

                    if s["alive"] and monster.gimmick == "inflict_status" and not s["status_inflicted"] and random.random() < GIMMICK_STATUS_CHANCE * (1 - trait_mods.gimmick_resist_percent):
                        s["status_inflicted"] = True
                        p_stats.atk_phys = int(p_stats.atk_phys * (1 - monster.gimmick_value / 100))
                        p_stats.atk_magic = int(p_stats.atk_magic * (1 - monster.gimmick_value / 100))
                        log.append(f"[{t:.2f}초] [기믹] {monster.name}이(가) 상태이상을 걸었다! 공격력 -{monster.gimmick_value}%")

            if s["alive"]:
                s["next_time"] = t + s["interval"]
