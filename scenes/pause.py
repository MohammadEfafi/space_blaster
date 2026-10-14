"""
scenes/pause.py
===============

منوی توقف (Pause Scene) برای SPACE BLASTER.

این صحنه با استفاده از SceneManager.push روی GameplayScene قرار
می‌گیرد. به لطف طراحی Stack، صحنه‌ی زیرین (Gameplay) به‌صورت خودکار
وارد حالت Pause می‌شود و همچنان پشت این صحنه رندر می‌شود تا
حس «منوی شیشه‌ای» بدهد.

ویژگی‌ها:
    • پس‌زمینه‌ی نیمه‌شفاف + وینیت تیره
    • دکمه‌های تعاملی (Resume, Restart, Main Menu, Quit)
    • ناوبری کامل با کیبورد (↑↓ Enter) و ماوس (hover + click)
    • ESC برای Resume سریع
    • ورود نرم با انیمیشن (fade-in + slide از بالا)
    • صدای UI (اگر AudioSystem موجود باشد)
    • نمایش آمار لحظه‌ای (امتیاز، موج) از Game

خروجی‌ها:
    Resume     → SceneManager.pop() — برگشت به Gameplay
    Restart    → go_to(Gameplay) — شروع مجدد
    Main Menu  → go_to(Menu)
    Quit       → بستن بازی
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

import pygame

from core import settings as S
from scenes.base import Scene
from systems.audio import AudioSystem, Bus


# ═══════════════════════════════════════════════════════════════════════════
#  دکمه‌ی منوی Pause
# ═══════════════════════════════════════════════════════════════════════════

class _PauseButton:
    """
    دکمه‌ی منوی Pause — با انیمیشن hover و انتخاب.

    تفاوت با دکمه‌ی منو:
        • عرض بیشتر برای هماهنگی با ظاهر Pause
        • hover نرم با lerp
        • نشانگر ← انتخاب شده با پالس
    """

    def __init__(
        self,
        label: str,
        action: Callable[[], None],
        y: int,
        *,
        width: int = 320,
        height: int = 52,
        is_danger: bool = False,
    ) -> None:
        self.label = label
        self.action = action
        self.base_y = y
        self.width = width
        self.height = height
        self.is_danger = is_danger

        self.hovered = False
        self.selected = False
        self._t = 0.0
        self._hover_amt = 0.0
        self._click_amt = 0.0

        self._rect = pygame.Rect(0, 0, width, height)
        self._rect.center = (S.Window.WIDTH // 2, y)

    @property
    def rect(self) -> pygame.Rect:
        return self._rect

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        self._t += dt
        self.hovered = self._rect.collidepoint(mouse_pos) or self.selected
        target = 1.0 if self.hovered else 0.0
        self._hover_amt += (target - self._hover_amt) * min(1.0, dt * 12.0)
        if self._click_amt > 0.0:
            self._click_amt = max(0.0, self._click_amt - dt * 4.0)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._rect.collidepoint(event.pos):
                self.trigger_click()
                return True
        return False

    def trigger_click(self) -> None:
        self._click_amt = 1.0
        self.action()

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pad_x = int(8 * self._hover_amt)
        pad_y = int(4 * self._hover_amt)
        rect = self._rect.inflate(pad_x * 2, pad_y * 2)

        # انتخاب رنگ بر اساس is_danger و hover
        if self.is_danger:
            base = S.Palette.HUD_HP
        else:
            base = S.Palette.HUD_ACCENT

        alpha = int(80 + 120 * self._hover_amt)

        # ---- پس‌زمینه ----
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (*base, alpha // 3), bg.get_rect(), border_radius=8)
        surface.blit(bg, rect.topleft)

        # ---- حاشیه ----
        border_alpha = int(150 + 105 * self._hover_amt)
        border_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            border_surf, (*base, border_alpha),
            border_surf.get_rect(), 2, border_radius=8,
        )
        surface.blit(border_surf, rect.topleft)

        # ---- درخشش روی hover ----
        if self._hover_amt > 0.05:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            ga = int(90 * self._hover_amt)
            pygame.draw.rect(glow, (*base, ga), glow.get_rect(), 0, border_radius=8)
            surface.blit(glow, rect.topleft)

        # ---- متن با سایه ----
        text_color = S.Palette.WHITE if self.hovered else S.Palette.HUD_TEXT
        img = font.render(self.label, True, text_color)
        text_rect = img.get_rect(center=rect.center)

        shadow = font.render(self.label, True, (0, 0, 0))
        surface.blit(shadow, (text_rect.x + 2, text_rect.y + 2))
        surface.blit(img, text_rect)

        # ---- فلش‌های انتخاب ----
        if self.selected:
            pulse = 6 + int(3 * math.sin(self._t * 6.0))
            ax = rect.left - 20 - int(6 * self._hover_amt) - pulse
            ay = rect.centery
            pygame.draw.polygon(surface, base, [
                (ax, ay - 8), (ax + 12, ay), (ax, ay + 8),
            ])
            rx = rect.right + 10 + int(6 * self._hover_amt) + pulse
            pygame.draw.polygon(surface, base, [
                (rx, ay - 8), (rx - 12, ay), (rx, ay + 8),
            ])

        # ---- فلاش کلیک ----
        if self._click_amt > 0.01:
            flash = pygame.Surface(rect.size, pygame.SRCALPHA)
            fa = int(140 * self._click_amt)
            pygame.draw.rect(flash, (*S.Palette.WHITE, fa), flash.get_rect(),
                             border_radius=8)
            surface.blit(flash, rect.topleft)


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس PauseScene
# ═══════════════════════════════════════════════════════════════════════════

class PauseScene(Scene):
    """منوی توقف بازی."""

    # ─────────────────────────────────────────────────────────────────────
    #  چرخه‌ی حیات
    # ─────────────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        # ---- فونت‌ها ----
        self.font_title = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.HUGE, bold=True)
        self.font_btn   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.LARGE, bold=True)
        self.font_small = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL)

        # ---- دکمه‌ها ----
        y0 = S.Window.HEIGHT // 2 - 30
        self.buttons: list[_PauseButton] = [
            _PauseButton("RESUME",     self._resume,     y=y0),
            _PauseButton("RESTART",    self._restart,    y=y0 + 70),
            _PauseButton("MAIN MENU",  self._main_menu,  y=y0 + 140),
            _PauseButton("QUIT",       self._quit,       y=y0 + 210, is_danger=True),
        ]
        self.selected_idx = 0
        self.buttons[self.selected_idx].selected = True

        # ---- انیمیشن ورود ----
        self._enter_t = 0.0
        self._enter_duration = 0.25

        # ---- Audio ----
        self.audio: Optional[AudioSystem] = getattr(self.game, "audio", None)

        # ---- آمار نمایشی ----
        self._score = int(getattr(self.game, "last_score", 0))
        # اگر در Game ذخیره نشده، از Gameplay بگیر
        gameplay = self.game.scenes._scenes.get(S.SceneName.GAMEPLAY.value)
        if gameplay is not None:
            self._score = getattr(gameplay, "score", self._score)
            wave = getattr(gameplay.spawner, "current_wave", 1) if hasattr(gameplay, "spawner") else 1
            self._wave = wave
        else:
            self._wave = 1

    def on_exit(self) -> None:
        self.buttons.clear()

    # ─────────────────────────────────────────────────────────────────────
    #  ورودی
    # ─────────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        # ---- کیبورد ----
        if event.type == pygame.KEYDOWN:
            if event.key in S.Keys.PAUSE or event.key == pygame.K_ESCAPE:
                self._resume()
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
        self.buttons[self.selected_idx].selected = False
        self.selected_idx = (self.selected_idx + delta) % len(self.buttons)
        self.buttons[self.selected_idx].selected = True
        self._play_ui("ui_move")

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        # ---- انیمیشن ورود ----
        if self._enter_t < 1.0:
            self._enter_t = min(1.0, self._enter_t + dt / self._enter_duration)

        # ---- دکمه‌ها ----
        mouse_pos = pygame.mouse.get_pos()
        for i, b in enumerate(self.buttons):
            b.update(dt, mouse_pos)
            if b.hovered and i != self.selected_idx:
                self.buttons[self.selected_idx].selected = False
                self.selected_idx = i
                b.selected = True

    # ─────────────────────────────────────────────────────────────────────
    #  رندر
    # ─────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        # ---- پس‌زمینه‌ی نیمه‌شفاف ----
        # چون صحنه‌ی زیرین (Gameplay) توسط SceneManager رسم می‌شود،
        # اینجا فقط یک لایه‌ی تیره با gradient می‌کشیم.
        self._draw_backdrop(surface)

        # ---- انیمیشن ورود: اسلاید از بالا + fade ----
        t = self._enter_t
        # easing: ease-out cubic
        e = 1.0 - (1.0 - t) ** 3
        slide = int((1.0 - e) * -40)   # از -40 به 0
        alpha = e

        # ---- عنوان ----
        self._draw_title(surface, slide, alpha)

        # ---- دکمه‌ها ----
        for b in self.buttons:
            b.draw(surface, self.font_btn)

        # ---- آمار پایین صفحه ----
        self._draw_stats(surface, alpha)

        # ---- راهنما ----
        self._draw_hint(surface, alpha)

    # ── پس‌زمینه: تیره + وینیت + بلور سبک ──
    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        # گرادیان عمودی ملایم — تیره‌تر در وسط
        w, h = surface.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            t = y / max(1, h - 1)
            # وسط پررنگ‌تر
            intensity = 0.45 + 0.25 * math.sin(math.pi * t)
            a = int(180 * intensity)
            pygame.draw.line(overlay, (0, 0, 0, a), (0, y), (w, y))
        surface.blit(overlay, (0, 0))

        # قاب نئونی ملایم در لبه‌ها
        border = pygame.Surface((w, h), pygame.SRCALPHA)
        glow_color = (*S.Palette.HUD_ACCENT, 40)
        pygame.draw.rect(border, glow_color, border.get_rect(), 3, border_radius=4)
        pygame.draw.rect(border, (0, 0, 0, 0), border.get_rect().inflate(-8, -8), 1)
        surface.blit(border, (0, 0))

    # ── عنوان ----
    def _draw_title(self, surface: pygame.Surface, slide: int, alpha: float) -> None:
        cx = S.Window.WIDTH // 2
        cy = S.Window.HEIGHT // 2 - 160 + slide

        text = "PAUSED"
        pulse = 1.0 + 0.03 * math.sin(self.time * 3.0)

        img = self.font_title.render(text, True, S.Palette.HUD_ACCENT)
        w = int(img.get_width() * pulse)
        h = int(img.get_height() * pulse)
        img_scaled = pygame.transform.smoothscale(img, (w, h))
        if alpha < 1.0:
            img_scaled.set_alpha(int(255 * alpha))

        rect = img_scaled.get_rect(center=(cx, cy))

        # هاله
        for layer in range(3, 0, -1):
            glow = pygame.transform.smoothscale(img, (w + layer * 12, h + layer * 12))
            gs = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
            gs.blit(glow, (0, 0))
            gs.set_alpha(int(28 * alpha))
            surface.blit(
                gs, gs.get_rect(center=(cx, cy)),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

        surface.blit(img_scaled, rect)

        # خط تزئینی
        line_w = 240
        line_y = cy + 50
        a = int(200 * alpha)
        pygame.draw.line(
            surface, (*S.Palette.HUD_ACCENT, a),
            (cx - line_w // 2, line_y),
            (cx + line_w // 2, line_y),
            1,
        )
        # نقطه‌های درخشان در دو سر
        if alpha > 0.3:
            pygame.draw.circle(surface, S.Palette.HUD_ACCENT, (cx - line_w // 2, line_y), 3)
            pygame.draw.circle(surface, S.Palette.HUD_ACCENT, (cx + line_w // 2, line_y), 3)

    # ── آمار پایین صفحه ----
    def _draw_stats(self, surface: pygame.Surface, alpha: float) -> None:
        if alpha < 0.6:
            return
        cx = S.Window.WIDTH // 2
        y = S.Window.HEIGHT - 90

        score_text = f"SCORE  {self._score:,}"
        wave_text  = f"WAVE  {self._wave:02d}"

        img1 = self.font_small.render(score_text, True, S.Palette.HUD_TEXT)
        img2 = self.font_small.render(wave_text, True, S.Palette.HUD_ACCENT)

        gap = 32
        total_w = img1.get_width() + img2.get_width() + gap
        x1 = cx - total_w // 2
        x2 = x1 + img1.get_width() + gap

        if alpha < 1.0:
            a = int(255 * alpha)
            img1.set_alpha(a)
            img2.set_alpha(a)

        surface.blit(img1, (x1, y))
        surface.blit(img2, (x2, y))

    # ── راهنمای پایین ──
    def _draw_hint(self, surface: pygame.Surface, alpha: float) -> None:
        if alpha < 0.7:
            return
        text = "↑↓ select  •  ENTER confirm  •  ESC/P resume"
        img = self.font_small.render(text, True, S.Palette.GREY)
        rect = img.get_rect(center=(S.Window.WIDTH // 2, S.Window.HEIGHT - 40))
        if alpha < 1.0:
            img.set_alpha(int(255 * alpha))
        surface.blit(img, rect)

    # ─────────────────────────────────────────────────────────────────────
    #  اکشن‌ها
    # ─────────────────────────────────────────────────────────────────────

    def _resume(self) -> None:
        self._play_ui("ui_cancel")
        # pop از Stack — Gameplay خودکار resume می‌شود
        self.game.scenes.pop()

    def _restart(self) -> None:
        self._play_ui("ui_confirm")
        # رفتن کامل به Gameplay — موج‌ها از اول
        self.game.scenes.go_to(S.SceneName.GAMEPLAY.value)

    def _main_menu(self) -> None:
        self._play_ui("ui_confirm")
        self.game.scenes.go_to(S.SceneName.MENU.value)

    def _quit(self) -> None:
        self._play_ui("ui_cancel")
        self.quit_game()

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی
    # ─────────────────────────────────────────────────────────────────────

    def _play_ui(self, sound: str) -> None:
        if self.audio:
            try:
                self.audio.play(sound)
            except Exception:
                pass


__all__ = ["PauseScene"]