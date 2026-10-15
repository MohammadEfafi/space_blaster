"""
scenes/leaderboard.py
=====================

صفحه‌ی جدول امتیازات (Hall of Fame) برای SPACE BLASTER.

ویژگی‌ها:
    • جدول تاپ ۱۰ امتیاز
    • نمایش رتبه، امتیاز، موج، سفینه، تاریخ
    • رنگ‌بندی ویژه برای ۳ رتبه‌ی برتر (طلا، نقره، برنز)
    • انیمیشن ورود نرم برای هر ردیف (staggered)
    • پس‌زمینه‌ی ستاره‌ای پارالاکس
    • حالت خالی (اگه هنوز بازی‌ای ثبت نشده)
    • دکمه‌ی BACK (ماوس + کیبورد)

ناوبری:
    ESC / Enter  → برگشت به منو
    ماوس          → کلیک روی BACK
"""

from __future__ import annotations

import math
import random
from typing import Callable, Optional

import pygame

from core import settings as S
from scenes.base import Scene
from systems.scores import HighScoreStore


# ═══════════════════════════════════════════════════════════════════════════
#  رنگ رتبه‌ها
# ═══════════════════════════════════════════════════════════════════════════

_RANK_COLORS: dict[int, tuple[tuple[int, int, int], str]] = {
    1: ((255, 210, 60), "★"),    # طلا
    2: ((200, 210, 230), "◆"),   # نقره
    3: ((210, 130, 70), "▲"),    # برنز
}
_DEFAULT_RANK_COLOR: tuple[int, int, int] = (140, 160, 200)


# ═══════════════════════════════════════════════════════════════════════════
#  دکمه‌ی ساده
# ═══════════════════════════════════════════════════════════════════════════

class _BackButton:
    """دکمه‌ی بازگشت."""

    def __init__(self, on_click: Callable[[], None], cx: int, cy: int) -> None:
        self.on_click = on_click
        self.rect = pygame.Rect(0, 0, 220, 50)
        self.rect.center = (cx, cy)
        self.hovered = False
        self._t = 0.0
        self._hover = 0.0

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        self._t += dt
        self.hovered = self.rect.collidepoint(mouse_pos)
        target = 1.0 if self.hovered else 0.0
        self._hover += (target - self._hover) * min(1.0, dt * 12.0)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()
                return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pad = int(6 * self._hover)
        rect = self.rect.inflate(pad * 2, pad)
        accent = S.Palette.HUD_ACCENT

        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (*accent, int(50 + 100 * self._hover)),
                         bg.get_rect(), border_radius=8)
        surface.blit(bg, rect.topleft)
        pygame.draw.rect(surface, accent, rect, 2, border_radius=8)

        if self._hover > 0.05:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (*accent, int(80 * self._hover)),
                             glow.get_rect(), 0, border_radius=8)
            surface.blit(glow, rect.topleft)

        text_color = S.Palette.WHITE if self.hovered else S.Palette.HUD_TEXT
        img = font.render("◀  BACK TO MENU", True, text_color)
        tr = img.get_rect(center=rect.center)
        shadow = font.render("◀  BACK TO MENU", True, (0, 0, 0))
        surface.blit(shadow, (tr.x + 2, tr.y + 2))
        surface.blit(img, tr)


# ═══════════════════════════════════════════════════════════════════════════
#  صحنه‌ی Leaderboard
# ═══════════════════════════════════════════════════════════════════════════

