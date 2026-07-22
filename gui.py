"""tcod 기반 최소 GUI (1장 한정 프로토타입).

기존 game/ 패키지의 로직(맵 생성, 전투, 상점, 유물, 허브)을 그대로 재사용하고
입출력만 콘솔 print/input 대신 tcod 타일 창으로 대체한 버전.

실행: (가상환경 활성화 후) python gui.py
종료: ESC 또는 창 닫기
"""

import random
import sys
from pathlib import Path

import tcod
import tcod.event
import tcod.los
import tcod.tileset

from game.combat import simulate_battle
from game.content import ACTS, RELIC_POOL, SAMPLE_ITEMS, STARTER_ITEM_NAMES, make_rogue
from game.hub import apply_unlocked_traits
from game.mapgen import generate_act_map
from game.models import EQUIPMENT_SLOTS
from game.relics import compute_relic_modifiers
from game.save_system import load_meta, save_meta
from game.shop import REROLL_COST, build_shop_entries, generate_shop_offer, reroll_all_entries
from game.synergy import SYNERGY_TAGS, TAG_LABEL, TIERS, describe_active_synergies

SAVE_PATH = Path(__file__).parent / "saves" / "meta_save.json"

# tcod 기본 폰트(CP437)엔 한글 글리프가 없어서 macOS 시스템 한글 폰트를 직접 로드한다.
# 후보를 순서대로 시도하고, 전부 없으면 tcod 기본 폰트로 폴백(이 경우 한글은 안 보임).
KOREAN_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]
TILE_W, TILE_H = 14, 18

SCREEN_W, SCREEN_H = 100, 70

EQUIP_Y0, EQUIP_H = 2, 9
MAP_Y0, MAP_H = 12, 11
SYN_Y0, SYN_H = 24, 7
RELIC_Y0, RELIC_H = 32, 9
PROMPT_Y0, PROMPT_H = 42, 14
LOG_Y0, LOG_H = 57, 12

WHITE = (235, 235, 235)
DIM = (100, 100, 100)
GOLD = (255, 215, 60)
RED = (230, 70, 70)
GREEN = (110, 220, 110)
PRISM = (235, 120, 245)
LINE_DIM = (150, 150, 165)

# 시너지 태그별 고유 색상 (장비 태그 표시용)
TAG_COLOR = {
    "poison": (140, 220, 120),
    "fire": (255, 140, 80),
    "berserker": (255, 90, 90),
    "ice": (140, 200, 255),
    "mana": (190, 140, 255),
}
# 시너지 발동 티어별 색상 (오토체스 등급 색상 참고: 초록<금색<프리즘)
TIER_COLOR = {0: DIM, 3: GREEN, 5: GOLD, 7: PRISM}

TYPE_GLYPH = {
    "normal": ("n", (210, 210, 210)),
    "elite": ("E", (255, 110, 110)),
    "shop": ("$", (255, 215, 60)),
    "well": ("w", (110, 190, 255)),
    "event": ("?", (210, 140, 255)),
    "blessing": ("B", (255, 240, 140)),
    "boss": ("X", (255, 60, 60)),
    "relic_room": ("R", (180, 255, 180)),
}
TYPE_LABEL = {
    "normal": "일반", "elite": "엘리트", "shop": "상점", "well": "우물",
    "event": "이벤트", "blessing": "축복", "boss": "보스", "relic_room": "유물방",
}

SLOT_LABEL = {
    "helmet": "투구", "left_hand": "왼손", "right_hand": "오른손", "armor": "갑옷",
    "boots": "신발", "necklace": "목걸이", "ring": "반지",
}
RARITY_LABEL = {"common": "일반", "rare": "희귀", "unique": "유니크", "legendary": "레전더리"}
STAT_LABEL = {
    "hp": "HP", "atk_phys": "물공", "atk_magic": "마공",
    "def_phys": "물방", "def_magic": "마방", "crit_chance": "크리율",
    "crit_damage": "크리뎀", "cooldown_reduction": "쿨감", "shield": "보호막",
}


def format_stat_bonus(stat_bonus: dict) -> str:
    parts = []
    for key, value in stat_bonus.items():
        label = STAT_LABEL.get(key, key)
        if key == "crit_chance":
            parts.append(f"{label}+{value * 100:.0f}%")
        else:
            parts.append(f"{label}+{value}")
    return ", ".join(parts)


