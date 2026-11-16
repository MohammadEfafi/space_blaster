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




def _normalize_color(
    color: tuple[int, ...],
    alpha: Optional[int],
) -> tuple[int, int, int, int]:
    """color را به RGBA نرمال کن."""
    # رنگ‌های RGB به RGBA تبدیل می‌شوند؛ رنگ‌های نامعتبر نیز به سفید کاملاً مات برمی‌گردند.
    # RGB colors are converted to RGBA; invalid color lengths fall back to fully opaque white.
    if len(color) == 4:
        c = color
    elif len(color) == 3:
        c = (*color, 255)
    else:
        c = (255, 255, 255, 255)

    # آلفای ورودی، در صورت وجود، جایگزین آلفای قبلی می‌شود و به بازه‌ی معتبر محدود می‌گردد.
    # When provided, the input alpha replaces the existing alpha and is clamped to the valid range.
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
    # برای شعاع‌های بسیار کوچک، رسم هاله متوقف می‌شود تا سطح غیرضروری ساخته نشود.
    # Skips glow rendering for very small radii to avoid creating an unnecessary surface.
    if radius < 2:
        return

    glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)

    # شدت پایه‌ی هاله با آلفای رنگ ورودی ترکیب می‌شود.
    # The glow's base intensity is multiplied by the alpha of the input color.
    base_alpha = int(intensity * (color[3] / 255.0))

    # دایره‌های هم‌مرکز با شعاع‌های کاهشی، هاله‌ای با محوشدگی تدریجی ایجاد می‌کنند.
    # Concentric circles with decreasing radii create a gradually fading glow.
    for rr in range(radius, 0, -2):
        a = int(base_alpha * (1 - rr / radius) ** 2)
        if a <= 0:
            continue
        pygame.draw.circle(
            glow, (color[0], color[1], color[2], a),
            (radius, radius), rr,
        )

    # ترکیب افزایشی، نور هاله را به سطح مقصد اضافه می‌کند.
    # Additive blending adds the glow's light to the destination surface.
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
    # Bounding area
    # مختصات نقاط برای محاسبه‌ی کوچک‌ترین مستطیل پوشاننده‌ی چندضلعی استخراج می‌شوند.
    # Extracts point coordinates to calculate the smallest rectangle enclosing the polygon.
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = int(min(xs)) - 2, int(max(xs)) + 2
    min_y, max_y = int(min(ys)) - 2, int(max(ys)) + 2
    w = max_x - min_x
    h = max_y - min_y

    # اگر محدوده ابعاد معتبری نداشته باشد، رسم چندضلعی انجام نمی‌شود.
    # Skips polygon rendering when the calculated bounds have invalid dimensions.
    if w <= 0 or h <= 0:
        return

    # سطح موقت فقط به‌اندازه‌ی محدوده‌ی چندضلعی ساخته می‌شود تا از ایجاد سطحی بزرگ‌تر جلوگیری شود.
    # Creates a temporary surface limited to the polygon bounds to avoid allocating a larger surface.
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)

    # مختصات نقاط از فضای سطح اصلی به فضای محلی سطح موقت منتقل می‌شوند.
    # Translates point coordinates from the main surface space into the temporary surface's local space.
    local = [(p[0] - min_x, p[1] - min_y) for p in points]

    # مقدار width مشخص می‌کند چندضلعی به‌صورت توپر رسم شود یا فقط خطوط پیرامونی آن نمایش داده شوند.
    # The width value determines whether the polygon is filled or only its outline is drawn.
    if width > 0:
        pygame.draw.polygon(tmp, color, local, width)
    else:
        pygame.draw.polygon(tmp, color, local)

    surface.blit(tmp, (min_x, min_y))




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
    # رنگ ورودی به RGBA تبدیل می‌شود تا رسم آیکون از آلفای مشخص‌شده پشتیبانی کند.
    # Normalizes the input color to RGBA so the icon can use the specified alpha value.
    c = _normalize_color(color, alpha)

    # در صورت فعال بودن glow، هاله پیش از خود آیکون رسم می‌شود.
    # When glow is enabled, the halo is drawn before the icon itself.
    if glow:
        _draw_glow(surface, cx, cy, size * 2, c)

    # سه رأس، مثلثی با جهت نوک به سمت راست تشکیل می‌دهند.
    # The three vertices form a triangle whose tip points to the right.
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

    # مختصات آینه‌ای فلش راست، نوک مثلث را به سمت چپ قرار می‌دهند.
    # Mirrored coordinates of the right arrow position the triangle's tip toward the left.
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

    # رأس بالایی و دو رأس پایینی، مثلث را رو به بالا می‌سازند.
    # The top vertex and two lower vertices form an upward-pointing triangle.
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

    # با جابه‌جایی رأس منفرد به پایین، جهت مثلث نسبت به فلش بالا معکوس می‌شود.
    # Moving the single vertex downward reverses the triangle's orientation relative to the upward arrow.
    pts = [
        (cx, cy + size),
        (cx - size * 0.9, cy - size * 0.6),
        (cx + size * 0.9, cy - size * 0.6),
    ]
    _draw_polygon_alpha(surface, pts, c)




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
    # از تابع فلش بالا استفاده می‌کند تا منطق رسم مثلث در یک نقطه متمرکز بماند.
    # Reuses the upward-arrow function to keep triangle rendering logic centralized.
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

    # چهار رأس بالا، راست، پایین و چپ، شکل الماس را تشکیل می‌دهند.
    # The top, right, bottom, and left vertices form the diamond shape.
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

    # رأس‌های بیرونی و داخلی جداگانه ساخته می‌شوند تا شعاع و شکل هر بخش قابل کنترل باشد.
    # Outer and inner vertices are generated separately to control the radius and shape of each section.
    outer = []
    inner = []
    for i in range(points):
        # زاویه‌ی رأس‌ها با فاصله‌ی مساوی در یک دور کامل محاسبه می‌شود.
        # Vertex angles are calculated at equal intervals around a full circle.
        a_out = rotation + i * math.tau / points
        a_in = a_out + math.pi / points

        # تبدیل مختصات قطبی به دکارتی، موقعیت هر رأس را نسبت به مرکز ستاره تعیین می‌کند.
        # Converts polar coordinates to Cartesian coordinates to position each vertex relative to the star's center.
        outer.append((
            cx + math.cos(a_out) * size,
            cy + math.sin(a_out) * size,
        ))
        inner.append((
            cx + math.cos(a_in) * size * inner_ratio,
            cy + math.sin(a_in) * size * inner_ratio,
        ))

    # رأس‌های بیرونی و داخلی به‌صورت یکی‌درمیان مرتب می‌شوند تا چندضلعی ستاره تشکیل شود.
    # Alternates outer and inner vertices to construct the star polygon.
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

    # دو دایره‌ی بالایی و یک چندضلعی پایینی، اجزای اصلی شکل قلب هستند.
    # Two upper circles and a lower polygon form the main parts of the heart.
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

    # برای رنگ‌های تقریباً مات، دایره مستقیماً روی سطح مقصد رسم می‌شود.
    # For nearly opaque colors, the circle is drawn directly onto the destination surface.
    if c[3] >= 250:
        pygame.draw.circle(surface, (c[0], c[1], c[2]), (cx, cy), size)
    else:
        # برای پشتیبانی از شفافیت، دایره روی یک سطح موقت با آلفا رسم و سپس ترکیب می‌شود.
        # To support transparency, draws the circle on a temporary alpha surface before compositing it.
        tmp = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(tmp, c, (size * 2, size * 2), size * 2)
        surface.blit(tmp, (cx - size * 2, cy - size * 2))




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

    # سه نقطه‌ی متصل، مسیر شکسته‌ی فلش رو به راست را تشکیل می‌دهند.
    # Three connected points form the angled path of the right-pointing chevron.
    pts = [
        (cx - size * 0.6, cy - size),
        (cx + size * 0.6, cy),
        (cx - size * 0.6, cy + size),
    ]

    # در حالت نیمه‌شفاف، خطوط روی سطح موقت رسم می‌شوند تا آلفا حفظ شود.
    # For semi-transparent colors, draws the lines on a temporary surface to preserve alpha.
    if c[3] < 250:
        tmp_size = size * 3
        tmp = pygame.Surface((tmp_size, tmp_size), pygame.SRCALPHA)
        local = [(p[0] - cx + tmp_size // 2, p[1] - cy + tmp_size // 2) for p in pts]
        pygame.draw.lines(tmp, c, False, local, thickness)
        surface.blit(tmp, (cx - tmp_size // 2, cy - tmp_size // 2))
    else:
        # برای رنگ‌های مات، رسم مستقیم از ساخت سطح موقت جلوگیری می‌کند.
        # For opaque colors, drawing directly avoids creating a temporary surface.
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

    # ترتیب نقاط نسبت به فلش راست معکوس شده تا نوک فلش به سمت چپ باشد.
    # Reverses the point arrangement of the right chevron so its tip faces left.
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

    # سه رتبه‌ی نخست با نمادهای هندسی متفاوت نمایش داده می‌شوند.
    # The top three ranks are represented by distinct geometric symbols.
    if rank == 1:
        draw_star(surface, cx, cy, size, c, glow=True)
    elif rank == 2:
        draw_diamond(surface, cx, cy, size, c, glow=True)
    elif rank == 3:
        draw_triangle_up(surface, cx, cy, size, c, glow=True)
    elif font is not None:
        # بقیه رتبه‌ها: شماره
        # Remaining ranks: number
        # برای رتبه‌های دیگر، در صورت ارائه‌ی فونت، مقدار عددی به‌جای نماد رسم می‌شود.
        # For other ranks, renders the numeric value instead of a symbol when a font is provided.
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