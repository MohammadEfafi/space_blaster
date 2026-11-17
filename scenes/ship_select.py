"""
scenes/ship_select.py
=====================

صفحه‌ی انتخاب سفینه — نسخه‌ی بازطراحی‌شده.

چیدمان دو-ستونی:
    • چپ: قاب هگزاگونال با پیش‌نمایش زنده‌ی سفینه + ذرات چرخان
    • راست: نام، نقش، توضیحات، نوارهای آمار
    • پایین: ناوبری با ← →، دکمه‌ی SELECT، BACK

ویژگی‌ها:
    • قاب هگزاگونال با گوشه‌های تیز (سیلوئت sci-fi)
    • ذرات چرخان دور قاب با رنگ سفینه
    • نام سفینه با درخشش (بدون جعبه)
    • نوارهای آمار با گرادیان و گوشه‌ی گرد
    • انیمیشن تعویض نرم (اسلاید + fade)
    • کاملاً ریسپانسیو بر اساس W و H
"""

from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from core import settings as S
from entities.player.registry import (
    DEFAULT_SHIP_KEY,
    SHIP_CLASSES,
    SHIP_INFO,
    SHIP_LIST,
    next_ship_key,
    prev_ship_key,
)
from scenes.base import Scene


W = S.Window.WIDTH
H = S.Window.HEIGHT

# نسبت‌های کلیدی صفحه
# موقعیت اجزای رابط کاربری از ابعاد پنجره محاسبه می‌شود تا چیدمان با رزولوشن سازگار بماند.
# UI element positions are calculated from the window dimensions to keep the layout resolution-independent.
TITLE_Y      = int(H * 0.10)             # ۶۵ از ۶۵۰
DIVIDER_Y    = int(H * 0.16)             # ۱۰۴

# ستون چپ (پیش‌نمایش)
PREVIEW_CX   = int(W * 0.26)             # ۲۳۴
PREVIEW_CY   = int(H * 0.55)             # ۳۵۷
FRAME_R      = int(min(W, H) * 0.20)     # ۱۳۰

# ستون راست (اطلاعات)
INFO_X       = int(W * 0.50)             # ۴۵۰
INFO_W       = int(W * 0.46)             # ۴۱۴

NAME_Y       = int(H * 0.24)             # ۱۵۶
ROLE_Y       = int(H * 0.31)             # ۲۰۱
DESC_Y       = int(H * 0.38)             # ۲۴۷
STATS_TOP    = int(H * 0.47)             # ۳۰۵
STATS_ROW_H  = int(H * 0.062)            # ۴۰
STATS_BAR_W  = int(INFO_W * 0.70)
STATS_BAR_H  = 9

# پایین
BTN_Y        = int(H * 0.88)             # ۵۷۲
BTN_W        = 180
BTN_H        = 48
BTN_GAP      = 70

HINT_Y       = H - 20


# درون‌یابی خطی برای حرکت تدریجی مقادیر بین دو نقطه.
# Linear interpolation smoothly moves a value between two endpoints.
def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# هر کانال رنگ به‌صورت جداگانه درون‌یابی می‌شود تا یک رنگ میانی ساخته شود.
# Each color channel is interpolated independently to produce an intermediate color.
def _color_lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(_lerp(a[0], b[0], t)),
        int(_lerp(a[1], b[1], t)),
        int(_lerp(a[2], b[2], t)),
    )


# منحنی ease-out باعث می‌شود انیمیشن در ابتدا سریع‌تر و در انتها آرام‌تر شود.
# The ease-out curve makes the animation start quickly and slow down toward the end.
def _ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


