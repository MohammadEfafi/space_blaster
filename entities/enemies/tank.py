"""
entities/enemies/tank.py
========================

دشمن نوع دوم — SIEGE CRAWLER (خزنده‌ی محاصره) — نسخه‌ی بازطراحی‌شده.

طراحی جدید (سفینه‌ی جنگی سنگین):
    • بدنه‌ی کشیده و پهن (مثل ناوچه‌ی فضایی)
    • دو پاد سلاح مدرن با دهانه‌ی چرخان درخشان
    • بال‌های زره‌ای با خطوط نئونی
    • هسته‌ی انرژی مرکزی با خطوط شعاعی
    • صفحه‌ی شیشه‌ای (کابین) در جلو
    • چراغ‌های هشدار چشمک‌زن
    • نوار HP در بالا (بعد از آسیب)

رفتار:
    • کند، مقاوم (HP=4)
    • شلیک دوگانه از پادهای سلاح
    • نوسان افقی ملایم
"""

from __future__ import annotations

import math
import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies.base import Enemy, EnemyKind


class TankEnemy(Enemy):
    """SIEGE CRAWLER — ناوچه‌ی جنگی سنگین."""

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
        self.y += self.SPEED * dt
        self.x = self._base_x + math.sin(self._t * 0.9) * 14.0

    # ─────────────────────────────────────────────────────────────────────
    #  شلیک
    # ─────────────────────────────────────────────────────────────────────

    def _do_shoot(self) -> list[Bullet]:
        if self.scene is None:
            return []
        player = getattr(self.scene, "player", None)
        if player is None or not player.alive:
            return []

        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        px, py = -uy, ux

        bullets: list[Bullet] = []
        for side in (-1.0, 1.0):
            bx = self.x + px * 16 * side
            by = self.y + py * 16 * side
            bullets.append(Bullet(
                bx, by,
                ux * self.BULLET_SPEED, uy * self.BULLET_SPEED,
                friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
            ))
        try:
            for b in bullets:
                self.scene.spawn_bullet(b)
            self.scene.audio.play("enemy_shoot")
        except Exception:
            pass
        return bullets

    # ─────────────────────────────────────────────────────────────────────
    #  رسم
    # ─────────────────────────────────────────────────────────────────────

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = max(12, int(self.radius * 1.2))
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 100)
        darker = self._darker(base, 150)
        bright = self._lighter(base, 70)

        # ---- ۱. سایه‌ی زیر (شناور) ----
        self._draw_ground_shadow(surface, cx, cy, r)

        # ---- ۲. بال‌های زره‌ای دو طرف ----
        self._draw_armored_wings(surface, cx, cy, r, dark, brighter := self._lighter(base, 40))

        # ---- ۳. پادهای سلاح مدرن (کناری) ----
        self._draw_weapon_pods(surface, cx, cy, r, dark, bright)

        # ---- ۴. بدنه‌ی اصلی (کشیده) ----
        self._draw_hull(surface, cx, cy, r, base, dark, bright)

        # ---- ۵. کابین شیشه‌ای (جلو) ----
        self._draw_cockpit(surface, cx, cy, r)

        # ---- ۶. هسته‌ی انرژی مرکزی ----
        self._draw_energy_core(surface, cx, cy, r)

        # ---- ۷. خطوط نئونی روی بدنه ----
        self._draw_panel_lines(surface, cx, cy, r, bright)

        # ---- ۸. چراغ‌های هشدار ----
        self._draw_warning_lights(surface, cx, cy, r)

        # ---- ۹. نوار HP ----
        if self.max_hp > 1 and self.hp < self.max_hp:
            self._draw_hp_bar(surface, cx, cy, r)

        # ---- ۱۰. فید ----
        if alpha < 250:
            self._apply_fade(surface, cx, cy, r, alpha)

    # ─────────────────────────────────────────────────────────────────────
    #  اجزای رسم
    # ─────────────────────────────────────────────────────────────────────

    def _draw_ground_shadow(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        sw = int(r * 1.5)
        sh = int(r * 0.4)
        shadow = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        for rr in range(sh, 0, -1):
            a = int(90 * (1 - rr / sh) ** 1.6)
            if a <= 0:
                continue
            pygame.draw.ellipse(shadow, (0, 0, 0, a),
                                (sw - rr, sh - rr, rr * 2, rr * 2))
        surface.blit(shadow, (cx - sw, cy + int(r * 0.55) - sh))

    def _draw_armored_wings(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        dark: tuple[int, int, int],
        mid: tuple[int, int, int],
    ) -> None:
        """بال‌های زره‌ای پهن با لبه‌های نئونی."""
        for sign in (-1, 1):
            wing = [
                (cx + sign * int(r * 0.35), cy - int(r * 0.55)),
                (cx + sign * int(r * 1.35), cy - int(r * 0.35)),
                (cx + sign * int(r * 1.30), cy + int(r * 0.40)),
                (cx + sign * int(r * 0.85), cy + int(r * 0.55)),
                (cx + sign * int(r * 0.35), cy + int(r * 0.35)),
            ]
            pygame.draw.polygon(surface, dark, wing)
            pygame.draw.polygon(surface, mid, wing, 2)

            # خطوط زره‌ای روی بال
            for i in range(3):
                y_off = -0.35 + i * 0.3
                pygame.draw.line(
                    surface, mid,
                    (cx + sign * int(r * 0.55), cy + int(r * y_off)),
                    (cx + sign * int(r * 1.15), cy + int(r * y_off * 0.9)),
                    1,
                )

            # نوک درخشان بال (چراغ ناوبری)
            tip_x = cx + sign * int(r * 1.30)
            tip_y = cy + int(r * 0.05)
            color = (255, 80, 80) if sign < 0 else (80, 255, 120)
            blink = 0.5 + 0.5 * math.sin(self._t * 4.0 + (0 if sign < 0 else math.pi))
            a = int(200 * blink)
            if a > 0:
                glow = pygame.Surface((14, 14), pygame.SRCALPHA)
                for rr in range(7, 0, -2):
                    aa = int(a * (1 - rr / 7))
                    if aa > 0:
                        pygame.draw.circle(glow, (*color, aa), (7, 7), rr)
                surface.blit(glow, (tip_x - 7, tip_y - 7),
                             special_flags=pygame.BLEND_RGBA_ADD)
                pygame.draw.circle(surface, color, (tip_x, tip_y), 3)

    def _draw_weapon_pods(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """پادهای سلاح مدرن — استوانه‌ای با دهانه‌ی چرخان درخشان."""
        for sign in (-1, 1):
            px = cx + sign * int(r * 0.65)
            py = cy + int(r * 0.35)

            # ---- بدنه‌ی پاد (استوانه) ----
            pod_w = max(6, int(r * 0.28))
            pod_h = max(12, int(r * 0.55))
            pod_rect = pygame.Rect(
                px - pod_w, py, pod_w * 2, pod_h,
            )

            # سایه
            pygame.draw.rect(surface, dark,
                             pod_rect.move(0, 2), border_radius=4)
            # بدنه
            pygame.draw.rect(surface, (30, 30, 50),
                             pod_rect, border_radius=4)
            pygame.draw.rect(surface, bright, pod_rect, 2, border_radius=4)

            # خطوط فنری روی پاد
            for i in range(3):
                ly = py + int(pod_h * (0.25 + i * 0.25))
                pygame.draw.line(surface, bright,
                                 (px - pod_w, ly), (px + pod_w, ly), 1)

            # ---- دهانه‌ی چرخان (درخشان) ----
            tip_y = py + pod_h
            tip_r = max(4, int(r * 0.16))

            # هاله
            for rr in range(tip_r * 3, 0, -1):
                a = int(120 * (1 - rr / (tip_r * 3)))
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 100, 220, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (px - rr * 2, tip_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

            # حلقه‌ی چرخان
            for i in range(6):
                angle = self._t * 5.0 + i * math.tau / 6
                dx = int(math.cos(angle) * tip_r * 0.85)
                dy = int(math.sin(angle) * tip_r * 0.85)
                pygame.draw.circle(surface, (255, 200, 240),
                                   (px + dx, tip_y + dy), 1)

            # هسته‌ی مرکزی
            pygame.draw.circle(surface, (255, 130, 240),
                               (px, tip_y), tip_r)
            pygame.draw.circle(surface, (255, 240, 255),
                               (px, tip_y), max(1, tip_r // 2))

    def _draw_hull(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        base: tuple[int, int, int],
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """بدنه‌ی اصلی کشیده (مثل ناوچه)."""
        hull = [
            (cx - int(r * 0.5),  cy - int(r * 0.75)),   # بالا-چپ
            (cx,                  cy - int(r * 0.90)),  # بالا (نوک)
            (cx + int(r * 0.5),  cy - int(r * 0.75)),   # بالا-راست
            (cx + int(r * 0.65), cy - int(r * 0.30)),   # شانه راست
            (cx + int(r * 0.55), cy + int(r * 0.55)),   # پایین-راست
            (cx,                  cy + int(r * 0.85)),  # نوک پایین
            (cx - int(r * 0.55), cy + int(r * 0.55)),   # پایین-چپ
            (cx - int(r * 0.65), cy - int(r * 0.30)),   # شانه چپ
        ]

        # سایه
        shadow = [(x, y + 3) for (x, y) in hull]
        pygame.draw.polygon(surface, dark, shadow)

        # بدنه (دو لایه)
        pygame.draw.polygon(surface, base, hull)

        # لایه‌ی میانی روشن‌تر
        mid = [
            (cx - int(r * 0.35), cy - int(r * 0.55)),
            (cx,                  cy - int(r * 0.75)),
            (cx + int(r * 0.35), cy - int(r * 0.55)),
            (cx + int(r * 0.40), cy + int(r * 0.25)),
            (cx,                  cy + int(r * 0.55)),
            (cx - int(r * 0.40), cy + int(r * 0.25)),
        ]
        pygame.draw.polygon(surface, self._lighter(base, 40), mid)

        # خط نئونی دور
        pygame.draw.polygon(surface, bright, hull, 2)

    def _draw_cockpit(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """کابین شیشه‌ای (جلو، رو به پایین)."""
        cab_y = cy + int(r * 0.35)
        cab_w = max(5, int(r * 0.30))
        cab_h = max(4, int(r * 0.15))

        rect = pygame.Rect(cab_x := cx - cab_w, cab_y - cab_h, cab_w * 2, cab_h * 2)
        pygame.draw.ellipse(surface, (20, 60, 100), rect)
        pygame.draw.ellipse(surface, (100, 220, 255), rect, 2)

        # درخشش داخلی
        inner = rect.inflate(-4, -4)
        pygame.draw.ellipse(surface, (60, 160, 220), inner)

        # خط بازتاب
        pygame.draw.arc(surface, (200, 250, 255), inner, 0.3, 2.0, 1)

    def _draw_energy_core(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """هسته‌ی انرژی مرکزی با خطوط شعاعی."""
        core_y = cy - int(r * 0.10)
        pulse = 0.7 + 0.3 * math.sin(self._t * 6.0)
        core_r = max(3, int(r * 0.22 * pulse))

        # خطوط شعاعی (از مرکز به بیرون)
        for i in range(6):
            angle = self._t * 1.2 + i * math.tau / 6
            x1 = cx + int(math.cos(angle) * (core_r + 3))
            y1 = core_y + int(math.sin(angle) * (core_r + 3))
            x2 = cx + int(math.cos(angle) * (core_r + 10))
            y2 = core_y + int(math.sin(angle) * (core_r + 10))
            a = int(140 * pulse)
            if a > 0:
                line_surf = pygame.Surface((abs(x2 - x1) + 4, abs(y2 - y1) + 4), pygame.SRCALPHA)
                ox = min(x1, x2) - 2
                oy = min(y1, y2) - 2
                pygame.draw.line(line_surf, (255, 150, 240, a),
                                 (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), 1)
                surface.blit(line_surf, (ox, oy))

        # هاله
        glow_size = int(r * 0.5)
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -2):
            a = int(150 * (1 - rr / glow_size) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(glow, (255, 100, 220, a),
                               (glow_size, glow_size), rr)
        surface.blit(glow, (cx - glow_size, core_y - glow_size),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # هسته
        pygame.draw.circle(surface, (255, 130, 230), (cx, core_y), core_r)
        pygame.draw.circle(surface, (255, 240, 255), (cx, core_y), max(1, core_r // 2))

    def _draw_panel_lines(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        bright: tuple[int, int, int],
    ) -> None:
        """خطوط نئونی افقی روی بدنه."""
        for i, y_off in enumerate((-0.45, -0.15, 0.15)):
            y = cy + int(r * y_off)
            w = int(r * (0.35 - i * 0.05))
            pygame.draw.line(surface, bright,
                             (cx - w, y), (cx + w, y), 1)

    def _draw_warning_lights(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """چراغ‌های هشدار کوچک روی بدنه."""
        blink = 0.5 + 0.5 * math.sin(self._t * 6.0)
        for sign in (-1, 1):
            lx = cx + sign * int(r * 0.25)
            ly = cy - int(r * 0.55)
            a = int(200 * blink)
            if a <= 0:
                continue
            glow = pygame.Surface((10, 10), pygame.SRCALPHA)
            for rr in range(5, 0, -1):
                aa = int(a * (1 - rr / 5))
                if aa > 0:
                    pygame.draw.circle(glow, (255, 60, 60, aa), (5, 5), rr)
            surface.blit(glow, (lx - 5, ly - 5),
                         special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.circle(surface, (255, 100, 100), (lx, ly), 2)

    def _draw_hp_bar(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        w = int(r * 1.8)
        h = 5
        x = cx - w // 2
        y = cy - int(r * 0.95) - 14

        bg = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        surface.blit(bg, (x - 2, y - 2))

        ratio = max(0.0, self.hp / self.max_hp)
        color = (80, 255, 140) if ratio > 0.5 else (255, 220, 60) if ratio > 0.25 else (255, 60, 60)
        pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
        pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), 1)



__all__ = ["TankEnemy"]