from __future__ import annotations

import heapq
import json
import math
import random
import time
import tkinter as tk

from dataclasses import dataclass
from dataclasses import field

from enum import Enum
from enum import auto

from pathlib import Path

from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple


APP_TITLE = "사람 쓰레기 수거 시뮬레이션"

MAP_WIDTH = 34
MAP_HEIGHT = 22

CELL_SIZE = 27

DEFAULT_AGENT_COUNT = 5
DEFAULT_TRASH_COUNT = 55
DEFAULT_OBSTACLE_COUNT = 75

DEFAULT_STATION_COUNT = 2
DEFAULT_REST_AREA_COUNT = 3

DEFAULT_MAX_TURNS = 1500
DEFAULT_TICK_DELAY = 100

DEFAULT_RANDOM_SEED = 20260619

MAX_TRASH_ON_MAP = 150

TRASH_SPAWN_INTERVAL = 7
TRASH_SPAWN_MIN_COUNT = 1
TRASH_SPAWN_MAX_COUNT = 4

AGENT_MAX_ENERGY = 100
AGENT_BAG_CAPACITY = 14

MOVE_ENERGY_COST = 1
PICKUP_ENERGY_COST = 2
RECYCLE_ENERGY_COST = 1

REST_RECOVERY_AMOUNT = 20
IDLE_RECOVERY_AMOUNT = 2

LOW_ENERGY_THRESHOLD = 24

BAG_RETURN_RATIO = 0.82

EVENT_LOG_LIMIT = 150

SAVE_FILE_NAME = "trash_pickup_save.json"


class TileType(Enum):
    EMPTY = auto()
    WALL = auto()
    WATER = auto()
    FLOWER = auto()
    STATION = auto()
    REST_AREA = auto()


class TrashKind(Enum):
    PLASTIC = (
        "플라스틱",
        10,
        1,
        "#42A5F5",
    )

    CAN = (
        "캔",
        12,
        1,
        "#B0BEC5",
    )

    GLASS = (
        "유리",
        16,
        2,
        "#66BB6A",
    )

    PAPER = (
        "종이",
        8,
        1,
        "#FFEE58",
    )

    FOOD = (
        "음식물",
        9,
        2,
        "#FFA726",
    )

    GENERAL = (
        "일반 쓰레기",
        6,
        1,
        "#AB47BC",
    )

    def __init__(
        self,
        display_name: str,
        score: int,
        weight: int,
        color: str,
    ) -> None:
        self.display_name = display_name
        self.score = score
        self.weight = weight
        self.color = color

    @classmethod
    def random_kind(
        cls,
    ) -> "TrashKind":
        kinds = list(cls)

        weights = [
            25,
            17,
            8,
            22,
            12,
            16,
        ]

        return random.choices(
            population=kinds,
            weights=weights,
            k=1,
        )[0]


class AgentState(Enum):
    SEARCHING = "쓰레기 탐색"

    MOVING_TO_TRASH = "쓰레기로 이동"

    PICKING_UP = "쓰레기 수거"

    MOVING_TO_STATION = "분리수거장으로 이동"

    RECYCLING = "분리배출"

    MOVING_TO_REST = "휴식 장소로 이동"

    RESTING = "휴식"

    WANDERING = "주변 이동"

    IDLE = "대기"


class WeatherType(Enum):
    CLEAR = (
        "맑음",
        1.0,
        1.0,
        "#E3F2FD",
    )

    CLOUDY = (
        "흐림",
        0.95,
        1.0,
        "#ECEFF1",
    )

    RAIN = (
        "비",
        0.80,
        1.25,
        "#CFD8DC",
    )

    WINDY = (
        "강풍",
        0.90,
        1.15,
        "#E0E0E0",
    )

    HOT = (
        "폭염",
        0.85,
        1.30,
        "#FFF3E0",
    )

    def __init__(
        self,
        display_name: str,
        vision_multiplier: float,
        energy_multiplier: float,
        background_color: str,
    ) -> None:
        self.display_name = display_name

        self.vision_multiplier = (
            vision_multiplier
        )

        self.energy_multiplier = (
            energy_multiplier
        )

        self.background_color = (
            background_color
        )


