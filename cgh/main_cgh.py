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


@dataclass
class CleanerAgent:
    agent_id: int

    name: str

    position: Position

    color: str

    energy: int = (
        AGENT_MAX_ENERGY
    )

    maximum_energy: int = (
        AGENT_MAX_ENERGY
    )

    bag: TrashBag = field(
        default_factory=TrashBag,
    )

    state: AgentState = (
        AgentState.SEARCHING
    )

    score: int = 0

    collected_count: int = 0

    recycled_count: int = 0

    moved_steps: int = 0

    rested_count: int = 0

    total_energy_used: int = 0

    idle_turns: int = 0

    target_trash_id: Optional[
        int
    ] = None

    target_position: Optional[
        Position
    ] = None

    path: List[
        Position
    ] = field(
        default_factory=list,
    )

    def is_low_energy(
        self,
    ) -> bool:
        return (
            self.energy
            <= LOW_ENERGY_THRESHOLD
        )

    def is_bag_empty(
        self,
    ) -> bool:
        return self.bag.is_empty()

    def should_return_to_station(
        self,
    ) -> bool:
        return (
            self.bag.fill_ratio
            >= BAG_RETURN_RATIO
        )

    def can_move(
        self,
    ) -> bool:
        return self.energy > 0

    def spend_energy(
        self,
        amount: int,
    ) -> int:
        amount = max(
            0,
            amount,
        )

        actual_amount = min(
            self.energy,
            amount,
        )

        self.energy -= (
            actual_amount
        )

        self.total_energy_used += (
            actual_amount
        )

        return actual_amount

    def recover_energy(
        self,
        amount: int,
    ) -> int:
        previous_energy = (
            self.energy
        )

        self.energy = clamp(
            self.energy + amount,
            0,
            self.maximum_energy,
        )

        return (
            self.energy
            - previous_energy
        )

    def set_trash_target(
        self,
        trash: Trash,
        path: List[Position],
    ) -> None:
        self.target_trash_id = (
            trash.trash_id
        )

        self.target_position = (
            trash.position
        )

        self.path = list(
            path
        )

        self.state = (
            AgentState.MOVING_TO_TRASH
        )

    def set_destination(
        self,
        position: Position,
        path: List[Position],
        state: AgentState,
    ) -> None:
        self.target_position = (
            position
        )

        self.target_trash_id = None

        self.path = list(
            path
        )

        self.state = state

    def clear_target(
        self,
    ) -> None:
        self.target_trash_id = None

        self.target_position = None

        self.path.clear()

    def next_step(
        self,
    ) -> Optional[Position]:
        if not self.path:
            return None

        return self.path.pop(
            0
        )

    def move_to(
        self,
        position: Position,
        energy_cost: int,
    ) -> bool:
        if not self.can_move():
            return False

        self.position = position

        self.spend_energy(
            energy_cost
        )

        self.moved_steps += 1

        self.idle_turns = 0

        return True

    def collect_trash(
        self,
        trash: Trash,
    ) -> bool:
        if not self.bag.add(
            trash
        ):
            return False

        self.spend_energy(
            PICKUP_ENERGY_COST
        )

        self.collected_count += 1

        self.score += (
            trash.score
        )

        self.clear_target()

        self.state = (
            AgentState.SEARCHING
        )

        return True

    def recycle_bag(
        self,
        station: RecyclingStation,
    ) -> Tuple[int, int]:
        recycled_count = 0

        gained_score = 0

        remaining_items: List[
            Trash
        ] = []

        for trash in self.bag.items:
            if station.recycle(
                trash
            ):
                recycled_count += 1

                gained_score += max(
                    1,
                    trash.score // 2,
                )

            else:
                remaining_items.append(
                    trash
                )

        self.bag.items = (
            remaining_items
        )

        self.recycled_count += (
            recycled_count
        )

        self.score += (
            gained_score
        )

        if recycled_count > 0:
            self.spend_energy(
                RECYCLE_ENERGY_COST
            )

        self.clear_target()

        self.state = (
            AgentState.SEARCHING
        )

        return (
            recycled_count,
            gained_score,
        )

    def rest_at(
        self,
        rest_area: RestArea,
    ) -> int:
        recovered_energy = (
            rest_area.use(
                self.energy,
                self.maximum_energy,
            )
        )

        self.recover_energy(
            recovered_energy
        )

        self.rested_count += 1

        self.clear_target()

        self.state = (
            AgentState.RESTING
        )

        return recovered_energy

    def continue_resting(
        self,
        recovery_amount: int,
    ) -> int:
        recovered_energy = (
            self.recover_energy(
                recovery_amount
            )
        )

        if (
            self.energy
            >= int(
                self.maximum_energy
                * 0.8
            )
        ):
            self.state = (
                AgentState.SEARCHING
            )

        else:
            self.state = (
                AgentState.RESTING
            )

        return recovered_energy

    def idle(
        self,
    ) -> None:
        self.idle_turns += 1

        self.state = (
            AgentState.IDLE
        )

        if (
            self.energy
            < self.maximum_energy
        ):
            self.recover_energy(
                IDLE_RECOVERY_AMOUNT
            )

    def status_text(
        self,
    ) -> str:
        target_text = "없음"

        if (
            self.target_position
            is not None
        ):
            target_text = (
                f"("
                f"{self.target_position.x}, "
                f"{self.target_position.y}"
                f")"
            )

        return (
            f"이름: {self.name}\n"
            f"번호: {self.agent_id}\n"
            f"상태: {self.state.value}\n"
            f"위치: "
            f"({self.position.x}, "
            f"{self.position.y})\n"
            f"체력: "
            f"{self.energy}/"
            f"{self.maximum_energy}\n"
            f"체력 막대: {create_progress_bar(self.energy, self.maximum_energy)}\n"
            f"가방: "
            f"{self.bag.total_weight}/"
            f"{self.bag.capacity}\n"
            f"목표 위치: "
            f"{target_text}\n"
            f"남은 경로: "
            f"{len(self.path)}칸\n"
            f"점수: "
            f"{self.score}\n"
            f"수거 횟수: "
            f"{self.collected_count}\n"
            f"분리배출 횟수: "
            f"{self.recycled_count}\n"
            f"이동 횟수: "
            f"{self.moved_steps}\n"
            f"휴식 횟수: "
            f"{self.rested_count}"
        )

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "x": self.position.x,
            "y": self.position.y,
            "color": self.color,
            "energy": self.energy,
            "maximum_energy": (
                self.maximum_energy
            ),
            "bag": self.bag.to_dict(),
            "state": self.state.name,
            "score": self.score,
            "collected_count": (
                self.collected_count
            ),
            "recycled_count": (
                self.recycled_count
            ),
            "moved_steps": (
                self.moved_steps
            ),
            "rested_count": (
                self.rested_count
            ),
            "total_energy_used": (
                self.total_energy_used
            ),
            "idle_turns": (
                self.idle_turns
            ),
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "CleanerAgent":
        state_name = str(
            data.get(
                "state",
                AgentState.SEARCHING.name,
            )
        )

        try:
            state = AgentState[
                state_name
            ]

        except KeyError:
            state = (
                AgentState.SEARCHING
            )

        agent = cls(
            agent_id=safe_int(
                data.get("agent_id"),
                0,
            ),
            name=str(
                data.get(
                    "name",
                    "청소원",
                )
            ),
            position=Position(
                safe_int(
                    data.get("x"),
                    1,
                ),
                safe_int(
                    data.get("y"),
                    1,
                ),
            ),
            color=str(
                data.get(
                    "color",
                    "#EF5350",
                )
            ),
            energy=safe_int(
                data.get("energy"),
                AGENT_MAX_ENERGY,
            ),
            maximum_energy=safe_int(
                data.get("maximum_energy"),
                AGENT_MAX_ENERGY,
            ),
            state=state,
        )

        agent.bag = TrashBag.from_dict(
            data.get(
                "bag",
                {},
            )
        )

        agent.score = safe_int(
            data.get("score"),
            0,
        )

        agent.collected_count = safe_int(
            data.get("collected_count"),
            0,
        )

        agent.recycled_count = safe_int(
            data.get("recycled_count"),
            0,
        )

        agent.moved_steps = safe_int(
            data.get("moved_steps"),
            0,
        )

        agent.rested_count = safe_int(
            data.get("rested_count"),
            0,
        )

        agent.total_energy_used = safe_int(
            data.get("total_energy_used"),
            0,
        )

        agent.idle_turns = safe_int(
            data.get("idle_turns"),
            0,
        )

        return agent


