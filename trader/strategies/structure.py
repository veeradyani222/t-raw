"""Confirmed fractal swing points used by BOS signals and research."""
import numpy as np


def swing_points(high: np.ndarray, low: np.ndarray, window: int) -> tuple[list[int], list[int]]:
    """Fractal swings: index i is a swing high if high[i] is strictly greater
    than the `window` bars on each side (mirrored for lows). The last `window`
    bars can never qualify — they aren't confirmed yet."""
    n = len(high)
    highs, lows = [], []
    for i in range(window, n - window):
        left, right = slice(i - window, i), slice(i + 1, i + window + 1)
        if high[i] > high[left].max() and high[i] > high[right].max():
            highs.append(i)
        if low[i] < low[left].min() and low[i] < low[right].min():
            lows.append(i)
    return highs, lows
