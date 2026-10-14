"""
scenes/gameover.py
==================

صفحه‌ی پایان بازی (Game Over) برای SPACE BLASTER.

این صحنه پس از نابودی سفینه‌ی پلیر نمایش داده می‌شود. تجربه‌ی کاربر
در اینجا بسیار مهم است: نه تلخ، نه بی‌روح — بلکه دراماتیک، زیبا، و
انگیزه‌بخش برای «دوباره تلاش کردن».

ویژگی‌ها:
    • ورود سینمایی: عنوان از دور می‌آید و fade می‌شود
    • نمایش آمار نهایی: امتیاز، موج، High Score
    • تشخیص خودکار رکورد جدید + جشن (ذرات طلایی، متن تپنده)
    • ذخیره‌ی High Score در فایل JSON (بین اجراها حفظ می‌شود)
    • پس‌زمینه‌ی ستاره‌ای آرام (کمتر از Gameplay)
    • رنگ‌بندی قرمز (شکست) + طلایی (رکورد جدید)
    • دکمه‌ها: Play Again, Main Menu, Quit
    • ناوبری کامل با کیبورد و ماوس
    • صدای ورود دراماتیک
    • تایپ‌رایتر برای آمار (کمی نمایشی)

ذخیره‌سازی:
    فایل saves/highscore.json با ساختار:
        {
          "high_score": 12540,
          "best_wave": 7,
          "total_games": 23,
          "last_played": "2024-01-15T20:30:00"
        }
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import pygame

from core import settings as S
from scenes.base import Scene
from systems.audio import AudioSystem


# ═══════════════════════════════════════════════════════════════════════════
#  مدیریت فایل رکورد (High Score Persistence)
# ═══════════════════════════════════════════════════════════════════════════

class HighScoreStore:
    """
    ذخیره و بارگذاری رکوردها از/به یک فایل JSON.

    اگر فایل نباشد یا خوانا نباشد، مقادیر پیش‌فرض استفاده می‌شوند.
    ذخیره‌سازی خطا-tolerant است: خطا باعث کرش نمی‌شود، فقط لاگ می‌شود.
    """

    DEFAULT: dict = {
        "high_score": 0,
        "best_wave": 0,
        "total_games": 0,
        "last_played": "",
    }

    def __init__(self, path: Optional[Path] = None) -> None:
        if path is None:
            path = S.SAVE_DIR / "highscore.json"
        self.path: Path = Path(path)
        self.data: dict = dict(self.DEFAULT)
        self._load()

    def _load(self) -> None:
        try:
            if self.path.is_file():
                with self.path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    for k, v in loaded.items():
                        if k in self.DEFAULT:
                            self.data[k] = v
        except Exception as exc:
            print(f"[HighScore] Failed to load '{self.path}': {exc}")

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[HighScore] Failed to save '{self.path}': {exc}")

    # ── API ──

    def submit(
        self,
        score: int,
        wave: int,
    ) -> tuple[bool, bool]:
        """
        ثبت یک بازی جدید.

        برمی‌گرداند: (new_high_score, new_best_wave)
        """
        new_high = False
        new_best_wave = False

        if score > self.data.get("high_score", 0):
            self.data["high_score"] = int(score)
            new_high = True

        if wave > self.data.get("best_wave", 0):
            self.data["best_wave"] = int(wave)
            new_best_wave = True

        self.data["total_games"] = int(self.data.get("total_games", 0)) + 1
        self.data["last_played"] = datetime.now().isoformat(timespec="seconds")

        self.save()
        return new_high, new_best_wave

    @property
    def high_score(self) -> int:
        return int(self.data.get("high_score", 0))

    @property
    def best_wave(self) -> int:
        return int(self.data.get("best_wave", 0))

    @property
    def total_games(self) -> int:
        return int(self.data.get("total_games", 0))


# ═══════════════════════════════════════════════════════════════════════════
#  دکمه
# ═══════════════════════════════════════════════════════════════════════════

class _GameOverButton:
    """دکمه‌ی صفحه‌ی پایان — بسیار شبیه دکمه‌های منو، با استایل متفاوت."""

    def __init__(
        self,
        label: str,
        action: Callable[[], None],
        y: int,
        *,
        width: int = 260,
        height: int = 48,
        accent: tuple[int, int, int] = S.Palette.HUD_ACCENT,
    ) -> None:
        self.label = label
        self.action = action
        self.width = width
        self.height = height
        self.accent = accent

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

    def trigger_click(self) -> None:
        self._click_amt = 1.0
        self.action()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._rect.collidepoint(event.pos):
                self.trigger_click()
                return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pad_x = int(8 * self._hover_amt)
        pad_y = int(4 * self._hover_amt)
        rect = self._rect.inflate(pad_x * 2, pad_y * 2)

        alpha = int(80 + 130 * self._hover_amt)

        # پس‌زمینه
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (*self.accent, alpha // 3), bg.get_rect(), border_radius=8)
        surface.blit(bg, rect.topleft)

        # حاشیه
        border_alpha = int(150 + 105 * self._hover_amt)
        border = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            border, (*self.accent, border_alpha),
            border.get_rect(), 2, border_radius=8,
        )
        surface.blit(border, rect.topleft)

        # درخشش
        if self._hover_amt > 0.05:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            ga = int(80 * self._hover_amt)
            pygame.draw.rect(glow, (*self.accent, ga), glow.get_rect(),
                             0, border_radius=8)
            surface.blit(glow, rect.topleft)

        # متن
        text_color = S.Palette.WHITE if self.hovered else S.Palette.HUD_TEXT
        img = font.render(self.label, True, text_color)
        text_rect = img.get_rect(center=rect.center)

        shadow = font.render(self.label, True, (0, 0, 0))
        surface.blit(shadow, (text_rect.x + 2, text_rect.y + 2))
        surface.blit(img, text_rect)

        # فلش‌های انتخاب
        if self.selected:
            pulse = 6 + int(3 * math.sin(self._t * 6.0))
            ax = rect.left - 20 - int(6 * self._hover_amt) - pulse
            ay = rect.centery
            pygame.draw.polygon(surface, self.accent, [
                (ax, ay - 7), (ax + 10, ay), (ax, ay + 7),
            ])
            rx = rect.right + 10 + int(6 * self._hover_amt) + pulse
            pygame.draw.polygon(surface, self.accent, [
                (rx, ay - 7), (rx - 10, ay), (rx, ay + 7),
            ])

        # فلاش
        if self._click_amt > 0.01:
            flash = pygame.Surface(rect.size, pygame.SRCALPHA)
            fa = int(140 * self._click_amt)
            pygame.draw.rect(flash, (*S.Palette.WHITE, fa), flash.get_rect(),
                             border_radius=8)
            surface.blit(flash, rect.topleft)


# ═══════════════════════════════════════════════════════════════════════════
#  ذره‌ی جشن (برای رکورد جدید)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class _CelebrationParticle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple[int, int, int]
    size: float
    angle: float
    angle_speed: float


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس GameOverScene
# ═══════════════════════════════════════════════════════════════════════════

class GameOverScene(Scene):
    """صفحه‌ی پایان بازی."""

    # ---- زمان‌بندی ----
    TITLE_IN_TIME: float = 0.9       # ثانیه — ورود عنوان
    STATS_REVEAL_DELAY: float = 0.5  # مکث قبل از نمایش آمار
    STATS_REVEAL_TIME: float = 0.6   # ثانیه — نمایش آمار
    BUTTONS_DELAY: float = 1.6       # مکث قبل از نمایش دکمه‌ها
    BUTTONS_FADE_TIME: float = 0.4

    # ─────────────────────────────────────────────────────────────────────
    #  چرخه‌ی حیات
    # ─────────────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        # ---- فونت‌ها ----
        self.font_title  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.HUGE, bold=True)
        self.font_sub    = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.LARGE, bold=True)
        self.font_label  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.NORMAL)
        self.font_value  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.BIG, bold=True)
        self.font_btn    = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.NORMAL, bold=True)
        self.font_small  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL)

        # ---- آمار ----
        self.score = int(getattr(self.game, "last_score", 0))
        self.wave = int(getattr(self.game, "last_wave", 0))

        # ---- رکورد ----
        self.store = HighScoreStore()
        self._prev_high = self.store.high_score
        self.is_new_high, self.is_new_best_wave = self.store.submit(self.score, self.wave)
        self.high_score = self.store.high_score
        self.best_wave = self.store.best_wave
        self.total_games = self.store.total_games

        # ---- زمان‌بندی ----
        self._t: float = 0.0
        self._t_title: float = 0.0        # 0..1 پیشرفت ورود عنوان
        self._t_stats: float = 0.0        # 0..1 پیشرفت نمایش آمار
        self._t_buttons: float = 0.0      # 0..1 پیشرفت نمایش دکمه‌ها

        # ---- ستاره‌های پس‌زمینه ----
        self.stars: list[list[float]] = []
        for _ in range(80):
            self.stars.append([
                random.uniform(0, S.Window.WIDTH),
                random.uniform(0, S.Window.HEIGHT),
                random.uniform(4.0, 22.0),
                random.uniform(0.6, 2.0),
            ])

        # ---- ذرات جشن ----
        self.celebration: list[_CelebrationParticle] = []
        if self.is_new_high:
            self._spawn_celebration_burst()

        # ---- دکمه‌ها ----
        y0 = S.Window.HEIGHT - 190
        self.buttons: list[_GameOverButton] = [
            _GameOverButton(
                "PLAY AGAIN", self._play_again, y=y0,
                accent=S.Palette.HUD_ACCENT,
            ),
            _GameOverButton(
                "MAIN MENU", self._main_menu, y=y0 + 60,
                accent=S.Palette.HUD_ACCENT,
            ),
            _GameOverButton(
                "QUIT", self._quit, y=y0 + 120,
                accent=S.Palette.HUD_HP,
            ),
        ]
        self.selected_idx = 0
        self.buttons[self.selected_idx].selected = True

        # ---- Audio ----
        self.audio: Optional[AudioSystem] = getattr(self.game, "audio", None)
        if self.audio:
            # موسیقی منو در پس‌زمینه
            self.audio.play_music("music_menu", loop=True, fade_ms=800)

    def on_exit(self) -> None:
        self.buttons.clear()
        self.stars.clear()
        self.celebration.clear()

    # ─────────────────────────────────────────────────────────────────────
    #  ورودی
    # ─────────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        # ---- فقط وقتی دکمه‌ها ظاهر شده‌اند ----
        if self._t_buttons < 0.5:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self._move_selection(+1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._move_selection(-1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.buttons[self.selected_idx].trigger_click()
            elif event.key == pygame.K_ESCAPE:
                # ESC → Main Menu (رفتار امن)
                self._main_menu()

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
        self._t += dt

        # ---- پیشرفت‌های انیمیشن ----
        if self._t_title < 1.0:
            self._t_title = min(1.0, self._t_title + dt / self.TITLE_IN_TIME)

        # آمار بعد از مکث ظاهر می‌شود
        if self._t > self.STATS_REVEAL_DELAY and self._t_stats < 1.0:
            self._t_stats = min(1.0, self._t_stats + dt / self.STATS_REVEAL_TIME)

        # دکمه‌ها دیرتر
        if self._t > self.BUTTONS_DELAY and self._t_buttons < 1.0:
            self._t_buttons = min(1.0, self._t_buttons + dt / self.BUTTONS_FADE_TIME)

        # ---- ستاره‌ها ----
        for st in self.stars:
            st[1] += st[2] * dt
            if st[1] > S.Window.HEIGHT + 4:
                st[1] = -4
                st[0] = random.uniform(0, S.Window.WIDTH)

        # ---- ذرات جشن ----
        if self.celebration:
            alive: list[_CelebrationParticle] = []
            for p in self.celebration:
                p.life -= dt
                if p.life <= 0.0:
                    continue
                p.vy += 140.0 * dt
                p.vx *= (1.0 - dt * 1.4)
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.angle += p.angle_speed * dt
                alive.append(p)
            self.celebration = alive

            # هر چند وقت یک‌بار، ذرات جدید (فوران مداوم)
            if self.is_new_high and random.random() < dt * 5.0:
                self._spawn_celebration_burst(count=8, small=True)

        # ---- دکمه‌ها ----
        if self._t_buttons > 0.5:
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
        # ---- پس‌زمینه ----
        surface.fill(S.Palette.BG_DEEP)
        self._draw_backdrop(surface)
        self._draw_stars(surface)
        self._draw_vignette(surface)

        # ---- ذرات جشن (روی پس‌زمینه) ----
        self._draw_celebration(surface)

        # ---- عنوان ----
        self._draw_title(surface)

        # ---- آمار ----
        self._draw_stats(surface)

        # ---- دکمه‌ها ----
        if self._t_buttons > 0.01:
            self._draw_buttons(surface)

        # ---- پانویس ----
        self._draw_footer(surface)

    # ── پس‌زمینه: گرادیان رنگی ملایم ──
    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        # گرادیان عمودی قرمز-تیره (تضاد با پس‌زمینه‌ی آبی گیم‌پلی)
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        top = (12, 5, 15)
        bot = (5, 8, 20)
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(top[0] * (1 - t) + bot[0] * t)
            g = int(top[1] * (1 - t) + bot[1] * t)
            b = int(top[2] * (1 - t) + bot[2] * t)
            pygame.draw.line(overlay, (r, g, b, 255), (0, y), (w, y))
        surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    def _draw_stars(self, surface: pygame.Surface) -> None:
        for x, y, _, r in self.stars:
            pygame.draw.circle(
                surface, S.Palette.STAR_FAR,
                (int(x), int(y)), max(1, int(r * 0.7)),
            )

    def _draw_vignette(self, surface: pygame.Surface) -> None:
        """وینیت قرمز ملایم در اطراف صفحه."""
        w, h = surface.get_size()
        thickness = 120
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(thickness):
            alpha = int(70 * (1 - i / thickness) ** 1.6)
            if alpha <= 0:
                continue
            color = (60, 0, 20, alpha)
            pygame.draw.line(overlay, color, (i, 0), (i, h))
            pygame.draw.line(overlay, color, (w - 1 - i, 0), (w - 1 - i, h))
        for i in range(thickness // 2):
            alpha = int(50 * (1 - i / (thickness // 2)) ** 1.6)
            if alpha <= 0:
                continue
            color = (60, 0, 20, alpha)
            pygame.draw.line(overlay, color, (0, i), (w, i))
            pygame.draw.line(overlay, color, (0, h - 1 - i), (w, h - 1 - i))
        surface.blit(overlay, (0, 0))

    # ── عنوان: GAME OVER با ورود دراماتیک ──
    def _draw_title(self, surface: pygame.Surface) -> None:
        t = self._t_title
        # easing ease-out cubic
        e = 1.0 - (1.0 - t) ** 3
        scale = 0.6 + 0.4 * e          # از ۰.۶ به ۱.۰
        alpha = e

        cx = S.Window.WIDTH // 2
        cy = 130

        # متن
        text = "GAME OVER"
        img = self.font_title.render(text, True, S.Palette.HUD_HP)
        w = max(1, int(img.get_width() * scale))
        h = max(1, int(img.get_height() * scale))
        img_scaled = pygame.transform.smoothscale(img, (w, h))
        if alpha < 1.0:
            img_scaled.set_alpha(int(255 * alpha))

        rect = img_scaled.get_rect(center=(cx, cy))

        # هاله‌ی قرمز
        if alpha > 0.15:
            for layer in range(4, 0, -1):
                glow = pygame.transform.smoothscale(
                    img, (w + layer * 14, h + layer * 14)
                )
                gs = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
                gs.blit(glow, (0, 0))
                gs.set_alpha(int(28 * alpha))
                surface.blit(
                    gs, gs.get_rect(center=(cx, cy)),
                    special_flags=pygame.BLEND_RGBA_ADD,
                )

        surface.blit(img_scaled, rect)

        # زیرعنوان: اگر رکورد جدید بوده
        if self.is_new_high and alpha > 0.5:
            pulse = 1.0 + 0.08 * math.sin(self._t * 5.0)
            sub_img = self.font_sub.render("★ NEW HIGH SCORE ★", True, S.Palette.YELLOW)
            w2 = int(sub_img.get_width() * pulse)
            h2 = int(sub_img.get_height() * pulse)
            sub_scaled = pygame.transform.smoothscale(sub_img, (w2, h2))
            sub_rect = sub_scaled.get_rect(center=(cx, cy + 70))
            # هاله‌ی طلایی
            for layer in range(3, 0, -1):
                glow = pygame.transform.smoothscale(
                    sub_img, (w2 + layer * 10, h2 + layer * 10)
                )
                gs = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
                gs.blit(glow, (0, 0))
                gs.set_alpha(40)
                surface.blit(
                    gs, gs.get_rect(center=sub_rect.center),
                    special_flags=pygame.BLEND_RGBA_ADD,
                )
            surface.blit(sub_scaled, sub_rect)

    # ── آمار ──
    def _draw_stats(self, surface: pygame.Surface) -> None:
        if self._t_stats < 0.01:
            return

        alpha = self._t_stats
        cx = S.Window.WIDTH // 2
        y0 = 260

        # سه ردیف: SCORE، WAVE، BEST
        rows = [
            ("FINAL SCORE", f"{self.score:,}",
             S.Palette.YELLOW if self.is_new_high else S.Palette.WHITE),
            ("WAVE REACHED", f"{self.wave}",
             S.Palette.YELLOW if self.is_new_best_wave else S.Palette.WHITE),
            ("BEST SCORE", f"{self.high_score:,}", S.Palette.HUD_ACCENT),
        ]

        row_h = 58
        # پس‌زمینه‌ی نیمه‌شفاف پشت آمار (پنل)
        panel_w = 480
        panel_h = row_h * len(rows) + 40
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, int(120 * alpha)))
        panel_rect = panel.get_rect(center=(cx, y0 + panel_h // 2))
        pygame.draw.rect(
            panel, (*S.Palette.HUD_ACCENT, int(90 * alpha)),
            panel.get_rect(), 1, border_radius=10,
        )
        surface.blit(panel, panel_rect.topleft)

        # ردیف‌ها
        for i, (label, value, color) in enumerate(rows):
            ry = y0 + 30 + i * row_h

            lbl_img = self.font_label.render(label, True, S.Palette.GREY)
            val_img = self.font_value.render(value, True, color)

            if alpha < 1.0:
                lbl_img.set_alpha(int(255 * alpha))
                val_img.set_alpha(int(255 * alpha))

            # چپ: label، راست: value
            surface.blit(lbl_img, (panel_rect.x + 30, ry))
            vrect = val_img.get_rect()
            vrect.right = panel_rect.right - 30
            vrect.centery = ry + lbl_img.get_height() // 2
            surface.blit(val_img, vrect)

    # ── دکمه‌ها ──
    def _draw_buttons(self, surface: pygame.Surface) -> None:
        alpha = self._t_buttons

        if alpha < 1.0:
            # رسم روی سطح موقت و سپس blit با آلفا
            temp = pygame.Surface((S.Window.WIDTH, S.Window.HEIGHT), pygame.SRCALPHA)
            for b in self.buttons:
                b.draw(temp, self.font_btn)
            temp.set_alpha(int(255 * alpha))
            surface.blit(temp, (0, 0))
        else:
            for b in self.buttons:
                b.draw(surface, self.font_btn)

    # ── پانویس ──
    def _draw_footer(self, surface: pygame.Surface) -> None:
        hint = "↑↓ select  •  ENTER confirm  •  ESC menu"
        img = self.font_small.render(hint, True, S.Palette.GREY)
        rect = img.get_rect(center=(S.Window.WIDTH // 2, S.Window.HEIGHT - 26))
        surface.blit(img, rect)

        # تعداد بازی‌های انجام‌شده
        if self.total_games > 1:
            games_img = self.font_small.render(
                f"GAMES PLAYED: {self.total_games}", True, S.Palette.GREY,
            )
            grect = games_img.get_rect()
            grect.bottomright = (S.Window.WIDTH - 12, S.Window.HEIGHT - 10)
            surface.blit(games_img, grect)

    # ── ذرات جشن ──
    def _draw_celebration(self, surface: pygame.Surface) -> None:
        for p in self.celebration:
            t = 1.0 - (p.life / p.max_life)
            alpha = int(255 * (1.0 - t * t))
            if alpha <= 0:
                continue
            size = max(1, int(p.size * (1.0 - t * 0.5)))
            # رسم مربع چرخان
            ang = math.radians(p.angle)
            cs, sn = math.cos(ang), math.sin(ang)
            pts = [
                (p.x + cs * -size - sn * -size, p.y + sn * -size + cs * -size),
                (p.x + cs * size - sn * -size,  p.y + sn * size + cs * -size),
                (p.x + cs * size - sn * size,   p.y + sn * size + cs * size),
                (p.x + cs * -size - sn * size,  p.y + sn * -size + cs * size),
            ]
            tmp = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
            local = [(x - p.x + size * 1.5, y - p.y + size * 1.5) for x, y in pts]
            pygame.draw.polygon(tmp, (*p.color, alpha), local)
            surface.blit(
                tmp, (p.x - size * 1.5, p.y - size * 1.5),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    # ─────────────────────────────────────────────────────────────────────
    #  جشن (رکورد جدید)
    # ─────────────────────────────────────────────────────────────────────

    def _spawn_celebration_burst(
        self,
        count: int = 26,
        *,
        small: bool = False,
    ) -> None:
        """انفجار ذرات طلایی از مرکز/گوشه‌ها."""
        cx = S.Window.WIDTH // 2
        cy = 180  # نزدیک عنوان

        for _ in range(count):
            # از دو طرف بالای صفحه پرت می‌شوند
            side = random.choice((-1, 1))
            origin_x = cx + side * random.uniform(40, 240)
            origin_y = cy + random.uniform(-30, 30)

            angle = random.uniform(0, math.tau)
            speed = random.uniform(80, 240) * (0.6 if small else 1.0)
            life = random.uniform(0.9, 1.8)
            color = random.choice([
                S.Palette.YELLOW,
                S.Palette.POWERUP_CORE,
                S.Palette.WHITE,
                S.Palette.HUD_ACCENT,
            ])
            self.celebration.append(_CelebrationParticle(
                x=origin_x,
                y=origin_y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 60,  # کمی به بالا
                life=life,
                max_life=life,
                color=color,
                size=random.uniform(2.5, 5.5),
                angle=random.uniform(0, 360),
                angle_speed=random.uniform(-360, 360),
            ))

    # ─────────────────────────────────────────────────────────────────────
    #  اکشن‌ها
    # ─────────────────────────────────────────────────────────────────────

    def _play_again(self) -> None:
        self._play_ui("ui_confirm")
        self.go_to(S.SceneName.GAMEPLAY.value)

    def _main_menu(self) -> None:
        self._play_ui("ui_cancel")
        self.go_to(S.SceneName.MENU.value)

    def _quit(self) -> None:
        self._play_ui("ui_cancel")
        self.quit_game()

    def _play_ui(self, sound: str) -> None:
        if self.audio:
            try:
                self.audio.play(sound)
            except Exception:
                pass


__all__ = ["GameOverScene", "HighScoreStore"]