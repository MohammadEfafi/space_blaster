"""
entities/player/interceptor.py
==============================

سفینه‌ی INTERCEPTOR — رهگیر سریع و شکننده.
"""

from __future__ import annotations

import math

import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.player.base import Player


class Interceptor(Player):
    """رهگیر سریع — سبک، تیز، تهاجمی."""

    NAME        = "INTERCEPTOR"
    DESCRIPTION = "Fast and fragile. Outspeed them or die trying."
    KIND_KEY    = "interceptor"

    MAX_HP:        int   = 3
    SPEED:         float = 480.0
    RADIUS:        float = 18.0
    INVULN_TIME:   float = 2.0
    SHOOT_CD:      float = 0.07
    BULLET_SPEED:  float = 900.0
    BULLET_DAMAGE: int   = 1
    BULLET_KIND:   BulletKind = BulletKind.LASER

    ACCEL: float = 14.0
    DRAG:  float = 9.5

    PRIMARY_COLOR:   tuple[int, int, int] = (60, 220, 255)
    SECONDARY_COLOR: tuple[int, int, int] = (30, 100, 160)
    ACCENT_COLOR:    tuple[int, int, int] = (255, 240, 100)
    HIGHLIGHT_COLOR: tuple[int, int, int] = (235, 245, 255)
    FLAME_COLOR:     tuple[int, int, int] = (100, 200, 255)

    # ─────────────────────────────────────────────────────────────────────
    #  موتور
    # ─────────────────────────────────────────────────────────────────────

    def get_engine_offsets(self) -> list[tuple[float, float, float]]:
        return [
            (-0.45, 0.95, 0.85),
            ( 0.45, 0.95, 0.85),
        ]

    # ─────────────────────────────────────────────────────────────────────
    #  رسم بدنه
    # ─────────────────────────────────────────────────────────────────────

    def draw_ship(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = int(self.radius)
        primary = self.PRIMARY_COLOR
        secondary = self.SECONDARY_COLOR
        highlight = self.HIGHLIGHT_COLOR
        accent = self.ACCENT_COLOR

        # ---- ۱. سایه‌ی زیر ----
        shadow_pts = [
            (cx,                  cy - int(r * 1.25) + 2),
            (cx - int(r * 1.30),  cy + int(r * 0.55) + 2),
            (cx + int(r * 1.30),  cy + int(r * 0.55) + 2),
        ]
        pygame.draw.polygon(surface, (5, 30, 60), shadow_pts)

        # ---- ۲. بال‌های تیز پیکانی ----
        left_wing = [
            (cx - int(r * 0.35), cy - int(r * 0.30)),
            (cx - int(r * 1.30), cy + int(r * 0.15)),
            (cx - int(r * 1.10), cy + int(r * 0.55)),
            (cx - int(r * 0.30), cy + int(r * 0.45)),
        ]
        right_wing = [(cx + (cx - x), y) for (x, y) in left_wing]

        pygame.draw.polygon(surface, secondary, left_wing)
        pygame.draw.polygon(surface, secondary, right_wing)
        pygame.draw.polygon(surface, primary, left_wing, 2)
        pygame.draw.polygon(surface, primary, right_wing, 2)

        # ---- ۳. خط نئونی روی بال‌ها ----
        for sign in (-1, 1):
            pygame.draw.line(
                surface, primary,
                (cx + sign * int(r * 0.55), cy - int(r * 0.1)),
                (cx + sign * int(r * 1.15), cy + int(r * 0.30)),
                1,
            )

        # ---- ۴. بدنه‌ی اصلی ----
        hull = [
            (cx,                  cy - int(r * 1.25)),
            (cx - int(r * 0.35),  cy - int(r * 0.20)),
            (cx - int(r * 0.45),  cy + int(r * 0.55)),
            (cx,                  cy + int(r * 0.75)),
            (cx + int(r * 0.45),  cy + int(r * 0.55)),
            (cx + int(r * 0.35),  cy - int(r * 0.20)),
        ]
        pygame.draw.polygon(surface, primary, hull)
        pygame.draw.polygon(surface, highlight, hull, 2)

        # ---- ۵. نوار مرکزی ----
        stripe = [
            (cx,                  cy - int(r * 1.15)),
            (cx - int(r * 0.15),  cy - int(r * 0.20)),
            (cx,                  cy + int(r * 0.30)),
            (cx + int(r * 0.15),  cy - int(r * 0.20)),
        ]
        pygame.draw.polygon(surface, highlight, stripe)
        pygame.draw.line(
            surface, accent,
            (cx, cy - int(r * 1.05)),
            (cx, cy + int(r * 0.25)),
            2,
        )

        # ---- ۶. کابین ----
        cab_y = cy - int(r * 0.30)
        cab_r = max(2, int(r * 0.20))
        pygame.draw.circle(surface, accent, (cx, cab_y), cab_r + 1)
        pygame.draw.circle(surface, (255, 255, 220), (cx, cab_y), cab_r)

        # ---- ۷. خطوط تزئینی ----
        for sign in (-1, 1):
            pygame.draw.line(
                surface, secondary,
                (cx + sign * int(r * 0.25), cy - int(r * 0.4)),
                (cx + sign * int(r * 0.30), cy + int(r * 0.5)),
                1,
            )

        # ---- ۸. رأس‌های درخشان ----
        for sign in (-1, 1):
            tip_x = cx + sign * int(r * 1.25)
            tip_y = cy + int(r * 0.20)
            self._draw_tip_glow(surface, tip_x, tip_y, int(r * 0.15))

    # ─────────────────────────────────────────────────────────────────────
    #  شلیک با pierce
    # ─────────────────────────────────────────────────────────────────────

    def try_shoot(self) -> list:
        """شلیک با pierce — گلوله از ۲ دشمن رد می‌شه."""
        if self.shoot_cd > 0.0 or not self.alive:
            return []

        self.shoot_cd = self.current_shoot_cd
        self.muzzle_flash = 1.0
        self.recoil = 0.6

        bullets = []
        for angle_deg in self._get_shot_angles():
            a = math.radians(angle_deg)
            vx = math.cos(a) * self.BULLET_SPEED
            vy = math.sin(a) * self.BULLET_SPEED
            ox = math.cos(a) * (self.radius + 6)
            oy = math.sin(a) * (self.radius + 6)

            b = Bullet(
                self.x + ox, self.y + oy,
                vx, vy,
                friendly=True,
                kind=self.BULLET_KIND,
                damage=self.BULLET_DAMAGE,
                scene=self.scene,
                pierce=2,
            )
            bullets.append(b)

        if self.scene is not None:
            try:
                self.scene.audio.play("player_shoot")
            except Exception:
                pass

        return bullets

    # ─────────────────────────────────────────────────────────────────────
    #  نقطه‌ی درخشان رأس بال
    # ─────────────────────────────────────────────────────────────────────

    def _draw_tip_glow(
        self,
        surface: pygame.Surface,
        x: int, y: int,
        size: int,
    ) -> None:
        """نقطه‌ی درخشان روی رأس بال (نئون)."""
        size = max(2, size)
        accent = self.ACCENT_COLOR

        glow = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        for rr in range(size * 2, 0, -1):
            a = int(120 * (1 - rr / (size * 2)))
            if a <= 0:
                continue
            pygame.draw.circle(glow, (*accent, a), (size * 2, size * 2), rr)
        surface.blit(
            glow, (x - size * 2, y - size * 2),
            special_flags=pygame.BLEND_RGBA_ADD,
        )
        pygame.draw.circle(surface, (255, 255, 255), (x, y), max(1, size // 2))


__all__ = ["Interceptor"]