def format_tags(tags) -> str:
    return "/".join(TAG_LABEL.get(t, t) for t in tags)


class QuitGame(Exception):
    pass


def log(state, message):
    for line in str(message).split("\n"):
        state["log"].append(line)


def _load_tileset():
    for path in KOREAN_FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return tcod.tileset.load_truetype_font(path, TILE_W, TILE_H)
            except Exception:
                continue
    print("[경고] 한글 폰트를 찾지 못해 기본 폰트로 실행합니다 - 한글이 안 보일 수 있습니다.")
    return None


class Screen:
    def __init__(self):
        self.console = tcod.console.Console(SCREEN_W, SCREEN_H)
        tileset = _load_tileset()
        self.context = tcod.context.new(console=self.console, title="로그라이트 오토배틀러 (프로토타입)", tileset=tileset)

    def close(self):
        self.context.close()

    def draw_status(self, character, state):
        c = self.console
        max_hp = character.base_stats.hp
        hp = max(0, state["hp"])
        frac = 0 if max_hp <= 0 else hp / max_hp
        bar_w = 30
        filled = int(bar_w * frac)
        hp_color = GREEN if frac > 0.5 else (GOLD if frac > 0.2 else RED)

        c.print(2, 0, f"{character.name}  [{state['act']}장: {ACTS[state['act']]['theme']}]", fg=WHITE)
        c.print(2, 1, "HP [", fg=WHITE)
        c.print(6, 1, "#" * filled + "-" * (bar_w - filled), fg=hp_color)
        c.print(6 + bar_w, 1, f"] {hp}/{max_hp}", fg=WHITE)

        ring = character.equipment.get("ring")
        ring_shield = ring.stat_bonus.get("shield", 0) if ring else 0
        if ring_shield:
            c.print(6 + bar_w + 12, 1, f"방어막(반지) {ring_shield} (HP보다 먼저 차감)", fg=(120, 200, 255))

        c.print(50, 0, f"골드 {state['gold']}G   다이아 {state['diamond']}", fg=GOLD)

    def draw_equipment(self, character):
        c = self.console
        c.draw_frame(0, EQUIP_Y0, SCREEN_W, EQUIP_H, title="장비 (슬롯별 아이템의 시너지 태그)", fg=WHITE, bg=(0, 0, 0))
        y = EQUIP_Y0 + 1
        for slot in EQUIPMENT_SLOTS:
            item = character.equipment.get(slot)
            x = 2
            c.print(x, y, f"{SLOT_LABEL[slot]:<4}", fg=WHITE)
            x += 5
            if item is None:
                c.print(x, y, "(비어있음)", fg=DIM)
            else:
                grade = RARITY_LABEL.get(item.rarity, item.rarity)
                label = f"{item.name} ({grade})"
                c.print(x, y, f"{label:<22}", fg=GREEN if item.rarity != "common" else WHITE)
                x += 23
                for tag in item.tags:
                    pip = f"[{TAG_LABEL[tag]}]"
                    c.print(x, y, pip, fg=TAG_COLOR[tag])
                    x += len(pip) + 1
            y += 1

    def draw_synergy(self, character):
        c = self.console
        c.draw_frame(0, SYN_Y0, SCREEN_W, SYN_H, title="시너지 (5종 전체, 발동 여부 무관하게 표시)", fg=WHITE, bg=(0, 0, 0))
        tags = character.equipped_tags()
        active_lines = describe_active_synergies(tags)
        y = SYN_Y0 + 1
        for tag in SYNERGY_TAGS:
            label = TAG_LABEL[tag]
            count = tags.count(tag)
            tier = 0
            for t in TIERS:
                if count >= t:
                    tier = t
                    break

            if tier:
                line = next((l for l in active_lines if l.startswith(f"[{label} ")), f"[{label} {tier}] 발동")
            else:
                line = f"[{label} {count}/3] 미발동 (같은 태그 3개 이상 장착 시 발동)"

            color = TIER_COLOR[tier] if tier or count == 0 else WHITE
            c.print(2, y, line[: SCREEN_W - 4], fg=color)
            y += 1

    def draw_relics(self, character):
        c = self.console
        relics = character.relics
        title = f"보유 유물 ({len(relics)}개)" if relics else "보유 유물"
        c.draw_frame(0, RELIC_Y0, SCREEN_W, RELIC_H, title=title, fg=WHITE, bg=(0, 0, 0))
        if not relics:
            c.print(2, RELIC_Y0 + 1, "없음", fg=DIM)
            return

        inner_h = RELIC_H - 2
        col_w = (SCREEN_W - 6) // 2
        capacity = inner_h * 2
        overflow = len(relics) > capacity
        shown = relics[: capacity - 1] if overflow else relics

        for i, relic in enumerate(shown):
            col, row = divmod(i, inner_h)
            x = 2 + col * (col_w + 2)
            y = RELIC_Y0 + 1 + row
            c.print(x, y, f"{relic.name} - {relic.description}"[:col_w], fg=GOLD)

        if overflow:
            remaining = len(relics) - len(shown)
            col, row = divmod(len(shown), inner_h)
            x = 2 + col * (col_w + 2)
            y = RELIC_Y0 + 1 + row
            c.print(x, y, f"...외 {remaining}개 더 보유", fg=DIM)

    def draw_map(self, act_map, current_id):
        c = self.console
        c.draw_frame(0, MAP_Y0, SCREEN_W, MAP_H, title="맵", fg=WHITE, bg=(0, 0, 0))
        inner_x0, inner_y0 = 2, MAP_Y0 + 1
        inner_w, inner_h = SCREEN_W - 4, MAP_H - 3

        layers = act_map.layers
        n_layers = len(layers)
        spacing_x = inner_w / max(1, n_layers - 1) if n_layers > 1 else 0

        # 노드 중심 좌표 먼저 계산 (글리프는 3칸 폭이라 중심은 x+1)
        positions = {}
        for layer_idx, layer_ids in enumerate(layers):
            x = inner_x0 + int(layer_idx * spacing_x)
            n = len(layer_ids)
            for i, nid in enumerate(layer_ids):
                y = inner_y0 + inner_h // 2 + int((i - (n - 1) / 2) * 3)
                y = max(inner_y0, min(inner_y0 + inner_h - 1, y))
                positions[nid] = (x + 1, y)

        def draw_edges(color, only_from=None):
            for nid, (cx0, cy0) in positions.items():
                if only_from is not None and nid != only_from:
                    continue
                for target in act_map.nodes[nid].next_ids:
                    cx1, cy1 = positions[target]
                    line = tcod.los.bresenham((cx0, cy0), (cx1, cy1)).tolist()[1:-1]
                    for lx, ly in line:
                        if inner_x0 <= lx < inner_x0 + inner_w and inner_y0 <= ly < inner_y0 + inner_h:
                            c.print(lx, ly, "•", fg=color)

        # 1) 전체 경로를 흐리게, 2) 현재 위치에서 갈 수 있는 경로만 강조 (Slay the Spire 스타일)
        draw_edges(LINE_DIM)
        if current_id in positions:
            draw_edges(GOLD, only_from=current_id)

        # 3) 노드 글리프는 선 위에 덮어그려서 항상 보이게
        for nid, (cx, cy) in positions.items():
            node = act_map.nodes[nid]
            glyph, color = TYPE_GLYPH[node.node_type]
            if nid == current_id:
                c.print(cx - 1, cy, f"[{glyph}]", fg=(0, 0, 0), bg=WHITE)
            else:
                c.print(cx - 1, cy, f" {glyph} ", fg=color)

        legend = "  ".join(f"{g}={TYPE_LABEL[t]}" for t, (g, _) in TYPE_GLYPH.items())
        c.print(inner_x0, MAP_Y0 + MAP_H - 1, legend[: inner_w], fg=DIM)

    def draw_prompt(self, title, options):
        c = self.console
        c.draw_frame(0, PROMPT_Y0, SCREEN_W, PROMPT_H, title=title, fg=WHITE, bg=(0, 0, 0))
        x = 2
        y = PROMPT_Y0 + 1
        for idx, opt in enumerate(options, start=1):
            c.print(x, y, f"{idx}. {opt}"[: SCREEN_W - 4], fg=WHITE)
            y += 1
            if y >= PROMPT_Y0 + PROMPT_H - 2:
                break

    def draw_hint(self, text):
        self.console.print(2, PROMPT_Y0 + PROMPT_H - 2, text[: SCREEN_W - 4], fg=DIM)

    def draw_log(self, lines):
        c = self.console
        c.draw_frame(0, LOG_Y0, SCREEN_W, LOG_H, title="기록", fg=WHITE, bg=(0, 0, 0))
        inner_h = LOG_H - 2
        shown = lines[-inner_h:]
        for i, line in enumerate(shown):
            c.print(2, LOG_Y0 + 1 + i, line[: SCREEN_W - 4], fg=WHITE)

    def clear(self):
        self.console.clear()

    def present(self):
        self.context.present(self.console)