class TimePeriod(Enum):
    MORNING = (
        "아침",
        "#E3F2FD",
    )

    AFTERNOON = (
        "낮",
        "#F7FBFF",
    )

    EVENING = (
        "저녁",
        "#FFF3E0",
    )

    NIGHT = (
        "밤",
        "#CFD8DC",
    )

    def __init__(
        self,
        display_name: str,
        background_color: str,
    ) -> None:
        self.display_name = display_name
        self.background_color = background_color


class EventType(Enum):
    SYSTEM = "시스템"

    INFO = "정보"

    MOVE = "이동"

    TRASH_SPAWN = "쓰레기 생성"

    PICKUP = "수거"

    RECYCLE = "분리배출"

    REST = "휴식"

    WEATHER = "날씨"

    WARNING = "경고"


@dataclass(
    frozen=True,
)
class Position:
    x: int
    y: int

    def neighbors(
        self,
    ) -> List["Position"]:
        return [
            Position(
                self.x + 1,
                self.y,
            ),
            Position(
                self.x - 1,
                self.y,
            ),
            Position(
                self.x,
                self.y + 1,
            ),
            Position(
                self.x,
                self.y - 1,
            ),
        ]

    def manhattan_distance(
        self,
        other: "Position",
    ) -> int:
        return (
            abs(self.x - other.x)
            + abs(self.y - other.y)
        )

    def euclidean_distance(
        self,
        other: "Position",
    ) -> float:
        difference_x = (
            self.x - other.x
        )

        difference_y = (
            self.y - other.y
        )

        return math.sqrt(
            difference_x ** 2
            + difference_y ** 2
        )

    def moved(
        self,
        difference_x: int,
        difference_y: int,
    ) -> "Position":
        return Position(
            self.x + difference_x,
            self.y + difference_y,
        )

    def as_tuple(
        self,
    ) -> Tuple[int, int]:
        return (
            self.x,
            self.y,
        )


@dataclass
class SimulationEvent:
    turn: int

    event_type: EventType

    message: str

    def formatted(
        self,
    ) -> str:
        return (
            f"[{self.turn:04d}턴] "
            f"[{self.event_type.value}] "
            f"{self.message}"
        )


@dataclass
class SimulationConfig:
    width: int = MAP_WIDTH

    height: int = MAP_HEIGHT

    agent_count: int = (
        DEFAULT_AGENT_COUNT
    )

    initial_trash_count: int = (
        DEFAULT_TRASH_COUNT
    )

    obstacle_count: int = (
        DEFAULT_OBSTACLE_COUNT
    )

    station_count: int = (
        DEFAULT_STATION_COUNT
    )

    rest_area_count: int = (
        DEFAULT_REST_AREA_COUNT
    )

    max_turns: int = (
        DEFAULT_MAX_TURNS
    )

    tick_delay: int = (
        DEFAULT_TICK_DELAY
    )

    random_seed: int = (
        DEFAULT_RANDOM_SEED
    )

    def normalize(
        self,
    ) -> None:
        self.width = max(
            16,
            min(
                60,
                self.width,
            ),
        )

        self.height = max(
            12,
            min(
                40,
                self.height,
            ),
        )

        self.agent_count = max(
            1,
            min(
                12,
                self.agent_count,
            ),
        )

        self.initial_trash_count = max(
            1,
            min(
                250,
                self.initial_trash_count,
            ),
        )

        maximum_obstacle_count = (
            self.width
            * self.height
            // 3
        )

        self.obstacle_count = max(
            0,
            min(
                maximum_obstacle_count,
                self.obstacle_count,
            ),
        )

        self.station_count = max(
            1,
            min(
                6,
                self.station_count,
            ),
        )

        self.rest_area_count = max(
            1,
            min(
                6,
                self.rest_area_count,
            ),
        )

        self.max_turns = max(
            50,
            min(
                20000,
                self.max_turns,
            ),
        )

        self.tick_delay = max(
            20,
            min(
                2000,
                self.tick_delay,
            ),
        )


def clamp(
    value: int,
    minimum: int,
    maximum: int,
) -> int:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def safe_int(
    value: Any,
    default: int,
) -> int:
    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def format_percent(
    value: float,
) -> str:
    return (
        f"{value * 100:.1f}%"
    )


