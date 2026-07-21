"""Kivy 기반 모바일용 GUI (1차: 데스크톱에서 폰 화면 비율로 완주 가능하게).

tcod 버전(gui.py)과 달리 안드로이드 APK 빌드가 가능한 Kivy로 작성됐다.
game/ 패키지 로직은 한 줄도 수정하지 않고 그대로 재사용하고, 화면은 이미지 에셋 없이
색상 도형(사각형/버튼 배경색)만으로 구성한다 — 캐릭터/몬스터/아이템 이미지는 추후 별도 작업.

실행: (가상환경 활성화 후) python mobile_app.py
"""

import random
from pathlib import Path

from kivy.config import Config

Config.set("graphics", "width", "420")
Config.set("graphics", "height", "800")

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from game.combat import simulate_battle
from game.content import ACTS, RELIC_POOL, SAMPLE_ITEMS, STARTER_ITEM_NAMES, make_rogue
from game.hub import TRAIT_TREE, apply_unlocked_traits, get_trait, is_purchasable
from game.mapgen import generate_act_map
from game.models import EQUIPMENT_SLOTS
from game.relics import compute_relic_modifiers
from game.save_system import load_meta, save_meta
from game.shop import REROLL_COST, build_shop_entries, generate_shop_offer, refill_sold_entries
from game.synergy import SYNERGY_TAGS, TAG_LABEL, TIERS, describe_active_synergies

# ---------------------------------------------------------------------------
# 한글 폰트 — 번들 자산(assets/fonts/NotoSansKR-Regular.ttf, OFL 라이선스)을 우선 사용한다.
# 이 폰트는 APK에도 그대로 포함되므로 데스크톱/안드로이드 어느 쪽에서도 동일하게 렌더링된다.
# (macOS 시스템 폰트는 라이선스상 APK에 재배포할 수 없어 폴백으로만 남겨둔다.)
# ---------------------------------------------------------------------------
KOREAN_FONT_CANDIDATES = [
    str(Path(__file__).parent / "assets" / "fonts" / "NotoSansKR-Regular.ttf"),
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]
FONT_NAME = None
for _path in KOREAN_FONT_CANDIDATES:
    if Path(_path).exists():
        try:
            LabelBase.register(name="Korean", fn_regular=_path)
            FONT_NAME = "Korean"
            break
        except Exception:
            continue
if FONT_NAME is None:
    print("[경고] 한글 폰트를 찾지 못해 기본 폰트로 실행합니다 - 한글이 안 보일 수 있습니다.")


# ---------------------------------------------------------------------------
# 팔레트 (이미지 에셋 없이 색상 도형만 사용 — gui.py의 팔레트를 0-1 range로 재사용)
# ---------------------------------------------------------------------------
def _c(r, g, b, a=255):
    return (r / 255, g / 255, b / 255, a / 255)


BG_DARK = _c(18, 18, 22)
PANEL_BG = _c(38, 38, 46)
WHITE = _c(235, 235, 235)
DIM = _c(140, 140, 140)
GOLD = _c(255, 215, 60)
RED = _c(230, 90, 90)
GREEN = _c(110, 220, 110)
PRISM = _c(235, 120, 245)

TAG_COLOR = {
    "poison": _c(140, 220, 120),
    "fire": _c(255, 140, 80),
    "berserker": _c(255, 90, 90),
    "ice": _c(140, 200, 255),
    "mana": _c(190, 140, 255),
}
TIER_COLOR = {0: DIM, 3: GREEN, 5: GOLD, 7: PRISM}

# ---------------------------------------------------------------------------
# 라벨/상수 (play.py / gui.py와 동일한 값 — tcod 의존성 없이 이 파일에서 독립적으로 보유)
# ---------------------------------------------------------------------------
GOLD_BASE = {"normal": 15, "elite": 30}
DIAMOND_BASE = {"normal": 2, "elite": 5}
DIAMOND_PER_NODE = 1