class _StatBar:
    def __init__(self, label: str, value: int) -> None:
        self.label = label
        self.target = float(value)
        self.displayed = float(value)
        self._flash = 0.0    # وقتی تغییر می‌کنه، فلاش کوتاه

    def update(self, dt: float, new_target: int) -> None:
        # تغییر مقدار هدف، افکت فلاش کوتاه نوار را فعال می‌کند.
        # Changing the target value triggers a brief flash effect on the bar.
        if new_target != int(self.target):
            self._flash = 1.0
        self.target = float(new_target)

        # مقدار نمایشی با سرعت محدود به مقدار هدف نزدیک می‌شود.
        # The displayed value gradually approaches the target at a frame-rate-independent rate.
        diff = self.target - self.displayed
        if abs(diff) < 0.01:
            self.displayed = self.target
        else:
            self.displayed += diff * min(1.0, dt * 8.0)

        if self._flash > 0:
            self._flash = max(0.0, self._flash - dt * 3.0)

    def draw(
        self,
        surface: pygame.Surface,
        x: int, y: int,
        width: int, bar_height: int,
        font: pygame.font.Font,
        accent: tuple[int, int, int],
    ) -> None:
        # ---- برچسب ----
        label_img = font.render(self.label, True, (160, 175, 200))
        surface.blit(label_img, (x, y))

        # ---- نوار ----
        bar_x = x + 110
        bar_w = width - 110 - 60
        bar_y = y + 4

        # پس‌زمینه
        bg_surf = pygame.Surface((bar_w, bar_height), pygame.SRCALPHA)
        pygame.draw.rect(
            bg_surf, (15, 22, 38, 230),
            bg_surf.get_rect(), border_radius=bar_height // 2,
        )
        surface.blit(bg_surf, (bar_x, bar_y))

        # حاشیه‌ی ظریف
        pygame.draw.rect(
            surface, (40, 55, 80),
            (bar_x, bar_y, bar_w, bar_height),
            1, border_radius=bar_height // 2,
        )

        # نوار پرشده با گرادیان
        # مقدار نمایش‌داده‌شده به بازه‌ی صفر تا یک محدود می‌شود تا طول نوار از محدوده خارج نشود.
        # The displayed value is clamped to the zero-to-one range so the fill stays within the bar.
        ratio = max(0.0, min(1.0, self.displayed / 5.0))
        filled = int(bar_w * ratio)
        if filled > 0:
            fill_surf = pygame.Surface((filled, bar_height), pygame.SRCALPHA)

            # گرادیان افقی: تیره‌تر در چپ، روشن‌تر در راست
            # The horizontal gradient transitions from a darker shade on the left to a brighter one on the right.
            dark = (max(0, accent[0] - 60), max(0, accent[1] - 60), max(0, accent[2] - 60))
            for i in range(filled):
                t = i / max(1, filled - 1)
                c = _color_lerp(dark, accent, t)
                pygame.draw.line(fill_surf, (*c, 255), (i, 0), (i, bar_height))

            # رندر با گوشه‌ی گرد
            # A rounded mask clips the gradient to give the filled section rounded corners.
            rounded = pygame.Surface((filled, bar_height), pygame.SRCALPHA)
            pygame.draw.rect(
                rounded, (255, 255, 255, 255),
                rounded.get_rect(), border_radius=bar_height // 2,
            )
            fill_surf.blit(rounded, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(fill_surf, (bar_x, bar_y))

        # ---- عدد ----
        val_img = font.render(f"{int(round(self.displayed))}", True, accent)
        surface.blit(val_img, (bar_x + bar_w + 12, y))


class _Button:
    def __init__(
        self,
        label: str,
        action,
        cx: int, cy: int,
        *,
        width: int = BTN_W,
        height: int = BTN_H,
        accent: tuple[int, int, int] = (60, 220, 255),
    ) -> None:
        self.label = label
        self.action = action
        self.accent = accent
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (cx, cy)
        self.hovered = False
        self._t = 0.0
        self._hover = 0.0
        self._click = 0.0

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        self._t += dt
        self.hovered = self.rect.collidepoint(mouse_pos)

        # مقدار hover به‌صورت تدریجی به وضعیت جدید نزدیک می‌شود.
        # The hover amount gradually approaches its new target state.
        target = 1.0 if self.hovered else 0.0
        self._hover += (target - self._hover) * min(1.0, dt * 12.0)

        if self._click > 0:
            self._click = max(0.0, self._click - dt * 4.0)

    def trigger(self) -> None:
        self._click = 1.0
        self.action()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.trigger()
                return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        # محدوده‌ی دکمه هنگام hover کمی بزرگ‌تر می‌شود تا حس واکنش‌پذیری ایجاد کند.
        # The button expands slightly while hovered to create a responsive visual effect.
        pad_x = int(6 * self._hover)
        pad_y = int(3 * self._hover)
        rect = self.rect.inflate(pad_x * 2, pad_y * 2)

        # پس‌زمینه
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        alpha = int(50 + 90 * self._hover)
        pygame.draw.rect(bg, (*self.accent, alpha // 3), bg.get_rect(), border_radius=8)
        surface.blit(bg, rect.topleft)

        # حاشیه‌ی درخشان
        border_a = int(180 + 75 * self._hover)
        border = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            border, (*self.accent, border_a),
            border.get_rect(), 2, border_radius=8,
        )
        surface.blit(border, rect.topleft)

        # درخشش روی hover
        if self._hover > 0.05:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                glow, (*self.accent, int(70 * self._hover)),
                glow.get_rect(), 0, border_radius=8,
            )
            surface.blit(glow, rect.topleft)

        # متن
        text_color = S.Palette.WHITE if self.hovered else S.Palette.HUD_TEXT
        img = font.render(self.label, True, text_color)
        tr = img.get_rect(center=rect.center)
        shadow = font.render(self.label, True, (0, 0, 0))
        surface.blit(shadow, (tr.x + 2, tr.y + 2))
        surface.blit(img, tr)

        # فلاش
        if self._click > 0.01:
            flash = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                flash, (255, 255, 255, int(120 * self._click)),
                flash.get_rect(), 0, border_radius=8,
            )
            surface.blit(flash, rect.topleft)