class WorldMap:
    def __init__(
        self,
        width: int,
        height: int,
    ) -> None:
        self.width = width
        self.height = height

        self.tiles = [
            [
                TileType.EMPTY
                for _ in range(width)
            ]
            for _ in range(height)
        ]

        self.stations: List[
            RecyclingStation
        ] = []

        self.rest_areas: List[
            RestArea
        ] = []

    def in_bounds(
        self,
        position: Position,
    ) -> bool:
        return (
            0 <= position.x < self.width
            and 0 <= position.y < self.height
        )

    def tile_at(
        self,
        position: Position,
    ) -> TileType:
        if not self.in_bounds(position):
            return TileType.WALL

        return self.tiles[
            position.y
        ][
            position.x
        ]

    def set_tile(
        self,
        position: Position,
        tile_type: TileType,
    ) -> None:
        if self.in_bounds(position):
            self.tiles[
                position.y
            ][
                position.x
            ] = tile_type

    def is_walkable(
        self,
        position: Position,
    ) -> bool:
        return (
            self.in_bounds(position)
            and self.tile_at(position)
            not in {
                TileType.WALL,
                TileType.WATER,
            }
        )

    def random_empty_position(
        self,
        blocked: Optional[
            Set[Position]
        ] = None,
    ) -> Optional[Position]:
        blocked = blocked or set()

        candidates: List[
            Position
        ] = []

        for y in range(
            1,
            self.height - 1,
        ):
            for x in range(
                1,
                self.width - 1,
            ):
                position = Position(
                    x,
                    y,
                )

                if (
                    self.tile_at(position)
                    == TileType.EMPTY
                    and position not in blocked
                ):
                    candidates.append(
                        position
                    )

        if not candidates:
            return None

        return random.choice(
            candidates
        )

    def generate(
        self,
        config: SimulationConfig,
    ) -> None:
        for x in range(
            self.width
        ):
            self.set_tile(
                Position(x, 0),
                TileType.WALL,
            )

            self.set_tile(
                Position(
                    x,
                    self.height - 1,
                ),
                TileType.WALL,
            )

        for y in range(
            self.height
        ):
            self.set_tile(
                Position(0, y),
                TileType.WALL,
            )

            self.set_tile(
                Position(
                    self.width - 1,
                    y,
                ),
                TileType.WALL,
            )

        for _ in range(
            config.obstacle_count
        ):
            position = (
                self.random_empty_position()
            )

            if position:
                self.set_tile(
                    position,
                    TileType.WALL,
                )

        for _ in range(18):
            position = (
                self.random_empty_position()
            )

            if position:
                self.set_tile(
                    position,
                    TileType.FLOWER,
                )

        for index in range(
            config.station_count
        ):
            position = (
                self.random_empty_position()
            )

            if position:
                self.set_tile(
                    position,
                    TileType.STATION,
                )

                self.stations.append(
                    RecyclingStation(
                        index + 1,
                        position,
                        f"분리수거장 {index + 1}",
                    )
                )

        for index in range(
            config.rest_area_count
        ):
            position = (
                self.random_empty_position()
            )

            if position:
                self.set_tile(
                    position,
                    TileType.REST_AREA,
                )

                self.rest_areas.append(
                    RestArea(
                        index + 1,
                        position,
                        f"휴식 공간 {index + 1}",
                    )
                )

    def nearest_station(
        self,
        position: Position,
    ) -> Optional[
        RecyclingStation
    ]:
        if not self.stations:
            return None

        return min(
            self.stations,
            key=lambda station:
            position.manhattan_distance(
                station.position
            ),
        )

    def nearest_rest_area(
        self,
        position: Position,
    ) -> Optional[RestArea]:
        if not self.rest_areas:
            return None

        return min(
            self.rest_areas,
            key=lambda area:
            position.manhattan_distance(
                area.position
            ),
        )


