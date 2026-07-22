"""유물 효과를 전투 스탯/흐름에 반영.

유물 보너스는 해당 시너지를 실제로 보유하고 있는지와 무관하게 그대로 더해진다
(예: 독 시너지를 안 꼈어도 독 관련 유물은 자기 몫의 효과를 낸다) — 단순한 모델을
우선시한 설계 선택이며, "시너지를 갖춰야만 유물이 의미있다"는 쪽으로 바꾸고 싶으면
compute_relic_modifiers 호출부에서 게이팅을 추가하면 된다.
"""

from dataclasses import dataclass


@dataclass
class RelicModifiers:
    atk_phys_mult: float = 1.0
    atk_magic_mult: float = 1.0
    def_phys_mult: float = 1.0
    def_magic_mult: float = 1.0
    max_hp_flat: int = 0
    max_hp_mult: float = 1.0
    crit_chance_bonus: float = 0.0
    crit_damage_bonus: float = 0.0
    cooldown_reduction_bonus: int = 0
    poison_proc_bonus: float = 0.0
    fire_stack_bonus: int = 0
    lifesteal_chance_bonus: float = 0.0
    ice_fail_bonus: float = 0.0
    shield_regen_chance_bonus: float = 0.0
    first_hit_immune: bool = False
    self_damage_percent_per_turn: float = 0.0
    heal_on_start_percent: float = 0.0
    gold_per_win: int = 0
    gold_percent_bonus: float = 0.0
    atk_speed_bonus: float = 0.0
    synergy_boost_highest: int = 0
    skill_sealed: bool = False
    revive_charges: int = 0  # 전투당 1회 (특성의 revive_charges와 달리 런 전체가 아니라 매 전투 리셋)
    revive_heal_percent: float = 0.5
    thorns_percent: float = 0.0
    magic_to_phys_percent: float = 0.0
    phys_to_magic_percent: float = 0.0


def compute_relic_modifiers(character) -> RelicModifiers:
    mods = RelicModifiers()
    for relic in character.relics:
        effect = relic.effect

        # --- 일반 유물 (소소한 효과) ---
        if effect == "worn_wallet":
            mods.gold_per_win += 5
        elif effect == "travelers_charm":
            mods.heal_on_start_percent += 0.05
        elif effect == "dull_whetstone":
            mods.atk_phys_mult *= 1.05
        elif effect == "worn_staff":
            mods.atk_magic_mult *= 1.05

        # --- 시너지 보조형 ---
        elif effect == "poison_proc_boost":
            mods.poison_proc_bonus += 0.10
        elif effect == "fire_stack_boost":
            mods.fire_stack_bonus += 5
        elif effect == "berserker_lifesteal_boost":
            mods.lifesteal_chance_bonus += 0.10
        elif effect == "ice_fail_boost":
            mods.ice_fail_bonus += 0.10
        elif effect == "mana_shield_boost":
            mods.shield_regen_chance_bonus += 0.10

        # --- 강력형 (부작용 없음) ---
        elif effect == "first_hit_immune":
            mods.first_hit_immune = True
        elif effect == "max_hp_up":
            mods.max_hp_flat += 30

        # --- 하이리스크 강력형 (부작용 동반) ---
        elif effect == "demons_pact":
            mods.atk_phys_mult *= 1.25
            mods.atk_magic_mult *= 1.25
            mods.self_damage_percent_per_turn += 0.03
        elif effect == "berserk_plate":
            mods.atk_phys_mult *= 1.3
            mods.atk_magic_mult *= 1.3
            mods.def_phys_mult *= 0.8
            mods.def_magic_mult *= 0.8
        elif effect == "gamblers_dice":
            mods.crit_chance_bonus += 0.20
            mods.crit_damage_bonus -= 0.25
        elif effect == "black_brand":
            mods.cooldown_reduction_bonus += 1
            mods.max_hp_mult *= 0.85

        # --- 일반 유물 추가 ---
        elif effect == "sturdy_belt":
            mods.def_phys_mult *= 1.05
            mods.def_magic_mult *= 1.05
        elif effect == "lucky_charm":
            mods.crit_chance_bonus += 0.05

        # --- 시너지 무관 스탯 강화형 ---
        elif effect == "beast_claw":
            mods.atk_phys_mult *= 1.08
        elif effect == "sage_lens":
            mods.atk_magic_mult *= 1.08

        # --- 하이리스크 강력형 추가 ---
        elif effect == "blood_oath":
            mods.crit_damage_bonus += 0.4
            mods.max_hp_mult *= 0.8
        elif effect == "ring_of_salvation":
            mods.heal_on_start_percent += 0.20
            mods.self_damage_percent_per_turn += 0.01

        # --- 공속 유물 ---
        elif effect == "light_boots":
            mods.atk_speed_bonus += 0.10
        elif effect == "windwalker_amulet":
            mods.atk_speed_bonus += 0.25

        # --- 골드 유물 ---
        elif effect == "coin_pouch":
            mods.gold_percent_bonus += 0.10
        elif effect == "greed_scale":
            mods.gold_percent_bonus += 0.25
        elif effect == "golden_touch":
            mods.gold_percent_bonus += 0.50

        # --- 시너지 동적 강화 (장비 태그 변경 시 매 전투 시작마다 새로 계산됨) ---
        elif effect == "adaptive_signet":
            mods.synergy_boost_highest += 1

        # --- 방어형 ---
        elif effect == "thorn_plate":
            mods.thorns_percent += 0.08

        # --- 유니크: 빌드를 정의하는 강력 효과 ---
        elif effect == "silent_rune":
            mods.skill_sealed = True
            mods.atk_phys_mult *= 1.4
            mods.atk_magic_mult *= 1.4
        elif effect == "undying_charm":
            mods.revive_charges += 1
            mods.revive_heal_percent = max(mods.revive_heal_percent, 0.5)
        elif effect == "arcane_amplifier":
            mods.magic_to_phys_percent += 0.6
        elif effect == "arcane_engraving":
            mods.phys_to_magic_percent += 0.6
        elif effect == "tempest_heart":
            mods.atk_speed_bonus += 0.40
            mods.def_phys_mult *= 0.85
            mods.def_magic_mult *= 0.85

    return mods


def apply_relic_gold_bonus(mods: RelicModifiers, gold: int) -> int:
    """동전 주머니/탐욕의 저울/황금의 손 등 처치 골드 %증가 유물을 보상 골드에 반영."""
    return int(gold * (1 + mods.gold_percent_bonus))
