"""
TITAN — غول زره‌پوش (نسخه‌ی نهایی).

ظاهر: غول با ۶ پای مفصلی، بدنه‌ی بیضی زره‌پوش، هسته‌ی راکتور غول‌پیکر،
پنل‌های زره با خطوط زرد هشدار، چراغ‌های قرمز.
"""

from __future__ import annotations

import math
import random
import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies.base import Enemy, EnemyKind


class TitanEnemy(Enemy):
    """TITAN — غول زره‌پوش."""

    KIND = EnemyKind.TITAN

    HP = 10
    RADIUS = 30
    SPEED = 35
    SCORE = 100
    DROP_CHANCE = 0.50
    SHOOT_CD = 3.0
    BULLET_SPEED = 180
    BODY_COLOR = (200, 180, 60)

    def _configure(self) -> None:
        self._leg_phases = [random.uniform(0, math.tau) for _ in range(6)]
        self._heartbeat = 0.0

    def update_ai(self, dt: float) -> None:
        self.y += self.SPEED * dt
        self.x = self._base_x + math.sin(self._t * 0.5) * 20.0
        self._heartbeat += dt * 4.0
        for i in range(6):
            self._leg_phases[i] += dt * 5.0

    def _do_shoot(self) -> list:
        if self.scene is None:
            return []
        try:
            from entities.bullet import Bomb
            mine = Bomb(
                self.x, self.y + self.radius * 0.5,
                0, 60,
                scene=self.scene,
            )
            mine.radius = 12
            mine._bomb_age = 0.0
            mine._titan_mine = True
            self.scene.spawn_bullet(mine)
            self.scene.audio.play("enemy_shoot")
            self.scene.camera.shake(3.0)
            return [mine]
        except Exception:
            pass
        return []

    # ═════════════════════════════════════════════════════════════════════
    #  رسم — غول زره‌پوش
    # ═════════════════════════════════════════════════════════════════════

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = int(self.radius * 1.2)
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 120)
        darker = self._darker(base, 180)
        bright = self._lighter(base, 70)
        glow = (255, 240, 100)
        warn_yellow = (255, 210, 60)

        # ---- ۱. سایه‌ی غول‌پیکر ----
        sw, sh = int(r * 1.7), int(r * 0.45)
        shadow = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        for rr in range(sh, 0, -1):
            a = int(120 * (1 - rr / sh) ** 1.5)
            if a > 0:
                pygame.draw.ellipse(shadow, (0, 0, 0, a),
                                    (sw - rr, sh - rr, rr * 2, rr * 2))
        surface.blit(shadow, (cx - sw, cy + int(r * 0.6) - sh))

        # ---- ۲. هاله‌ی زرد ملایم ----
        aura_r = int(r * 1.5)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -5):
            a = int(30 * (1 - rr / aura_r) ** 2)
            if a > 0:
                pygame.draw.circle(aura, (*glow, a), (aura_r, aura_r), rr)
        surface.blit(aura, (cx - aura_r, cy - aura_r),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۳. ۶ پای مفصلی (زاویه‌دار) ----
        for i in range(6):
            # زاویه‌ی هر پا (سه‌تا در هر طرف)
            if i < 3:
                angle = math.pi * 0.85 + (i * 0.35) + math.pi * 0.15
            else:
                angle = math.pi * 0.05 - ((i - 3) * 0.35) - math.pi * 0.15

            wave = math.sin(self._leg_phases[i]) * 5

            # سه‌بخشی: ران، ساق، پا
            hip_x = cx + math.cos(angle) * r * 0.55
            hip_y = cy + int(r * 0.15) + math.sin(angle) * r * 0.15

            knee_x = cx + math.cos(angle) * r * 1.0
            knee_y = cy + int(r * 0.35) + math.sin(angle) * r * 0.3 + wave

            ankle_x = cx + math.cos(angle) * r * 1.2
            ankle_y = cy + int(r * 0.7) + wave

            foot_x = cx + math.cos(angle) * r * 1.4
            foot_y = cy + int(r * 0.9) + wave

            # ران (ضخیم)
            pygame.draw.line(surface, darker,
                             (int(hip_x), int(hip_y)),
                             (int(knee_x), int(knee_y)), 8)
            # ساق (متوسط)
            pygame.draw.line(surface, dark,
                             (int(knee_x), int(knee_y)),
                             (int(ankle_x), int(ankle_y)), 6)
            # پا (نازک)
            pygame.draw.line(surface, base,
                             (int(ankle_x), int(ankle_y)),
                             (int(foot_x), int(foot_y)), 4)

            # خط روشن روی ساق
            pygame.draw.line(surface, bright,
                             (int(knee_x), int(knee_y)),
                             (int(ankle_x), int(ankle_y)), 1)

            # مفصل زانو
            pygame.draw.circle(surface, bright, (int(knee_x), int(knee_y)), 4)
            pygame.draw.circle(surface, base, (int(knee_x), int(knee_y)), 4, 1)
            # مفصل مچ
            pygame.draw.circle(surface, bright, (int(ankle_x), int(ankle_y)), 3)

            # پنجه‌ی پا (مثلث)
            pygame.draw.circle(surface, warn_yellow, (int(foot_x), int(foot_y)), 4)
            pygame.draw.circle(surface, dark, (int(foot_x), int(foot_y)), 4, 1)

        # ---- ۴. بدنه‌ی بیضی غول‌پیکر ----
        body_rect = pygame.Rect(cx - r, cy - int(r * 0.85), r * 2, int(r * 1.6))

        # لایه‌ی سایه
        shadow_rect = body_rect.move(0, 4)
        pygame.draw.ellipse(surface, darker, shadow_rect)

        # بدنه‌ی اصلی
        pygame.draw.ellipse(surface, dark, body_rect)

        # لایه‌ی میانی (روشن‌تر)
        mid_rect = body_rect.inflate(-int(r * 0.2), -int(r * 0.2))
        pygame.draw.ellipse(surface, base, mid_rect)

        # خط نئونی دور
        pygame.draw.ellipse(surface, bright, body_rect, 3)

        # ---- ۵. خطوط هشدار زرد-مشکی روی بدنه ----
        # نوارهای زرد عمودی
        for i in range(4):
            t = (i + 1) / 5
            stripe_x = body_rect.left + int(body_rect.width * t)
            pygame.draw.line(surface, warn_yellow,
                             (stripe_x, body_rect.top + 8),
                             (stripe_x, body_rect.bottom - 8), 2)

        # ---- ۶. پنل‌های زره (بیضی کناری) ----
        for sign in (-1, 1):
            panel_x = cx + sign * int(r * 0.55)
            panel_y = cy - int(r * 0.05)
            panel_w = int(r * 0.35)
            panel_h = int(r * 0.85)
            panel_rect = pygame.Rect(panel_x - panel_w // 2, panel_y - panel_h // 2,
                                     panel_w, panel_h)
            pygame.draw.ellipse(surface, darker, panel_rect)
            pygame.draw.ellipse(surface, bright, panel_rect, 2)

            # خطوط افقی روی پنل
            for j in range(3):
                ly = panel_rect.top + int(panel_rect.height * (0.3 + j * 0.25))
                pygame.draw.line(surface, bright,
                                 (panel_rect.left + 3, ly),
                                 (panel_rect.right - 3, ly), 1)

            # نقطه‌ی درخشان وسط پنل
            pygame.draw.circle(surface, warn_yellow,
                               (panel_x, panel_y), 3)

        # ---- ۷. هسته‌ی راکتور غول‌پیکر ----
        core_y = cy - int(r * 0.05)
        pulse = 0.7 + 0.3 * math.sin(self._heartbeat)
        core_r = int(r * 0.32 * pulse)

        # هاله‌ی بزرگ
        for rr in range(int(r * 0.7), 0, -3):
            a = int(160 * (1 - rr / (r * 0.7)) ** 1.5 * pulse)
            if a > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (*glow, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, core_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # هسته (سه لایه)
        pygame.draw.circle(surface, (200, 100, 20), (cx, core_y), core_r + 3)
        pygame.draw.circle(surface, glow, (cx, core_y), core_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, core_y), max(3, core_r // 2))

        # حلقه‌ی چرخان دور هسته
        ring_r = int(r * 0.5)
        for i in range(6):
            angle = self._t * 2 + i * math.tau / 6
            rx = cx + int(math.cos(angle) * ring_r)
            ry = core_y + int(math.sin(angle) * ring_r * 0.7)
            pygame.draw.circle(surface, warn_yellow, (rx, ry), 3)
            pygame.draw.circle(surface, (255, 255, 200), (rx, ry), 1)

        # ---- ۸. چراغ‌های هشدار قرمز ----
        blink = 0.5 + 0.5 * math.sin(self._t * 6)
        for sign in (-1, 1):
            lx = cx + sign * int(r * 0.65)
            ly = cy - int(r * 0.65)
            a = int(240 * blink)
            if a > 0:
                g = pygame.Surface((16, 16), pygame.SRCALPHA)
                for rr in range(8, 0, -2):
                    aa = int(a * (1 - rr / 8))
                    if aa > 0:
                        pygame.draw.circle(g, (255, 60, 60, aa), (8, 8), rr)
                surface.blit(g, (lx - 8, ly - 8),
                             special_flags=pygame.BLEND_RGBA_ADD)
                pygame.draw.circle(surface, (255, 100, 100), (lx, ly), 3)

        # ---- ۹. نوار HP (بزرگ) ----
        if self.hp < self.max_hp:
            w = int(r * 2.2)
            h = 7
            x = cx - w // 2
            y = cy - int(r * 1.05)
            bg = pygame.Surface((w + 6, h + 6), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 240))
            surface.blit(bg, (x - 3, y - 3))
            ratio = max(0.0, self.hp / self.max_hp)
            color = (80, 255, 140) if ratio > 0.5 else (255, 220, 60) if ratio > 0.25 else (255, 60, 60)
            pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
            pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), 2)



__all__ = ["TitanEnemy"]