"""
ui/button.py
============

دکمه‌ی مشترک برای تمام منوها.


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



    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        # زمان انیمیشن را بر اساس مدت سپری‌شده افزایش می‌دهد تا حرکت‌ها مستقل از نرخ فریم باشند.
        # Advances animation time by elapsed time so motion remains independent of frame rate.
        self._t += dt

        # دکمه در صورت قرار گرفتن نشانگر ماوس روی آن یا انتخاب شدن، در حالت فعال قرار می‌گیرد.
        # The button enters its active state when hovered by the mouse or selected.
        self.hovered = self._rect.collidepoint(mouse_pos) or self.selected

        # مقدار هدف برای انیمیشن hover تعیین می‌شود و با ضریب نرم به آن نزدیک می‌شود.
        # Sets the hover animation target and smoothly interpolates toward it.
        target = 1.0 if self.hovered else 0.0
        self._hover_amt += (target - self._hover_amt) * min(1.0, dt * 12.0)

        # شدت فلاش کلیک به‌تدریج کاهش می‌یابد تا انیمیشن آن محو شود.
        # Gradually decreases the click flash intensity so the animation fades out.
        if self._click_amt > 0.0:
            self._click_amt = max(0.0, self._click_amt - dt * 4.0)

    def trigger_click(self) -> None:
        # انیمیشن فلاش را فعال می‌کند و سپس تابع متصل‌شده به دکمه را اجرا می‌کند.
        # Activates the flash animation and then executes the callback assigned to the button.
        self._click_amt = 1.0
        self.action()

    def handle_event(self, event: pygame.event.Event) -> bool:
        # فقط رویداد فشردن دکمه‌ی اصلی ماوس را بررسی می‌کند.
        # Handles only mouse button-down events for the primary mouse button.
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # کلیک خارج از محدوده‌ی دکمه نادیده گرفته می‌شود.
            # Clicks outside the button's rectangle are ignored.
            if self._rect.collidepoint(event.pos):
                self.trigger_click()
                return True
        return False



    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        # هنگام hover ابعاد دکمه افزایش می‌یابد تا حالت فعال آن برجسته‌تر شود.
        # Expands the button while hovered to make its active state more prominent.
        pad_x = int(8 * self._hover_amt)
        pad_y = int(4 * self._hover_amt)
        rect = self._rect.inflate(pad_x * 2, pad_y * 2)

        # شفافیت عناصر بصری با شدت hover تنظیم می‌شود.
        # Adjusts the transparency of visual elements according to the hover intensity.
        alpha = int(80 + 130 * self._hover_amt)
        radius = self.border_radius

        # پس‌زمینه
        # Background
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            bg, (*self.accent, alpha // 3),
            bg.get_rect(), border_radius=radius,
        )
        surface.blit(bg, rect.topleft)

        # حاشیه
        # Border
        border_alpha = int(150 + 105 * self._hover_amt)
        border = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            border, (*self.accent, border_alpha),
            border.get_rect(), 2, border_radius=radius,
        )
        surface.blit(border, rect.topleft)

        # درخشش
        # Glow
        # افکت درخشش فقط زمانی رسم می‌شود که شدت hover از آستانه‌ی تعیین‌شده عبور کند.
        # Draws the glow effect only when the hover intensity exceeds the specified threshold.
        if self._hover_amt > 0.05:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            ga = int(80 * self._hover_amt)
            pygame.draw.rect(
                glow, (*self.accent, ga),
                glow.get_rect(), 0, border_radius=radius,
            )
            surface.blit(glow, rect.topleft)

        # متن + سایه
        # Text + Shadow
        # رنگ متن با توجه به فعال بودن دکمه تغییر می‌کند و سایه برای خوانایی بیشتر رسم می‌شود.
        # Changes the text color based on the button's active state and draws a shadow for readability.
        text_color = S.Palette.WHITE if self.hovered else S.Palette.HUD_TEXT
        img = font.render(self.label, True, text_color)
        text_rect = img.get_rect(center=rect.center)

        shadow = font.render(self.label, True, (0, 0, 0))
        surface.blit(shadow, (text_rect.x + 2, text_rect.y + 2))
        surface.blit(img, text_rect)

        # فلش‌های انتخاب
        # Selection Arrows
        # موقعیت فلش‌ها با اندازه‌ی دکمه و شدت hover تنظیم می‌شود.
        # Positions the arrows according to the button's dimensions and hover intensity.
        if self.selected and self.show_arrows:
            # حرکت سینوسی، فلش‌ها را به‌صورت ضربانی به جلو و عقب جابه‌جا می‌کند.
            # Sinusoidal motion moves the arrows back and forth in a pulsing pattern.
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
        # Click Flash
        # یک لایه‌ی سفید با شفافیت متغیر روی دکمه رسم می‌شود تا بازخورد بصری کلیک ایجاد شود.
        # Draws a white overlay with variable transparency to provide visual feedback for clicks.
        if self._click_amt > 0.01:
            flash = pygame.Surface(rect.size, pygame.SRCALPHA)
            fa = int(140 * self._click_amt)
            pygame.draw.rect(
                flash, (*S.Palette.WHITE, fa),
                flash.get_rect(), border_radius=radius,
            )
            surface.blit(flash, rect.topleft)


__all__ = ["Button"]