def pump_or_quit():
    for event in tcod.event.get():
        if isinstance(event, tcod.event.Quit):
            raise QuitGame


def wait_key():
    for event in tcod.event.wait():
        if isinstance(event, tcod.event.Quit):
            raise QuitGame
        if isinstance(event, tcod.event.KeyDown):
            return event.sym
    return None


def wait_continue(render_fn):
    while True:
        render_fn()
        sym = wait_key()
        if sym in (tcod.event.KeySym.SPACE, tcod.event.KeySym.RETURN):
            return


def prompt_choice(render_fn, count, allow_escape=False, extra_keys=None):
    extra_keys = extra_keys or {}
    while True:
        render_fn()
        sym = wait_key()
        if sym is None:
            continue
        if allow_escape and sym == tcod.event.KeySym.ESCAPE:
            return None
        if sym in extra_keys:
            return extra_keys[sym]
        if tcod.event.KeySym.N1 <= sym <= tcod.event.KeySym.N9:
            idx = sym - tcod.event.KeySym.N1
            if idx < count:
                return idx


def make_render_map(screen, character, state, act_map, current_id, options):
    def render():
        screen.clear()
        screen.draw_status(character, state)
        screen.draw_equipment(character)
        screen.draw_map(act_map, current_id)
        screen.draw_synergy(character)
        screen.draw_relics(character)
        if options:
            labels = [TYPE_LABEL[act_map.nodes[nid].node_type] for nid in options]
            screen.draw_prompt("다음 노드를 선택하세요 (숫자키)", labels)
        else:
            screen.draw_prompt("", [])
        screen.draw_log(state["log"])
        screen.present()

    return render


