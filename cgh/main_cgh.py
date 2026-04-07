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