class PathFinder:
    def __init__(
        self,
        world: WorldMap,
    ) -> None:
        self.world = world

    def find_path(
        self,
        start: Position,
        goal: Position,
    ) -> List[Position]:
        if start == goal:
            return []

        queue = [
            (
                0,
                0,
                start,
            )
        ]

        came_from = {
            start: None
        }

        cost = {
            start: 0
        }

        sequence = 0

        while queue:
            _, _, current = (
                heapq.heappop(
                    queue
                )
            )

            if current == goal:
                break

            for neighbor in (
                current.neighbors()
            ):
                if not self.world.is_walkable(
                    neighbor
                ):
                    continue

                new_cost = (
                    cost[current] + 1
                )

                if (
                    neighbor not in cost
                    or new_cost
                    < cost[neighbor]
                ):
                    cost[
                        neighbor
                    ] = new_cost

                    priority = (
                        new_cost
                        + neighbor.manhattan_distance(
                            goal
                        )
                    )

                    sequence += 1

                    heapq.heappush(
                        queue,
                        (
                            priority,
                            sequence,
                            neighbor,
                        ),
                    )

                    came_from[
                        neighbor
                    ] = current

        if goal not in came_from:
            return []

        path: List[
            Position
        ] = []

        current = goal

        while current != start:
            path.append(
                current
            )

            current = came_from[
                current
            ]

        path.reverse()

        return path