TYPE_LABEL = {
    "normal": "일반", "elite": "엘리트", "shop": "상점", "well": "우물",
    "event": "이벤트", "blessing": "축복", "boss": "보스", "relic_room": "유물방",
}
SLOT_LABEL = {
    "helmet": "투구", "left_hand": "왼손", "right_hand": "오른손", "armor": "갑옷",
    "boots": "신발", "necklace": "목걸이", "ring": "반지",
}
STAT_LABEL = {
    "hp": "HP", "atk_phys": "물공", "atk_magic": "마공",
    "def_phys": "물방", "def_magic": "마방", "crit_chance": "크리율",
    "crit_damage": "크리뎀", "cooldown_reduction": "쿨감", "shield": "보호막",
}
_HUB_LINE_LABEL = {"hp": "체력", "atk_phys": "물리공격력", "atk_magic": "마법공격력"}

BLESSING_OPTIONS = [
    ("item", "무작위 아이템 획득 (빈 슬롯에 자동 장착)"),
    ("trivialize", "이후 3번의 전투, 적 HP 1로 시작"),
    ("relic", "무작위 유물 획득"),
    ("maxhp", "최대 HP +20"),
]


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


# ---------------------------------------------------------------------------
# 공용 위젯 생성 헬퍼
# ---------------------------------------------------------------------------
def mk_label(text, **kwargs):
    kwargs.setdefault("color", WHITE)
    kwargs.setdefault("font_name", FONT_NAME)
    kwargs.setdefault("font_size", 15)
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    return Label(text=text, **kwargs)


def mk_button(text, **kwargs):
    kwargs.setdefault("color", WHITE)
    kwargs.setdefault("font_name", FONT_NAME)
    kwargs.setdefault("font_size", 15)
    kwargs.setdefault("background_normal", "")
    kwargs.setdefault("background_down", "")
    kwargs.setdefault("background_color", PANEL_BG)
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    kwargs.setdefault("padding", (12, 8))
    return Button(text=text, **kwargs)


