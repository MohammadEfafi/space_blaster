"""
utils
=====

توابع کاربردی خالص (pure) که در چند ماژول تکرار شده بودن.

دسته‌بندی:
    • Math       — lerp, clamp, easing
    • Color      — color_lerp, color_darker, color_lighter

هیچ‌کدام به pygame یا Game وابسته نیستن — کاملاً قابل تست و reuse.
"""

from __future__ import annotations

import math


# ═══════════════════════════════════════════════════════════════════════════
#  Math helpers
# ═══════════════════════════════════════════════════════════════════════════

def lerp(a: float, b: float, t: float) -> float:
    """میان‌یابی خطی بین a و b با نسبت t (0..1)."""
    return a + (b - a) * t


def clamp(value: float, lo: float, hi: float) -> float:
    """محدود کردن مقدار به بازه‌ی [lo, hi]."""
    return max(lo, min(hi, value))


def clamp01(value: float) -> float:
    """محدود کردن به [0.0, 1.0] — برای نرمال‌سازی و آلفا."""
    return max(0.0, min(1.0, value))


# ═══════════════════════════════════════════════════════════════════════════
#  Easing functions
# ═══════════════════════════════════════════════════════════════════════════

def ease_out_cubic(t: float) -> float:
    """حرکت با شتاب اولیه، آرام در انتها (رایج‌ترین)."""
    return 1.0 - (1.0 - t) ** 3


def ease_in_cubic(t: float) -> float:
    """حرکت آرام در ابتدا، سریع در انتها."""
    return t * t * t


def ease_in_out_cubic(t: float) -> float:
    """آرام-سریع-آرام — برای transition های نرم."""
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def ease_out_back(t: float, overshoot: float = 1.70158) -> float:
    """حرکت با کمی عبور (overshoot) — برای pop-in پاورآپ‌ها."""
    if t >= 1.0:
        return 1.0
    c3 = overshoot + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + overshoot * (t - 1.0) ** 2


# ═══════════════════════════════════════════════════════════════════════════
#  Color helpers
# ═══════════════════════════════════════════════════════════════════════════

def color_lerp(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """میان‌یابی خطی بین دو رنگ."""
    return (
        int(lerp(a[0], b[0], t)),
        int(lerp(a[1], b[1], t)),
        int(lerp(a[2], b[2], t)),
    )


def color_darker(
    color: tuple[int, int, int],
    amount: int,
) -> tuple[int, int, int]:
    """کم کردن روشنایی."""
    return (
        max(0, color[0] - amount),
        max(0, color[1] - amount),
        max(0, color[2] - amount),
    )


def color_lighter(
    color: tuple[int, int, int],
    amount: int,
) -> tuple[int, int, int]:
    """افزودن روشنایی."""
    return (
        min(255, color[0] + amount),
        min(255, color[1] + amount),
        min(255, color[2] + amount),
    )


__all__ = [
    # math
    "lerp", "clamp", "clamp01",
    # easing
    "ease_out_cubic", "ease_in_cubic", "ease_in_out_cubic", "ease_out_back",
    # color
    "color_lerp", "color_darker", "color_lighter",
]