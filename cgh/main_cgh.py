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
        "#26A69A",
        "#EC407A",
        "#7E57C2",
        "#78909C",
        "#8D6E63",
    ]

    NAMES = [
        "가현",
        "민수",
        "지우",
        "서연",
        "도윤",
        "하린",
        "현우",
        "유진",
        "지민",
        "수아",
    ]

    def __init__(
        self,
        config: Optional[SimulationConfig] = None,
    ) -> None:
        self.config = config or SimulationConfig()
        self.config.normalize()

        random.seed(self.config.random_seed)

        self.world = WorldMap(
            self.config.width,
            self.config.height,
        )
        self.world.generate(self.config)

        self.pathfinder = PathFinder(self.world)
        self.environment = EnvironmentState()
        self.statistics = SimulationStatistics()

        self.agents: List[CleanerAgent] = []
        self.trash_items: Dict[int, Trash] = {}
        self.events: List[SimulationEvent] = []

        self.turn = 0
        self.next_trash_id = 1
        self.running = False
        self.finished = False

        self.create_agents()
        self.spawn_trash(self.config.initial_trash_count, initial=True)
        self.add_event(EventType.SYSTEM, "시뮬레이션이 준비되었습니다.")

    def reset(self) -> None:
        self.__init__(self.config)

    def occupied_positions(
        self,
        exclude_agent_id: Optional[int] = None,
    ) -> Set[Position]:
        return {
            agent.position
            for agent in self.agents
            if agent.agent_id != exclude_agent_id
        }

    def trash_positions(self) -> Set[Position]:
        return {
            trash.position
            for trash in self.trash_items.values()
        }

    def create_agents(self) -> None:
        blocked: Set[Position] = set()

        for index in range(self.config.agent_count):
            position = self.world.random_empty_position(blocked)

            if position is None:
                break

            blocked.add(position)

            self.agents.append(
                CleanerAgent(
                    agent_id=index + 1,
                    name=self.NAMES[index % len(self.NAMES)],
                    position=position,
                    color=self.COLORS[index % len(self.COLORS)],
                )
            )

    def spawn_trash(
        self,
        count: int,
        initial: bool = False,
    ) -> int:
        remaining_slots = MAX_TRASH_ON_MAP - len(self.trash_items)
        count = max(0, min(count, remaining_slots))

        blocked = (
            self.occupied_positions()
            | self.trash_positions()
        )

        created = 0

        for _ in range(count):
            position = self.world.random_empty_position(blocked)

            if position is None:
                break

            kind = TrashKind.random_kind()

            trash = Trash(
                trash_id=self.next_trash_id,
                kind=kind,
                position=position,
                created_turn=self.turn,
                wet=(
                    self.environment.weather == WeatherType.RAIN
                    and random.random() < 0.65
                ),
                damaged=(
                    self.environment.weather == WeatherType.WINDY
                    and random.random() < 0.35
                ),
            )

            self.trash_items[trash.trash_id] = trash
            self.next_trash_id += 1
            blocked.add(position)
            created += 1

        self.environment.total_spawned_trash += created

        if created and not initial:
            self.statistics.trash_spawn_events += 1
            self.add_event(
                EventType.TRASH_SPAWN,
                f"새로운 쓰레기 {created}개가 생성되었습니다.",
            )

        return created

    def add_event(
        self,
        event_type: EventType,
        message: str,
    ) -> None:
        self.events.append(
            SimulationEvent(
                turn=self.turn,
                event_type=event_type,
                message=message,
            )
        )

        if len(self.events) > EVENT_LOG_LIMIT:
            self.events = self.events[-EVENT_LOG_LIMIT:]

    def get_trash(
        self,
        trash_id: Optional[int],
    ) -> Optional[Trash]:
        if trash_id is None:
            return None

        return self.trash_items.get(trash_id)

    def release_reservation(
        self,
        agent: CleanerAgent,
    ) -> None:
        trash = self.get_trash(agent.target_trash_id)

        if trash is not None and trash.reserved_by == agent.agent_id:
            trash.reserved_by = None

    def choose_target(
        self,
        agent: CleanerAgent,
    ) -> Optional[Tuple[Trash, List[Position]]]:
        candidates: List[Trash] = []
        vision_range = self.environment.vision_range()

        for trash in self.trash_items.values():
            if trash.reserved_by not in (None, agent.agent_id):
                continue

            if not agent.bag.can_add(trash):
                continue

            if agent.position.manhattan_distance(trash.position) > vision_range:
                continue

            candidates.append(trash)

        candidates.sort(
            key=lambda item: (
                agent.position.manhattan_distance(item.position),
                -item.score,
                item.trash_id,
            )
        )

        blocked = self.occupied_positions(agent.agent_id)

        for trash in candidates:
            path = self.pathfinder.find_path(
                agent.position,
                trash.position,
            )

            if path or agent.position == trash.position:
                return trash, path

        return None

    def send_to_station(
        self,
        agent: CleanerAgent,
    ) -> bool:
        stations = sorted(
            self.world.stations,
            key=lambda station: agent.position.manhattan_distance(
                station.position
            ),
        )

        for station in stations:
            path = self.pathfinder.find_path(
                agent.position,
                station.position,
            )

            if path or agent.position == station.position:
                agent.set_destination(
                    station.position,
                    path,
                    AgentState.MOVING_TO_STATION,
                )
                return True

        return False

    def send_to_rest(
        self,
        agent: CleanerAgent,
    ) -> bool:
        areas = sorted(
            self.world.rest_areas,
            key=lambda area: agent.position.manhattan_distance(
                area.position
            ),
        )

        for area in areas:
            path = self.pathfinder.find_path(
                agent.position,
                area.position,
            )

            if path or agent.position == area.position:
                agent.set_destination(
                    area.position,
                    path,
                    AgentState.MOVING_TO_REST,
                )
                return True

        return False

    def station_at(
        self,
        position: Position,
    ) -> Optional[RecyclingStation]:
        for station in self.world.stations:
            if station.position == position:
                return station

        return None

    def rest_area_at(
        self,
        position: Position,
    ) -> Optional[RestArea]:
        for area in self.world.rest_areas:
            if area.position == position:
                return area

        return None

    def move_one_step(
        self,
        agent: CleanerAgent,
    ) -> bool:
        next_position = agent.next_step()

        if next_position is None:
            return False

        if next_position in self.occupied_positions(agent.agent_id):
            agent.path.insert(0, next_position)
            agent.idle()
            return False

        if not self.world.is_walkable(next_position):
            agent.path.clear()
            return False

        moved = agent.move_to(
            next_position,
            self.environment.movement_energy_cost(),
        )

        if moved:
            self.add_event(
                EventType.MOVE,
                f"{agent.name}이(가) ({next_position.x}, {next_position.y})로 이동했습니다.",
            )

        return moved

    def pickup_target(
        self,
        agent: CleanerAgent,
    ) -> None:
        trash = self.get_trash(agent.target_trash_id)

        if trash is None:
            agent.clear_target()
            agent.state = AgentState.SEARCHING
            return

        if agent.position != trash.position:
            return

        if not agent.collect_trash(trash):
            self.statistics.failed_pickups += 1
            trash.reserved_by = None
            agent.clear_target()
            self.send_to_station(agent)
            return

        self.trash_items.pop(trash.trash_id, None)
        self.environment.total_removed_trash += 1

        self.add_event(
            EventType.PICKUP,
            (
                f"{agent.name}이(가) {trash.kind.display_name}을(를) "
                f"수거했습니다. (+{trash.score}점)"
            ),
        )

    def recycle_agent(
        self,
        agent: CleanerAgent,
        station: RecyclingStation,
    ) -> None:
        recycled_count, gained_score = agent.recycle_bag(station)

        if recycled_count:
            self.add_event(
                EventType.RECYCLE,
                (
                    f"{agent.name}이(가) {station.name}에서 "
                    f"쓰레기 {recycled_count}개를 분리배출했습니다. "
                    f"(+{gained_score}점)"
                ),
            )
        else:
            agent.state = AgentState.SEARCHING

    def rest_agent(
        self,
        agent: CleanerAgent,
        area: RestArea,
    ) -> None:
        recovered = agent.rest_at(area)

        self.add_event(
            EventType.REST,
            f"{agent.name}이(가) {area.name}에서 체력 {recovered}을 회복했습니다.",
        )

    def wander(
        self,
        agent: CleanerAgent,
    ) -> None:
        candidates = [
            position
            for position in agent.position.neighbors()
            if self.world.is_walkable(position)
            and position not in self.occupied_positions(agent.agent_id)
        ]

        if not candidates:
            agent.idle()
            return

        next_position = random.choice(candidates)
        agent.path = [next_position]
        agent.state = AgentState.WANDERING
        self.move_one_step(agent)
        agent.state = AgentState.SEARCHING

    def update_agent(
        self,
        agent: CleanerAgent,
    ) -> None:
        if agent.energy <= 0:
            area = self.rest_area_at(agent.position)

            if area is not None:
                agent.continue_resting(6)
            else:
                agent.recover_energy(1)
                agent.state = AgentState.IDLE

            return

        if agent.state == AgentState.RESTING:
            area = self.rest_area_at(agent.position)

            if area is None:
                agent.state = AgentState.SEARCHING
            else:
                agent.continue_resting(6)

            return

        if agent.is_low_energy() and agent.state != AgentState.MOVING_TO_REST:
            self.release_reservation(agent)
            agent.clear_target()

            if self.send_to_rest(agent):
                return

        if (
            not agent.is_bag_empty()
            and agent.should_return_to_station()
            and agent.state != AgentState.MOVING_TO_STATION
        ):
            self.release_reservation(agent)
            agent.clear_target()

            if self.send_to_station(agent):
                return

        if agent.state == AgentState.MOVING_TO_STATION:
            station = self.station_at(agent.position)

            if station is not None:
                self.recycle_agent(agent, station)
                return

            if not agent.path:
                self.send_to_station(agent)

            self.move_one_step(agent)
            station = self.station_at(agent.position)

            if station is not None:
                self.recycle_agent(agent, station)

            return

        if agent.state == AgentState.MOVING_TO_REST:
            area = self.rest_area_at(agent.position)

            if area is not None:
                self.rest_agent(agent, area)
                return

            if not agent.path:
                self.send_to_rest(agent)

            self.move_one_step(agent)
            area = self.rest_area_at(agent.position)

            if area is not None:
                self.rest_agent(agent, area)

            return

        if agent.state == AgentState.MOVING_TO_TRASH:
            trash = self.get_trash(agent.target_trash_id)

            if trash is None:
                agent.clear_target()
                agent.state = AgentState.SEARCHING
                return

            if agent.position == trash.position:
                self.pickup_target(agent)
                return

            if not agent.path:
                agent.path = self.pathfinder.find_path(
                    agent.position,
                    trash.position,
                )

            if not agent.path:
                trash.reserved_by = None
                agent.clear_target()
                agent.state = AgentState.SEARCHING
                self.statistics.unreachable_targets += 1
                return

            self.move_one_step(agent)

            if agent.position == trash.position:
                self.pickup_target(agent)

            return

        if not self.trash_items and not agent.is_bag_empty():
            if self.send_to_station(agent):
                return

        target_result = self.choose_target(agent)

        if target_result is None:
            self.wander(agent)
            return

        trash, path = target_result
        trash.reserved_by = agent.agent_id
        agent.set_trash_target(trash, path)

        if agent.position == trash.position:
            self.pickup_target(agent)
        else:
            self.move_one_step(agent)

    def maintain_stations(self) -> None:
        for station in self.world.stations:
            emptied = station.maintenance()

            if emptied:
                self.add_event(
                    EventType.INFO,
                    f"{station.name}의 가득 찬 수거함 {emptied}개를 비웠습니다.",
                )

    def step(self) -> None:
        if self.finished:
            return

        if self.turn >= self.config.max_turns:
            self.finished = True
            self.running = False
            return

        self.turn += 1

        for event in self.environment.update(self.turn):
            self.events.append(event)

        if self.turn % TRASH_SPAWN_INTERVAL == 0:
            base_count = random.randint(
                TRASH_SPAWN_MIN_COUNT,
                TRASH_SPAWN_MAX_COUNT,
            )

            adjusted_count = max(
                1,
                round(base_count * self.environment.spawn_multiplier()),
            )

            self.spawn_trash(adjusted_count)

        for agent in self.agents:
            self.update_agent(agent)

        self.maintain_stations()
        self.statistics.update_from_agents(self.agents)
        self.statistics.observe_trash_count(
            self.turn,
            len(self.trash_items),
        )

        if self.turn >= self.config.max_turns:
            self.finished = True
            self.running = False
            self.add_event(
                EventType.SYSTEM,
                "최대 턴에 도달하여 시뮬레이션을 종료합니다.",
            )

    def summary_report(self) -> str:
        lines = [
            "=" * 56,
            "사람 쓰레기 수거 시뮬레이션 결과",
            "=" * 56,
            f"현재 턴: {self.turn}",
            f"현재 날씨: {self.environment.weather.display_name}",
            f"현재 시간대: {self.environment.time_period.display_name}",
            f"남은 쓰레기: {len(self.trash_items)}개",
            f"총 생성 쓰레기: {self.environment.total_spawned_trash}개",
            f"총 수거: {self.statistics.total_pickups}개",
            f"총 분리배출: {self.statistics.total_recycled}개",
            f"총점: {self.statistics.total_score}점",
            "",
            "[청소원별 결과]",
        ]

        for agent in self.agents:
            lines.append(
                (
                    f"- {agent.name}: 점수 {agent.score}, "
                    f"수거 {agent.collected_count}, "
                    f"분리배출 {agent.recycled_count}, "
                    f"이동 {agent.moved_steps}, "
                    f"휴식 {agent.rested_count}"
                )
            )

        lines.extend(
            [
                "",
                "[분리수거장별 결과]",
            ]
        )

        for station in self.world.stations:
            lines.append(
                (
                    f"- {station.name}: 처리 {station.processed_count}개, "
                    f"처리 무게 {station.processed_weight}, "
                    f"정비 {station.maintenance_count}회"
                )
            )

        lines.append("=" * 56)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": {
                "width": self.config.width,
                "height": self.config.height,
                "agent_count": self.config.agent_count,
                "initial_trash_count": self.config.initial_trash_count,
                "obstacle_count": self.config.obstacle_count,
                "station_count": self.config.station_count,
                "rest_area_count": self.config.rest_area_count,
                "max_turns": self.config.max_turns,
                "tick_delay": self.config.tick_delay,
                "random_seed": self.config.random_seed,
            },
            "turn": self.turn,
            "next_trash_id": self.next_trash_id,
            "finished": self.finished,
            "tiles": [
                [tile.name for tile in row]
                for row in self.world.tiles
            ],
            "stations": [station.to_dict() for station in self.world.stations],
            "rest_areas": [area.to_dict() for area in self.world.rest_areas],
            "agents": [agent.to_dict() for agent in self.agents],
            "trash_items": [trash.to_dict() for trash in self.trash_items.values()],
            "environment": self.environment.to_dict(),
            "statistics": self.statistics.to_dict(),
            "events": [
                {
                    "turn": event.turn,
                    "event_type": event.event_type.name,
                    "message": event.message,
                }
                for event in self.events
            ],
        }

    def save(self, path: str) -> None:
        Path(path).write_text(
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self.add_event(
            EventType.SYSTEM,
            f"시뮬레이션을 저장했습니다: {path}",
        )

    @classmethod
    def load(cls, path: str) -> "SimulationEngine":
        data = json.loads(
            Path(path).read_text(encoding="utf-8")
        )

        config_data = data.get("config", {})
        config = SimulationConfig(
            width=safe_int(config_data.get("width"), MAP_WIDTH),
            height=safe_int(config_data.get("height"), MAP_HEIGHT),
            agent_count=safe_int(config_data.get("agent_count"), DEFAULT_AGENT_COUNT),
            initial_trash_count=safe_int(
                config_data.get("initial_trash_count"),
                DEFAULT_TRASH_COUNT,
            ),
            obstacle_count=safe_int(
                config_data.get("obstacle_count"),
                DEFAULT_OBSTACLE_COUNT,
            ),
            station_count=safe_int(
                config_data.get("station_count"),
                DEFAULT_STATION_COUNT,
            ),
            rest_area_count=safe_int(
                config_data.get("rest_area_count"),
                DEFAULT_REST_AREA_COUNT,
            ),
            max_turns=safe_int(config_data.get("max_turns"), DEFAULT_MAX_TURNS),
            tick_delay=safe_int(config_data.get("tick_delay"), DEFAULT_TICK_DELAY),
            random_seed=safe_int(config_data.get("random_seed"), DEFAULT_RANDOM_SEED),
        )

        engine = cls(config)
        engine.turn = safe_int(data.get("turn"), 0)
        engine.next_trash_id = safe_int(data.get("next_trash_id"), 1)
        engine.finished = bool(data.get("finished", False))
        engine.running = False

        tile_rows = data.get("tiles", [])

        if tile_rows:
            for y, row in enumerate(tile_rows[: engine.world.height]):
                for x, tile_name in enumerate(row[: engine.world.width]):
                    try:
                        engine.world.tiles[y][x] = TileType[tile_name]
                    except KeyError:
                        engine.world.tiles[y][x] = TileType.EMPTY

        engine.world.stations = []

        for station_data in data.get("stations", []):
            station = RecyclingStation(
                station_id=safe_int(station_data.get("station_id"), 0),
                position=Position(
                    safe_int(station_data.get("x"), 0),
                    safe_int(station_data.get("y"), 0),
                ),
                name=str(station_data.get("name", "분리수거장")),
                processed_count=safe_int(
                    station_data.get("processed_count"),
                    0,
                ),
                processed_weight=safe_int(
                    station_data.get("processed_weight"),
                    0,
                ),
                maintenance_count=safe_int(
                    station_data.get("maintenance_count"),
                    0,
                ),
            )

            station.bins = {}

            for bin_data in station_data.get("bins", []):
                recycling_bin = RecyclingBin.from_dict(bin_data)
                station.bins[recycling_bin.trash_kind] = recycling_bin

            for kind in TrashKind:
                station.bins.setdefault(kind, RecyclingBin(kind))

            engine.world.stations.append(station)

        engine.world.rest_areas = []

        for area_data in data.get("rest_areas", []):
            engine.world.rest_areas.append(
                RestArea(
                    area_id=safe_int(area_data.get("area_id"), 0),
                    position=Position(
                        safe_int(area_data.get("x"), 0),
                        safe_int(area_data.get("y"), 0),
                    ),
                    name=str(area_data.get("name", "휴식 공간")),
                    recovery_amount=safe_int(
                        area_data.get("recovery_amount"),
                        REST_RECOVERY_AMOUNT,
                    ),
                    usage_count=safe_int(area_data.get("usage_count"), 0),
                    total_recovered_energy=safe_int(
                        area_data.get("total_recovered_energy"),
                        0,
                    ),
                )
            )

        engine.agents = [
            CleanerAgent.from_dict(agent_data)
            for agent_data in data.get("agents", [])
        ]

        engine.trash_items = {}

        for trash_data in data.get("trash_items", []):
            trash = Trash.from_dict(trash_data)
            engine.trash_items[trash.trash_id] = trash

        engine.environment = EnvironmentState.from_dict(
            data.get("environment", {})
        )
        engine.statistics = SimulationStatistics.from_dict(
            data.get("statistics", {})
        )

        engine.events = []

        for event_data in data.get("events", []):
            try:
                event_type = EventType[event_data.get("event_type", "INFO")]
            except KeyError:
                event_type = EventType.INFO

            engine.events.append(
                SimulationEvent(
                    turn=safe_int(event_data.get("turn"), 0),
                    event_type=event_type,
                    message=str(event_data.get("message", "")),
                )
            )

        engine.pathfinder = PathFinder(engine.world)
        engine.add_event(EventType.SYSTEM, f"저장 파일을 불러왔습니다: {path}")
        return engine


class SimulationApp:
    TILE_COLORS = {
        TileType.EMPTY: "#E8F5E9",
        TileType.WALL: "#5D4037",
        TileType.WATER: "#81D4FA",
        TileType.FLOWER: "#F8BBD0",
        TileType.STATION: "#90CAF9",
        TileType.REST_AREA: "#C5E1A5",
    }

    def __init__(
        self,
        root: tk.Tk,
    ) -> None:
        self.root = root
        self.root.title(APP_TITLE)

        self.engine = SimulationEngine()
        self.after_id: Optional[str] = None
        self.selected_agent_id: Optional[int] = None

        self.speed_var = tk.IntVar(value=self.engine.config.tick_delay)
        self.status_var = tk.StringVar(value="정지")
        self.turn_var = tk.StringVar(value="턴: 0")
        self.weather_var = tk.StringVar(value="날씨: 맑음")
        self.trash_var = tk.StringVar(value="쓰레기: 0개")

        self.build_ui()
        self.bind_events()
        self.refresh()

    def build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(top, text="시작", command=self.start).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="일시정지", command=self.pause).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="한 턴", command=self.step_once).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="초기화", command=self.reset).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="쓰레기 추가", command=self.add_trash).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="저장", command=self.save).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="불러오기", command=self.load).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="보고서", command=self.show_report).pack(side=tk.LEFT, padx=3)

        ttk.Label(top, text="속도").pack(side=tk.LEFT, padx=(18, 4))
        ttk.Scale(
            top,
            from_=20,
            to=1000,
            orient=tk.HORIZONTAL,
            variable=self.speed_var,
            length=150,
        ).pack(side=tk.LEFT)

        ttk.Label(top, textvariable=self.status_var).pack(side=tk.RIGHT, padx=8)
        ttk.Label(top, textvariable=self.trash_var).pack(side=tk.RIGHT, padx=8)
        ttk.Label(top, textvariable=self.weather_var).pack(side=tk.RIGHT, padx=8)
        ttk.Label(top, textvariable=self.turn_var).pack(side=tk.RIGHT, padx=8)

        main = ttk.Frame(self.root, padding=(8, 0, 8, 0))
        main.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            main,
            width=self.engine.config.width * CELL_SIZE,
            height=self.engine.config.height * CELL_SIZE,
            highlightthickness=1,
            highlightbackground="#999999",
        )
        self.canvas.pack(side=tk.LEFT)

        side = ttk.Frame(main, padding=(10, 0, 0, 0))
        side.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(
            side,
            text="청소원 목록",
            font=("맑은 고딕", 11, "bold"),
        ).pack(anchor=tk.W)

        self.agent_tree = ttk.Treeview(
            side,
            columns=("state", "energy", "bag", "score"),
            show="headings",
            height=9,
        )
        self.agent_tree.heading("state", text="상태")
        self.agent_tree.heading("energy", text="체력")
        self.agent_tree.heading("bag", text="가방")
        self.agent_tree.heading("score", text="점수")
        self.agent_tree.column("state", width=125)
        self.agent_tree.column("energy", width=50, anchor=tk.CENTER)
        self.agent_tree.column("bag", width=55, anchor=tk.CENTER)
        self.agent_tree.column("score", width=55, anchor=tk.CENTER)
        self.agent_tree.pack(fill=tk.X, pady=(4, 8))

        ttk.Label(
            side,
            text="상세 정보",
            font=("맑은 고딕", 11, "bold"),
        ).pack(anchor=tk.W)

        self.detail_text = tk.Text(
            side,
            width=42,
            height=15,
            wrap=tk.WORD,
            font=("맑은 고딕", 9),
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        ttk.Label(
            side,
            text="최근 이벤트",
            font=("맑은 고딕", 11, "bold"),
        ).pack(anchor=tk.W)

        self.log_text = tk.Text(
            side,
            width=42,
            height=10,
            wrap=tk.WORD,
            font=("Consolas", 8),
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

    def bind_events(self) -> None:
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.agent_tree.bind("<<TreeviewSelect>>", self.on_agent_select)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def start(self) -> None:
        if self.engine.finished:
            messagebox.showinfo(APP_TITLE, "이미 종료된 시뮬레이션입니다.")
            return

        if self.engine.running:
            return

        self.engine.running = True
        self.status_var.set("실행 중")
        self.schedule_next()

    def pause(self) -> None:
        self.engine.running = False
        self.status_var.set("일시정지")

        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def step_once(self) -> None:
        self.pause()
        self.engine.step()
        self.refresh()

    def reset(self) -> None:
        self.pause()

        if not messagebox.askyesno(APP_TITLE, "처음부터 다시 시작할까요?"):
            return

        self.engine = SimulationEngine(self.engine.config)
        self.selected_agent_id = None
        self.speed_var.set(self.engine.config.tick_delay)
        self.status_var.set("정지")
        self.refresh()

    def add_trash(self) -> None:
        created = self.engine.spawn_trash(5)
        self.engine.add_event(
            EventType.TRASH_SPAWN,
            f"사용자가 쓰레기 {created}개를 추가했습니다.",
        )
        self.refresh()

    def save(self) -> None:
        path = filedialog.asksaveasfilename(
            title="시뮬레이션 저장",
            defaultextension=".json",
            initialfile=SAVE_FILE_NAME,
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
        )

        if not path:
            return

        try:
            self.engine.save(path)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"저장 중 오류가 발생했습니다.\n{error}")
            return

        self.refresh()
        messagebox.showinfo(APP_TITLE, "저장했습니다.")

    def load(self) -> None:
        self.pause()
        path = filedialog.askopenfilename(
            title="시뮬레이션 불러오기",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
        )

        if not path:
            return

        try:
            self.engine = SimulationEngine.load(path)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"불러오기 중 오류가 발생했습니다.\n{error}")
            return

        self.selected_agent_id = None
        self.speed_var.set(self.engine.config.tick_delay)
        self.status_var.set("불러오기 완료")
        self.refresh()

    def show_report(self) -> None:
        report = self.engine.summary_report()

        report_window = tk.Toplevel(self.root)
        report_window.title("시뮬레이션 결과 보고서")

        text = tk.Text(
            report_window,
            width=75,
            height=35,
            font=("Consolas", 10),
        )
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        text.insert(tk.END, report)
        text.configure(state=tk.DISABLED)

    def schedule_next(self) -> None:
        if not self.engine.running:
            return

        delay = int(self.speed_var.get())
        self.engine.config.tick_delay = delay
        self.after_id = self.root.after(delay, self.tick)

    def tick(self) -> None:
        self.after_id = None

        if not self.engine.running:
            return

        self.engine.step()
        self.refresh()

        if self.engine.finished:
            self.status_var.set("종료")
            messagebox.showinfo(APP_TITLE, self.engine.summary_report())
            return

        self.schedule_next()

    def on_canvas_click(self, event: tk.Event) -> None:
        position = Position(
            event.x // CELL_SIZE,
            event.y // CELL_SIZE,
        )

        for agent in self.engine.agents:
            if agent.position == position:
                self.selected_agent_id = agent.agent_id
                self.refresh_detail()
                return

    def on_agent_select(self, _event: tk.Event) -> None:
        selection = self.agent_tree.selection()

        if not selection:
            return

        try:
            self.selected_agent_id = int(selection[0])
        except ValueError:
            return

        self.refresh_detail()

    def cell_bounds(
        self,
        position: Position,
    ) -> Tuple[int, int, int, int]:
        left = position.x * CELL_SIZE
        top = position.y * CELL_SIZE
        return left, top, left + CELL_SIZE, top + CELL_SIZE

    def draw(self) -> None:
        self.canvas.delete("all")
        self.canvas.configure(
            background=self.engine.environment.time_period.background_color
        )

        for y in range(self.engine.world.height):
            for x in range(self.engine.world.width):
                position = Position(x, y)
                tile = self.engine.world.tile_at(position)
                left, top, right, bottom = self.cell_bounds(position)

                self.canvas.create_rectangle(
                    left,
                    top,
                    right,
                    bottom,
                    fill=self.TILE_COLORS[tile],
                    outline="#CCCCCC",
                )

                if tile == TileType.STATION:
                    self.canvas.create_text(
                        (left + right) / 2,
                        (top + bottom) / 2,
                        text="R",
                        font=("Arial", 11, "bold"),
                    )
                elif tile == TileType.REST_AREA:
                    self.canvas.create_text(
                        (left + right) / 2,
                        (top + bottom) / 2,
                        text="H",
                        font=("Arial", 11, "bold"),
                    )
                elif tile == TileType.FLOWER:
                    self.canvas.create_text(
                        (left + right) / 2,
                        (top + bottom) / 2,
                        text="✿",
                    )

        for trash in self.engine.trash_items.values():
            left, top, right, bottom = self.cell_bounds(trash.position)

            self.canvas.create_oval(
                left + 7,
                top + 7,
                right - 7,
                bottom - 7,
                fill=trash.kind.color,
                outline="#333333",
            )

            self.canvas.create_text(
                (left + right) / 2,
                (top + bottom) / 2,
                text=trash.kind.display_name[0],
                font=("맑은 고딕", 7, "bold"),
            )

        for agent in self.engine.agents:
            left, top, right, bottom = self.cell_bounds(agent.position)
            selected = agent.agent_id == self.selected_agent_id

            self.canvas.create_oval(
                left + 3,
                top + 3,
                right - 3,
                bottom - 3,
                fill=agent.color,
                outline="#000000" if selected else "#FFFFFF",
                width=3 if selected else 2,
            )

            self.canvas.create_text(
                (left + right) / 2,
                (top + bottom) / 2,
                text=str(agent.agent_id),
                fill="#FFFFFF",
                font=("Arial", 9, "bold"),
            )

    def refresh_top(self) -> None:
        self.turn_var.set(f"턴: {self.engine.turn}")
        self.weather_var.set(
            (
                f"날씨: {self.engine.environment.weather.display_name} / "
                f"{self.engine.environment.time_period.display_name}"
            )
        )
        self.trash_var.set(f"쓰레기: {len(self.engine.trash_items)}개")

    def refresh_agents(self) -> None:
        for item in self.agent_tree.get_children():
            self.agent_tree.delete(item)

        for agent in self.engine.agents:
            self.agent_tree.insert(
                "",
                tk.END,
                iid=str(agent.agent_id),
                values=(
                    agent.state.value,
                    agent.energy,
                    f"{agent.bag.total_weight}/{agent.bag.capacity}",
                    agent.score,
                ),
            )

        if (
            self.selected_agent_id is not None
            and self.agent_tree.exists(str(self.selected_agent_id))
        ):
            self.agent_tree.selection_set(str(self.selected_agent_id))

    def refresh_detail(self) -> None:
        self.detail_text.delete("1.0", tk.END)

        selected = next(
            (
                agent
                for agent in self.engine.agents
                if agent.agent_id == self.selected_agent_id
            ),
            None,
        )

        if selected is None:
            self.detail_text.insert(
                tk.END,
                self.engine.statistics.status_text(),
            )
            return

        self.detail_text.insert(
            tk.END,
            selected.status_text() + "\n\n" + selected.bag.description(),
        )

    def refresh_log(self) -> None:
        self.log_text.delete("1.0", tk.END)

        for event in self.engine.events[-12:]:
            self.log_text.insert(tk.END, event.formatted() + "\n")

        self.log_text.see(tk.END)

    def refresh(self) -> None:
        self.draw()
        self.refresh_top()
        self.refresh_agents()
        self.refresh_detail()
        self.refresh_log()

    def close(self) -> None:
        self.pause()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()

    try:
        style = ttk.Style(root)

        if "vista" in style.theme_names():
            style.theme_use("vista")
    except tk.TclError:
        pass

    SimulationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