class SimulationEngine:
    COLORS = [
        "#EF5350",
        "#42A5F5",
        "#66BB6A",
        "#AB47BC",
        "#FFA726",
    ]

    NAMES = [
        "가현",
        "민수",
        "지우",
        "서연",
        "도윤",
    ]

    def __init__(
        self,
    ) -> None:
        self.config = (
            SimulationConfig()
        )

        self.config.normalize()

        random.seed(
            self.config.random_seed
        )

        self.world = WorldMap(
            self.config.width,
            self.config.height,
        )

        self.world.generate(
            self.config
        )

        self.pathfinder = PathFinder(
            self.world
        )

        self.environment = (
            EnvironmentState()
        )

        self.statistics = (
            SimulationStatistics()
        )

        self.agents: List[
            CleanerAgent
        ] = []

        self.trash_items: Dict[
            int,
            Trash
        ] = {}

        self.events: List[
            SimulationEvent
        ] = []

        self.turn = 0
        self.next_trash_id = 1
        self.running = False

        self.create_agents()
        self.spawn_trash(
            self.config.initial_trash_count
        )

    def create_agents(
        self,
    ) -> None:
        blocked: Set[
            Position
        ] = set()

        for index in range(
            self.config.agent_count
        ):
            position = (
                self.world.random_empty_position(
                    blocked
                )
            )

            if not position:
                continue

            blocked.add(
                position
            )

            self.agents.append(
                CleanerAgent(
                    agent_id=index + 1,
                    name=self.NAMES[
                        index
                        % len(self.NAMES)
                    ],
                    position=position,
                    color=self.COLORS[
                        index
                        % len(self.COLORS)
                    ],
                )
            )

    def spawn_trash(
        self,
        count: int,
    ) -> None:
        blocked = {
            trash.position
            for trash
            in self.trash_items.values()
        }

        for _ in range(count):
            position = (
                self.world.random_empty_position(
                    blocked
                )
            )

            if not position:
                break

            trash = Trash(
                trash_id=self.next_trash_id,
                kind=TrashKind.random_kind(),
                position=position,
                created_turn=self.turn,
            )

            self.trash_items[
                trash.trash_id
            ] = trash

            blocked.add(
                position
            )

            self.next_trash_id += 1

    def add_event(
        self,
        event_type: EventType,
        message: str,
    ) -> None:
        self.events.append(
            SimulationEvent(
                self.turn,
                event_type,
                message,
            )
        )

        self.events = self.events[
            -EVENT_LOG_LIMIT:
        ]

    def update_agent(
        self,
        agent: CleanerAgent,
    ) -> None:
        if agent.is_low_energy():
            rest_area = (
                self.world.nearest_rest_area(
                    agent.position
                )
            )

            if rest_area:
                if (
                    agent.position
                    == rest_area.position
                ):
                    agent.rest_at(
                        rest_area
                    )

                    return

                agent.path = (
                    self.pathfinder.find_path(
                        agent.position,
                        rest_area.position,
                    )
                )

        elif agent.should_return_to_station():
            station = (
                self.world.nearest_station(
                    agent.position
                )
            )

            if station:
                if (
                    agent.position
                    == station.position
                ):
                    agent.recycle_bag(
                        station
                    )

                    return

                agent.path = (
                    self.pathfinder.find_path(
                        agent.position,
                        station.position,
                    )
                )

        elif not agent.path:
            available = [
                trash
                for trash
                in self.trash_items.values()
                if agent.bag.can_add(
                    trash
                )
            ]

            if available:
                target = min(
                    available,
                    key=lambda trash:
                    agent.position.manhattan_distance(
                        trash.position
                    ),
                )

                agent.target_trash_id = (
                    target.trash_id
                )

                agent.path = (
                    self.pathfinder.find_path(
                        agent.position,
                        target.position,
                    )
                )

        if agent.path:
            next_position = (
                agent.next_step()
            )

            if next_position:
                agent.move_to(
                    next_position,
                    self.environment.movement_energy_cost(),
                )

        target = self.trash_items.get(
            agent.target_trash_id
            or -1
        )

        if (
            target
            and target.position
            == agent.position
        ):
            if agent.collect_trash(
                target
            ):
                self.trash_items.pop(
                    target.trash_id,
                    None,
                )

                self.add_event(
                    EventType.PICKUP,
                    (
                        f"{agent.name}이(가) "
                        f"{target.kind.display_name}을 "
                        f"수거했습니다."
                    ),
                )

    def step(
        self,
    ) -> None:
        self.turn += 1

        for event in (
            self.environment.update(
                self.turn
            )
        ):
            self.events.append(
                event
            )

        if (
            self.turn
            % TRASH_SPAWN_INTERVAL
            == 0
        ):
            self.spawn_trash(
                random.randint(
                    TRASH_SPAWN_MIN_COUNT,
                    TRASH_SPAWN_MAX_COUNT,
                )
            )

        for agent in self.agents:
            self.update_agent(
                agent
            )

        self.statistics.update_from_agents(
            self.agents
        )