def create_progress_bar(
    current: int,
    maximum: int,
    length: int = 10,
) -> str:
    if maximum <= 0:
        return "□" * length

    ratio = (
        current
        / maximum
    )

    ratio = max(
        0.0,
        min(
            1.0,
            ratio,
        ),
    )

    filled_count = round(
        ratio * length
    )

    empty_count = (
        length
        - filled_count
    )

    return (
        "■" * filled_count
        + "□" * empty_count
    )


def choose_random_item(
    items: List[Any],
) -> Optional[Any]:
    if not items:
        return None

    return random.choice(
        items
    )


def calculate_average(
    values: Iterable[float],
) -> float:
    value_list = list(values)

    if not value_list:
        return 0.0

    return (
        sum(value_list)
        / len(value_list)
    )
@dataclass
class Trash:
    trash_id: int

    kind: TrashKind

    position: Position

    created_turn: int

    wet: bool = False

    damaged: bool = False

    reserved_by: Optional[int] = None

    @property
    def weight(
        self,
    ) -> int:
        return self.kind.weight

    @property
    def score(
        self,
    ) -> int:
        penalty = 0

        if self.wet:
            penalty += 1

        if self.damaged:
            penalty += 1

        return max(
            1,
            self.kind.score - penalty,
        )

    def age(
        self,
        current_turn: int,
    ) -> int:
        return max(
            0,
            current_turn - self.created_turn,
        )

    def condition_text(
        self,
    ) -> str:
        conditions: List[str] = []

        if self.wet:
            conditions.append(
                "젖음"
            )

        if self.damaged:
            conditions.append(
                "훼손"
            )

        if not conditions:
            return "정상"

        return ", ".join(
            conditions
        )

    def description(
        self,
    ) -> str:
        return (
            f"쓰레기 번호: {self.trash_id}\n"
            f"종류: {self.kind.display_name}\n"
            f"위치: ({self.position.x}, {self.position.y})\n"
            f"무게: {self.weight}\n"
            f"점수: {self.score}\n"
            f"상태: {self.condition_text()}"
        )

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "trash_id": self.trash_id,
            "kind": self.kind.name,
            "x": self.position.x,
            "y": self.position.y,
            "created_turn": self.created_turn,
            "wet": self.wet,
            "damaged": self.damaged,
            "reserved_by": self.reserved_by,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "Trash":
        kind_name = str(
            data.get(
                "kind",
                TrashKind.GENERAL.name,
            )
        )

        try:
            kind = TrashKind[
                kind_name
            ]

        except KeyError:
            kind = TrashKind.GENERAL

        return cls(
            trash_id=safe_int(
                data.get(
                    "trash_id",
                ),
                0,
            ),
            kind=kind,
            position=Position(
                safe_int(
                    data.get(
                        "x",
                    ),
                    0,
                ),
                safe_int(
                    data.get(
                        "y",
                    ),
                    0,
                ),
            ),
            created_turn=safe_int(
                data.get(
                    "created_turn",
                ),
                0,
            ),
            wet=bool(
                data.get(
                    "wet",
                    False,
                )
            ),
            damaged=bool(
                data.get(
                    "damaged",
                    False,
                )
            ),
            reserved_by=data.get(
                "reserved_by"
            ),
        )


