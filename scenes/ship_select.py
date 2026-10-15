"""
scenes/ship_select.py
=====================

صفحه‌ی انتخاب سفینه (Ship Selection Scene) برای SPACE BLASTER.
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


# ═══════════════════════════════════════════════════════════════════════════
#  تنظیمات چیدمان
# ═══════════════════════════════════════════════════════════════════════════

W = S.Window.WIDTH          # 900
H = S.Window.HEIGHT         # 650

TITLE_Y        = 60
SUBTITLE_Y     = 100

PREVIEW_CX     = 260
PREVIEW_CY     = 285
PREVIEW_SCALE  = 2.4

STATS_X        = 500
STATS_Y        = 200
STATS_ROW_H    = 34
STATS_WIDTH    = 350
STATS_BAR_H    = 10

NAME_Y         = 445
ROLE_Y         = 478
DESC_Y         = 512

BTN_Y          = 585
BTN_W          = 170
BTN_H          = 46
BTN_GAP        = 60

HINT_Y         = H - 22


# ═══════════════════════════════════════════════════════════════════════════
#  نوار آمار
# ═══════════════════════════════════════════════════════════════════════════

class _StatBar:
    def __init__(self, label: str, value: int) -> None:
        self.label = label
        self.target = float(value)
        self.displayed = float(value)

    def update(self, dt: float, new_target: int) -> None:
        self.target = float(new_target)
        diff = self.target - self.displayed
        if abs(diff) < 0.01:
            self.displayed = self.target
        else:
            self.displayed += diff * min(1.0, dt * 8.0)

    def draw(
        self,
        surface: pygame.Surface,
        x: int, y: int,
        width: int, height: int,
        font: pygame.font.Font,
        color: tuple[int, int, int],
    ) -> None:
        # ---- برچسب ----
        label_img = font.render(self.label, True, S.Palette.GREY)
        surface.blit(label_img, (x, y - 1))

        # ---- نوار ----
        bar_x = x + 95
        bar_w = width - 95 - 48

        bg = pygame.Surface((bar_w, height), pygame.SRCALPHA)
        bg.fill((10, 18, 32, 220))
        surface.blit(bg, (bar_x, y))

        ratio = max(0.0, min(1.0, self.displayed / 5.0))
        filled = int(bar_w * ratio)
        if filled > 0:
            pygame.draw.rect(surface, color, (bar_x, y, filled, height))

        pygame.draw.rect(surface, color, (bar_x, y, bar_w, height), 1)

        # ---- عدد ----
        val_img = font.render(f"{int(round(self.displayed))}/5", True, S.Palette.WHITE)
        surface.blit(val_img, (bar_x + bar_w + 8, y - 1))


# ═══════════════════════════════════════════════════════════════════════════
#  دکمه
# ═══════════════════════════════════════════════════════════════════════════

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
        self.selected = False
        self._t = 0.0
        self._hover = 0.0
        self._click = 0.0

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        self._t += dt
        is_over = self.rect.collidepoint(mouse_pos)
        self.hovered = is_over or self.selected
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
        pad_x = int(8 * self._hover)
        pad_y = int(4 * self._hover)
        rect = self.rect.inflate(pad_x * 2, pad_y * 2)

        # ---- پس‌زمینه ----
        alpha = int(80 + 140 * self._hover)
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (*self.accent, alpha // 3), bg.get_rect(), border_radius=8)
        surface.blit(bg, rect.topleft)

        # ---- حاشیه ----
        border_alpha = int(160 + 95 * self._hover)
        border_col = tuple(min(255, c) for c in self.accent) + (border_alpha,)
        border_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(border_surf, border_col, border_surf.get_rect(), 2, border_radius=8)
        surface.blit(border_surf, rect.topleft)

        # ---- درخشش ----
        if self._hover > 0.05:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                glow, (*self.accent, int(70 * self._hover)),
                glow.get_rect(), 0, border_radius=8,
            )
            surface.blit(glow, rect.topleft)

        # ---- متن ----
        text_color = S.Palette.WHITE if self.hovered else S.Palette.HUD_TEXT
        img = font.render(self.label, True, text_color)
        text_rect = img.get_rect(center=rect.center)
        shadow = font.render(self.label, True, (0, 0, 0))
        surface.blit(shadow, (text_rect.x + 2, text_rect.y + 2))
        surface.blit(img, text_rect)

        # ---- فلاش کلیک ----
        if self._click > 0.01:
            flash = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(
                flash, (255, 255, 255, int(140 * self._click)),
                flash.get_rect(), 0, border_radius=8,
            )
            surface.blit(flash, rect.topleft)


# ═══════════════════════════════════════════════════════════════════════════
#  صحنه‌ی انتخاب سفینه
# ═══════════════════════════════════════════════════════════════════════════

class ShipSelectScene(Scene):

    TRANSITION_TIME = 0.22

    # ─────────────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        # ---- فونت‌ها ----
        self.font_title = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.BIG, bold=True)
        self.font_name  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.LARGE, bold=True)
        self.font_role  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)
        self.font_stat  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)
        self.font_desc  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL)
        self.font_btn   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.NORMAL, bold=True)
        self.font_hint  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.TINY)

        # ---- سفینه‌ی فعلی ----
        self.current_key = getattr(self.game, "selected_ship", DEFAULT_SHIP_KEY)
        if self.current_key not in SHIP_LIST:
            self.current_key = DEFAULT_SHIP_KEY

        # ---- نمونه‌ی پیش‌نمایش ----
        self._preview_cache: dict = {}
        for key in SHIP_LIST:
            try:
                ship = SHIP_CLASSES[key](scene=None)
                ship.radius = ship.RADIUS * PREVIEW_SCALE
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

        # ---- انیمیشن تعویض ----
        self._transition_t = 1.0
        self._transition_dir = 1

        # ---- رنگ ----
        self._color_curr = tuple(float(c) for c in info.color)
        self._color_target = info.color
        self._accent = info.color

        # ---- ستاره‌ها ----
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
            "◀  BACK", self._go_back,
            cx - BTN_W // 2 - BTN_GAP, BTN_Y,
            accent=(140, 160, 200),
        )
        self.btn_select = _Button(
            "SELECT  ▶", self._confirm_select,
            cx + BTN_W // 2 + BTN_GAP, BTN_Y,
            accent=info.color,
        )

        # ---- Audio ----
        self.audio = getattr(self.game, "audio", None)

        # ---- قفل ورودی ----
        self._input_lock = False

    def on_exit(self) -> None:
        self._preview_cache.clear()

    # ─────────────────────────────────────────────────────────────────────
    #  ورودی
    # ─────────────────────────────────────────────────────────────────────

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

        for b in (self.btn_back, self.btn_select):
            if b.handle_event(event):
                break

    def _switch(self, direction: int) -> None:
        if self._input_lock:
            return
        self._input_lock = True
        self._transition_dir = direction
        self._transition_t = 0.0

        if direction > 0:
            self.current_key = next_ship_key(self.current_key)
        else:
            self.current_key = prev_ship_key(self.current_key)

        info = SHIP_INFO[self.current_key]
        self._color_target = info.color
        self.btn_select.accent = info.color
        self._play_ui("ui_move")

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        # ---- انیمیشن تعویض ----
        if self._transition_t < 1.0:
            self._transition_t = min(1.0, self._transition_t + dt / self.TRANSITION_TIME)
        else:
            self._input_lock = False

        # ---- ستاره‌ها ----
        for st in self.stars:
            st[1] += st[2] * dt
            if st[1] > H + 4:
                st[1] = -4
                st[0] = random.uniform(0, W)

        # ---- نوارهای آمار ----
        info = SHIP_INFO[self.current_key]
        targets = [info.speed, info.hp, info.fire_rate, info.damage, info.agility]
        for bar, t in zip(self.stats, targets):
            bar.update(dt, t)

        # ---- رنگ lerp ----
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

    # ─────────────────────────────────────────────────────────────────────
    #  رندر
    # ─────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(S.Palette.BG_DEEP)

        for x, y, _, r in self.stars:
            pygame.draw.circle(surface, S.Palette.STAR_FAR,
                               (int(x), int(y)), max(1, int(r)))

        self._draw_nebula(surface)
        self._draw_title(surface)
        self._draw_preview(surface)
        self._draw_arrows(surface)
        self._draw_stats(surface)
        self._draw_info(surface)

        self.btn_back.draw(surface, self.font_btn)
        self.btn_select.draw(surface, self.font_btn)

        self._draw_hint(surface)

    def _draw_nebula(self, surface: pygame.Surface) -> None:
        cx = PREVIEW_CX + math.sin(self.time * 0.3) * 20
        cy = PREVIEW_CY + math.cos(self.time * 0.25) * 15
        r = 200
        aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for rr in range(r, 0, -8):
            a = int(5 * (1 - rr / r) ** 1.5)
            if a <= 0:
                continue
            pygame.draw.circle(aura, (*self._accent, a), (r, r), rr)
        surface.blit(aura, (int(cx - r), int(cy - r)),
                     special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_title(self, surface: pygame.Surface) -> None:
        cx = W // 2
        pulse = 1.0 + 0.02 * math.sin(self.time * 2.5)

        img = self.font_title.render("SELECT YOUR SHIP", True, self._accent)
        w = int(img.get_width() * pulse)
        h = int(img.get_height() * pulse)
        img_s = pygame.transform.smoothscale(img, (w, h))

        for layer in range(3, 0, -1):
            glow = pygame.transform.smoothscale(img, (w + layer * 10, h + layer * 10))
            gs = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
            gs.blit(glow, (0, 0))
            gs.set_alpha(30 - layer * 6)
            surface.blit(gs, gs.get_rect(center=(cx, TITLE_Y)),
                         special_flags=pygame.BLEND_RGBA_ADD)

        surface.blit(img_s, img_s.get_rect(center=(cx, TITLE_Y)))

        sub = self.font_role.render("CHOOSE WISELY", True, S.Palette.GREY)
        surface.blit(sub, sub.get_rect(center=(cx, SUBTITLE_Y)))

        line_y = SUBTITLE_Y + 22
        line_w = 400
        pygame.draw.line(surface, (*self._accent, 160),
                         (cx - line_w // 2, line_y),
                         (cx + line_w // 2, line_y), 1)

    def _draw_preview(self, surface: pygame.Surface) -> None:
        preview = self._preview_cache.get(self.current_key)
        if preview is None:
            return

        # ---- انیمیشن ----
        t = self._transition_t
        e = 1.0 - (1.0 - t) ** 3
        offset_x = int((1.0 - e) * -self._transition_dir * 120)
        alpha = e

        cx = PREVIEW_CX + offset_x
        cy = PREVIEW_CY

        # ---- آماده‌سازی preview ----
        preview.x = cx
        preview.y = cy
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
            size = int(preview.radius * 5)
            tmp = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            preview.x = size
            preview.y = size
            preview.draw_entity(tmp)
            tmp.set_alpha(int(255 * alpha))
            surface.blit(tmp, (cx - size, cy - size))

    def _draw_arrows(self, surface: pygame.Surface) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.time * 4.0)
        offset = int(8 + 6 * pulse)
        cy = PREVIEW_CY

        lx = PREVIEW_CX - 145 - offset
        pygame.draw.polygon(surface, self._accent, [
            (lx, cy - 16), (lx + 22, cy), (lx, cy + 16),
        ])

        rx = PREVIEW_CX + 145 + offset
        pygame.draw.polygon(surface, self._accent, [
            (rx, cy - 16), (rx - 22, cy), (rx, cy + 16),
        ])

        idx = SHIP_LIST.index(self.current_key) + 1
        total = len(SHIP_LIST)
        idx_img = self.font_role.render(f"{idx} / {total}", True, S.Palette.GREY)
        surface.blit(idx_img, idx_img.get_rect(center=(PREVIEW_CX, PREVIEW_CY + 145)))

    def _draw_stats(self, surface: pygame.Surface) -> None:
        for i, bar in enumerate(self.stats):
            y = STATS_Y + i * STATS_ROW_H
            bar.draw(surface, STATS_X, y, STATS_WIDTH, STATS_BAR_H,
                     self.font_stat, self._accent)

    def _draw_info(self, surface: pygame.Surface) -> None:
        cx = W // 2
        info = SHIP_INFO[self.current_key]

        # ---- نام ----
        name_img = self.font_name.render(info.name, True, self._accent)
        glow = pygame.Surface(name_img.get_size(), pygame.SRCALPHA)
        glow.blit(name_img, (0, 0))
        glow.set_alpha(80)
        surface.blit(glow, glow.get_rect(center=(cx + 2, NAME_Y + 2)),
                     special_flags=pygame.BLEND_RGBA_ADD)
        surface.blit(name_img, name_img.get_rect(center=(cx, NAME_Y)))

        # ---- نقش + سختی ----
        role_txt = f"{info.role}  ·  {info.difficulty}"
        role_img = self.font_role.render(role_txt, True, S.Palette.GREY)
        surface.blit(role_img, role_img.get_rect(center=(cx, ROLE_Y)))

        # ---- توضیحات ----
        desc_img = self.font_desc.render(info.description, True, S.Palette.HUD_TEXT)
        surface.blit(desc_img, desc_img.get_rect(center=(cx, DESC_Y)))

    def _draw_hint(self, surface: pygame.Surface) -> None:
        hint = "← →  browse  •  ENTER  select  •  ESC  back"
        img = self.font_hint.render(hint, True, S.Palette.GREY)
        surface.blit(img, img.get_rect(center=(W // 2, HINT_Y)))

    # ─────────────────────────────────────────────────────────────────────
    #  اکشن‌ها
    # ─────────────────────────────────────────────────────────────────────

    def _confirm_select(self) -> None:
        self._play_ui("ui_confirm")
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