def make_render_simple(screen, character, state, title, options, hint=None):
    def render():
        screen.clear()
        screen.draw_status(character, state)
        screen.draw_equipment(character)
        screen.draw_synergy(character)
        screen.draw_relics(character)
        screen.draw_prompt(title, options)
        if hint:
            screen.draw_hint(hint)
        screen.draw_log(state["log"])
        screen.present()

    return render


def _prompt_item_reward(screen, character, state, pool):
    choices = random.sample(pool, min(3, len(pool)))
    labels = [
        f"[{SLOT_LABEL[i.slot]}/{RARITY_LABEL.get(i.rarity, i.rarity)}] {i.name} - "
        f"{format_stat_bonus(i.stat_bonus)} [{format_tags(i.tags)}]"
        for i in choices
    ]
    labels.append("받지 않고 넘어가기")
    render = make_render_simple(screen, character, state, "아이템 선택 (숫자키)", labels)
    idx = prompt_choice(render, len(labels))
    if idx == len(labels) - 1:
        return None
    return choices[idx]


def resolve_combat(screen, character, state, tier, act_map=None, current_id=None):
    act_content = ACTS[state["act"]]
    key = random.choice(act_content[tier])
    monster = act_content["monsters"][key]()

    if state["trivialize"] > 0:
        monster.stats.hp = 1
        state["trivialize"] -= 1
        log(state, f"[축복 효과] {monster.name} HP 1로 시작 (남은 {state['trivialize']}회)")

    won, battle_log, ending_hp, overkill, ending_shield = simulate_battle(character, monster, starting_hp=state["hp"])
    for line in battle_log:
        log(state, line)
    state["hp"] = ending_hp
    state["shield"] = ending_shield

    render = (
        make_render_map(screen, character, state, act_map, current_id, [])
        if act_map is not None
        else make_render_simple(screen, character, state, f"{TYPE_LABEL[tier]} 전투", [])
    )
    wait_continue(render)

    if not won:
        state["alive"] = False
        return

    state["nodes_cleared"] += 1
    act = state["act"]

    gold_bonus = compute_relic_modifiers(character).gold_per_win
    if gold_bonus:
        state["gold"] += gold_bonus
        log(state, f"[유물] 승리 보너스 골드 +{gold_bonus}")

    if tier == "normal":
        state["gold"] += 15 * act
        state["diamond"] += 2 * act
        common_pool = [i for i in SAMPLE_ITEMS if i.rarity == "common"]
        picked = _prompt_item_reward(screen, character, state, common_pool)
        if picked is None:
            log(state, "[아이템 선택] 아이템을 받지 않고 넘어갑니다.")
        else:
            character.equip(picked)
            log(state, f"[아이템 획득] {picked.name} 장착 완료")
    elif tier == "elite":
        state["gold"] += 30 * act
        state["diamond"] += 5 * act
        rare_pool = [i for i in SAMPLE_ITEMS if i.rarity == "rare"]
        picked = _prompt_item_reward(screen, character, state, rare_pool)
        if picked is None:
            log(state, "[아이템 선택] 아이템을 받지 않고 넘어갑니다.")
        else:
            character.equip(picked)
            log(state, f"[아이템 획득] {picked.name} 장착 완료")
        relic = random.choice(RELIC_POOL)
        character.relics.append(relic)
        log(state, f"[유물 획득] {relic.name} - {relic.description}")
    elif tier == "boss":
        state["diamond"] += 5 * act * 2
        state["act_cleared"] = True
        log(state, f"{act}장 보스 처치!")

        choices = random.sample(RELIC_POOL, min(3, len(RELIC_POOL)))
        labels = [f"{r.name} - {r.description}" for r in choices]
        render2 = make_render_simple(screen, character, state, "유물 선택 (숫자키)", labels)
        idx = prompt_choice(render2, len(choices))
        picked = choices[idx]
        character.relics.append(picked)
        log(state, f"[유물 획득] {picked.name}")

    if overkill:
        bonus = overkill // 10
        if bonus:
            state["diamond"] += bonus
            log(state, f"[오버킬] {overkill} 초과 피해 -> 다이아 +{bonus}")


