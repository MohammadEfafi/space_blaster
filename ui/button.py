"""
ui/button.py
============

دکمه‌ی مشترک برای تمام منوها.

قبلاً ۵ نسخه‌ی تقریباً یکسان وجود داشت:
    scenes/menu.py       → _MenuButton
    scenes/pause.py      → _PauseButton
    scenes/gameover.py   → _GameOverButton
    scenes/ship_select.py → _Button
    scenes/leaderboard.py → _BackButton

این ماژول یک نسخه‌ی واحد ارائه می‌دهد. برای استایل‌های متفاوت
(اندازه، رنگ، فلش‌ها) از پارامترهای سازنده استفاده کن.
"""

from __future__ import annotations

import math
from typing import Callable

import pygame

from core import settings as S


class Button:
    """
    دکمه‌ی همه‌کاره با انیمیشن نرم.

    پارامترها:
        label         — متن دکمه
        action        — تابعی که هنگام کلیک/Enter صدا زده می‌شود
        y             — موقعیت عمودی (مرکز)
        width/height  — ابعاد
        accent        — رنگ اصلی
        show_arrows   — نمایش فلش‌های کنار دکمه‌ی انتخاب‌شده
        border_radius — گوشه‌های گرد
    """

    def __init__(
        self,
        label: str,
        action: Callable[[], None],
        *,
        y: int,
        width: int = 260,
        height: int = 48,
        accent: tuple[int, int, int] = S.Palette.HUD_ACCENT,
        show_arrows: bool = True,
        border_radius: int = 8,
    ) -> None:
        self.label = label
        self.action = action
        self.accent = accent
        self.show_arrows = show_arrows
        self.border_radius = border_radius

        self.hovered = False
        self.selected = False

        self._t: float = 0.0
        self._hover_amt: float = 0.0
        self._click_amt: float = 0.0

        self._rect = pygame.Rect(0, 0, width, height)
        self._rect.center = (S.Window.WIDTH // 2, y)

    @property
    def rect(self) -> pygame.Rect:
        return self._rect

    # ─────────────────────────────────────────────────────────────────────

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        self._t += dt
        self.hovered = self._rect.collidepoint(mouse_pos) or self.selected

        target = 1.0 if self.hovered else 0.0
        self._hover_amt += (target - self._hover_amt) * min(1.0, dt * 12.0)

        if self._click_amt > 0.0:
            self._click_amt = max(0.0, self._click_amt - dt * 4.0)

    def trigger_click(self) -> None:
        self._click_amt = 1.0
        self.action()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._rect.collidepoint(event.pos):
                self.trigger_click()
                return True
        return False

    # ─────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pad_x = int(8 * self._hover_amt)
        pad_y = int(4 * self._hover_amt)
        rect = self._rect.inflate(pad_x * 2, pad_y * 2)

        alpha = int(80 + 130 * self._hover_amt)
        radius = self.border_radius

        # پس‌زمینه
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            bg, (*self.accent, alpha // 3),
            bg.get_rect(), border_radius=radius,
        )
        surface.blit(bg, rect.topleft)

        # حاشیه
        border_alpha = int(150 + 105 * self._hover_amt)
        border = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            border, (*self.accent, border_alpha),
            border.get_rect(), 2, border_radius=radius,
        )
        surface.blit(border, rect.topleft)

        # درخشش
        if self._hover_amt > 0.05:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            ga = int(80 * self._hover_amt)
            pygame.draw.rect(
                glow, (*self.accent, ga),
                glow.get_rect(), 0, border_radius=radius,
            )
            surface.blit(glow, rect.topleft)

        # متن + سایه
        text_color = S.Palette.WHITE if self.hovered else S.Palette.HUD_TEXT
        img = font.render(self.label, True, text_color)
        text_rect = img.get_rect(center=rect.center)

        shadow = font.render(self.label, True, (0, 0, 0))
        surface.blit(shadow, (text_rect.x + 2, text_rect.y + 2))
        surface.blit(img, text_rect)

        # فلش‌های انتخاب
        if self.selected and self.show_arrows:
            pulse = 6 + int(3 * math.sin(self._t * 6.0))
            ay = rect.centery

            ax = rect.left - 20 - int(6 * self._hover_amt) - pulse
            pygame.draw.polygon(surface, self.accent, [
                (ax, ay - 7), (ax + 10, ay), (ax, ay + 7),
            ])

            rx = rect.right + 10 + int(6 * self._hover_amt) + pulse
            pygame.draw.polygon(surface, self.accent, [
                (rx, ay - 7), (rx - 10, ay), (rx, ay + 7),
            ])

        # فلاش کلیک
        if self._click_amt > 0.01:
            flash = pygame.Surface(rect.size, pygame.SRCALPHA)
            fa = int(140 * self._click_amt)
            pygame.draw.rect(
                flash, (*S.Palette.WHITE, fa),
                flash.get_rect(), border_radius=radius,
            )
            surface.blit(flash, rect.topleft)


__all__ = ["Button"]