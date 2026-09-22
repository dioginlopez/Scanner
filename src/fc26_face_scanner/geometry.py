from __future__ import annotations

from math import sqrt
from typing import Iterable, Sequence


Point2D = tuple[float, float]


def distance(a: Point2D, b: Point2D) -> float:
    return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def midpoint(a: Point2D, b: Point2D) -> Point2D:
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def median(values: Iterable[float]) -> float:
    sorted_values = sorted(values)
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 1:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))