BLESSING_OPTIONS = [
    ("item", "무작위 아이템 획득 (빈 슬롯에 자동 장착)"),
    ("trivialize", "이후 3번의 전투, 적 HP 1로 시작"),
    ("relic", "무작위 유물 획득"),
    ("maxhp", "최대 HP +20"),
]


def resolve_blessing(screen, character, state):
    labels = [desc for _, desc in BLESSING_OPTIONS]
    render = make_render_simple(screen, character, state, "축복 - 하나를 선택하세요", labels)
    idx = prompt_choice(render, len(labels))
    effect = BLESSING_OPTIONS[idx][0]

    if effect == "item":
        empty_slots = [s for s in EQUIPMENT_SLOTS if s not in character.equipment]
        candidates = [i for i in SAMPLE_ITEMS if i.slot in empty_slots]
        if candidates:
            item = random.choice(candidates)
            character.equip(item)
            log(state, f"[축복] 랜덤 아이템 획득 및 즉시 장착: {item.name}")
        else:
            log(state, "[축복] 빈 슬롯이 없어 효과가 발동하지 않았습니다.")
    elif effect == "trivialize":
        state["trivialize"] = 3
        log(state, "[축복] 이후 3번의 전투는 적 HP가 1로 시작합니다.")
    elif effect == "relic":
        relic = random.choice(RELIC_POOL)
        character.relics.append(relic)
        log(state, f"[축복] 유물 획득: {relic.name} - {relic.description}")
    elif effect == "maxhp":
        character.base_stats.hp += 20
        state["hp"] += 20
        log(state, f"[축복] 최대 HP +20 (현재 {state['hp']}/{character.base_stats.hp})")


def resolve_relic_room(screen, character, state):
    log(state, "[유물방] 무조건 유물을 획득합니다.")
    relic = random.choice(RELIC_POOL)
    character.relics.append(relic)
    log(state, f"[유물 획득] {relic.name} - {relic.description}")


def resolve_well(screen, character, state):
    common_items = [item for item in character.equipment.values() if item.rarity == "common"]
    labels = ["HP 40% 회복"]
    if common_items:
        labels.append("장비 하나 업그레이드 (일반 -> 희귀)")

    render = make_render_simple(screen, character, state, "우물 - 하나를 선택하세요", labels)
    idx = prompt_choice(render, len(labels))

    if idx == 0:
        heal = int(character.base_stats.hp * 0.4)
        state["hp"] = min(character.base_stats.hp, state["hp"] + heal)
        log(state, f"[우물] HP {heal} 회복 (현재 {state['hp']}/{character.base_stats.hp})")
    else:
        item = random.choice(common_items)
        item.rarity = "rare"
        available_tags = [t for t in SYNERGY_TAGS if t not in item.tags]
        if available_tags:
            item.tags.append(random.choice(available_tags))
        log(state, f"[우물] {item.name} 희귀 등급으로 업그레이드! (태그: {item.tags})")