@dataclass
class TrashBag:
    capacity: int = (
        AGENT_BAG_CAPACITY
    )

    items: List[Trash] = field(
        default_factory=list,
    )

    @property
    def total_weight(
        self,
    ) -> int:
        return sum(
            trash.weight
            for trash in self.items
        )

    @property
    def item_count(
        self,
    ) -> int:
        return len(
            self.items
        )

    @property
    def remaining_capacity(
        self,
    ) -> int:
        return max(
            0,
            self.capacity
            - self.total_weight,
        )

    @property
    def fill_ratio(
        self,
    ) -> float:
        if self.capacity <= 0:
            return 1.0

        return min(
            1.0,
            self.total_weight
            / self.capacity,
        )

    def is_empty(
        self,
    ) -> bool:
        return (
            self.item_count
            == 0
        )

    def is_full(
        self,
    ) -> bool:
        return (
            self.total_weight
            >= self.capacity
        )

    def can_add(
        self,
        trash: Trash,
    ) -> bool:
        return (
            self.total_weight
            + trash.weight
            <= self.capacity
        )

    def add(
        self,
        trash: Trash,
    ) -> bool:
        if not self.can_add(
            trash
        ):
            return False

        self.items.append(
            trash
        )

        return True

    def remove(
        self,
        trash: Trash,
    ) -> bool:
        if trash not in self.items:
            return False

        self.items.remove(
            trash
        )

        return True

    def clear(
        self,
    ) -> None:
        self.items.clear()

    def grouped_counts(
        self,
    ) -> Dict[TrashKind, int]:
        result: Dict[
            TrashKind,
            int,
        ] = {
            kind: 0
            for kind in TrashKind
        }

        for trash in self.items:
            result[
                trash.kind
            ] += 1

        return result

    def grouped_weights(
        self,
    ) -> Dict[TrashKind, int]:
        result: Dict[
            TrashKind,
            int,
        ] = {
            kind: 0
            for kind in TrashKind
        }

        for trash in self.items:
            result[
                trash.kind
            ] += trash.weight

        return result

    def description(
        self,
    ) -> str:
        if self.is_empty():
            return "가방이 비어 있습니다."

        lines: List[str] = [
            (
                f"가방 무게: "
                f"{self.total_weight}/"
                f"{self.capacity}"
            )
        ]

        counts = (
            self.grouped_counts()
        )

        for kind in TrashKind:
            count = counts[
                kind
            ]

            if count <= 0:
                continue

            lines.append(
                (
                    f"- {kind.display_name}: "
                    f"{count}개"
                )
            )

        return "\n".join(
            lines
        )

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "capacity": self.capacity,
            "items": [
                trash.to_dict()
                for trash in self.items
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "TrashBag":
        bag = cls(
            capacity=safe_int(
                data.get(
                    "capacity",
                ),
                AGENT_BAG_CAPACITY,
            )
        )

        item_data_list = data.get(
            "items",
            [],
        )

        for item_data in item_data_list:
            if not isinstance(
                item_data,
                dict,
            ):
                continue

            bag.items.append(
                Trash.from_dict(
                    item_data
                )
            )

        return bag


@dataclass
class RecyclingBin:
    trash_kind: TrashKind

    capacity: int = 120

    stored_weight: int = 0

    stored_count: int = 0

    @property
    def remaining_capacity(
        self,
    ) -> int:
        return max(
            0,
            self.capacity
            - self.stored_weight,
        )

    @property
    def fill_ratio(
        self,
    ) -> float:
        if self.capacity <= 0:
            return 1.0

        return min(
            1.0,
            self.stored_weight
            / self.capacity,
        )

    def is_full(
        self,
    ) -> bool:
        return (
            self.stored_weight
            >= self.capacity
        )

    def can_accept(
        self,
        trash: Trash,
    ) -> bool:
        if (
            trash.kind
            != self.trash_kind
        ):
            return False

        return (
            self.stored_weight
            + trash.weight
            <= self.capacity
        )

    def accept(
        self,
        trash: Trash,
    ) -> bool:
        if not self.can_accept(
            trash
        ):
            return False

        self.stored_weight += (
            trash.weight
        )

        self.stored_count += 1

        return True

    def empty(
        self,
    ) -> None:
        self.stored_weight = 0
        self.stored_count = 0

    def status_text(
        self,
    ) -> str:
        return (
            f"{self.trash_kind.display_name}: "
            f"{self.stored_weight}/"
            f"{self.capacity} "
            f"({format_percent(self.fill_ratio)})"
        )

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "trash_kind": (
                self.trash_kind.name
            ),
            "capacity": self.capacity,
            "stored_weight": (
                self.stored_weight
            ),
            "stored_count": (
                self.stored_count
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "RecyclingBin":
        kind_name = str(
            data.get(
                "trash_kind",
                TrashKind.GENERAL.name,
            )
        )

        try:
            trash_kind = TrashKind[
                kind_name
            ]

        except KeyError:
            trash_kind = (
                TrashKind.GENERAL
            )

        return cls(
            trash_kind=trash_kind,
            capacity=safe_int(
                data.get(
                    "capacity",
                ),
                120,
            ),
            stored_weight=safe_int(
                data.get(
                    "stored_weight",
                ),
                0,
            ),
            stored_count=safe_int(
                data.get(
                    "stored_count",
                ),
                0,
            ),
        )
    @dataclass
class RecyclingStation:
    station_id: int

    position: Position

    name: str

    bins: Dict[
        TrashKind,
        RecyclingBin,
    ] = field(
        default_factory=dict,
    )

    processed_count: int = 0

    processed_weight: int = 0

    maintenance_count: int = 0

    def __post_init__(
        self,
    ) -> None:
        if self.bins:
            return

        self.bins = {
            kind: RecyclingBin(
                trash_kind=kind,
            )
            for kind in TrashKind
        }

    def recycle(
        self,
        trash: Trash,
    ) -> bool:
        target_bin = self.bins.get(
            trash.kind
        )

        if target_bin is None:
            return False

        if not target_bin.accept(
            trash
        ):
            return False

        self.processed_count += 1

        self.processed_weight += (
            trash.weight
        )

        return True

    def maintenance(
        self,
    ) -> int:
        emptied_count = 0

        for recycling_bin in (
            self.bins.values()
        ):
            if (
                recycling_bin.fill_ratio
                < 0.95
            ):
                continue

            recycling_bin.empty()

            emptied_count += 1

        if emptied_count > 0:
            self.maintenance_count += 1

        return emptied_count

    def total_stored_weight(
        self,
    ) -> int:
        return sum(
            recycling_bin.stored_weight
            for recycling_bin
            in self.bins.values()
        )

    def total_stored_count(
        self,
    ) -> int:
        return sum(
            recycling_bin.stored_count
            for recycling_bin
            in self.bins.values()
        )

    def status_text(
        self,
    ) -> str:
        lines: List[str] = [
            self.name,
            (
                f"위치: "
                f"({self.position.x}, "
                f"{self.position.y})"
            ),
            (
                f"처리 개수: "
                f"{self.processed_count}"
            ),
            (
                f"처리 무게: "
                f"{self.processed_weight}"
            ),
        ]

        for trash_kind in TrashKind:
            recycling_bin = (
                self.bins[
                    trash_kind
                ]
            )

            lines.append(
                recycling_bin.status_text()
            )

        return "\n".join(
            lines
        )

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "station_id": (
                self.station_id
            ),
            "x": self.position.x,
            "y": self.position.y,
            "name": self.name,
            "processed_count": (
                self.processed_count
            ),
            "processed_weight": (
                self.processed_weight
            ),
            "maintenance_count": (
                self.maintenance_count
            ),
            "bins": [
                recycling_bin.to_dict()
                for recycling_bin
                in self.bins.values()
            ],
        }


@dataclass
class RestArea:
    area_id: int

    position: Position

    name: str

    recovery_amount: int = (
        REST_RECOVERY_AMOUNT
    )

    usage_count: int = 0

    total_recovered_energy: int = 0

    def use(
        self,
        current_energy: int,
        maximum_energy: int,
    ) -> int:
        available_recovery = max(
            0,
            maximum_energy
            - current_energy,
        )

        recovered_energy = min(
            self.recovery_amount,
            available_recovery,
        )

        self.usage_count += 1

        self.total_recovered_energy += (
            recovered_energy
        )

        return recovered_energy

    def status_text(
        self,
    ) -> str:
        return (
            f"{self.name}\n"
            f"위치: "
            f"({self.position.x}, "
            f"{self.position.y})\n"
            f"회복량: "
            f"{self.recovery_amount}\n"
            f"사용 횟수: "
            f"{self.usage_count}\n"
            f"총 회복 체력: "
            f"{self.total_recovered_energy}"
        )

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "area_id": self.area_id,
            "x": self.position.x,
            "y": self.position.y,
            "name": self.name,
            "recovery_amount": (
                self.recovery_amount
            ),
            "usage_count": (
                self.usage_count
            ),
            "total_recovered_energy": (
                self.total_recovered_energy
            ),
        }