class HPBar(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.frac = 0.0
        with self.canvas:
            self._bg_color = Color(*PANEL_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            self._fg_color = Color(*GREEN)
            self._fg_rect = Rectangle(pos=self.pos, size=(0, 0))
        self.bind(pos=self._redraw, size=self._redraw)

    def set_frac(self, frac, color):
        self.frac = max(0.0, min(1.0, frac))
        self._fg_color.rgba = color
        self._redraw()

    def _redraw(self, *_args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._fg_rect.pos = self.pos
        self._fg_rect.size = (self.width * self.frac, self.height)


class StatusBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=96, padding=(12, 6), spacing=4, **kwargs)
        with self.canvas.before:
            Color(*BG_DARK)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        row1 = BoxLayout(size_hint_y=None, height=24)
        self.name_label = mk_label("", size_hint_x=0.65, font_size=14)
        self.res_label = mk_label("", size_hint_x=0.35, font_size=14, color=GOLD, halign="right")
        self.res_label.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        row1.add_widget(self.name_label)
        row1.add_widget(self.res_label)

        row2 = BoxLayout(size_hint_y=None, height=22, spacing=8)
        self.hp_bar = HPBar(size_hint_x=0.78)
        self.hp_text = mk_label("", size_hint_x=0.22, font_size=13)
        row2.add_widget(self.hp_bar)
        row2.add_widget(self.hp_text)

        self.message_label = mk_label("", size_hint_y=None, height=20, font_size=13, color=GOLD)

        self.add_widget(row1)
        self.add_widget(row2)
        self.add_widget(self.message_label)

    def _update_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def update(self, character, state):
        self.name_label.text = f"{character.name}  [{state['act']}장]"
        self.res_label.text = f"{state['gold']}G   다이아 {state['diamond']}"
        max_hp = character.base_stats.hp
        hp = max(0, state["hp"])
        frac = 0 if max_hp <= 0 else hp / max_hp
        color = GREEN if frac > 0.5 else (GOLD if frac > 0.2 else RED)
        self.hp_bar.set_frac(frac, color)
        self.hp_text.text = f"{hp}/{max_hp}"

    def show_menu_mode(self):
        self.name_label.text = "로그라이트 오토배틀러 (프로토타입)"
        self.res_label.text = ""
        self.hp_text.text = ""
        self.hp_bar.set_frac(0, DIM)

    def toast(self, text):
        self.message_label.text = text


class GameScreen(BoxLayout):
    def __init__(self, save_path: Path, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        with self.canvas.before:
            Color(*BG_DARK)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.save_path = save_path
        self.character = None
        self.state = None
        self.act_map = None
        self.current_id = None
        self.relic_room_act = None
        self.meta = None
        self._shop_entries = None

        self.status_bar = StatusBar()
        self.content_area = BoxLayout(orientation="vertical")
        self.bottom_bar = self._build_bottom_bar()

        self.add_widget(self.status_bar)
        self.add_widget(self.content_area)
        self.add_widget(self.bottom_bar)

        self.show_main_menu()

    def _update_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _build_bottom_bar(self):
        bar = BoxLayout(size_hint_y=None, height=64, spacing=4, padding=4)
        equip_btn = mk_button("장비 / 시너지", halign="center")
        equip_btn.bind(on_release=lambda *_a: self.open_equipment_popup())
        relic_btn = mk_button("보유 유물", halign="center")
        relic_btn.bind(on_release=lambda *_a: self.open_relics_popup())
        bar.add_widget(equip_btn)
        bar.add_widget(relic_btn)
        return bar

    # -- 공용 화면 유틸 ------------------------------------------------

    def set_content(self, widget):
        self.content_area.clear_widgets()
        self.content_area.add_widget(widget)

    def refresh_status(self):
        if self.character and self.state:
            self.status_bar.update(self.character, self.state)

    def _toast(self, text):
        self.status_bar.toast(text)

    def _build_choice_widget(self, title, options, on_choice, subtitle=None):
        content = BoxLayout(orientation="vertical", spacing=8, padding=12)
        content.add_widget(mk_label(title, size_hint_y=None, height=44, font_size=18, bold=True))

        scroll = ScrollView(size_hint=(1, 1))
        col = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None, padding=(0, 4))
        col.bind(minimum_height=col.setter("height"))

        if subtitle:
            sub = mk_label(subtitle, size_hint_y=None, valign="top")
            sub.bind(width=lambda inst, val, sub=sub: setattr(sub, "text_size", (val, None)))
            sub.bind(texture_size=lambda inst, val, sub=sub: setattr(sub, "height", val[1]))
            col.add_widget(sub)

        for idx, label in enumerate(options):
            btn = mk_button(label, size_hint_y=None, height=64)
            btn.bind(width=lambda inst, val, btn=btn: setattr(btn, "text_size", (val - 24, None)))
            btn.bind(texture_size=lambda inst, val, btn=btn: setattr(btn, "height", max(64, val[1] + 20)))
            btn.bind(on_release=lambda inst, i=idx: on_choice(i))
            col.add_widget(btn)

        scroll.add_widget(col)
        content.add_widget(scroll)
        return content

    def _show_battle_log(self, monster, log_lines, won, on_continue):
        result = "승리" if won else "패배"
        content = BoxLayout(orientation="vertical", spacing=8, padding=12)
        content.add_widget(mk_label(
            f"{self.character.name} vs {monster.name} - {result}",
            size_hint_y=None, height=36, font_size=17, bold=True,
            color=(GREEN if won else RED),
        ))

        scroll = ScrollView(size_hint=(1, 1))
        log_label = mk_label("\n".join(log_lines), size_hint_y=None, valign="top")
        log_label.bind(width=lambda inst, val: setattr(log_label, "text_size", (val, None)))
        log_label.bind(texture_size=lambda inst, val: setattr(log_label, "height", val[1]))
        scroll.add_widget(log_label)
        content.add_widget(scroll)

        btn = mk_button("계속", size_hint_y=None, height=64, halign="center")
        btn.bind(on_release=lambda *_a: on_continue())
        content.add_widget(btn)

        self.set_content(content)

    # -- 장비 / 시너지 / 유물 팝업 ---------------------------------------

    def _popup_scroll_column(self):
        col = BoxLayout(orientation="vertical", spacing=6, size_hint_y=None, padding=(0, 4))
        col.bind(minimum_height=col.setter("height"))
        return col

    def _add_wrapping_label(self, col, text, **kwargs):
        lbl = mk_label(text, size_hint_y=None, **kwargs)
        lbl.bind(width=lambda inst, val, lbl=lbl: setattr(lbl, "text_size", (val, None)))
        lbl.bind(texture_size=lambda inst, val, lbl=lbl: setattr(lbl, "height", val[1]))
        col.add_widget(lbl)

    def open_equipment_popup(self):
        if not self.character:
            self._toast("런을 시작한 뒤 확인할 수 있습니다.")
            return

        content = BoxLayout(orientation="vertical", spacing=10, padding=12)
        scroll = ScrollView()
        col = self._popup_scroll_column()

        self._add_wrapping_label(col, "[장비]", bold=True, color=GOLD)
        for slot in EQUIPMENT_SLOTS:
            item = self.character.equipment.get(slot)
            if item is None:
                self._add_wrapping_label(col, f"{SLOT_LABEL[slot]}: (비어있음)", color=DIM)
            else:
                grade = "희귀" if item.rarity == "rare" else "일반"
                self._add_wrapping_label(
                    col, f"{SLOT_LABEL[slot]}: {item.name} ({grade}) [{format_tags(item.tags)}]"
                )

        self._add_wrapping_label(col, "\n[시너지 (5종 전체)]", bold=True, color=GOLD)
        tags_all = self.character.equipped_tags()
        active_lines = describe_active_synergies(tags_all)
        for tag in SYNERGY_TAGS:
            label = TAG_LABEL[tag]
            count = tags_all.count(tag)
            tier = 0
            for t in TIERS:
                if count >= t:
                    tier = t
                    break
            if tier:
                line = next((l for l in active_lines if l.startswith(f"[{label} ")), f"[{label} {tier}] 발동")
                color = TIER_COLOR[tier]
            else:
                line = f"[{label} {count}/3] 미발동"
                color = DIM
            self._add_wrapping_label(col, line, color=color)

        scroll.add_widget(col)
        content.add_widget(scroll)

        popup = Popup(title="장비 / 시너지", content=content, size_hint=(0.92, 0.85))
        close_btn = mk_button("닫기", size_hint_y=None, height=56, halign="center")
        close_btn.bind(on_release=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()

    def open_relics_popup(self):
        if not self.character:
            self._toast("런을 시작한 뒤 확인할 수 있습니다.")
            return

        content = BoxLayout(orientation="vertical", spacing=10, padding=12)
        scroll = ScrollView()
        col = self._popup_scroll_column()

        relics = self.character.relics
        if not relics:
            self._add_wrapping_label(col, "보유한 유물이 없습니다.", color=DIM)
        for relic in relics:
            self._add_wrapping_label(col, f"{relic.name} - {relic.description}", color=GOLD)

        scroll.add_widget(col)
        content.add_widget(scroll)

        popup = Popup(title=f"보유 유물 ({len(relics)}개)", content=content, size_hint=(0.92, 0.85))
        close_btn = mk_button("닫기", size_hint_y=None, height=56, halign="center")
        close_btn.bind(on_release=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()

    # -- 메인 메뉴 / 허브 ------------------------------------------------

    def show_main_menu(self):
        self.character = None
        self.state = None
        self.status_bar.show_menu_mode()

        meta = load_meta(self.save_path)
        labels = ["런 시작", f"허브 (보유 다이아 {meta['total_diamond']})"]

        def on_choice(idx):
            if idx == 0:
                self.start_new_run()
            else:
                self.show_hub()

        self.set_content(self._build_choice_widget("로그라이트 오토배틀러", labels, on_choice))

    def show_hub(self):
        meta = load_meta(self.save_path)

        def render():
            owned = set(meta["unlocked_traits"])
            lines = [f"보유 다이아: {meta['total_diamond']}", ""]
            options = []
            option_ids = []
            for line_key, ranks in TRAIT_TREE.items():
                lines.append(f"[{_HUB_LINE_LABEL[line_key]}]")
                for rank in ranks:
                    if rank.id in owned:
                        status = "보유"
                    elif is_purchasable(rank, owned):
                        status = "구매 가능"
                    else:
                        status = "잠김 (이전 단계 필요)"
                    lines.append(f"  {rank.name} (+{rank.amount} {rank.stat}) - {rank.cost} 다이아 [{status}]")
                    if status == "구매 가능":
                        options.append(f"{rank.name} 구매 ({rank.cost} 다이아)")
                        option_ids.append(rank.id)
            options.append("메인 메뉴로")

            def on_choice(idx):
                if idx == len(options) - 1:
                    save_meta(self.save_path, meta)
                    self.show_main_menu()
                    return
                trait = get_trait(option_ids[idx])
                if trait.cost > meta["total_diamond"]:
                    self._toast("다이아가 부족합니다.")
                else:
                    meta["total_diamond"] -= trait.cost
                    meta["unlocked_traits"] = sorted(set(meta["unlocked_traits"]) | {trait.id})
                    save_meta(self.save_path, meta)
                    self._toast(f"구매 완료: {trait.name}")
                render()

            self.set_content(
                self._build_choice_widget("허브 (특성 상점)", options, on_choice, subtitle="\n".join(lines))
            )

        render()

    # -- 런 진행 ---------------------------------------------------------

    def start_new_run(self):
        self.meta = load_meta(self.save_path)
        self.character = make_rogue()
        apply_unlocked_traits(self.character, self.meta["unlocked_traits"])
        for item in SAMPLE_ITEMS:
            if item.name in STARTER_ITEM_NAMES:
                self.character.equip(item)

        self.state = {
            "hp": self.character.base_stats.hp,
            "shield": 0,
            "gold": 0,
            "diamond": 0,
            "trivialize": 0,
            "alive": True,
            "act_cleared": False,
            "nodes_cleared": 0,
            "act": 1,
        }
        self.relic_room_act = random.choice([1, 2, 3])
        self.start_act(1)

    def start_act(self, act_num):
        self.state["act"] = act_num
        self.state["act_cleared"] = False
        self.act_map = generate_act_map(act_num, include_relic_room=(act_num == self.relic_room_act))
        self.current_id = self.act_map.start_id
        self.refresh_status()
        self.resolve_node(self.act_map.nodes[self.current_id])

    def resolve_node(self, node):
        if node.node_type == "blessing":
            self.resolve_blessing()
        elif node.node_type == "well":
            self.resolve_well()
        elif node.node_type == "shop":
            self.resolve_shop()
        elif node.node_type == "event":
            self.resolve_event()
        elif node.node_type == "relic_room":
            self.resolve_relic_room()
        elif node.node_type in ("normal", "elite", "boss"):
            self._resolve_combat(node.node_type, self._after_node)

    def _after_node(self):
        self.refresh_status()
        if not self.state["alive"]:
            self.finish_run(cleared=False)
            return
        if self.state["act_cleared"]:
            if self.state["act"] == 3:
                self.finish_run(cleared=True)
            else:
                self.start_act(self.state["act"] + 1)
            return
        self.show_map_choice()

    def show_map_choice(self):
        node = self.act_map.nodes[self.current_id]
        options = node.next_ids
        if not options:
            self.finish_run(cleared=False)
            return
        labels = [TYPE_LABEL[self.act_map.nodes[nid].node_type] for nid in options]

        def on_choice(idx):
            self.current_id = options[idx]
            self.resolve_node(self.act_map.nodes[self.current_id])

        self.set_content(
            self._build_choice_widget(f"{self.state['act']}장 - 다음 노드를 선택하세요", labels, on_choice)
        )

    def finish_run(self, cleared):
        diamond_total = self.state["diamond"] + self.state["nodes_cleared"] * DIAMOND_PER_NODE
        self.meta["total_diamond"] += diamond_total
        save_meta(self.save_path, self.meta)

        if cleared:
            title = "런 클리어!"
            result_line = "3장 보스까지 전부 격파했습니다."
        elif not self.state["alive"]:
            title = "런 종료"
            result_line = f"{self.state['act']}장에서 사망했습니다."
        else:
            title = "런 종료"
            result_line = "더 이상 이동할 노드가 없습니다."

        relic_names = ", ".join(r.name for r in self.character.relics) or "없음"
        body = (
            f"{result_line}\n\n"
            f"획득 유물: {relic_names}\n"
            f"다이아 정산: +{diamond_total} (누적 {self.meta['total_diamond']})"
        )

        def on_choice(_idx):
            self.show_main_menu()

        self.set_content(self._build_choice_widget(title, ["메인 메뉴로"], on_choice, subtitle=body))

    # -- 노드 타입별 처리 --------------------------------------------------

    def resolve_blessing(self):
        labels = [desc for _, desc in BLESSING_OPTIONS]

        def on_choice(idx):
            effect = BLESSING_OPTIONS[idx][0]
            if effect == "item":
                empty_slots = [s for s in EQUIPMENT_SLOTS if s not in self.character.equipment]
                candidates = [i for i in SAMPLE_ITEMS if i.slot in empty_slots]
                if candidates:
                    item = random.choice(candidates)
                    self.character.equip(item)
                    self._toast(f"[축복] 랜덤 아이템 획득 및 즉시 장착: {item.name}")
                else:
                    self._toast("[축복] 빈 슬롯이 없어 효과가 발동하지 않았습니다.")
            elif effect == "trivialize":
                self.state["trivialize"] = 3
                self._toast("[축복] 이후 3번의 전투는 적 HP가 1로 시작합니다.")
            elif effect == "relic":
                relic = random.choice(RELIC_POOL)
                self.character.relics.append(relic)
                self._toast(f"[축복] 유물 획득: {relic.name}")
            elif effect == "maxhp":
                self.character.base_stats.hp += 20
                self.state["hp"] += 20
                self._toast("[축복] 최대 HP +20")
            self._after_node()

        self.set_content(self._build_choice_widget("축복 - 하나를 선택하세요", labels, on_choice))

    def resolve_well(self):
        common_items = [item for item in self.character.equipment.values() if item.rarity == "common"]
        labels = ["HP 40% 회복"]
        if common_items:
            labels.append("장비 하나 업그레이드 (일반 -> 희귀)")

        def on_choice(idx):
            if idx == 0:
                heal = int(self.character.base_stats.hp * 0.4)
                self.state["hp"] = min(self.character.base_stats.hp, self.state["hp"] + heal)
                self._toast(f"[우물] HP {heal} 회복")
            else:
                item = random.choice(common_items)
                item.rarity = "rare"
                available_tags = [t for t in SYNERGY_TAGS if t not in item.tags]
                if available_tags:
                    item.tags.append(random.choice(available_tags))
                self._toast(f"[우물] {item.name} 희귀 등급으로 업그레이드!")
            self._after_node()

        self.set_content(self._build_choice_widget("우물 - 하나를 선택하세요", labels, on_choice))

    def resolve_relic_room(self):
        relic = random.choice(RELIC_POOL)
        self.character.relics.append(relic)
        self._toast(f"[유물방] {relic.name} 획득 - {relic.description}")
        self._after_node()

    def resolve_event(self):
        def curse_altar(done):
            loss = int(self.state["hp"] * 0.15)
            self.state["hp"] = max(1, self.state["hp"] - loss)
            relic = random.choice(RELIC_POOL)
            self.character.relics.append(relic)
            self._toast(f"[저주받은 제단] HP {loss} 소모, 유물 획득: {relic.name}")
            done()

        def treasure_chest(done):
            if random.random() < 0.5:
                self.state["gold"] += 20
                self._toast("[버려진 보물상자] 골드 +20")
            else:
                loss = int(self.state["hp"] * 0.1)
                self.state["hp"] = max(1, self.state["hp"] - loss)
                self._toast(f"[버려진 보물상자] 함정 발동! HP {loss} 소모")
            done()

        def mystic_spring(done):
            if random.random() < 0.5:
                self.character.base_stats.hp += 15
                self.state["hp"] += 15
                self._toast("[신비한 샘] 최대 HP +15")
            else:
                self.character.base_stats.hp = max(1, self.character.base_stats.hp - 10)
                self.state["hp"] = min(self.state["hp"], self.character.base_stats.hp)
                self._toast("[신비한 샘] 실패, 최대 HP -10")
            done()

        def short_rest(done):
            if random.random() < 0.5:
                self.state["gold"] += 15
                self._toast("[짧은 휴식] 골드 +15")
            else:
                heal = int(self.character.base_stats.hp * 0.2)
                self.state["hp"] = min(self.character.base_stats.hp, self.state["hp"] + heal)
                self._toast(f"[짧은 휴식] HP {heal} 회복")
            done()

        def ambush(done):
            self._toast("[매복] 적이 나타났다!")
            self._resolve_combat("normal", done)

        def challenge(done):
            self._toast("[도전장] 강한 상대가 도전을 걸어왔다!")
            self._resolve_combat("elite", done)

        def sealed_ward(done):
            self._toast("[봉인된 결계] 위험을 무릅쓰고 결계를 개방한다 (조기 보스 도전)!")

            def after():
                self.state["act_cleared"] = False
                done()

            self._resolve_combat("boss", after)

        events = [curse_altar, treasure_chest, mystic_spring, short_rest, ambush, challenge, sealed_ward]
        random.choice(events)(self._after_node)

    def resolve_shop(self):
        offer = generate_shop_offer(self.character)
        self._shop_entries = build_shop_entries(offer)
        self._render_shop()

    def _render_shop(self):
        self.refresh_status()
        entries = self._shop_entries
        labels = []
        for entry in entries:
            obj = entry["obj"]
            if entry["sold"]:
                labels.append(f"[품절] {obj.name}")
                continue
            if entry["kind"] == "item":
                rarity_kr = "희귀" if obj.rarity == "rare" else "일반"
                labels.append(
                    f"[{SLOT_LABEL[obj.slot]}/{rarity_kr}] {obj.name} - "
                    f"{format_stat_bonus(obj.stat_bonus)} [{format_tags(obj.tags)}] - {entry['price']}G"
                )
            else:
                labels.append(f"[유물] {obj.name} - {obj.description} - {entry['price']}G")
        labels.append(f"리롤 (품절 슬롯 새 아이템으로 채움) - {REROLL_COST}G")
        labels.append("나가기")

        def on_choice(idx):
            if idx == len(labels) - 1:
                self._after_node()
                return
            if idx == len(labels) - 2:
                if not any(e["sold"] for e in entries):
                    self._toast("[상점] 품절된 아이템이 없어 리롤할 필요가 없습니다.")
                elif self.state["gold"] < REROLL_COST:
                    self._toast("[상점] 골드가 부족합니다.")
                else:
                    self.state["gold"] -= REROLL_COST
                    refill_sold_entries(entries)
                    self._toast(f"[상점] 리롤 완료 (남은 골드 {self.state['gold']}G)")
                self._render_shop()
                return

            entry = entries[idx]
            if entry["sold"]:
                self._toast("[상점] 이미 품절된 아이템입니다.")
            elif entry["price"] > self.state["gold"]:
                self._toast("[상점] 골드가 부족합니다.")
            else:
                self.state["gold"] -= entry["price"]
                entry["sold"] = True
                if entry["kind"] == "item":
                    self.character.equip(entry["obj"])
                    self._toast(f"[상점] 구매: {entry['obj'].name} 장착 완료")
                else:
                    self.character.relics.append(entry["obj"])
                    self._toast(f"[상점] 구매: {entry['obj'].name} 획득")
            self._render_shop()

        self.set_content(self._build_choice_widget(f"상점 (보유 {self.state['gold']}G)", labels, on_choice))

    # -- 전투 ------------------------------------------------------------

    def _resolve_combat(self, tier, on_done):
        act_content = ACTS[self.state["act"]]
        key = random.choice(act_content[tier])
        monster = act_content["monsters"][key]()

        if self.state["trivialize"] > 0:
            monster.stats.hp = 1
            self.state["trivialize"] -= 1
            self._toast(f"[축복 효과] {monster.name} HP 1로 시작 (남은 {self.state['trivialize']}회)")

        won, battle_log, ending_hp, overkill, ending_shield = simulate_battle(
            self.character, monster, starting_hp=self.state["hp"]
        )
        self.state["hp"] = ending_hp
        self.state["shield"] = ending_shield

        def after_continue():
            if not won:
                self.state["alive"] = False
                on_done()
                return

            self.state["nodes_cleared"] += 1
            act = self.state["act"]

            gold_bonus = compute_relic_modifiers(self.character).gold_per_win
            if gold_bonus:
                self.state["gold"] += gold_bonus
                self._toast(f"[유물] 승리 보너스 골드 +{gold_bonus}")

            def finish_rewards():
                if overkill:
                    bonus = overkill // 10
                    if bonus:
                        self.state["diamond"] += bonus
                on_done()

            if tier == "normal":
                self.state["gold"] += GOLD_BASE["normal"] * act
                self.state["diamond"] += DIAMOND_BASE["normal"] * act
                common_pool = [i for i in SAMPLE_ITEMS if i.rarity == "common"]
                self._choose_item_reward(common_pool, finish_rewards)
            elif tier == "elite":
                self.state["gold"] += GOLD_BASE["elite"] * act
                self.state["diamond"] += DIAMOND_BASE["elite"] * act
                rare_pool = [i for i in SAMPLE_ITEMS if i.rarity == "rare"]

                def after_item():
                    relic = random.choice(RELIC_POOL)
                    self.character.relics.append(relic)
                    self._toast(f"[유물 획득] {relic.name} - {relic.description}")
                    finish_rewards()

                self._choose_item_reward(rare_pool, after_item)
            elif tier == "boss":
                self.state["diamond"] += DIAMOND_BASE["elite"] * act * 2
                self.state["act_cleared"] = True
                self._toast(f"{act}장 보스 처치!")
                self._choose_boss_relic(finish_rewards)

        self._show_battle_log(monster, battle_log, won, after_continue)

    def _choose_item_reward(self, pool, on_done):
        choices = random.sample(pool, min(3, len(pool)))
        labels = [
            f"[{SLOT_LABEL[i.slot]}/{'희귀' if i.rarity == 'rare' else '일반'}] {i.name} - "
            f"{format_stat_bonus(i.stat_bonus)} [{format_tags(i.tags)}]"
            for i in choices
        ]
        labels.append("받지 않고 넘어가기")

        def on_choice(idx):
            if idx == len(labels) - 1:
                self._toast("아이템을 받지 않고 넘어갑니다.")
            else:
                picked = choices[idx]
                self.character.equip(picked)
                self._toast(f"[아이템 획득] {picked.name} 장착 완료")
            self.refresh_status()
            on_done()

        self.set_content(self._build_choice_widget("아이템 선택 - 하나를 고르세요", labels, on_choice))

    def _choose_boss_relic(self, on_done):
        choices = random.sample(RELIC_POOL, min(3, len(RELIC_POOL)))
        labels = [f"{r.name} - {r.description}" for r in choices]

        def on_choice(idx):
            picked = choices[idx]
            self.character.relics.append(picked)
            self._toast(f"[유물 획득] {picked.name}")
            on_done()

        self.set_content(self._build_choice_widget("보스 처치! 유물을 선택하세요", labels, on_choice))


class RogueliteApp(App):
    def build(self):
        self.title = "로그라이트 오토배틀러"
        save_path = Path(self.user_data_dir) / "saves" / "meta_save.json"
        return GameScreen(save_path)


if __name__ == "__main__":
    RogueliteApp().run()
