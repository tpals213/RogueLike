"""장(Act)별 노드맵 생성 (기획서 3장 + 이후 정의):

- 장당 24~28개 노드, 갈림길 형태로 유저가 다음 노드를 선택
- 노드 0 = 축복(고정, 항상 첫 노드), 마지막 노드 = 보스(고정)
- 상점 3개 / 우물 3개 / 엘리트 최대 6개, 나머지는 일반/이벤트로 채움
- 도입부(Phase A): 일반전투 레이어 3개(각 2~3노드, 전부 "normal" 타입 - 어느 쪽을 골라도
  일반전투)와 필러 레이어 2개(각 2~3노드, 그 중 1자리는 상점 또는 우물이 보장되고 나머지는
  이벤트)가 번갈아 배치된다. 갈림길 자체는 있지만 이 구간에는 elite 타입이 아예 섞이지 않으므로,
  "최소 일반전투 3회 이후에만 엘리트 등장" 조건이 어떤 경로를 타든 항상 보장된다.
- include_relic_room=True로 생성하면 도입부 직후에 유물방(무조건 통과) 레이어가 하나 추가된다.
  런 전체에서 유물방은 한 장(act)에서만 등장해야 하므로, 호출하는 쪽에서 3개 장 중 하나만
  True로 넘겨야 한다.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

NODE_TYPES = ["normal", "elite", "shop", "well", "event", "blessing", "boss", "relic_room"]

ACT_NODE_COUNT_RANGE = (24, 28)
SHOP_COUNT = 3
WELL_COUNT = 3
ELITE_MAX = 6
ELITE_MIN = 3

PHASE_A_FILLER_TYPES = ["shop", "well", "event"]


@dataclass
class Node:
    id: int
    layer: int
    node_type: str
    next_ids: list[int] = field(default_factory=list)


@dataclass
class ActMap:
    act: int
    nodes: dict[int, Node]
    layers: list[list[int]]  # 레이어별 노드 id (layers[0] = [start_id], layers[-1] = [boss_id])
    start_id: int
    boss_id: int


def _build_middle_type_pool(middle_count: int, shop_count: int, well_count: int, rng: random.Random) -> list[str]:
    max_elite = min(ELITE_MAX, middle_count - shop_count - well_count)
    max_elite = max(ELITE_MIN, max_elite)
    elite_count = rng.randint(ELITE_MIN, max_elite)
    remaining = middle_count - shop_count - well_count - elite_count
    normal_count = round(remaining * 0.6)
    event_count = remaining - normal_count

    pool = ["shop"] * shop_count + ["well"] * well_count + ["elite"] * elite_count \
        + ["normal"] * normal_count + ["event"] * event_count
    rng.shuffle(pool)
    return pool


def _split_into_layers(pool: list[str], rng: random.Random) -> list[list[str]]:
    layers: list[list[str]] = []
    i = 0
    while i < len(pool):
        size = min(rng.randint(1, 3), len(pool) - i)
        layers.append(pool[i:i + size])
        i += size
    return layers


def _build_phase_a_layers(rng: random.Random) -> tuple[list[list[str]], int, int]:
    """도입부 5개 레이어(일반/필러/일반/필러/일반) 생성. 갈림길이 있되 elite는 절대 섞이지 않는다.

    반환: (레이어별 타입 리스트, 이 구간에서 소모한 상점 개수, 우물 개수)
    """
    filler_budget = rng.sample(PHASE_A_FILLER_TYPES, 2)  # 상점/우물/이벤트 중 2개(중복 없이)
    shop_used = filler_budget.count("shop")
    well_used = filler_budget.count("well")

    def normal_layer() -> list[str]:
        return ["normal"] * rng.randint(2, 3)

    def filler_layer(guaranteed_type: str) -> list[str]:
        size = rng.randint(2, 3)
        layer = [guaranteed_type] + ["event"] * (size - 1)
        rng.shuffle(layer)
        return layer

    layers = [
        normal_layer(),
        filler_layer(filler_budget[0]),
        normal_layer(),
        filler_layer(filler_budget[1]),
        normal_layer(),
    ]
    return layers, shop_used, well_used


def generate_act_map(act: int, rng: Optional[random.Random] = None, include_relic_room: bool = False) -> ActMap:
    rng = rng or random.Random()

    total_nodes = rng.randint(*ACT_NODE_COUNT_RANGE)

    phase_a_layers, shop_used, well_used = _build_phase_a_layers(rng)
    remaining_shop = SHOP_COUNT - shop_used
    # 보스 직전에 우물 1개를 무조건 배치하므로(아래 pre_boss_well_layer) 그만큼 일반 예산에서 미리 뺀다.
    remaining_well = max(0, WELL_COUNT - well_used - 1)

    relic_layer_types = ["relic_room"] if include_relic_room else []

    reserved = sum(len(layer) for layer in phase_a_layers) + len(relic_layer_types)
    middle_count = total_nodes - 2 - reserved  # 축복 + 보스 제외, Phase A/유물방 제외한 Phase B 몫
    min_needed = remaining_shop + remaining_well + ELITE_MIN
    if middle_count < min_needed:
        middle_count = min_needed  # 안전장치 - 총 노드 수가 살짝 늘어날 수 있음

    phase_b_pool = _build_middle_type_pool(middle_count, remaining_shop, remaining_well, rng)
    phase_b_layers = _split_into_layers(phase_b_pool, rng)

    # 보스 직전 레이어는 노드 1개짜리 "우물"로 고정 — 다음 레이어 노드가 1개면 이전 레이어의
    # 모든 노드가 그 하나로 연결되는 기존 간선 로직(아래) 덕분에, 어떤 경로를 타든 이 우물을
    # 반드시 거쳐야 보스방에 도달한다.
    pre_boss_well_layer = [["well"]]

    all_type_layers = (
        phase_a_layers + ([relic_layer_types] if relic_layer_types else []) + phase_b_layers + pre_boss_well_layer
    )

    nodes: dict[int, Node] = {}
    next_id = 0

    start_id = next_id
    nodes[start_id] = Node(id=start_id, layer=0, node_type="blessing")
    next_id += 1

    id_layers: list[list[int]] = [[start_id]]
    for layer_idx, type_layer in enumerate(all_type_layers, start=1):
        layer_ids = []
        for node_type in type_layer:
            nodes[next_id] = Node(id=next_id, layer=layer_idx, node_type=node_type)
            layer_ids.append(next_id)
            next_id += 1
        id_layers.append(layer_ids)

    boss_id = next_id
    nodes[boss_id] = Node(id=boss_id, layer=len(id_layers), node_type="boss")
    id_layers.append([boss_id])
    next_id += 1

    # 시작 -> 첫 레이어: 전부 연결 (첫 갈림길)
    for target in id_layers[1]:
        nodes[start_id].next_ids.append(target)

    # 레이어 간 연결 (각 노드가 다음 레이어의 1~2개 노드로 연결, 고립 노드 없도록 보정)
    # Phase A도 동일한 분기 로직을 그대로 타므로 도입부에도 자연스럽게 갈림길이 생긴다.
    for i in range(1, len(id_layers) - 1):
        current_layer = id_layers[i]
        next_layer = id_layers[i + 1]
        for node_id in current_layer:
            k = min(rng.randint(1, 2), len(next_layer))
            targets = rng.sample(next_layer, k)
            nodes[node_id].next_ids.extend(targets)

        incoming = {t for node_id in current_layer for t in nodes[node_id].next_ids}
        for orphan in next_layer:
            if orphan not in incoming:
                source = rng.choice(current_layer)
                nodes[source].next_ids.append(orphan)

    return ActMap(act=act, nodes=nodes, layers=id_layers, start_id=start_id, boss_id=boss_id)


_TYPE_LABEL = {
    "normal": "일반",
    "elite": "엘리트",
    "shop": "상점",
    "well": "우물",
    "event": "이벤트",
    "blessing": "축복",
    "boss": "보스",
    "relic_room": "유물방",
}


def render_map(act_map: ActMap) -> str:
    lines = [f"=== {act_map.act}장 맵 (총 {len(act_map.nodes)}개 노드) ==="]
    for layer_idx, layer_ids in enumerate(act_map.layers):
        parts = []
        for node_id in layer_ids:
            node = act_map.nodes[node_id]
            label = _TYPE_LABEL[node.node_type]
            parts.append(f"[{node_id}:{label}]")
        lines.append(f"L{layer_idx}: " + "  ".join(parts))
    return "\n".join(lines)
