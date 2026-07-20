"""장비 태그 기반 시너지 계산 (5종 태그, 3/5/7 스택 임계값).

수치는 초기 설계값이며 밸런싱은 추후 조정 대상.
"""

from dataclasses import dataclass

TIERS = (7, 5, 3)  # 높은 임계값부터 확인
SYNERGY_TAGS = ["poison", "fire", "berserker", "ice", "mana"]
TAG_LABEL = {"poison": "독", "fire": "화염", "berserker": "버서커", "ice": "얼음", "mana": "마나"}


def _tier(count: int) -> int:
    for t in TIERS:
        if count >= t:
            return t
    return 0


@dataclass
class SynergyResult:
    # 독: 매턴 시작 시 스택당 최대HP 1% 피해, 공격 시 poison_proc_chance로 1스택 부여
    poison_proc_chance: float = 0.0
    poison_tick_percent: float = 0.01

    # 화염: 매턴 종료 시 스택당 고정 피해, 공격 시 fire_proc_chance로 fire_stack_amount만큼 부여
    fire_proc_chance: float = 0.0
    fire_stack_amount: int = 0
    fire_tick_flat: int = 2  # 스택당 고정 피해 (플레이스홀더, 밸런싱 대상)

    # 버서커: 물리공격력 배율, 공격 시 lifesteal_chance로 가한 피해의 50% 흡혈
    atk_phys_mult: float = 1.0
    lifesteal_chance: float = 0.0
    lifesteal_ratio: float = 0.5

    # 얼음: 공격 시 ice_proc_chance로 빙결 부여, 빙결 상태는 매턴 시작 시 ice_fail_chance로 행동 불가
    ice_proc_chance: float = 0.0
    ice_fail_chance: float = 0.15

    # 마나: 마법공격력 배율, 공격 시 shield_regen_chance로 링 보호막을 가한 피해의 50%만큼 재생
    atk_magic_mult: float = 1.0
    shield_regen_chance: float = 0.0
    shield_regen_ratio: float = 0.5


def compute_synergy(tags: list[str]) -> SynergyResult:
    result = SynergyResult()

    poison_tier = _tier(tags.count("poison"))
    if poison_tier == 7:
        result.poison_proc_chance = 1.0
    elif poison_tier == 5:
        result.poison_proc_chance = 0.7
    elif poison_tier == 3:
        result.poison_proc_chance = 0.5

    fire_tier = _tier(tags.count("fire"))
    if fire_tier == 7:
        result.fire_proc_chance, result.fire_stack_amount = 1.0, 15
    elif fire_tier == 5:
        result.fire_proc_chance, result.fire_stack_amount = 1.0, 10
    elif fire_tier == 3:
        result.fire_proc_chance, result.fire_stack_amount = 0.5, 10

    berserker_tier = _tier(tags.count("berserker"))
    if berserker_tier == 7:
        result.atk_phys_mult, result.lifesteal_chance = 1.5, 0.3
    elif berserker_tier == 5:
        result.atk_phys_mult, result.lifesteal_chance = 1.3, 0.15
    elif berserker_tier == 3:
        result.atk_phys_mult = 1.15

    ice_tier = _tier(tags.count("ice"))
    if ice_tier == 7:
        result.ice_proc_chance, result.ice_fail_chance = 0.5, 0.3
    elif ice_tier == 5:
        result.ice_proc_chance = 0.5
    elif ice_tier == 3:
        result.ice_proc_chance = 0.3

    mana_tier = _tier(tags.count("mana"))
    if mana_tier == 7:
        result.atk_magic_mult, result.shield_regen_chance = 1.5, 0.3
    elif mana_tier == 5:
        result.atk_magic_mult, result.shield_regen_chance = 1.3, 0.15
    elif mana_tier == 3:
        result.atk_magic_mult = 1.15

    return result


def describe_active_synergies(tags: list[str]) -> list[str]:
    """장착 태그 기준으로 현재 발동 중인(3티어 이상) 시너지를 사람이 읽을 설명으로 반환."""
    result = compute_synergy(tags)
    lines = []

    poison_t = _tier(tags.count("poison"))
    if poison_t:
        lines.append(
            f"[독 {poison_t}] 중독 부여 {result.poison_proc_chance * 100:.0f}%, "
            f"스택당 매턴 최대HP {result.poison_tick_percent * 100:.0f}% 피해"
        )

    fire_t = _tier(tags.count("fire"))
    if fire_t:
        lines.append(
            f"[화염 {fire_t}] 화상 부여 {result.fire_proc_chance * 100:.0f}% "
            f"({result.fire_stack_amount}스택, 스택당 {result.fire_tick_flat} 고정피해)"
        )

    berserker_t = _tier(tags.count("berserker"))
    if berserker_t:
        extra = f", 흡혈 {result.lifesteal_chance * 100:.0f}%" if result.lifesteal_chance else ""
        lines.append(f"[버서커 {berserker_t}] 물공 +{int((result.atk_phys_mult - 1) * 100)}%{extra}")

    ice_t = _tier(tags.count("ice"))
    if ice_t:
        lines.append(
            f"[얼음 {ice_t}] 빙결 부여 {result.ice_proc_chance * 100:.0f}%, "
            f"행동불가 확률 {result.ice_fail_chance * 100:.0f}%"
        )

    mana_t = _tier(tags.count("mana"))
    if mana_t:
        extra = f", 보호막 재생 {result.shield_regen_chance * 100:.0f}%" if result.shield_regen_chance else ""
        lines.append(f"[마나 {mana_t}] 마공 +{int((result.atk_magic_mult - 1) * 100)}%{extra}")

    return lines


def describe_synergy_progress(tags: list[str]) -> str:
    """발동 중인 시너지가 하나도 없을 때, 가장 많이 모은 태그의 다음 임계값(3) 진행도를 보여준다.
    (예: 독 태그 2개 장착 -> "2/3 독"). 장착한 태그가 아예 없으면 빈 문자열.
    """
    counts = {tag: tags.count(tag) for tag in SYNERGY_TAGS}
    best_tag = max(counts, key=lambda t: counts[t])
    best_count = counts[best_tag]
    if best_count == 0:
        return ""
    return f"{min(best_count, 3)}/3 {TAG_LABEL[best_tag]}"
