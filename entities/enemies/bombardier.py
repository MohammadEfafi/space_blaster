"""
BOMBARDIER — بمب‌افکن سنگین (نسخه‌ی بازطراحی‌شده).
"""
from __future__ import annotations

import math
import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind, Bomb
from entities.enemies.base import Enemy, EnemyKind


class BombardierEnemy(Enemy):
    """BOMBARDIER — بمب‌افکن سنگین."""

    KIND = EnemyKind.BOMBARDIER

    HP = 3
    RADIUS = 22
    SPEED = 65
    SCORE = 35
    DROP_CHANCE = 0.25
    SHOOT_CD = 2.8
    BULLET_SPEED = 100
    BODY_COLOR = (255, 130, 60)

    def update_ai(self, dt: float) -> None:
        self.y += self.SPEED * dt
        self.x = self._base_x + math.sin(self._t * 0.6) * 12.0

    def _do_shoot(self) -> list:
        """۲ بمب آروم به سمت پایین (کمتر برای راحتی بیشتر)."""
        if self.scene is None:
            return []
        bullets = []
        # فقط ۲ بمب (به جای ۳) با فاصله‌ی بیشتر
        for offset_x in (-30, 30):
            try:
                b = Bomb(
                    self.x + offset_x, self.y + self.radius * 0.6,
                    0, self.BULLET_SPEED,
                    scene=self.scene,
                )
                b.radius = 8
                bullets.append(b)
            except Exception:
                pass
        try:
            for b in bullets:
                self.scene.spawn_bullet(b)
            self.scene.audio.play("enemy_shoot")
        except Exception:
            pass
        return bullets

    # ═════════════════════════════════════════════════════════════════════
    #  رسم — Bomber نظامی
    # ═════════════════════════════════════════════════════════════════════

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = int(self.radius * 1.3)
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 110)
        darker = self._darker(base, 170)
        bright = self._lighter(base, 70)
        yellow = (255, 210, 60)

        # ---- ۱. سایه‌ی زیر ----
        sw, sh = int(r * 1.4), int(r * 0.4)
        shadow = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        for rr in range(sh, 0, -1):
            a = int(100 * (1 - rr / sh) ** 1.5)
            if a > 0:
                pygame.draw.ellipse(shadow, (0, 0, 0, a),
                                    (sw - rr, sh - rr, rr * 2, rr * 2))
        surface.blit(shadow, (cx - sw, cy + int(r * 0.6) - sh))

        # ---- ۲. هاله‌ی نارنجی ملایم ----
        aura_r = int(r * 1.5)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -4):
            a = int(40 * (1 - rr / aura_r) ** 2)
            if a > 0:
                pygame.draw.circle(aura, (255, 100, 40, a), (aura_r, aura_r), rr)
        surface.blit(aura, (cx - aura_r, cy - aura_r),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۳. بال‌های پهن (دو لایه) ----
        for sign in (-1, 1):
            # بال زیر (تیره، بزرگ‌تر)
            wing_back = [
                (cx + sign * int(r * 0.5), cy - int(r * 0.4)),
                (cx + sign * int(r * 1.55), cy - int(r * 0.45)),
                (cx + sign * int(r * 1.65), cy + int(r * 0.35)),
                (cx + sign * int(r * 0.7), cy + int(r * 0.55)),
            ]
            pygame.draw.polygon(surface, darker, wing_back)
            pygame.draw.polygon(surface, bright, wing_back, 3)

            # خطوط زرد-مشکی روی بال
            for i in range(3):
                t1 = i / 3
                t2 = (i + 0.4) / 3
                x1 = cx + sign * int(r * (0.9 + t1 * 0.65))
                x2 = cx + sign * int(r * (0.9 + t2 * 0.65))
                pygame.draw.line(surface, yellow,
                                 (x1, cy - int(r * 0.35)),
                                 (x2, cy - int(r * 0.35)), 3)

            # چراغ ناوبری چشمک‌زن
            blink = 0.5 + 0.5 * math.sin(self._t * 4 + (0 if sign < 0 else math.pi))
            tip_x = cx + sign * int(r * 1.6)
            tip_y = cy - int(r * 0.05)
            a = int(220 * blink)
            if a > 0:
                color = (255, 60, 60) if sign < 0 else (60, 255, 120)
                g = pygame.Surface((16, 16), pygame.SRCALPHA)
                for rr in range(8, 0, -2):
                    aa = int(a * (1 - rr / 8))
                    if aa > 0:
                        pygame.draw.circle(g, (*color, aa), (8, 8), rr)
                surface.blit(g, (tip_x - 8, tip_y - 8),
                             special_flags=pygame.BLEND_RGBA_ADD)
                pygame.draw.circle(surface, color, (tip_x, tip_y), 3)

        # ---- ۴. بدنه‌ی کشیده (شبیه بمب‌افکن B-2) ----
        hull = [
            (cx - int(r * 0.7), cy - int(r * 0.5)),
            (cx - int(r * 0.3), cy - int(r * 0.65)),
            (cx + int(r * 0.3), cy - int(r * 0.65)),
            (cx + int(r * 0.7), cy - int(r * 0.5)),
            (cx + int(r * 0.6), cy + int(r * 0.4)),
            (cx - int(r * 0.6), cy + int(r * 0.4)),
        ]
        pygame.draw.polygon(surface, darker, [(x, y + 3) for x, y in hull])
        pygame.draw.polygon(surface, base, hull)
        pygame.draw.polygon(surface, bright, hull, 3)

        # پنل زره میانی (روشن‌تر)
        mid = [
            (cx - int(r * 0.45), cy - int(r * 0.35)),
            (cx - int(r * 0.2), cy - int(r * 0.45)),
            (cx + int(r * 0.2), cy - int(r * 0.45)),
            (cx + int(r * 0.45), cy - int(r * 0.35)),
            (cx + int(r * 0.4), cy + int(r * 0.25)),
            (cx - int(r * 0.4), cy + int(r * 0.25)),
        ]
        pygame.draw.polygon(surface, self._lighter(base, 30), mid)
        pygame.draw.polygon(surface, bright, mid, 1)

        # خطوط افقی روی بدنه
        for i in range(2):
            ly = cy - int(r * 0.15) + i * int(r * 0.25)
            pygame.draw.line(surface, dark,
                             (cx - int(r * 0.45), ly),
                             (cx + int(r * 0.45), ly), 2)

        # ---- ۵. کابین شیشه‌ای ----
        cab_y = cy - int(r * 0.45)
        cab_w = max(5, int(r * 0.35))
        cab_h = max(4, int(r * 0.15))
        rect = pygame.Rect(cx - cab_w, cab_y - cab_h, cab_w * 2, cab_h * 2)
        pygame.draw.ellipse(surface, (20, 40, 60), rect)
        pygame.draw.ellipse(surface, (100, 220, 255), rect, 2)
        # درخشش داخل کابین
        inner = rect.inflate(-4, -4)
        if inner.width > 0 and inner.height > 0:
            pygame.draw.ellipse(surface, (60, 160, 220), inner)

        # ---- ۶. دو موتور کناری با شعله ----
        for sign in (-1, 1):
            ex = cx + sign * int(r * 0.5)
            ey = cy + int(r * 0.45)
            flicker = 0.7 + 0.3 * math.sin(self._t * 15 + sign)
            flame_len = int(r * 0.4 * flicker)

            # هاله‌ی شعله
            for rr in range(8, 0, -2):
                a = int(150 * (1 - rr / 8) * flicker)
                if a > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (255, 150, 40, a), (rr * 2, rr * 2), rr)
                    surface.blit(g, (ex - rr * 2, ey - rr * 2 + 4),
                                 special_flags=pygame.BLEND_RGBA_ADD)

            # شعله (سه لایه)
            pygame.draw.polygon(surface, (255, 100, 20), [
                (ex - 6, ey), (ex + 6, ey), (ex, ey + flame_len),
            ])
            pygame.draw.polygon(surface, (255, 200, 80), [
                (ex - 3, ey), (ex + 3, ey), (ex, ey + int(flame_len * 0.7)),
            ])
            pygame.draw.polygon(surface, (255, 255, 220), [
                (ex - 1, ey), (ex + 1, ey), (ex, ey + int(flame_len * 0.4)),
            ])

        # ---- ۷. سه بمب بزرگ زیر بدنه (بصری) ----
        bomb_y = cy + int(r * 0.55)
        for offset in (-30, 0, 30):
            bx = cx + offset
            # بدنه‌ی بمب (بیضی بزرگ)
            bomb_rect = pygame.Rect(bx - 8, bomb_y - 10, 16, 20)
            pygame.draw.ellipse(surface, (40, 40, 55), bomb_rect)
            pygame.draw.ellipse(surface, dark, bomb_rect, 2)
            # فیوز درخشان
            flicker = 0.5 + 0.5 * math.sin(self._t * 12 + offset * 0.5)
            fz_color = (255, int(150 + 100 * flicker), 40)
            # هاله‌ی فیوز
            for rr in range(8, 0, -1):
                a = int(180 * (1 - rr / 8) * flicker)
                if a > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (*fz_color, a), (rr * 2, rr * 2), rr)
                    surface.blit(g, (bx - rr * 2, bomb_y - 12 - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.circle(surface, fz_color, (bx, bomb_y - 12), 3)
            pygame.draw.circle(surface, (255, 255, 255), (bx, bomb_y - 12), 1)

        # ---- ۸. چراغ قرمز هشدار ----
        blink = 0.5 + 0.5 * math.sin(self._t * 5.0)
        for sign in (-1, 1):
            lx = cx + sign * int(r * 0.3)
            ly = cy - int(r * 0.55)
            a = int(220 * blink)
            if a > 0:
                g = pygame.Surface((14, 14), pygame.SRCALPHA)
                for rr in range(7, 0, -2):
                    aa = int(a * (1 - rr / 7))
                    if aa > 0:
                        pygame.draw.circle(g, (255, 60, 60, aa), (7, 7), rr)
                surface.blit(g, (lx - 7, ly - 7),
                             special_flags=pygame.BLEND_RGBA_ADD)
                pygame.draw.circle(surface, (255, 100, 100), (lx, ly), 3)

        # ---- ۹. نوار HP ----
        if self.hp < self.max_hp:
            w = int(r * 1.8)
            h = 4
            x = cx - w // 2
            y = cy - int(r * 0.85)
            bg = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 200))
            surface.blit(bg, (x - 1, y - 1))
            ratio = max(0.0, self.hp / self.max_hp)
            color = (80, 255, 140) if ratio > 0.5 else (255, 220, 60)
            pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
            pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), 1)

    @staticmethod
    def _darker(c, amount):
        return (max(0, c[0] - amount), max(0, c[1] - amount), max(0, c[2] - amount))

    @staticmethod
    def _lighter(c, amount):
        return (min(255, c[0] + amount), min(255, c[1] + amount), min(255, c[2] + amount))


__all__ = ["BombardierEnemy"]