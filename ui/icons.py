"""
ui/icons.py
===========

مجموعه‌ی آیکون‌های برداری (Vector Icons) برای SPACE BLASTER.

چرا این فایل؟
    فونت‌های معمولی (consolas, bahnschrift) کاراکترهایی مثل ▶ ◀ ★ ◆ ▲
    را پشتیبانی نمی‌کنند و pygame به‌جای آن‌ها «مربع خالی» (tofu) نشان
    می‌دهد. این فایل همان آیکون‌ها را با pygame.draw می‌کشد تا در هر
    فونت و سیستمی درست نمایش داده شوند.

توابع اصلی:
    draw_arrow_right / draw_arrow_left / draw_arrow_up / draw_arrow_down
    draw_triangle_up / draw_diamond / draw_star / draw_heart
    draw_dot
    draw_chevron_right / draw_chevron_left

همه‌ی توابع:
    • position (x, y) = مرکز آیکون
    • size = اندازه (شعاع تقریبی)
    • color = tuple RGB یا RGBA
    • alpha = اگر داده شود، روی color اعمال می‌شود
    • glow = اگر True باشد، هاله‌ی نرم هم می‌کشد
"""

from __future__ import annotations

import math
from typing import Optional

import pygame


# ═══════════════════════════════════════════════════════════════════════════
#  کمکی
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_color(
    color: tuple[int, ...],
    alpha: Optional[int],
) -> tuple[int, int, int, int]:
    """color را به RGBA نرمال کن."""
    if len(color) == 4:
        c = color
    elif len(color) == 3:
        c = (*color, 255)
    else:
        c = (255, 255, 255, 255)

    if alpha is not None:
        c = (c[0], c[1], c[2], max(0, min(255, alpha)))
    return c


def _draw_glow(
    surface: pygame.Surface,
    cx: int, cy: int,
    radius: int,
    color: tuple[int, int, int, int],
    intensity: int = 40,
) -> None:
    """هاله‌ی نرم دایره‌ای پشت آیکون."""
    if radius < 2:
        return
    glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    base_alpha = int(intensity * (color[3] / 255.0))
    for rr in range(radius, 0, -2):
        a = int(base_alpha * (1 - rr / radius) ** 2)
        if a <= 0:
            continue
        pygame.draw.circle(
            glow, (color[0], color[1], color[2], a),
            (radius, radius), rr,
        )
    surface.blit(
        glow, (cx - radius, cy - radius),
        special_flags=pygame.BLEND_RGBA_ADD,
    )


def _draw_polygon_alpha(
    surface: pygame.Surface,
    points: list[tuple[float, float]],
    color: tuple[int, int, int, int],
    width: int = 0,
) -> None:
    """
    رسم چندضلعی با آلفا.
    pygame.draw.polygon آلفا را نادیده می‌گیرد، پس روی سطح موقت می‌کشیم.
    """
    # محدوده
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = int(min(xs)) - 2, int(max(xs)) + 2
    min_y, max_y = int(min(ys)) - 2, int(max(ys)) + 2
    w = max_x - min_x
    h = max_y - min_y

    if w <= 0 or h <= 0:
        return

    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    local = [(p[0] - min_x, p[1] - min_y) for p in points]

    if width > 0:
        pygame.draw.polygon(tmp, color, local, width)
    else:
        pygame.draw.polygon(tmp, color, local)

    surface.blit(tmp, (min_x, min_y))


# ═══════════════════════════════════════════════════════════════════════════
#  فلش‌های مثلثی
# ═══════════════════════════════════════════════════════════════════════════