def resolve_shop(screen, character, state):
    offer = generate_shop_offer(character, state["act"])
    entries = build_shop_entries(offer)

    while True:
        labels = []
        for entry in entries:
            obj = entry["obj"]
            price = entry["price"]
            if entry["sold"]:
                labels.append(f"[품절] {obj.name}")
                continue
            afford_tag = "" if price <= state["gold"] else " (골드 부족)"
            if entry["kind"] == "item":
                rarity_kr = RARITY_LABEL.get(obj.rarity, obj.rarity)
                effect = format_stat_bonus(obj.stat_bonus)
                tags_kr = format_tags(obj.tags)
                labels.append(
                    f"[{SLOT_LABEL[obj.slot]}/{rarity_kr}] {obj.name} - {effect} [{tags_kr}] - {price}G{afford_tag}"
                )
            else:
                labels.append(f"[유물] {obj.name} - {obj.description} - {price}G{afford_tag}")

        render = make_render_simple(
            screen,
            character,
            state,
            f"상점 (보유 {state['gold']}G)",
            labels,
            hint=f"숫자키=구매, R=리롤({REROLL_COST}G, 진열 전체 갱신), ESC=나가기",
        )
        idx = prompt_choice(
            render, len(labels), allow_escape=True, extra_keys={tcod.event.KeySym.r: "reroll"}
        )

        if idx is None:
            return

        if idx == "reroll":
            if state["gold"] < REROLL_COST:
                log(state, "[상점] 골드가 부족합니다.")
                continue
            state["gold"] -= REROLL_COST
            reroll_all_entries(entries, state["act"])
            log(state, f"[상점] 리롤 완료 (남은 골드 {state['gold']}G)")
            continue

        entry = entries[idx]
        if entry["sold"]:
            log(state, "[상점] 이미 품절된 아이템입니다.")
            continue
        if entry["price"] > state["gold"]:
            log(state, "[상점] 골드가 부족합니다.")
            continue

        state["gold"] -= entry["price"]
        entry["sold"] = True
        if entry["kind"] == "item":
            character.equip(entry["obj"])
            log(state, f"[상점] 구매: {entry['obj'].name} 장착 완료 (남은 골드 {state['gold']}G)")
        else:
            character.relics.append(entry["obj"])
            log(state, f"[상점] 구매: {entry['obj'].name} 획득 (남은 골드 {state['gold']}G)")


def resolve_event(screen, character, state, act_map, current_id):
    def curse_altar():
        loss = int(state["hp"] * 0.15)
        state["hp"] = max(1, state["hp"] - loss)
        log(state, f"[저주받은 제단] HP {loss} 소모")
        relic = random.choice(RELIC_POOL)
        character.relics.append(relic)
        log(state, f"[유물 획득] {relic.name} - {relic.description}")

    def treasure_chest():
        if random.random() < 0.5:
            state["gold"] += 20
            log(state, "[버려진 보물상자] 골드 +20")
        else:
            loss = int(state["hp"] * 0.1)
            state["hp"] = max(1, state["hp"] - loss)
            log(state, f"[버려진 보물상자] 함정 발동! HP {loss} 소모")

    def mystic_spring():
        if random.random() < 0.5:
            character.base_stats.hp += 15
            state["hp"] += 15
            log(state, f"[신비한 샘] 최대 HP +15 (현재 {state['hp']}/{character.base_stats.hp})")
        else:
            character.base_stats.hp = max(1, character.base_stats.hp - 10)
            state["hp"] = min(state["hp"], character.base_stats.hp)
            log(state, f"[신비한 샘] 실패, 최대 HP -10 (현재 {state['hp']}/{character.base_stats.hp})")

    def short_rest():
        if random.random() < 0.5:
            state["gold"] += 15
            log(state, "[짧은 휴식] 골드 +15")
        else:
            heal = int(character.base_stats.hp * 0.2)
            state["hp"] = min(character.base_stats.hp, state["hp"] + heal)
            log(state, f"[짧은 휴식] HP {heal} 회복")

    def ambush():
        log(state, "[매복] 적이 나타났다!")
        resolve_combat(screen, character, state, "normal", act_map, current_id)

    def challenge():
        log(state, "[도전장] 강한 상대가 도전을 걸어왔다!")
        resolve_combat(screen, character, state, "elite", act_map, current_id)

    def sealed_ward():
        log(state, "[봉인된 결계] 위험을 무릅쓰고 결계를 개방한다 (조기 보스 도전)!")
        resolve_combat(screen, character, state, "boss", act_map, current_id)
        state["act_cleared"] = False

    events = [curse_altar, treasure_chest, mystic_spring, short_rest, ambush, challenge, sealed_ward]
    random.choice(events)()


