from dataclasses import dataclass
from typing import List


@dataclass
class TemporalWindow:
    start_seconds: float
    end_seconds: float


def generate_sliding_windows(
    duration_seconds: float,
    window_duration: float = 4.0,
    stride: float = 2.0
) -> List[TemporalWindow]:
    """
    Generates overlapping sliding temporal windows over video duration.
    Ensures non-empty intervals and boundaries respecting media duration.
    """
    if duration_seconds <= 0:
        return []

    if duration_seconds <= window_duration:
        return [TemporalWindow(start_seconds=0.0, end_seconds=round(duration_seconds, 2))]

    windows: List[TemporalWindow] = []
    current_start = 0.0

    while current_start < duration_seconds:
        current_end = min(duration_seconds, current_start + window_duration)
        windows.append(
            TemporalWindow(
                start_seconds=round(current_start, 2),
                end_seconds=round(current_end, 2)
            )
        )
        if current_end >= duration_seconds:
            break
        current_start += stride

    return windows