class ShipSelectScene(Scene):

    TRANSITION_TIME = 0.22
    PREVIEW_SCALE   = 2.4

    def on_enter(self) -> None:
        # ---- فونت‌ها ----
        self.font_title  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.BIG, bold=True)
        self.font_name   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.LARGE, bold=True)
        self.font_role   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)
        self.font_stat   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)
        self.font_desc   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL)
        self.font_btn    = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.NORMAL, bold=True)
        self.font_hint   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.TINY)
        self.font_num    = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)

        # ---- سفینه ----
        self.current_key = getattr(self.game, "selected_ship", DEFAULT_SHIP_KEY)
        if self.current_key not in SHIP_LIST:
            self.current_key = DEFAULT_SHIP_KEY

        # ---- نمونه‌ی پیش‌نمایش ----
        # نمونه‌ی جداگانه‌ای از هر سفینه ساخته می‌شود تا هنگام جابه‌جایی، نیازی به ساخت مجدد آن نباشد.
        # A separate instance is created for each ship so switching previews does not require recreating it.
        self._preview_cache: dict = {}
        for key in SHIP_LIST:
            try:
                ship = SHIP_CLASSES[key](scene=None)
                ship.radius = ship.RADIUS * self.PREVIEW_SCALE

                # وضعیت‌های وابسته به گیم‌پلی غیرفعال می‌شوند تا پیش‌نمایش بدون افکت‌های موقتی نمایش داده شود.
                # Gameplay-related states are disabled so the preview remains free of temporary effects.
                ship.invuln_time = 0.0
                ship.powerup_time = 0.0
                ship.muzzle_flash = 0.0
                ship.recoil = 0.0
                ship.vx = 0.0
                ship.vy = 0.0
                self._preview_cache[key] = ship
            except Exception as exc:
                print(f"[ShipSelect] preview failed for {key}: {exc}")
                self._preview_cache[key] = None

        # ---- نوارهای آمار ----
        info = SHIP_INFO[self.current_key]
        self.stats = [
            _StatBar("SPEED",   info.speed),
            _StatBar("HP",      info.hp),
            _StatBar("FIRE",    info.fire_rate),
            _StatBar("DAMAGE",  info.damage),
            _StatBar("AGILITY", info.agility),
        ]

        # ---- انیمیشن ----
        self._transition_t = 1.0
        self._transition_dir = 1
        self._color_curr = tuple(float(c) for c in info.color)
        self._color_target = info.color
        self._accent = info.color

        # ---- ذرات چرخان دور قاب ----
        # ذرات با زاویه‌های اولیه‌ی یکنواخت روی یک حلقه توزیع می‌شوند، اما سرعت و ظاهرشان تصادفی است.
        # Particles are evenly distributed around a ring initially, while their speeds and appearances are randomized.
        self._ring_dots: list[dict] = [
            {
                "angle": (i / 24) * math.tau,
                "speed": random.uniform(0.35, 0.55),
                "size": random.uniform(1.5, 3.0),
                "phase": random.uniform(0, math.tau),
            }
            for i in range(24)
        ]

        # ---- ستاره‌های پس‌زمینه ----
        # موقعیت، سرعت و اندازه‌ی هر ستاره مستقل انتخاب می‌شود تا پس‌زمینه یکنواخت به نظر نرسد.
        # Each star receives an independent position, speed, and size to avoid a uniform-looking background.
        self.stars = [
            [
                random.uniform(0, W),
                random.uniform(0, H),
                random.uniform(S.FxCfg.STAR_SPEED_MIN, S.FxCfg.STAR_SPEED_MAX),
                random.uniform(0.6, 2.0),
            ]
            for _ in range(120)
        ]

        # ---- دکمه‌ها ----
        cx = W // 2
        self.btn_back = _Button(
            "BACK", self._go_back,
            cx - BTN_W // 2 - BTN_GAP, BTN_Y,
            accent=(120, 140, 180),
        )
        self.btn_select = _Button(
            "SELECT", self._confirm_select,
            cx + BTN_W // 2 + BTN_GAP, BTN_Y,
            accent=info.color,
        )

        self.audio = getattr(self.game, "audio", None)
        self._input_lock = False

    def on_exit(self) -> None:
        self._preview_cache.clear()


    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._switch(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._switch(+1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._confirm_select()
            elif event.key == pygame.K_ESCAPE:
                self._go_back()
            return

        # رویداد کلیک به هر دو دکمه ارسال می‌شود و پس از پردازش توسط یکی از آن‌ها متوقف می‌شود.
        # Mouse events are passed to both buttons and stop once one of them handles the event.
        for b in (self.btn_back, self.btn_select):
            if b.handle_event(event):
                break

    def _switch(self, direction: int) -> None:
        # تا پایان انیمیشن تعویض، ورودی جدید پذیرفته نمی‌شود تا انتقال‌ها روی هم نیفتند.
        # New input is blocked until the switching animation finishes, preventing overlapping transitions.
        if self._input_lock:
            return
        self._input_lock = True
        self._transition_dir = direction
        self._transition_t = 0.0

        # جهت حرکت، سفینه‌ی بعدی یا قبلی را مشخص می‌کند.
        # The direction determines whether the next or previous ship is selected.
        if direction > 0:
            self.current_key = next_ship_key(self.current_key)
        else:
            self.current_key = prev_ship_key(self.current_key)

        info = SHIP_INFO[self.current_key]
        self._color_target = info.color
        self.btn_select.accent = info.color
        self._play_ui("ui_move")


    def update(self, dt: float) -> None:
        # ---- انیمیشن تعویض ----
        if self._transition_t < 1.0:
            self._transition_t = min(1.0, self._transition_t + dt / self.TRANSITION_TIME)
        else:
            self._input_lock = False

        # ---- ستاره‌ها ----
        # ستاره‌ها با سرعت اختصاصی خود به پایین حرکت می‌کنند و پس از خروج از صفحه از بالا بازمی‌گردند.
        # Stars move downward at their individual speeds and return from the top after leaving the screen.
        for st in self.stars:
            st[1] += st[2] * dt
            if st[1] > H + 4:
                st[1] = -4
                st[0] = random.uniform(0, W)

        # ---- نوار آمار ----
        info = SHIP_INFO[self.current_key]
        targets = [info.speed, info.hp, info.fire_rate, info.damage, info.agility]
        for bar, t in zip(self.stats, targets):
            bar.update(dt, t)

        # ---- رنگ lerp ----
        # رنگ فعلی به‌تدریج به رنگ سفینه‌ی انتخاب‌شده نزدیک می‌شود تا تغییر رنگ ناگهانی نباشد.
        # The current color gradually approaches the selected ship's color to avoid abrupt color changes.
        blend = min(1.0, dt * 8.0)
        self._color_curr = tuple(
            c + (t - c) * blend
            for c, t in zip(self._color_curr, self._color_target)
        )
        self._accent = tuple(int(c) for c in self._color_curr)

        # ---- دکمه‌ها ----
        mouse_pos = pygame.mouse.get_pos()
        self.btn_back.update(dt, mouse_pos)
        self.btn_select.update(dt, mouse_pos)


    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(S.Palette.BG_DEEP)

        # ---- ستاره‌ها ----
        for x, y, _, r in self.stars:
            pygame.draw.circle(surface, S.Palette.STAR_FAR,
                               (int(x), int(y)), max(1, int(r)))

        # ---- هاله‌ی پس‌زمینه ----
        self._draw_background_glow(surface)

        # ---- عنوان ----
        self._draw_title(surface)

        # ---- قاب + سفینه ----
        self._draw_ship_frame(surface)

        # ---- اطلاعات (سمت راست) ----
        self._draw_info_panel(surface)

        # ---- فلش‌ها ----
        self._draw_arrows(surface)

        # ---- دکمه‌ها ----
        self.btn_back.draw(surface, self.font_btn)
        self.btn_select.draw(surface, self.font_btn)

        # ---- راهنما ----
        self._draw_hint(surface)

    # ── هاله‌ی پس‌زمینه ──
    def _draw_background_glow(self, surface: pygame.Surface) -> None:
        # هاله‌ی چپ (زیر قاب)
        r = 320
        cx = PREVIEW_CX + math.sin(self.time * 0.3) * 20
        cy = PREVIEW_CY + math.cos(self.time * 0.25) * 15
        halo = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)

        # دایره‌های هم‌مرکز با آلفای تدریجی، هاله‌ای نرم و بدون لبه‌ی مشخص ایجاد می‌کنند.
        # Concentric circles with gradually changing alpha create a soft glow without a visible edge.
        for rr in range(r, 0, -10):
            a = int(5 * (1 - rr / r) ** 1.5)
            if a <= 0:
                continue
            pygame.draw.circle(halo, (*self._accent, a), (r, r), rr)
        surface.blit(halo, (int(cx - r), int(cy - r)),
                     special_flags=pygame.BLEND_RGBA_ADD)

    # ── عنوان بالا ──
    def _draw_title(self, surface: pygame.Surface) -> None:
        cx = W // 2
        pulse = 1.0 + 0.02 * math.sin(self.time * 2.5)

        # مقیاس عنوان با تابع سینوسی کمی تغییر می‌کند تا پالس ظریفی ایجاد شود.
        # The title scale changes slightly with a sine wave to create a subtle pulse.
        img = self.font_title.render("SELECT YOUR SHIP", True, self._accent)
        w = int(img.get_width() * pulse)
        h = int(img.get_height() * pulse)
        img_s = pygame.transform.smoothscale(img, (w, h))

        # هاله
        for layer in range(3, 0, -1):
            g = pygame.transform.smoothscale(img, (w + layer * 10, h + layer * 10))
            gs = pygame.Surface(g.get_size(), pygame.SRCALPHA)
            gs.blit(g, (0, 0))
            gs.set_alpha(28 - layer * 6)
            surface.blit(gs, gs.get_rect(center=(cx, TITLE_Y)),
                         special_flags=pygame.BLEND_RGBA_ADD)

        surface.blit(img_s, img_s.get_rect(center=(cx, TITLE_Y)))

        # خط تزئینی زیر عنوان (بدون متن اضافی)
        line_w = int(W * 0.42)
        line_y = DIVIDER_Y

        # شفافیت خط در مرکز بیشترین مقدار را دارد و به سمت دو انتها کاهش می‌یابد.
        # The line is most opaque at the center, with its opacity fading toward both ends.
        for i in range(line_w):
            t = i / line_w
            a = int(120 * math.sin(math.pi * t))
            x = cx - line_w // 2 + i
            pygame.draw.line(surface, (*self._accent, a),
                             (x, line_y), (x, line_y + 1))

    # ── قاب هگزاگونال + سفینه ──
    def _draw_ship_frame(self, surface: pygame.Surface) -> None:
        cx = PREVIEW_CX
        cy = PREVIEW_CY
        r = FRAME_R

        # ---- هگزاگونال پس‌زمینه ----
        # شش رأس با فاصله‌ی زاویه‌ای برابر، شکل هندسی قاب را تشکیل می‌دهند.
        # Six vertices with equal angular spacing define the hexagonal frame.
        hex_points = [
            (cx + math.cos(-math.pi / 2 + i * math.tau / 6) * (r + 14),
             cy + math.sin(-math.pi / 2 + i * math.tau / 6) * (r + 14))
            for i in range(6)
        ]

        # پس‌زمینه‌ی تیره
        hex_bg = pygame.Surface((int(r * 3), int(r * 3)), pygame.SRCALPHA)
        local_hex = [(p[0] - cx + r * 1.5, p[1] - cy + r * 1.5) for p in hex_points]
        pygame.draw.polygon(hex_bg, (10, 15, 28, 200), local_hex)
        surface.blit(hex_bg, (int(cx - r * 1.5), int(cy - r * 1.5)))

        # ---- حاشیه‌ی نئونی هگزاگونال (با پالس) ----
        pulse = 0.7 + 0.3 * math.sin(self.time * 2.5)
        border_alpha = int(180 * pulse + 60)
        border_surf = pygame.Surface((int(r * 3), int(r * 3)), pygame.SRCALPHA)
        pygame.draw.polygon(border_surf, (*self._accent, border_alpha), local_hex, 2)
        surface.blit(border_surf, (int(cx - r * 1.5), int(cy - r * 1.5)))

        # ---- گوشه‌های تیز (corner brackets) ----
        for i in range(6):
            a = -math.pi / 2 + i * math.tau / 6

            # نقطه‌ی رأس هگزاگونال
            vx = cx + math.cos(a) * (r + 14)
            vy = cy + math.sin(a) * (r + 14)

            # دو نقطه‌ی کناری برای کشیدن براکت
            a1 = a - 0.28
            a2 = a + 0.28
            p1 = (cx + math.cos(a1) * (r + 14), cy + math.sin(a1) * (r + 14))
            p2 = (cx + math.cos(a2) * (r + 14), cy + math.sin(a2) * (r + 14))

            # خط‌های ضخیم
            pygame.draw.line(surface, self._accent, p1, (vx, vy), 3)
            pygame.draw.line(surface, self._accent, (vx, vy), p2, 3)

        # ---- ذرات چرخان دور قاب ----
        # زاویه‌ی هر ذره با سرعت اختصاصی خودش افزایش می‌یابد و موقعیت آن روی مسیر دایره‌ای محاسبه می‌شود.
        # Each particle advances by its own angular speed, and its position is calculated along a circular path.
        for dot in self._ring_dots:
            dot["angle"] += dot["speed"] * 0.016   # dt جزئی
            a = dot["angle"]

            # موقعیت روی هگزاگونال (تقریبی با دایره)
            px = cx + math.cos(a) * (r + 6)
            py = cy + math.sin(a) * (r + 6)

            # فاز مستقل هر ذره باعث می‌شود شدت نور آن‌ها هم‌زمان تغییر نکند.
            # Each particle has an independent phase, so their glow intensities do not pulse in sync.
            pulse_a = 0.5 + 0.5 * math.sin(self.time * 4 + dot["phase"])
            alpha = int(120 + 100 * pulse_a)
            size = dot["size"]
            d = pygame.Surface((int(size * 6), int(size * 6)), pygame.SRCALPHA)
            pygame.draw.circle(d, (*self._accent, alpha),
                               (int(size * 3), int(size * 3)), int(size * 2))
            pygame.draw.circle(d, (255, 255, 255, alpha),
                               (int(size * 3), int(size * 3)), int(size * 0.8))
            surface.blit(d, (px - size * 3, py - size * 3),
                         special_flags=pygame.BLEND_RGBA_ADD)

        # ---- پیش‌نمایش سفینه ----
        preview = self._preview_cache.get(self.current_key)
        if preview is None:
            return

        # انیمیشن
        # منحنی ease-out هم‌زمان میزان جابه‌جایی افقی و شفافیت سفینه را کنترل می‌کند.
        # The ease-out curve controls both the ship's horizontal offset and its opacity.
        t = self._transition_t
        e = _ease_out_cubic(t)
        offset_x = int((1.0 - e) * -self._transition_dir * 80)
        alpha = e

        ship_cx = cx + offset_x
        ship_cy = cy

        # وضعیت نمونه‌ی پیش‌نمایش پیش از رسم، با زمان و موقعیت فعلی صحنه هماهنگ می‌شود.
        # The preview instance is synchronized with the scene's current time and position before rendering.
        preview.x = ship_cx
        preview.y = ship_cy
        preview.vx = 0.0
        preview.vy = 0.0
        preview._t = self.time
        preview.recoil = 0.0
        preview.muzzle_flash = 0.0
        preview.powerup_time = 0.0
        preview.invuln_time = 0.0

        if alpha >= 0.99:
            preview.draw_entity(surface)
        else:
            # هنگام انتقال، سفینه ابتدا روی سطحی جداگانه رسم می‌شود تا شفافیت کل تصویر اعمال شود.
            # During transitions, the ship is drawn onto a separate surface so opacity can be applied to the entire image.
            size = int(preview.radius * 5)
            tmp = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            preview.x = size
            preview.y = size
            preview.draw_entity(tmp)
            tmp.set_alpha(int(255 * alpha))
            surface.blit(tmp, (ship_cx - size, ship_cy - size))

        # ---- شماره‌ی سفینه ----
        idx = SHIP_LIST.index(self.current_key) + 1
        total = len(SHIP_LIST)
        num_text = f"{idx} / {total}"
        num_img = self.font_num.render(num_text, True, self._accent)
        num_rect = num_img.get_rect(center=(cx, cy + r + 40))

        # پس‌زمینه‌ی کوچک
        bg = pygame.Surface((num_rect.width + 16, num_rect.height + 6), pygame.SRCALPHA)
        pygame.draw.rect(bg, (10, 15, 28, 180), bg.get_rect(), border_radius=4)
        surface.blit(bg, (num_rect.x - 8, num_rect.y - 3))
        surface.blit(num_img, num_rect)

    # ── پنل اطلاعات (سمت راست) ──
    def _draw_info_panel(self, surface: pygame.Surface) -> None:
        info = SHIP_INFO[self.current_key]

        # انیمیشن ورود پنل
        t = self._transition_t
        e = _ease_out_cubic(t)
        offset_x = int((1.0 - e) * self._transition_dir * 30)
        alpha = e

        # ---- نام (بدون جعبه، فقط درخشش نرم پشت) ----
        name_img = self.font_name.render(info.name, True, self._accent)
        name_rect = name_img.get_rect()
        name_rect.midleft = (INFO_X + offset_x, NAME_Y)
        if alpha < 1.0:
            name_img.set_alpha(int(255 * alpha))
        surface.blit(name_img, name_rect)

        # ---- نقش + سختی ----
        role_text = f"{info.role}  ·  {info.difficulty}"
        role_img = self.font_role.render(role_text, True, (150, 170, 200))
        role_rect = role_img.get_rect()
        role_rect.midleft = (INFO_X + offset_x, ROLE_Y)
        if alpha < 1.0:
            role_img.set_alpha(int(255 * alpha))
        surface.blit(role_img, role_rect)

        # ---- توضیحات ----
        desc_img = self.font_desc.render(info.description, True, (200, 215, 240))
        desc_rect = desc_img.get_rect()
        desc_rect.midleft = (INFO_X + offset_x, DESC_Y)
        if alpha < 1.0:
            desc_img.set_alpha(int(255 * alpha))
        surface.blit(desc_img, desc_rect)

        # ---- خط جداکننده ----
        div_y = STATS_TOP - 24
        div_x1 = INFO_X
        div_x2 = INFO_X + INFO_W
        line_surf = pygame.Surface((div_x2 - div_x1, 1), pygame.SRCALPHA)

        # شفافیت خط در مرکز بیشتر است و به‌صورت متقارن به سمت لبه‌ها کاهش می‌یابد.
        # The line is more opaque at its center and fades symmetrically toward both edges.
        for i in range(div_x2 - div_x1):
            t_line = i / (div_x2 - div_x1)
            a = int(80 * alpha * (1 - abs(t_line - 0.5) * 2) + 40)
            line_surf.set_at((i, 0), (*self._accent, a))
        surface.blit(line_surf, (div_x1, div_y))

        # ---- نوارهای آمار ----
        for i, bar in enumerate(self.stats):
            y = STATS_TOP + i * STATS_ROW_H
            bar.draw(
                surface,
                INFO_X + offset_x, y,
                STATS_BAR_W, STATS_BAR_H,
                self.font_stat,
                self._accent,
            )

    # ── فلش‌های کناری ──
    def _draw_arrows(self, surface: pygame.Surface) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.time * 4.0)
        offset = int(8 + 6 * pulse)
        cy = PREVIEW_CY

        # فلش چپ
        lx = PREVIEW_CX - FRAME_R - 50 - offset
        pygame.draw.polygon(surface, self._accent, [
            (lx, cy - 16), (lx + 20, cy), (lx, cy + 16),
        ])

        # فلش راست
        rx = PREVIEW_CX + FRAME_R + 50 + offset
        pygame.draw.polygon(surface, self._accent, [
            (rx, cy - 16), (rx - 20, cy), (rx, cy + 16),
        ])

    # ── راهنما ──
    def _draw_hint(self, surface: pygame.Surface) -> None:
        hint = "LEFT/RIGHT  browse    |    ENTER  select    |    ESC  back"
        img = self.font_hint.render(hint, True, (120, 140, 170))
        surface.blit(img, img.get_rect(center=(W // 2, HINT_Y)))


    def _confirm_select(self) -> None:
        self._play_ui("ui_confirm")

        # کلید سفینه‌ی انتخاب‌شده در Game ذخیره می‌شود تا Gameplay از همان سفینه استفاده کند.
        # The selected ship key is stored in Game so Gameplay can use the chosen ship.
        try:
            setattr(self.game, "selected_ship", self.current_key)
        except Exception:
            pass
        self.go_to(S.SceneName.GAMEPLAY.value)

    def _go_back(self) -> None:
        self._play_ui("ui_cancel")
        self.go_to(S.SceneName.MENU.value)

    def _play_ui(self, sound: str) -> None:
        if self.audio is not None:
            try:
                self.audio.play(sound)
            except Exception:
                pass


__all__ = ["ShipSelectScene"]