def resolve_node(screen, node, character, state, act_map):
    if node.node_type == "blessing":
        resolve_blessing(screen, character, state)
        render = make_render_map(screen, character, state, act_map, node.id, [])
        wait_continue(render)
    elif node.node_type == "well":
        resolve_well(screen, character, state)
        render = make_render_map(screen, character, state, act_map, node.id, [])
        wait_continue(render)
    elif node.node_type == "shop":
        resolve_shop(screen, character, state)
    elif node.node_type == "event":
        resolve_event(screen, character, state, act_map, node.id)
        render = make_render_map(screen, character, state, act_map, node.id, [])
        wait_continue(render)
    elif node.node_type == "relic_room":
        resolve_relic_room(screen, character, state)
        render = make_render_map(screen, character, state, act_map, node.id, [])
        wait_continue(render)
    elif node.node_type in ("normal", "elite", "boss"):
        resolve_combat(screen, character, state, node.node_type, act_map, node.id)


def choose_next(screen, character, state, act_map, current_id):
    node = act_map.nodes[current_id]
    options = node.next_ids
    if not options:
        return None
    render = make_render_map(screen, character, state, act_map, current_id, options)
    idx = prompt_choice(render, len(options))
    return options[idx]


def main():
    meta = load_meta(SAVE_PATH)
    character = make_rogue()
    apply_unlocked_traits(character, meta["unlocked_traits"])
    for item in SAMPLE_ITEMS:
        if item.name in STARTER_ITEM_NAMES:
            character.equip(item)

    state = {
        "hp": character.base_stats.hp,
        "shield": 0,
        "gold": 0,
        "diamond": 0,
        "trivialize": 0,
        "alive": True,
        "act_cleared": False,
        "nodes_cleared": 0,
        "act": 1,
        "log": [],
    }
    if meta["unlocked_traits"]:
        log(state, f"[허브 특성 적용] {meta['unlocked_traits']}")

    screen = Screen()
    final_act_cleared = False
    relic_room_act = random.choice([1, 2, 3])  # 유물방은 런 전체에서 이 장(act)에만 등장
    try:
        for act_num in (1, 2, 3):
            if not state["alive"]:
                break

            state["act"] = act_num
            state["act_cleared"] = False
            act_map = generate_act_map(act_num, include_relic_room=(act_num == relic_room_act))
            log(state, f"===== {act_num}장 진입 ({ACTS[act_num]['theme']}) =====")

            current_id = act_map.start_id
            resolve_node(screen, act_map.nodes[current_id], character, state, act_map)

            while state["alive"] and not state["act_cleared"]:
                next_id = choose_next(screen, character, state, act_map, current_id)
                if next_id is None:
                    break
                current_id = next_id
                resolve_node(screen, act_map.nodes[current_id], character, state, act_map)

            if not state["alive"] or not state["act_cleared"]:
                break
            if act_num == 3:
                final_act_cleared = True

        if final_act_cleared:
            log(state, "결과: 런 클리어! 3장 보스까지 전부 격파했습니다.")
        elif not state["alive"]:
            log(state, f"결과: {state['act']}장에서 사망. 런 종료.")

        diamond_total = state["diamond"] + state["nodes_cleared"] * 1
        meta["total_diamond"] += diamond_total
        save_meta(SAVE_PATH, meta)
        log(state, f"다이아 정산: +{diamond_total} (누적 {meta['total_diamond']})")

        render = make_render_simple(screen, character, state, "게임 종료", ["ESC로 종료"])
        while True:
            render()
            sym = wait_key()
            if sym == tcod.event.KeySym.ESCAPE:
                break
    except QuitGame:
        pass
    finally:
        screen.close()


if __name__ == "__main__":
    main()
