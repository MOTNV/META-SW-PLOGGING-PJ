# ============================================================
# Trash Pickup Simulation
# Part 1 / 12
#
# 사람이 공원 안을 돌아다니며 쓰레기를 줍고,
# 분리수거장에 버리는 콘솔 기반 시뮬레이션
#
# 사용 방법:
# 1. trash_pickup_simulation.py 파일을 만든다.
# 2. Part 1부터 Part 12까지 순서대로 이어 붙인다.
# 3. python trash_pickup_simulation.py 명령으로 실행한다.
# ============================================================

from __future__ import annotations

import math
import random
import time

from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple


# ============================================================
# 시뮬레이션 기본 설정
# ============================================================

MAP_WIDTH = 30
MAP_HEIGHT = 16

MAX_TURNS = 300

INITIAL_TRASH_COUNT = 35
MAX_TRASH_COUNT = 70

TRASH_SPAWN_INTERVAL = 4
TRASH_SPAWN_MIN_COUNT = 1
TRASH_SPAWN_MAX_COUNT = 3

CLEANER_COUNT = 3

CLEANER_MAX_ENERGY = 100
CLEANER_INITIAL_ENERGY = 100
CLEANER_MOVE_ENERGY_COST = 1
CLEANER_PICKUP_ENERGY_COST = 2

CLEANER_BAG_CAPACITY = 12

REST_ENERGY_RECOVERY = 18
IDLE_ENERGY_RECOVERY = 2

RECYCLING_STATION_COUNT = 2
REST_AREA_COUNT = 2
OBSTACLE_COUNT = 35

TURN_DELAY = 0.08

RENDER_EVERY_TURN = True
SHOW_EVENT_LOG = True
EVENT_LOG_LIMIT = 8

RANDOM_SEED = 20260619


# ============================================================
# 화면에 출력할 문자
# ============================================================

EMPTY_SYMBOL = "."
OBSTACLE_SYMBOL = "#"
RECYCLING_STATION_SYMBOL = "R"
REST_AREA_SYMBOL = "H"
UNKNOWN_SYMBOL = "?"

CLEANER_SYMBOLS = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
]


# ============================================================
# 유틸리티 함수
# ============================================================

def clamp(value: int, minimum: int, maximum: int) -> int:
    """
    value가 minimum보다 작으면 minimum을 반환하고,
    maximum보다 크면 maximum을 반환한다.
    """

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


def clear_console() -> None:
    """
    콘솔 화면을 지우는 ANSI 제어문자이다.

    일부 오래된 콘솔에서는 화면이 지워지지 않을 수 있지만,
    대부분의 Windows Terminal, PowerShell, VS Code 터미널에서 작동한다.
    """

    print("\033[2J\033[H", end="")


def percentage(current: int, maximum: int) -> float:
    """
    현재 값이 최댓값의 몇 퍼센트인지 계산한다.
    """

    if maximum <= 0:
        return 0.0

    return current / maximum * 100.0


def format_bar(
    current: int,
    maximum: int,
    length: int = 10,
    fill_symbol: str = "■",
    empty_symbol: str = "□",
) -> str:
    """
    체력이나 가방 사용량을 막대 형태로 표현한다.

    예:
    ■■■■■□□□□□
    """

    if maximum <= 0:
        return empty_symbol * length

    ratio = current / maximum
    ratio = max(0.0, min(1.0, ratio))

    filled_count = round(ratio * length)
    empty_count = length - filled_count

    return fill_symbol * filled_count + empty_symbol * empty_count


def choose_random_item(items: List):
    """
    리스트에서 무작위 원소 하나를 반환한다.

    빈 리스트가 들어오면 None을 반환한다.
    """

    if not items:
        return None

    return random.choice(items)


# ============================================================
# 좌표 클래스
# ============================================================

@dataclass(frozen=True)
class Position:
    """
    맵 안에서 사용되는 2차원 좌표이다.

    frozen=True이므로 생성 후 x, y 값을 직접 변경할 수 없다.
    좌표 이동이 필요하면 moved() 메서드로 새 Position을 만든다.
    """

    x: int
    y: int

    def moved(self, dx: int, dy: int) -> "Position":
        """
        현재 좌표에서 dx, dy만큼 이동한 새 좌표를 반환한다.
        """

        return Position(
            x=self.x + dx,
            y=self.y + dy,
        )

    def distance_to(self, other: "Position") -> int:
        """
        두 좌표 사이의 맨해튼 거리를 계산한다.

        대각선 이동을 사용하지 않기 때문에
        가로 거리와 세로 거리를 더해서 계산한다.
        """

        return abs(self.x - other.x) + abs(self.y - other.y)

    def euclidean_distance_to(self, other: "Position") -> float:
        """
        두 좌표 사이의 직선거리를 계산한다.
        """

        dx = self.x - other.x
        dy = self.y - other.y

        return math.sqrt(dx * dx + dy * dy)

    def is_same(self, other: "Position") -> bool:
        """
        두 좌표가 같은 위치인지 확인한다.
        """

        return self.x == other.x and self.y == other.y

    def as_tuple(self) -> Tuple[int, int]:
        """
        Position 객체를 일반 튜플로 변환한다.
        """

        return self.x, self.y


# ============================================================
# 이동 방향
# ============================================================

