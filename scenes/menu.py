"""
scenes/menu.py
==============

منوی اصلی SPACE BLASTER.

این صحنه اولین چیزی است که کاربر می‌بیند. شامل:
    • پس‌زمینه‌ی ستاره‌ای با پارالاکس ساده (سه لایه با سرعت‌های متفاوت)
    • عنوان پالس‌دار با هاله‌ی نئونی
    • دکمه‌های تعاملی با hover (هم ماوس، هم کیبورد)
    • نسخه و راهنمای پایین صفحه

ناوبری:
    ↑ / ↓  یا  W / S   — انتخاب بین دکمه‌ها
    Enter / Space       — تأیید
    ESC                 — خروج از بازی
    ماوس                 — hover و کلیک

این صحنه از SceneManager برای رفتن به Gameplay استفاده می‌کند و از
Stack برای push کردن Leaderboard / Settings (که بعداً ساخته می‌شوند)
پشتیبانی می‌کند.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

import pygame

from core import settings as S
from scenes.base import Scene

if TYPE_CHECKING:
    from core.game import Game


# اطلاعات هر ستاره شامل موقعیت، سرعت، اندازه، رنگ و لایه عمق آن است.
# Each star stores its position, speed, size, color, and depth layer.
@dataclass
class _Star:
    x: float
    y: float
    speed: float
    radius: float
    color: tuple[int, int, int]
    layer: int   # 0 دور، 1 میانه، 2 نزدیک


# دکمه منو منطق تعامل و جلوه‌های بصری مستقل از خود صحنه را مدیریت می‌کند.
# The menu button manages its interaction logic and visual effects independently of the scene.
class _MenuButton:
    """
    یک دکمه‌ی تعاملی با انیمیشن نرم.

    ویژگی‌ها:
        • hover نرم با lerp (میان‌یابی خطی) — تغییر اندازه و شفافیت
        • پالس ملایم روی گزینه‌ی فعال
        • پشتیبانی از ماوس و کیبورد
        • انیمیشن offset افقی برای نشانگر انتخاب
    """

    def __init__(
        self,
        label: str,
        action: Callable[[], None],
        y: int,
        width: int = 340,     # ← بزرگ‌تر
        height: int = 60,     # ← بزرگ‌تر
    ) -> None:
        self.label = label
        self.action = action
        self.base_y = y
        self.width = width
        self.height = height

        # وضعیت
        self.hovered = False
        self.selected = False
        self._t = 0.0            # زمان برای انیمیشن
        self._hover_amt = 0.0    # 0 تا 1، نرم شده
        self._click_amt = 0.0    # 0 تا 1، پس از کلیک افت می‌کند
        self._rect = pygame.Rect(0, 0, width, height)
        self._rect.center = (S.Window.WIDTH // 2, y)

    # ── هندسه ──
    @property
    def rect(self) -> pygame.Rect:
        return self._rect

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        self._t += dt

        # وضعیت hover با بررسی قرار گرفتن نشانگر ماوس داخل محدوده دکمه تعیین می‌شود.
        # The hover state is determined by checking whether the mouse is inside the button bounds.
        # hover
        is_over = self._rect.collidepoint(mouse_pos)
        self.hovered = is_over or self.selected

        target = 1.0 if self.hovered else 0.0

        # میان‌یابی تدریجی باعث می‌شود تغییر وضعیت hover ناگهانی نباشد.
        # Gradual interpolation prevents abrupt changes in the hover state.
        # lerp نرم
        self._hover_amt += (target - self._hover_amt) * min(1.0, dt * 12.0)

        # مقدار افکت کلیک به‌مرور کاهش می‌یابد تا جلوه فلاش به‌صورت تدریجی محو شود.
        # The click effect gradually decreases so the flash fades out smoothly.
        # افکت کلیک
        if self._click_amt > 0.0:
            self._click_amt = max(0.0, self._click_amt - dt * 4.0)

    def trigger_click(self) -> None:
        self._click_amt = 1.0
        self.action()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """اگر رویداد به این دکمه مربوط باشد، True برمی‌گرداند."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._rect.collidepoint(event.pos):
                self.trigger_click()
                return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        # اندازه و شفافیت با توجه به hover_amt
        pad_x = int(6 * self._hover_amt)
        pad_y = int(3 * self._hover_amt)
        scale_y = int(2 * self._hover_amt)

        rect = self._rect.inflate(pad_x * 2, (pad_y + scale_y) * 2)
        alpha = int(60 + 160 * self._hover_amt)

        # ---- پس‌زمینه (با شفافیت) ----
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)

        # گرادیان عمودی خیلی ملایم برای زیبایی
        # A subtle vertical gradient adds depth to the button background.
        top_color = (*S.Palette.HUD_ACCENT, min(255, alpha // 3))
        bot_color = (*S.Palette.HUD_ACCENT, min(255, alpha // 5))
        for y in range(rect.height):
            t = y / max(1, rect.height - 1)
            r = int(top_color[0] * (1 - t) + bot_color[0] * t)
            g = int(top_color[1] * (1 - t) + bot_color[1] * t)
            b = int(top_color[2] * (1 - t) + bot_color[2] * t)
            a = int(top_color[3] * (1 - t) + bot_color[3] * t)
            pygame.draw.line(bg, (r, g, b, a), (0, y), (rect.width, y))
        surface.blit(bg, rect.topleft)

        # ---- حاشیه ----
        border_alpha = int(140 + 115 * self._hover_amt)
        border_col = (*S.Palette.HUD_ACCENT, border_alpha)
        border_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(border_surf, border_col, border_surf.get_rect(), 2, border_radius=6)
        surface.blit(border_surf, rect.topleft)

        # ---- درخشش داخلی روی hover ----
        if self._hover_amt > 0.05:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            ga = int(80 * self._hover_amt)
            pygame.draw.rect(glow, (*S.Palette.HUD_ACCENT, ga),
                             glow.get_rect(), 0, border_radius=6)
            surface.blit(glow, rect.topleft)

        # ---- متن ----
        # کمی جابه‌جایی افقی برای حس دینامیک
        # A slight horizontal offset creates a more dynamic visual effect.
        offset_x = int(4 * self._hover_amt) * (1 if self.selected else 0)
        text_color = S.Palette.WHITE if self.hovered else S.Palette.HUD_TEXT
        img = font.render(self.label, True, text_color)
        text_rect = img.get_rect(center=rect.center)
        text_rect.x += offset_x

        # سایه‌ی متن (کمی تیره‌تر و پایین‌تر) برای عمق
        shadow = font.render(self.label, True, (0, 0, 0))
        surface.blit(shadow, (text_rect.x + 2, text_rect.y + 2))
        surface.blit(img, text_rect)

        # ---- نشانگر انتخاب (فلش ▶) ----
        if self.selected:
            arrow_color = S.Palette.HUD_ACCENT

            # حرکت سینوسی اندازه فاصله فلش‌ها را تغییر می‌دهد و جلوه پالس ایجاد می‌کند.
            # Sinusoidal motion changes the arrows' spacing to create a pulsing effect.
            # پالس ملایم
            pulse = 6 + int(3 * math.sin(self._t * 6.0))
            arrow_x = rect.left - 22 - int(6 * self._hover_amt) - pulse
            arrow_y = rect.centery
            pts = [
                (arrow_x, arrow_y - 8),
                (arrow_x + 12, arrow_y),
                (arrow_x, arrow_y + 8),
            ]
            pygame.draw.polygon(surface, arrow_color, pts)

            # نشانگر سمت راست (آینه)
            rx = rect.right + 10 + int(6 * self._hover_amt) + pulse
            pts_r = [
                (rx, arrow_y - 8),
                (rx - 12, arrow_y),
                (rx, arrow_y + 8),
            ]
            pygame.draw.polygon(surface, arrow_color, pts_r)

        # ---- اثر کلیک (فلاش) ----
        if self._click_amt > 0.01:
            flash = pygame.Surface(rect.size, pygame.SRCALPHA)
            fa = int(120 * self._click_amt)
            pygame.draw.rect(flash, (*S.Palette.WHITE, fa),
                             flash.get_rect(), 0, border_radius=6)
            surface.blit(flash, rect.topleft)


# صحنه منوی اصلی، اجزای رابط کاربری و جلوه‌های پس‌زمینه را هماهنگ می‌کند.
# The main menu scene coordinates the user interface elements and background effects.
class MenuScene(Scene):


    def on_enter(self) -> None:
        # ---- فونت‌ها ----
        self.font_title = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.HUGE, bold=True)
        self.font_sub   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.NORMAL)
        self.font_btn   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.LARGE, bold=True)
        self.font_small = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL)

        # ---- ستاره‌های پس‌زمینه ----
        self.stars: list[_Star] = []
        self._spawn_stars(S.FxCfg.STAR_COUNT)

        # ---- دکمه‌های منو ----
        # چیدمان منو — با فاصله‌های بزرگ‌تر برای رزولوشن بالاتر
        btn_start_y = 430
        btn_gap = 68

        self.buttons: list[_MenuButton] = [
            _MenuButton("START MISSION", self._start_game,       y=btn_start_y),
            _MenuButton("SELECT SHIP",   self._select_ship,      y=btn_start_y + btn_gap),
            _MenuButton("LEADERBOARD",   self._open_leaderboard, y=btn_start_y + btn_gap * 2),
            _MenuButton("QUIT",          self.quit_game,         y=btn_start_y + btn_gap * 3),
        ]

        # اولین گزینه هنگام ورود به منو به‌صورت پیش‌فرض انتخاب می‌شود.
        # The first option is selected by default when entering the menu.
        self.selected_idx = 0
        self.buttons[self.selected_idx].selected = True

        # ---- زمان برای انیمیشن عنوان ----
        self._t = 0.0

    def _select_ship(self) -> None:
        self.go_to(S.SceneName.SHIP_SELECT.value)

    def on_exit(self) -> None:
        self.stars.clear()
        self.buttons.clear()


    def _spawn_stars(self, count: int) -> None:
        for _ in range(count):

            # انتخاب تصادفی لایه‌ها با وزن‌های متفاوت، تعداد ستاره‌های دور را بیشتر می‌کند.
            # Weighted random selection creates more distant stars than nearby ones.
            layer = random.choices([0, 1, 2], weights=[5, 3, 2])[0]

            # هر لایه با اندازه، سرعت و رنگ متفاوت، حس عمق و پارالاکس ایجاد می‌کند.
            # Each layer uses a different size, speed, and color to create depth and parallax.
            if layer == 0:
                r = random.uniform(0.6, 1.1)
                sp = random.uniform(S.FxCfg.STAR_SPEED_MIN, S.FxCfg.STAR_SPEED_MIN * 1.5)
                col = S.Palette.STAR_FAR
            elif layer == 1:
                r = random.uniform(1.0, 1.7)
                sp = random.uniform(S.FxCfg.STAR_SPEED_MIN * 1.5, S.FxCfg.STAR_SPEED_MIN * 3)
                col = (150, 160, 200)
            else:
                r = random.uniform(1.6, 2.6)
                sp = random.uniform(S.FxCfg.STAR_SPEED_MIN * 3, S.FxCfg.STAR_SPEED_MAX)
                col = S.Palette.STAR_NEAR

            self.stars.append(_Star(
                x=random.uniform(0, S.Window.WIDTH),
                y=random.uniform(0, S.Window.HEIGHT),
                speed=sp,
                radius=r,
                color=col,
                layer=layer,
            ))

    def _update_stars(self, dt: float) -> None:
        for st in self.stars:

            # جابه‌جایی بر اساس dt باعث می‌شود سرعت حرکت ستاره‌ها به نرخ فریم وابسته نباشد.
            # Movement based on dt keeps star speed independent of the frame rate.
            st.y += st.speed * dt

            # ستاره پس از خروج از پایین صفحه به بالای آن بازمی‌گردد و موقعیت افقی تازه‌ای می‌گیرد.
            # Once a star leaves the bottom of the screen, it returns to the top at a new horizontal position.
            if st.y > S.Window.HEIGHT + 4:
                st.y = -4
                st.x = random.uniform(0, S.Window.WIDTH)

    def _draw_stars(self, surface: pygame.Surface) -> None:
        for st in self.stars:
            pygame.draw.circle(
                surface, st.color,
                (int(st.x), int(st.y)),
                max(1, int(round(st.radius))),
            )


    def handle_event(self, event: pygame.event.Event) -> None:
        # ---- کیبورد ----
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.quit_game()
                return
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self._move_selection(+1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._move_selection(-1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.buttons[self.selected_idx].trigger_click()

        # ---- ماوس ----
        for b in self.buttons:
            if b.handle_event(event):
                break

    def _move_selection(self, delta: int) -> None:
        # گزینه فعلی غیرفعال می‌شود و انتخاب جدید با استفاده از پیمانه در محدوده دکمه‌ها باقی می‌ماند.
        # The current option is deselected, and modulo arithmetic keeps the new selection within the button list.
        self.buttons[self.selected_idx].selected = False
        self.selected_idx = (self.selected_idx + delta) % len(self.buttons)
        self.buttons[self.selected_idx].selected = True


    def update(self, dt: float) -> None:
        self._t += dt
        self._update_stars(dt)

        mouse_pos = pygame.mouse.get_pos()
        for i, b in enumerate(self.buttons):
            b.update(dt, mouse_pos)

            # اگر ماوس روی دکمه‌ای رفت، آن را انتخاب کن
            # Select a button when the mouse pointer moves over it.
            if b.hovered and i != self.selected_idx:
                self.buttons[self.selected_idx].selected = False
                self.selected_idx = i
                b.selected = True


    def draw(self, surface: pygame.Surface) -> None:
        # ---- پس‌زمینه ----
        surface.fill(S.Palette.BG_DEEP)
        self._draw_stars(surface)
        self._draw_nebula(surface)
        self._draw_title(surface)

        # ---- دکمه‌ها ----
        for b in self.buttons:
            b.draw(surface, self.font_btn)

        # ---- پانویس ----
        self._draw_footer(surface)

    # ── افکت سحابی: دو هاله‌ی رنگی ملایم که آرام حرکت می‌کنند ──
    def _draw_nebula(self, surface: pygame.Surface) -> None:
        w, h = S.Window.WIDTH, S.Window.HEIGHT

        # مختصات هر هاله با توابع سینوسی تغییر می‌کند تا حرکت آن‌ها نرم و پیوسته باشد.
        # Each halo's position changes sinusoidally to produce smooth, continuous movement.
        # دو هاله با حرکت نرم سینوسی
        cx1 = w * 0.30 + math.sin(self._t * 0.18) * 40
        cy1 = h * 0.35 + math.cos(self._t * 0.22) * 30
        cx2 = w * 0.72 + math.cos(self._t * 0.15) * 50
        cy2 = h * 0.60 + math.sin(self._t * 0.19) * 35

        for cx, cy, color, base_r in (
            (cx1, cy1, (30, 60, 120), 260),
            (cx2, cy2, (60, 20, 80), 220),
        ):
            surf = pygame.Surface((base_r * 2, base_r * 2), pygame.SRCALPHA)

            # رسم دایره‌های تو‌در‌تو با آلفای متغیر، هاله‌ای نرم و بدون مرز مشخص می‌سازد.
            # Drawing concentric circles with varying alpha creates a soft, borderless glow.
            for r in range(base_r, 0, -12):
                a = int(4 + 5 * (1 - r / base_r))
                pygame.draw.circle(surf, (*color, a), (base_r, base_r), r)

            # ترکیب افزایشی رنگ‌ها، نور هاله را با رنگ‌های موجود پس‌زمینه ادغام می‌کند.
            # Additive blending combines the halo's light with the existing background colors.
            surface.blit(surf, (cx - base_r, cy - base_r),
                         special_flags=pygame.BLEND_RGBA_ADD)

    # ── عنوان با پالس و هاله ──
    def _draw_title(self, surface: pygame.Surface) -> None:
        cx = S.Window.WIDTH // 2
        cy = 130

        # ---- پالس ----
        # تغییر سینوسی مقیاس عنوان، انیمیشن ضربان ملایمی ایجاد می‌کند.
        # Sinusoidal scaling creates a subtle pulsing animation for the title.
        pulse = 1.0 + 0.04 * math.sin(self._t * 2.4)

        # ---- متن اصلی ----
        img = self.font_title.render(S.Window.TITLE, True, S.Palette.MENU_TITLE)
        w = int(img.get_width() * pulse)
        h = int(img.get_height() * pulse)
        img_scaled = pygame.transform.smoothscale(img, (w, h))
        rect = img_scaled.get_rect(center=(cx, cy))

        # ---- هاله (کم‌تر از قبل، تمیزتر) ----
        # سه لایه با اندازه‌های متفاوت، درخشش اطراف عنوان را ایجاد می‌کنند.
        # Three layers with different sizes create a glow around the title.
        for layer in range(3, 0, -1):
            glow_img = pygame.transform.smoothscale(
                img, (w + layer * 8, h + layer * 8)
            )
            glow_surf = pygame.Surface(glow_img.get_size(), pygame.SRCALPHA)
            glow_surf.blit(glow_img, (0, 0))
            glow_surf.set_alpha(22 - layer * 6)
            surface.blit(
                glow_surf,
                glow_surf.get_rect(center=(cx, cy)),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

        surface.blit(img_scaled, rect)

        # ---- زیرعنوان: با فاصله‌ی بیشتر ----
        sub_y = cy + h // 2 + 40           # ← فاصله از لبه‌ی پایین عنوان
        sub_img = self.font_sub.render(
            "DEFEND  •  SURVIVE  •  ASCEND", True, S.Palette.MENU_HINT,
        )
        sub_rect = sub_img.get_rect(center=(cx, sub_y))
        surface.blit(sub_img, sub_rect)

        # ---- خط تزئینی: با فاصله‌ی مناسب ----
        line_w = 360
        line_y = sub_y + 36

        # شفافیت خط در مرکز بیشترین مقدار و در دو انتهای آن به صفر می‌رسد.
        # The line's opacity peaks at the center and fades to zero at both ends.
        for i in range(line_w):
            t = i / line_w
            a = int(180 * math.sin(math.pi * t))
            x = cx - line_w // 2 + i
            pygame.draw.line(
                surface, (*S.Palette.MENU_TITLE, a),
                (x, line_y), (x, line_y + 1),
            )

    # ── پانویس ──
    def _draw_footer(self, surface: pygame.Surface) -> None:
        hint = "UP/DOWN  select    |    ENTER  confirm    |    ESC  quit"
        img = self.font_small.render(hint, True, S.Palette.GREY)
        rect = img.get_rect(center=(S.Window.WIDTH // 2, S.Window.HEIGHT - 26))
        surface.blit(img, rect)

        ver = self.font_small.render("v0.1.0", True, S.Palette.GREY)
        ver_rect = ver.get_rect()
        ver_rect.bottomright = (S.Window.WIDTH - 12, S.Window.HEIGHT - 10)
        surface.blit(ver, ver_rect)


    def _start_game(self) -> None:
        self.go_to(S.SceneName.GAMEPLAY.value)

    def _open_leaderboard(self) -> None:
        self.go_to(S.SceneName.LEADERBOARD.value)

    def _open_settings(self) -> None:
        print("[Menu] Settings not implemented yet.")


__all__ = ["MenuScene"]