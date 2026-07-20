"""프로토타입 스모크 테스트: 1장(숲/폐허)을 도적으로 플레이하며
골드/다이아/유물 자원 흐름과 시너지 발동을 콘솔에서 확인한다.
"""

from pathlib import Path

from game.combat import simulate_battle
from game.content import ACT1_MONSTERS, SAMPLE_ITEMS, make_rogue
from game.models import Relic
from game.save_system import load_meta, save_meta

SAVE_PATH = Path(__file__).parent / "saves" / "meta_save.json"

# 다이아 산정용 지표 가중치 (오버킬은 이번 스모크 테스트에서는 생략, 추후 반영)
DIAMOND_PER_NORMAL_KILL = 2
DIAMOND_PER_ELITE_KILL = 5
DIAMOND_PER_NODE_CLEARED = 1
GOLD_PER_NORMAL_KILL = 15
GOLD_PER_ELITE_KILL = 30


def main() -> None:
    character = make_rogue()
    # 독 시너지 3티어(3개) 발동을 확인하기 위한 샘플 빌드: 투구/왼손/오른손을 독 태그로 구성
    for item in SAMPLE_ITEMS:
        if item.name in ("독사냥꾼의 투구", "독날 단검", "맹독의 쌍검"):
            character.equip(item)

    gold = 0
    diamond_earned = 0
    nodes_cleared = 0

    run_sequence = [
        ("goblin", "일반"),
        ("poison_frog", "일반"),
        ("orc_warrior", "엘리트"),
        ("ruin_witch", "엘리트"),
        ("forest_guardian", "보스"),
    ]

    for monster_key, kind in run_sequence:
        monster = ACT1_MONSTERS[monster_key]()
        won, log, _ending_hp, _overkill, _ending_shield = simulate_battle(character, monster)  # 매 전투 풀피 시작 (전투 로직 자체를 검증하는 스모크 테스트)
        print("\n".join(log))
        print("-" * 40)

        if not won:
            print(f"{character.name} 사망. 런 종료.")
            break

        nodes_cleared += 1
        if kind == "일반":
            gold += GOLD_PER_NORMAL_KILL
            diamond_earned += DIAMOND_PER_NORMAL_KILL
        elif kind == "엘리트":
            gold += GOLD_PER_ELITE_KILL
            diamond_earned += DIAMOND_PER_ELITE_KILL
            relic = Relic(name=f"{monster.name}의 유물", description="엘리트 처치 보상 (효과 미구현, 플레이스홀더)", effect="placeholder")
            character.relics.append(relic)
            print(f"[유물 획득] {relic.name}")
        elif kind == "보스":
            diamond_earned += DIAMOND_PER_ELITE_KILL * 2
            print("1장 클리어!")

    diamond_earned += nodes_cleared * DIAMOND_PER_NODE_CLEARED

    print(f"\n런 종료 - 골드(런 한정, 소멸): {gold}")
    print(f"획득 유물: {[r.name for r in character.relics]}")

    meta = load_meta(SAVE_PATH)
    meta["total_diamond"] += diamond_earned
    save_meta(SAVE_PATH, meta)
    print(f"다이아 정산: +{diamond_earned} (누적 {meta['total_diamond']})")
    print(f"저장 위치: {SAVE_PATH}")


if __name__ == "__main__":
    main()