class Direction(Enum):
    """
    캐릭터가 이동할 수 있는 방향이다.
    """

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)
    STAY = (0, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    def move(self, position: Position) -> Position:
        """
        입력받은 위치를 현재 방향으로 한 칸 이동시킨다.
        """

        return position.moved(
            dx=self.dx,
            dy=self.dy,
        )

    @staticmethod
    def movement_directions() -> List["Direction"]:
        """
        제자리를 제외한 실제 이동 방향만 반환한다.
        """

        return [
            Direction.UP,
            Direction.DOWN,
            Direction.LEFT,
            Direction.RIGHT,
        ]

    @staticmethod
    def random_direction(
        include_stay: bool = False,
    ) -> "Direction":
        """
        무작위 방향을 반환한다.
        """

        directions = Direction.movement_directions()

        if include_stay:
            directions.append(Direction.STAY)

        return random.choice(directions)


# ============================================================
# 쓰레기 종류
# ============================================================

class TrashType(Enum):
    """
    시뮬레이션에 등장하는 쓰레기의 종류이다.

    각 값은 다음 정보를 가진다.

    symbol:
        지도에 표시할 문자

    display_name:
        출력용 이름

    score:
        쓰레기를 올바르게 처리했을 때 얻는 점수

    weight:
        가방에서 차지하는 무게

    decomposition_turns:
        자연적으로 사라지기까지 걸리는 대략적인 턴 수
    """

    PLASTIC = (
        "p",
        "플라스틱",
        12,
        2,
        260,
    )

    CAN = (
        "c",
        "캔",
        14,
        2,
        280,
    )

    GLASS = (
        "g",
        "유리",
        18,
        4,
        350,
    )

    PAPER = (
        "a",
        "종이",
        8,
        1,
        120,
    )

    FOOD = (
        "f",
        "음식물",
        10,
        3,
        80,
    )

    GENERAL = (
        "t",
        "일반 쓰레기",
        6,
        2,
        180,
    )

    def __init__(
        self,
        symbol: str,
        display_name: str,
        score: int,
        weight: int,
        decomposition_turns: int,
    ):
        self.symbol = symbol
        self.display_name = display_name
        self.score = score
        self.weight = weight
        self.decomposition_turns = decomposition_turns

    @staticmethod
    def random_type() -> "TrashType":
        """
        쓰레기 종류별 등장 확률을 다르게 설정한다.
        """

        trash_types = [
            TrashType.PLASTIC,
            TrashType.CAN,
            TrashType.GLASS,
            TrashType.PAPER,
            TrashType.FOOD,
            TrashType.GENERAL,
        ]

        weights = [
            25,
            18,
            9,
            22,
            11,
            15,
        ]

        return random.choices(
            population=trash_types,
            weights=weights,
            k=1,
        )[0]


# ============================================================
# 분리수거 종류
# ============================================================

class RecyclingCategory(Enum):
    """
    분리수거장에서 사용하는 쓰레기 분류이다.
    """

    PLASTIC = "플라스틱"
    METAL = "금속"
    GLASS = "유리"
    PAPER = "종이"
    FOOD = "음식물"
    GENERAL = "일반"

    @staticmethod
    def from_trash_type(
        trash_type: TrashType,
    ) -> "RecyclingCategory":
        """
        TrashType을 알맞은 RecyclingCategory로 변환한다.
        """

        mapping = {
            TrashType.PLASTIC: RecyclingCategory.PLASTIC,
            TrashType.CAN: RecyclingCategory.METAL,
            TrashType.GLASS: RecyclingCategory.GLASS,
            TrashType.PAPER: RecyclingCategory.PAPER,
            TrashType.FOOD: RecyclingCategory.FOOD,
            TrashType.GENERAL: RecyclingCategory.GENERAL,
        }

        return mapping[trash_type]


# ============================================================
# 사람의 현재 행동 상태
# ============================================================

class CleanerState(Enum):
    """
    청소하는 사람이 현재 어떤 행동을 하는지 나타낸다.
    """

    SEARCHING = "쓰레기 탐색 중"
    MOVING_TO_TRASH = "쓰레기로 이동 중"
    PICKING_UP = "쓰레기 줍는 중"
    MOVING_TO_STATION = "분리수거장으로 이동 중"
    RECYCLING = "분리배출 중"
    MOVING_TO_REST = "휴식 장소로 이동 중"
    RESTING = "휴식 중"
    IDLE = "대기 중"


# ============================================================
# 시뮬레이션 이벤트 종류
# ============================================================

class EventType(Enum):
    """
    로그에 기록되는 사건의 종류이다.
    """

    INFO = "정보"
    MOVE = "이동"
    TRASH_SPAWNED = "쓰레기 생성"
    TRASH_PICKED_UP = "쓰레기 수거"
    TRASH_RECYCLED = "분리배출"
    WRONG_RECYCLING = "잘못된 분리배출"
    REST = "휴식"
    ENERGY_EMPTY = "에너지 부족"
    BAG_FULL = "가방 가득 참"
    SIMULATION_START = "시뮬레이션 시작"
    SIMULATION_END = "시뮬레이션 종료"


# ============================================================
# 시뮬레이션 이벤트 데이터
# ============================================================

@dataclass
class SimulationEvent:
    """
    시뮬레이션 중 발생한 사건 하나를 저장한다.
    """

    turn: int
    event_type: EventType
    message: str

    def formatted(self) -> str:
        """
        콘솔 출력용 문자열을 만든다.
        """

        return (
            f"[{self.turn:03d}턴]"
            f"[{self.event_type.value}] "
            f"{self.message}"
        )


# ============================================================
# Part 1 끝
# 다음 코드는 이 아래에 그대로 이어 붙이면 된다.
# ============================================================