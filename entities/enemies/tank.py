"""
entities/enemies/tank.py
========================

دشمن نوع دوم — Tank (قلعه‌ی پرنده).

طراحی:
    یک دشمن سنگین و ترسناک با سیلوئت گرد و پرقدرت. برخلاف Normal که
    تیز و سریعه، Tank حس «سختی» و «زره» رو منتقل می‌کنه:
        • بدنه‌ی شش‌ضلعی ضخیم با خطوط زره
        • دو توپ شلیک در جلو با نور درخشان
        • هسته‌ی مرکزی پالسی که قلب دشمنه
        • حلقه‌ی زره‌ای چرخان دور هسته
        • نوار HP که فقط بعد از آسیب دیده می‌شه

رفتار:
    • کند اما مقاوم (HP=4)
    • به سمت پلیر شلیک دوگانه می‌کند
    • نوسان افقی ملایم برای زنده‌تر شدن
    • امتیاز بالا، شانس افت پاورآپ بالا
"""

from __future__ import annotations

import math
import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies.base import Enemy, EnemyKind


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس TankEnemy
# ═══════════════════════════════════════════════════════════════════════════

class TankEnemy(Enemy):
    """قلعه‌ی پرنده — سنگین، مسلح، مقاوم."""

    KIND = EnemyKind.TANK

    HP           = S.EnemyCfg.Tank.HP
    RADIUS       = S.EnemyCfg.Tank.RADIUS
    SPEED        = S.EnemyCfg.Tank.SPEED
    SCORE        = S.EnemyCfg.Tank.SCORE
    DROP_CHANCE  = S.EnemyCfg.Tank.DROP_CHANCE
    SHOOT_CD     = S.EnemyCfg.Tank.SHOOT_CD
    BULLET_SPEED = S.EnemyCfg.Tank.BULLET_SPEED
    BODY_COLOR   = S.Palette.ENEMY_TANK

    # ─────────────────────────────────────────────────────────────────────
    #  منطق حرکت
    # ─────────────────────────────────────────────────────────────────────

    def update_ai(self, dt: float) -> None:
        """حرکت آرام به پایین + نوسان افقی ملایم."""
        self.y += self.SPEED * dt
        # نوسان سینوسی روی موقعیت افقی
        self.x = self._base_x + math.sin(self._t * 0.9) * 14.0

    # ─────────────────────────────────────────────────────────────────────
    #  شلیک دوگانه
    # ─────────────────────────────────────────────────────────────────────

    def _do_shoot(self) -> list[Bullet]:
        """شلیک دو گلوله‌ی موازی به سمت پلیر."""
        if self.scene is None:
            return []
        player = getattr(self.scene, "player", None)
        if player is None or not player.alive:
            return []

        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        # بردار عمود بر جهت شلیک
        px, py = -uy, ux

        bullets: list[Bullet] = []
        for side in (-1.0, 1.0):
            bx = self.x + px * 10 * side
            by = self.y + py * 10 * side
            b = Bullet(
                bx, by,
                ux * self.BULLET_SPEED,
                uy * self.BULLET_SPEED,
                friendly=False,
                kind=BulletKind.ENEMY,
                scene=self.scene,
            )
            bullets.append(b)

        try:
            for b in bullets:
                self.scene.spawn_bullet(b)
            self.scene.audio.play("enemy_shoot")
        except Exception:
            pass

        return bullets

    # ─────────────────────────────────────────────────────────────────────
    #  رسم — قلعه‌ی پرنده
    # ─────────────────────────────────────────────────────────────────────

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = max(6, int(self.radius))
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 100)
        darker = self._darker(base, 140)
        bright = self._lighter(base, 70)

        # ---- ۱. سایه‌ی زیر (حس شناور بودن) ----
        self._draw_ground_shadow(surface, cx, cy, r)

        # ---- ۲. توپ‌های شلیک (جلو) ----
        self._draw_cannons(surface, cx, cy, r, dark, bright)

        # ---- ۳. بدنه‌ی شش‌ضلعی زره‌ای ----
        self._draw_armored_hull(surface, cx, cy, r, base, dark, bright)

        # ---- ۴. خطوط زره ----
        self._draw_armor_lines(surface, cx, cy, r, darker)

        # ---- ۵. حلقه‌ی چرخان دور هسته ----
        self._draw_rotating_ring(surface, cx, cy, r, bright)

        # ---- ۶. هسته‌ی مرکزی پالسی ----
        self._draw_core(surface, cx, cy, r)

        # ---- ۷. نوار HP (فقط بعد از آسیب) ----
        if self.max_hp > 1 and self.hp < self.max_hp:
            self._draw_hp_bar(surface, cx, cy, r)

        # ---- ۸. فید در زمان ورود ----
        if alpha < 250:
            self._apply_fade(surface, cx, cy, r, alpha)

    # ─────────────────────────────────────────────────────────────────────
    #  اجزای رسم
    # ─────────────────────────────────────────────────────────────────────

    def _draw_ground_shadow(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """سایه‌ی بیضوی زیر بدنه برای حس عمق."""
        shadow_w = int(r * 1.6)
        shadow_h = int(r * 0.5)
        shadow_rect = pygame.Rect(
            cx - shadow_w, cy + int(r * 0.3) - shadow_h,
            shadow_w * 2, shadow_h * 2,
        )
        shadow = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 80), shadow.get_rect())
        surface.blit(shadow, shadow_rect.topleft)

    def _draw_cannons(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """دو توپ شلیک در دو طرف پایین بدنه."""
        for sign in (-1, 1):
            # بدنه‌ی توپ
            bx = cx + sign * int(r * 0.55)
            by = cy + int(r * 0.55)
            cannon_w = max(4, int(r * 0.22))
            cannon_h = max(6, int(r * 0.45))
            rect = pygame.Rect(
                bx - cannon_w, by, cannon_w * 2, cannon_h,
            )
            pygame.draw.rect(surface, dark, rect)
            pygame.draw.rect(surface, bright, rect, 1)

            # نوک درخشان (لوله)
            tip_x = bx
            tip_y = by + cannon_h
            pygame.draw.circle(surface, (255, 100, 200), (tip_x, tip_y), max(2, int(r * 0.12)))
            pygame.draw.circle(surface, (255, 220, 255), (tip_x, tip_y), max(1, int(r * 0.06)))

            # خط زره روی توپ
            pygame.draw.line(
                surface, bright,
                (bx - cannon_w, by + cannon_h // 2),
                (bx + cannon_w, by + cannon_h // 2),
                1,
            )

    def _draw_armored_hull(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        base: tuple[int, int, int],
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """بدنه‌ی شش‌ضلعی با لایه‌های زره."""
        # شش‌ضلعی اصلی
        hull = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 2
            hull.append((
                cx + math.cos(angle) * r,
                cy + math.sin(angle) * r,
            ))

        # سایه‌ی زیر
        shadow = [(x, y + 2) for (x, y) in hull]
        pygame.draw.polygon(surface, dark, shadow)

        # بدنه
        pygame.draw.polygon(surface, base, hull)

        # لایه‌ی زره داخلی (شش‌ضلعی کوچک‌تر)
        inner_r = r * 0.78
        inner = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 2
            inner.append((
                cx + math.cos(angle) * inner_r,
                cy + math.sin(angle) * inner_r,
            ))
        pygame.draw.polygon(surface, dark, inner)

        # خط نئونی دور هر دو لایه
        pygame.draw.polygon(surface, bright, hull, 2)
        pygame.draw.polygon(surface, bright, inner, 1)

    def _draw_armor_lines(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        darker: tuple[int, int, int],
    ) -> None:
        """خطوط زره بین رأس‌ها (شعاعی)."""
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 2
            x1 = cx + math.cos(angle) * r * 0.78
            y1 = cy + math.sin(angle) * r * 0.78
            x2 = cx + math.cos(angle) * r
            y2 = cy + math.sin(angle) * r
            pygame.draw.line(surface, darker, (x1, y1), (x2, y2), 2)

    def _draw_rotating_ring(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        bright: tuple[int, int, int],
    ) -> None:
        """حلقه‌ی چرخان دور هسته (حس زنده بودن)."""
        ring_r = int(r * 0.55)
        num_segments = 8
        base_angle = self._t * 0.8  # چرخش آرام

        for i in range(num_segments):
            a = base_angle + (i / num_segments) * math.tau
            x = cx + int(math.cos(a) * ring_r)
            y = cy + int(math.sin(a) * ring_r)
            size = max(1, int(r * 0.08))
            pygame.draw.circle(surface, bright, (x, y), size)

    def _draw_core(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """هسته‌ی مرکزی پالسی."""
        # ضربان
        pulse = 0.75 + 0.25 * math.sin(self._t * 5.0)
        core_r = max(3, int(r * 0.28 * pulse))

        # هاله‌ی بیرونی
        glow_size = int(r * 0.7)
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -2):
            a = int(120 * (1 - rr / glow_size) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(glow, (255, 90, 200, a), (glow_size, glow_size), rr)
        surface.blit(
            glow, (cx - glow_size, cy - glow_size),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        # دایره‌ی میانی
        pygame.draw.circle(surface, (255, 130, 230), (cx, cy), core_r)
        # هسته‌ی روشن
        pygame.draw.circle(surface, (255, 230, 255), (cx, cy), max(1, core_r // 2))

    def _draw_hp_bar(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """نوار HP بالای بدنه — فقط وقتی آسیب دیده."""
        w = int(r * 2)
        h = 4
        x = cx - w // 2
        y = cy - r - 10

        # پس‌زمینه
        bg = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 150))
        surface.blit(bg, (x - 1, y - 1))

        # نوار
        ratio = max(0.0, self.hp / self.max_hp)
        if ratio > 0.5:
            color = (80, 255, 140)
        elif ratio > 0.25:
            color = (255, 220, 60)
        else:
            color = (255, 60, 60)
        pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
        pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), 1)

    def _apply_fade(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        alpha: int,
    ) -> None:
        """پوشش نیمه‌شفاف سیاه برای انیمیشن ورود."""
        a = 255 - alpha
        if a <= 0:
            return
        fade = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        fade.fill((0, 0, 0, int(a * 0.7)))
        surface.blit(fade, (cx - r * 2, cy - r * 2))

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌های رنگ
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _darker(c: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
        return (max(0, c[0] - amount), max(0, c[1] - amount), max(0, c[2] - amount))

    @staticmethod
    def _lighter(c: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
        return (min(255, c[0] + amount), min(255, c[1] + amount), min(255, c[2] + amount))


__all__ = ["TankEnemy"]