class LeaderboardScene(Scene):

    # ---- چیدمان ----
    TITLE_Y        = 60
    HEADER_Y       = 145
    TABLE_X        = 140
    TABLE_TOP      = 175
    ROW_H          = 34
    TABLE_W        = 620
    BACK_BTN_Y     = 590

    # ---- انیمیشن ----
    ROW_STAGGER    = 0.055      # مکث بین ظهور ردیف‌ها
    ROW_FADE_TIME  = 0.28

    def on_enter(self) -> None:
        # ---- فونت‌ها ----
        self.font_title  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.BIG, bold=True)
        self.font_header = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)
        self.font_row    = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.NORMAL, bold=True)
        self.font_row_sm = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL)
        self.font_hint   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.TINY)
        self.font_empty  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.LARGE, bold=True)

        # ---- داده ----
        self.store = HighScoreStore()
        self.scores = self.store.scores
        self.total_games = self.store.total_games

        # ---- ستاره‌ها ----
        self.stars = [
            [random.uniform(0, S.Window.WIDTH),
             random.uniform(0, S.Window.HEIGHT),
             random.uniform(S.FxCfg.STAR_SPEED_MIN, S.FxCfg.STAR_SPEED_MAX),
             random.uniform(0.6, 2.0)]
            for _ in range(140)
        ]

        # ---- زمان ----
        self._t = 0.0

        # ---- دکمه ----
        self.btn_back = _BackButton(
            self._go_back,
            cx=S.Window.WIDTH // 2,
            cy=self.BACK_BTN_Y,
        )

        # ---- Audio ----
        self.audio = getattr(self.game, "audio", None)

    def on_exit(self) -> None:
        self.stars.clear()

    # ─────────────────────────────────────────────────────────────────────
    #  ورودی
    # ─────────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._go_back()
                return
        self.btn_back.handle_event(event)

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self._t += dt
        for st in self.stars:
            st[1] += st[2] * dt
            if st[1] > S.Window.HEIGHT + 4:
                st[1] = -4
                st[0] = random.uniform(0, S.Window.WIDTH)

        mouse_pos = pygame.mouse.get_pos()
        self.btn_back.update(dt, mouse_pos)

    # ─────────────────────────────────────────────────────────────────────
    #  رندر
    # ─────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        # ---- پس‌زمینه ----
        surface.fill(S.Palette.BG_DEEP)
        for x, y, _, r in self.stars:
            pygame.draw.circle(surface, S.Palette.STAR_FAR,
                               (int(x), int(y)), max(1, int(r)))

        self._draw_background_halo(surface)
        self._draw_title(surface)

        if self.store.is_empty:
            self._draw_empty(surface)
        else:
            self._draw_header(surface)
            self._draw_rows(surface)

        self._draw_hint(surface)
        self.btn_back.draw(surface, self.font_row)

    # ── هاله‌ی پس‌زمینه ──
    def _draw_background_halo(self, surface: pygame.Surface) -> None:
        cx = S.Window.WIDTH // 2
        cy = S.Window.HEIGHT // 2
        r = 280
        halo = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for rr in range(r, 0, -8):
            a = int(4 * (1 - rr / r) ** 1.4)
            if a <= 0:
                continue
            pygame.draw.circle(halo, (60, 100, 180, a), (r, r), rr)
        surface.blit(halo, (cx - r, cy - r),
                     special_flags=pygame.BLEND_RGBA_ADD)

    # ── عنوان ──
    def _draw_title(self, surface: pygame.Surface) -> None:
        cx = S.Window.WIDTH // 2
        pulse = 1.0 + 0.025 * math.sin(self._t * 2.5)

        img = self.font_title.render("HALL OF FAME", True, S.Palette.MENU_TITLE)
        w = int(img.get_width() * pulse)
        h = int(img.get_height() * pulse)
        img_s = pygame.transform.smoothscale(img, (w, h))

        # هاله
        for layer in range(3, 0, -1):
            g = pygame.transform.smoothscale(img, (w + layer * 10, h + layer * 10))
            gs = pygame.Surface(g.get_size(), pygame.SRCALPHA)
            gs.blit(g, (0, 0))
            gs.set_alpha(28 - layer * 6)
            surface.blit(gs, gs.get_rect(center=(cx, self.TITLE_Y)),
                         special_flags=pygame.BLEND_RGBA_ADD)

        surface.blit(img_s, img_s.get_rect(center=(cx, self.TITLE_Y)))

        # خط تزئینی
        line_w = 400
        line_y = self.TITLE_Y + 40
        for i in range(line_w):
            t = i / line_w
            a = int(150 * math.sin(math.pi * t))
            x = cx - line_w // 2 + i
            pygame.draw.line(surface, (*S.Palette.MENU_TITLE, a),
                             (x, line_y), (x, line_y + 1))

        # تعداد بازی
        tg = self.font_hint.render(
            f"total missions played: {self.total_games}", True, S.Palette.GREY,
        )
        surface.blit(tg, tg.get_rect(center=(cx, line_y + 20)))

    # ── هدر جدول ──
    def _draw_header(self, surface: pygame.Surface) -> None:
        x = self.TABLE_X
        y = self.HEADER_Y

        # خط بالای هدر
        pygame.draw.line(surface, (80, 100, 140),
                         (x, y + 20), (x + self.TABLE_W, y + 20), 1)

        headers = [
            ("#", 0),
            ("SCORE", 70),
            ("WAVE", 240),
            ("SHIP", 330),
            ("DATE", 480),
        ]

        for label, offset in headers:
            img = self.font_header.render(label, True, S.Palette.HUD_ACCENT)
            surface.blit(img, (x + offset, y))

    # ── ردیف‌ها ──
    def _draw_rows(self, surface: pygame.Surface) -> None:
        x = self.TABLE_X
        y_start = self.TABLE_TOP

        for i, entry in enumerate(self.scores):
            # انیمیشن ورود staggered
            delay = i * self.ROW_STAGGER
            local_t = (self._t - delay) / self.ROW_FADE_TIME
            if local_t <= 0:
                continue
            t = min(1.0, local_t)
            # ease-out cubic
            e = 1.0 - (1.0 - t) ** 3

            alpha = int(255 * e)
            slide_x = int((1.0 - e) * -40)
            y = y_start + i * self.ROW_H

            self._draw_row(surface, x, y, i + 1, entry, alpha, slide_x)

        # خط پایین جدول
        bottom_y = y_start + len(self.scores) * self.ROW_H + 6
        pygame.draw.line(surface, (80, 100, 140),
                         (x, bottom_y), (x + self.TABLE_W, bottom_y), 1)

    # ── یک ردیف ──
    def _draw_row(
        self,
        surface: pygame.Surface,
        x: int, y: int,
        rank: int,
        entry,
        alpha: int,
        slide_x: int,
    ) -> None:
        # ---- رنگ رتبه ----
        rank_color, rank_symbol = _RANK_COLORS.get(rank, (_DEFAULT_RANK_COLOR, " "))

        # ---- پس‌زمینه‌ی ردیف ----
        row_rect = pygame.Rect(x - 8, y - 4, self.TABLE_W + 16, self.ROW_H - 2)
        bg_alpha = int(alpha * (0.15 if rank > 3 else 0.28))
        bg = pygame.Surface(row_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (*rank_color, bg_alpha),
                         bg.get_rect(), border_radius=4)
        surface.blit(bg, row_rect.topleft)

        # ---- بردر برای تاپ ۳ ----
        if rank <= 3:
            pygame.draw.rect(
                surface, rank_color,
                row_rect, 1, border_radius=4,
            )

        # ---- ستون‌ها ----
        # ۱. رتبه (سمبل + عدد)
        prefix = f"{rank_symbol} " if rank <= 3 else "  "
        rank_txt = f"{prefix}{rank:>2}"
        rank_img = self.font_row.render(rank_txt, True, rank_color)
        rank_img.set_alpha(alpha)
        surface.blit(rank_img, (x + slide_x, y))

        # ۲. امتیاز
        score_img = self.font_row.render(
            f"{entry.score:,}", True,
            S.Palette.YELLOW if rank == 1 else S.Palette.WHITE,
        )
        score_img.set_alpha(alpha)
        surface.blit(score_img, (x + 70 + slide_x, y))

        # ۳. موج
        wave_img = self.font_row_sm.render(f"{entry.wave}", True, S.Palette.CYAN)
        wave_img.set_alpha(alpha)
        surface.blit(wave_img, (x + 240 + slide_x, y + 2))

        # ۴. سفینه
        ship_img = self.font_row_sm.render(
            entry.ship.upper(), True, S.Palette.GREY,
        )
        ship_img.set_alpha(alpha)
        surface.blit(ship_img, (x + 330 + slide_x, y + 2))

        # ۵. تاریخ
        date_img = self.font_row_sm.render(
            entry.date_short(), True, S.Palette.GREY,
        )
        date_img.set_alpha(alpha)
        surface.blit(date_img, (x + 480 + slide_x, y + 2))

    # ── حالت خالی ──
    def _draw_empty(self, surface: pygame.Surface) -> None:
        cx = S.Window.WIDTH // 2
        cy = S.Window.HEIGHT // 2 - 40

        empty_img = self.font_empty.render(
            "NO MISSIONS YET", True, S.Palette.GREY,
        )
        surface.blit(empty_img, empty_img.get_rect(center=(cx, cy)))

        sub = self.font_row_sm.render(
            "Complete a mission to appear on the leaderboard",
            True, S.Palette.GREY,
        )
        surface.blit(sub, sub.get_rect(center=(cx, cy + 50)))

    # ── راهنما ──
    def _draw_hint(self, surface: pygame.Surface) -> None:
        img = self.font_hint.render(
            "ESC or ENTER  •  back to menu", True, S.Palette.GREY,
        )
        surface.blit(img, img.get_rect(center=(S.Window.WIDTH // 2, S.Window.HEIGHT - 22)))

    # ─────────────────────────────────────────────────────────────────────
    #  اکشن‌ها
    # ─────────────────────────────────────────────────────────────────────

    def _go_back(self) -> None:
        if self.audio is not None:
            try:
                self.audio.play("ui_cancel")
            except Exception:
                pass
        self.go_to(S.SceneName.MENU.value)


__all__ = ["LeaderboardScene"]