def draw_arrow_right(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 8,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """مثلث رو به راست: ▶"""
    c = _normalize_color(color, alpha)
    if glow:
        _draw_glow(surface, cx, cy, size * 2, c)

    pts = [
        (cx - size * 0.5, cy - size),
        (cx + size * 0.8, cy),
        (cx - size * 0.5, cy + size),
    ]
    _draw_polygon_alpha(surface, pts, c)


def draw_arrow_left(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 8,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """مثلث رو به چپ: ◀"""
    c = _normalize_color(color, alpha)
    if glow:
        _draw_glow(surface, cx, cy, size * 2, c)

    pts = [
        (cx + size * 0.5, cy - size),
        (cx - size * 0.8, cy),
        (cx + size * 0.5, cy + size),
    ]
    _draw_polygon_alpha(surface, pts, c)


def draw_arrow_up(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 8,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """مثلث رو به بالا: ▲"""
    c = _normalize_color(color, alpha)
    if glow:
        _draw_glow(surface, cx, cy, size * 2, c)

    pts = [
        (cx, cy - size),
        (cx - size * 0.9, cy + size * 0.6),
        (cx + size * 0.9, cy + size * 0.6),
    ]
    _draw_polygon_alpha(surface, pts, c)


def draw_arrow_down(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 8,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """مثلث رو به پایین: ▼"""
    c = _normalize_color(color, alpha)
    if glow:
        _draw_glow(surface, cx, cy, size * 2, c)

    pts = [
        (cx, cy + size),
        (cx - size * 0.9, cy - size * 0.6),
        (cx + size * 0.9, cy - size * 0.6),
    ]
    _draw_polygon_alpha(surface, pts, c)


# ═══════════════════════════════════════════════════════════════════════════
#  نمادهای رتبه
# ═══════════════════════════════════════════════════════════════════════════

def draw_triangle_up(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 8,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """مثلث متساوی‌الاضلاع رو به بالا: ▲"""
    draw_arrow_up(surface, cx, cy, size, color, alpha=alpha, glow=glow)


def draw_diamond(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 8,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """الماس: ◆"""
    c = _normalize_color(color, alpha)
    if glow:
        _draw_glow(surface, cx, cy, size * 2, c)

    pts = [
        (cx, cy - size),
        (cx + size, cy),
        (cx, cy + size),
        (cx - size, cy),
    ]
    _draw_polygon_alpha(surface, pts, c)


def draw_star(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 10,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    points: int = 5,
    inner_ratio: float = 0.45,
    rotation: float = -math.pi / 2,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """ستاره‌ی چند پر: ★ (پیش‌فرض ۵ پر)"""
    c = _normalize_color(color, alpha)
    if glow:
        _draw_glow(surface, cx, cy, int(size * 1.8), c)

    outer = []
    inner = []
    for i in range(points):
        a_out = rotation + i * math.tau / points
        a_in = a_out + math.pi / points
        outer.append((
            cx + math.cos(a_out) * size,
            cy + math.sin(a_out) * size,
        ))
        inner.append((
            cx + math.cos(a_in) * size * inner_ratio,
            cy + math.sin(a_in) * size * inner_ratio,
        ))

    star = []
    for i in range(points):
        star.append(outer[i])
        star.append(inner[i])

    _draw_polygon_alpha(surface, star, c)


def draw_heart(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 10,
    color: tuple[int, ...] = (255, 70, 70),
    *,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """قلب: ♥"""
    c = _normalize_color(color, alpha)
    if glow:
        _draw_glow(surface, cx, cy, int(size * 1.5), c)

    offset = size // 2
    # دو دایره
    pygame.draw.circle(surface, c, (cx - offset, cy - offset // 2), size // 2 + 1)
    pygame.draw.circle(surface, c, (cx + offset, cy - offset // 2), size // 2 + 1)
    # مثلث پایین
    pts = [
        (cx - size + 1, cy - offset // 2 + 2),
        (cx + size - 1, cy - offset // 2 + 2),
        (cx, cy + size),
    ]
    _draw_polygon_alpha(surface, pts, c)


# ═══════════════════════════════════════════════════════════════════════════
#  نقطه
# ═══════════════════════════════════════════════════════════════════════════

def draw_dot(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 3,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """نقطه‌ی دایره‌ای: ·"""
    c = _normalize_color(color, alpha)
    if glow:
        _draw_glow(surface, cx, cy, size * 3, c)

    if c[3] >= 250:
        pygame.draw.circle(surface, (c[0], c[1], c[2]), (cx, cy), size)
    else:
        tmp = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(tmp, c, (size * 2, size * 2), size * 2)
        surface.blit(tmp, (cx - size * 2, cy - size * 2))


# ═══════════════════════════════════════════════════════════════════════════
#  chevron (فلش تیزتر — شبیه >)
# ═══════════════════════════════════════════════════════════════════════════

def draw_chevron_right(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 8,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    thickness: int = 2,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """فلش تیز رو به راست: >"""
    c = _normalize_color(color, alpha)
    if glow:
        _draw_glow(surface, cx, cy, size * 2, c)

    pts = [
        (cx - size * 0.6, cy - size),
        (cx + size * 0.6, cy),
        (cx - size * 0.6, cy + size),
    ]

    if c[3] < 250:
        tmp_size = size * 3
        tmp = pygame.Surface((tmp_size, tmp_size), pygame.SRCALPHA)
        local = [(p[0] - cx + tmp_size // 2, p[1] - cy + tmp_size // 2) for p in pts]
        pygame.draw.lines(tmp, c, False, local, thickness)
        surface.blit(tmp, (cx - tmp_size // 2, cy - tmp_size // 2))
    else:
        pygame.draw.lines(
            surface, (c[0], c[1], c[2]), False, pts, thickness,
        )


def draw_chevron_left(
    surface: pygame.Surface,
    cx: int, cy: int,
    size: int = 8,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    thickness: int = 2,
    alpha: Optional[int] = None,
    glow: bool = False,
) -> None:
    """فلش تیز رو به چپ: <"""
    c = _normalize_color(color, alpha)
    if glow:
        _draw_glow(surface, cx, cy, size * 2, c)

    pts = [
        (cx + size * 0.6, cy - size),
        (cx - size * 0.6, cy),
        (cx + size * 0.6, cy + size),
    ]

    if c[3] < 250:
        tmp_size = size * 3
        tmp = pygame.Surface((tmp_size, tmp_size), pygame.SRCALPHA)
        local = [(p[0] - cx + tmp_size // 2, p[1] - cy + tmp_size // 2) for p in pts]
        pygame.draw.lines(tmp, c, False, local, thickness)
        surface.blit(tmp, (cx - tmp_size // 2, cy - tmp_size // 2))
    else:
        pygame.draw.lines(
            surface, (c[0], c[1], c[2]), False, pts, thickness,
        )


# ═══════════════════════════════════════════════════════════════════════════
#  کمکی: رسم رتبه (شماره + آیکون)
# ═══════════════════════════════════════════════════════════════════════════

def draw_rank_badge(
    surface: pygame.Surface,
    cx: int, cy: int,
    rank: int,
    size: int = 10,
    color: tuple[int, ...] = (255, 255, 255),
    *,
    alpha: Optional[int] = None,
    font: Optional[pygame.font.Font] = None,
) -> None:
    """
    آیکون رتبه را رسم می‌کند:
        1 → ستاره
        2 → الماس
        3 → مثلث رو به بالا
    """
    c = _normalize_color(color, alpha)

    if rank == 1:
        draw_star(surface, cx, cy, size, c, glow=True)
    elif rank == 2:
        draw_diamond(surface, cx, cy, size, c, glow=True)
    elif rank == 3:
        draw_triangle_up(surface, cx, cy, size, c, glow=True)
    elif font is not None:
        # بقیه رتبه‌ها: شماره
        img = font.render(str(rank), True, (c[0], c[1], c[2]))
        if c[3] < 255:
            img.set_alpha(c[3])
        surface.blit(img, img.get_rect(center=(cx, cy)))


__all__ = [
    "draw_arrow_right", "draw_arrow_left",
    "draw_arrow_up", "draw_arrow_down",
    "draw_triangle_up",
    "draw_diamond", "draw_star", "draw_heart",
    "draw_dot",
    "draw_chevron_right", "draw_chevron_left",
    "draw_rank_badge",
]