class SimulationApp:
    def __init__(
        self,
        root: tk.Tk,
    ) -> None:
        self.root = root
        self.root.title(
            APP_TITLE
        )

        self.engine = (
            SimulationEngine()
        )

        self.canvas = tk.Canvas(
            root,
            width=MAP_WIDTH * CELL_SIZE,
            height=MAP_HEIGHT * CELL_SIZE,
        )

        self.canvas.pack(
            side=tk.LEFT
        )

        self.info = tk.Text(
            root,
            width=38,
        )

        self.info.pack(
            side=tk.RIGHT,
            fill=tk.BOTH,
        )

        self.root.after(
            DEFAULT_TICK_DELAY,
            self.update,
        )

    def draw(
        self,
    ) -> None:
        self.canvas.delete(
            "all"
        )

        for y in range(
            MAP_HEIGHT
        ):
            for x in range(
                MAP_WIDTH
            ):
                position = Position(
                    x,
                    y,
                )

                tile = (
                    self.engine.world.tile_at(
                        position
                    )
                )

                colors = {
                    TileType.EMPTY: "#E8F5E9",
                    TileType.WALL: "#5D4037",
                    TileType.WATER: "#81D4FA",
                    TileType.FLOWER: "#F8BBD0",
                    TileType.STATION: "#90CAF9",
                    TileType.REST_AREA: "#C5E1A5",
                }

                self.canvas.create_rectangle(
                    x * CELL_SIZE,
                    y * CELL_SIZE,
                    (x + 1) * CELL_SIZE,
                    (y + 1) * CELL_SIZE,
                    fill=colors[tile],
                    outline="#CCCCCC",
                )

        for trash in (
            self.engine.trash_items.values()
        ):
            x = trash.position.x
            y = trash.position.y

            self.canvas.create_oval(
                x * CELL_SIZE + 7,
                y * CELL_SIZE + 7,
                (x + 1) * CELL_SIZE - 7,
                (y + 1) * CELL_SIZE - 7,
                fill=trash.kind.color,
            )

        for agent in (
            self.engine.agents
        ):
            x = agent.position.x
            y = agent.position.y

            self.canvas.create_oval(
                x * CELL_SIZE + 3,
                y * CELL_SIZE + 3,
                (x + 1) * CELL_SIZE - 3,
                (y + 1) * CELL_SIZE - 3,
                fill=agent.color,
            )

    def update(
        self,
    ) -> None:
        self.engine.step()
        self.draw()

        self.info.delete(
            "1.0",
            tk.END,
        )

        self.info.insert(
            tk.END,
            (
                f"현재 턴: "
                f"{self.engine.turn}\n"
                f"남은 쓰레기: "
                f"{len(self.engine.trash_items)}개\n\n"
            ),
        )

        for agent in (
            self.engine.agents
        ):
            self.info.insert(
                tk.END,
                agent.status_text()
                + "\n\n",
            )

        if (
            self.engine.turn
            < self.engine.config.max_turns
        ):
            self.root.after(
                self.engine.config.tick_delay,
                self.update,
            )


def main(
) -> None:
    root = tk.Tk()

    SimulationApp(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()