@dataclass
class EnvironmentState:
    weather: WeatherType = (
        WeatherType.CLEAR
    )

    time_period: TimePeriod = (
        TimePeriod.MORNING
    )

    weather_turns_remaining: int = 45

    period_turns_remaining: int = 60

    total_spawned_trash: int = 0

    total_removed_trash: int = 0

    def movement_energy_cost(
        self,
    ) -> int:
        calculated_cost = (
            MOVE_ENERGY_COST
            * self.weather.energy_multiplier
        )

        return max(
            1,
            math.ceil(
                calculated_cost
            ),
        )

    def vision_range(
        self,
        base_range: int = 15,
    ) -> int:
        vision = int(
            base_range
            * self.weather.vision_multiplier
        )

        if (
            self.time_period
            == TimePeriod.NIGHT
        ):
            vision -= 3

        return max(
            4,
            vision,
        )
        def spawn_multiplier(
        self,
    ) -> float:
        multiplier = 1.0

        if (
            self.weather
            == WeatherType.WINDY
        ):
            multiplier += 0.35

        if (
            self.weather
            == WeatherType.RAIN
        ):
            multiplier -= 0.15

        if (
            self.time_period
            == TimePeriod.EVENING
        ):
            multiplier += 0.15

        if (
            self.time_period
            == TimePeriod.NIGHT
        ):
            multiplier -= 0.25

        return max(
            0.4,
            multiplier,
        )

    def update(
        self,
        current_turn: int,
    ) -> List[SimulationEvent]:
        events: List[
            SimulationEvent
        ] = []

        self.weather_turns_remaining -= 1

        self.period_turns_remaining -= 1

        if (
            self.weather_turns_remaining
            <= 0
        ):
            previous_weather = (
                self.weather
            )

            self.weather = random.choice(
                list(
                    WeatherType
                )
            )

            self.weather_turns_remaining = (
                random.randint(
                    35,
                    75,
                )
            )

            if (
                previous_weather
                != self.weather
            ):
                events.append(
                    SimulationEvent(
                        turn=current_turn,
                        event_type=(
                            EventType.WEATHER
                        ),
                        message=(
                            f"날씨가 "
                            f"{previous_weather.display_name}에서 "
                            f"{self.weather.display_name}(으)로 "
                            f"변했습니다."
                        ),
                    )
                )

        if (
            self.period_turns_remaining
            <= 0
        ):
            periods = list(
                TimePeriod
            )

            current_index = (
                periods.index(
                    self.time_period
                )
            )

            next_index = (
                current_index + 1
            ) % len(periods)

            self.time_period = (
                periods[
                    next_index
                ]
            )

            self.period_turns_remaining = 60

            events.append(
                SimulationEvent(
                    turn=current_turn,
                    event_type=(
                        EventType.INFO
                    ),
                    message=(
                        f"시간대가 "
                        f"{self.time_period.display_name}(으)로 "
                        f"변했습니다."
                    ),
                )
            )

        return events
        def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "weather": (
                self.weather.name
            ),
            "time_period": (
                self.time_period.name
            ),
            "weather_turns_remaining": (
                self.weather_turns_remaining
            ),
            "period_turns_remaining": (
                self.period_turns_remaining
            ),
            "total_spawned_trash": (
                self.total_spawned_trash
            ),
            "total_removed_trash": (
                self.total_removed_trash
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "EnvironmentState":
        weather_name = str(
            data.get(
                "weather",
                WeatherType.CLEAR.name,
            )
        )

        period_name = str(
            data.get(
                "time_period",
                TimePeriod.MORNING.name,
            )
        )

        try:
            weather = WeatherType[
                weather_name
            ]

        except KeyError:
            weather = (
                WeatherType.CLEAR
            )

        try:
            time_period = TimePeriod[
                period_name
            ]

        except KeyError:
            time_period = (
                TimePeriod.MORNING
            )

        return cls(
            weather=weather,
            time_period=time_period,
            weather_turns_remaining=safe_int(
                data.get(
                    "weather_turns_remaining",
                ),
                45,
            ),
            period_turns_remaining=safe_int(
                data.get(
                    "period_turns_remaining",
                ),
                60,
            ),
            total_spawned_trash=safe_int(
                data.get(
                    "total_spawned_trash",
                ),
                0,
            ),
            total_removed_trash=safe_int(
                data.get(
                    "total_removed_trash",
                ),
                0,
            ),
        )


@dataclass
class SimulationStatistics:
    total_pickups: int = 0

    total_recycled: int = 0

    total_score: int = 0

    total_moves: int = 0

    total_rests: int = 0

    total_energy_used: int = 0

    failed_pickups: int = 0

    unreachable_targets: int = 0

    trash_spawn_events: int = 0

    cleanest_turn: int = 0

    lowest_trash_count: int = (
        10 ** 9
    )

    highest_trash_count: int = 0

    def update_from_agents(
        self,
        agents: List["CleanerAgent"],
    ) -> None:
        self.total_pickups = sum(
            agent.collected_count
            for agent in agents
        )

        self.total_recycled = sum(
            agent.recycled_count
            for agent in agents
        )

        self.total_score = sum(
            agent.score
            for agent in agents
        )

        self.total_moves = sum(
            agent.moved_steps
            for agent in agents
        )

        self.total_rests = sum(
            agent.rested_count
            for agent in agents
        )

        self.total_energy_used = sum(
            agent.total_energy_used
            for agent in agents
        )

    def observe_trash_count(
        self,
        current_turn: int,
        trash_count: int,
    ) -> None:
        if (
            trash_count
            < self.lowest_trash_count
        ):
            self.lowest_trash_count = (
                trash_count
            )

            self.cleanest_turn = (
                current_turn
            )

        if (
            trash_count
            > self.highest_trash_count
        ):
            self.highest_trash_count = (
                trash_count
            )

    def average_score(
        self,
        agents: List["CleanerAgent"],
    ) -> float:
        if not agents:
            return 0.0

        return (
            self.total_score
            / len(agents)
        )

    def recycling_rate(
        self,
    ) -> float:
        if self.total_pickups <= 0:
            return 0.0

        return min(
            1.0,
            self.total_recycled
            / self.total_pickups,
        )

    def movement_efficiency(
        self,
    ) -> float:
        if self.total_moves <= 0:
            return 0.0

        return (
            self.total_pickups
            / self.total_moves
        )

    def energy_efficiency(
        self,
    ) -> float:
        if (
            self.total_energy_used
            <= 0
        ):
            return 0.0

        return (
            self.total_recycled
            / self.total_energy_used
        )

    def status_text(
        self,
    ) -> str:
        return (
            f"총 수거: "
            f"{self.total_pickups}개\n"
            f"총 분리배출: "
            f"{self.total_recycled}개\n"
            f"총점: "
            f"{self.total_score}점\n"
            f"총 이동: "
            f"{self.total_moves}회\n"
            f"총 휴식: "
            f"{self.total_rests}회\n"
            f"재활용률: "
            f"{format_percent(self.recycling_rate())}\n"
            f"최저 쓰레기 수: "
            f"{self.lowest_trash_count}개\n"
            f"가장 깨끗한 턴: "
            f"{self.cleanest_turn}"
        )

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "total_pickups": (
                self.total_pickups
            ),
            "total_recycled": (
                self.total_recycled
            ),
            "total_score": (
                self.total_score
            ),
            "total_moves": (
                self.total_moves
            ),
            "total_rests": (
                self.total_rests
            ),
            "total_energy_used": (
                self.total_energy_used
            ),
            "failed_pickups": (
                self.failed_pickups
            ),
            "unreachable_targets": (
                self.unreachable_targets
            ),
            "trash_spawn_events": (
                self.trash_spawn_events
            ),
            "cleanest_turn": (
                self.cleanest_turn
            ),
            "lowest_trash_count": (
                self.lowest_trash_count
            ),
            "highest_trash_count": (
                self.highest_trash_count
            ),
        }
        @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "SimulationStatistics":
        return cls(
            total_pickups=safe_int(
                data.get("total_pickups"),
                0,
            ),
            total_recycled=safe_int(
                data.get("total_recycled"),
                0,
            ),
            total_score=safe_int(
                data.get("total_score"),
                0,
            ),
            total_moves=safe_int(
                data.get("total_moves"),
                0,
            ),
            total_rests=safe_int(
                data.get("total_rests"),
                0,
            ),
            total_energy_used=safe_int(
                data.get("total_energy_used"),
                0,
            ),
            failed_pickups=safe_int(
                data.get("failed_pickups"),
                0,
            ),
            unreachable_targets=safe_int(
                data.get("unreachable_targets"),
                0,
            ),
            trash_spawn_events=safe_int(
                data.get("trash_spawn_events"),
                0,
            ),
            cleanest_turn=safe_int(
                data.get("cleanest_turn"),
                0,
            ),
            lowest_trash_count=safe_int(
                data.get("lowest_trash_count"),
                10 ** 9,
            ),
            highest_trash_count=safe_int(
                data.get("highest_trash_count"),
                0,
            ),
        )