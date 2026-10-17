"""
IRON DREADNOUGHT — ناوچه‌ی جنگی سنگین (نسخه‌ی افسانه‌ای).
"""
from __future__ import annotations
import math
import random
import pygame
from entities.bullet import Bullet, BulletKind
from entities.enemies.boss_base import BossBase, draw_poly_alpha, draw_line_alpha


class IronDreadnought(BossBase):
    """IRON DREADNOUGHT — ناوچه‌ی جنگی سنگین."""

    HP = 90
    RADIUS = 85
    BODY_COLOR = (230, 80, 50)
    boss_name = "IRON DREADNOUGHT"
    ATTACK_INTERVAL_P1 = 2.5
    ATTACK_INTERVAL_P2 = 2.0
    ATTACK_INTERVAL_P3 = 1.5

    def __init__(self, x, y, scene=None, *, target_y=None):
        super().__init__(x, y, scene=scene, target_y=target_y)
        # انیمیشن‌های اضافی
        self._ring_rot = 0.0
        self._cannon_recoil = [0.0, 0.0]
        self._eye_pulse = 0.0

    def update_ai(self, dt: float) -> None:
        super().update_ai(dt)
        self._ring_rot += dt * 1.2
        self._eye_pulse += dt * 4.0
        for i in range(2):
            if self._cannon_recoil[i] > 0:
                self._cannon_recoil[i] = max(0.0, self._cannon_recoil[i] - dt * 4)

    # ─── حمله‌ها ───
    def _pick_and_execute_attack(self):
        try:
            name = random.choice(["shotgun", "barrage", "missiles"])
            if name == "shotgun":
                self._attack_shotgun()
                self._cannon_recoil = [1.0, 1.0]
            elif name == "barrage":
                self._attack_barrage()
                self._cannon_recoil = [0.7, 0.7]
            elif name == "missiles":
                self._attack_missiles()
        except Exception as exc:
            print(f"[Dreadnought] Attack failed: {exc}")
        finally:
            self._attack_timer = self._get_attack_interval()

    def _attack_shotgun(self):
        if self.scene is None:
            return
        player = getattr(self.scene, "player", None)
        if player is None:
            return
        dx, dy = player.x - self.x, player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        for i in range(6):
            spread = (i / 5 - 0.5) * 0.55
            ca, sa = math.cos(spread), math.sin(spread)
            nx, ny = ux * ca - uy * sa, ux * sa + uy * ca
            try:
                self.scene.spawn_bullet(Bullet(
                    self.x, self.y + 30,
                    nx * 260, ny * 260,
                    friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
                ))
            except Exception:
                pass
        try:
            self.scene.audio.play("enemy_shoot")
            self.scene.camera.shake(5.0)
        except Exception:
            pass

    def _attack_barrage(self):
        if self.scene is None:
            return
        player = getattr(self.scene, "player", None)
        if player is None:
            return
        base = math.atan2(player.y - self.y, player.x - self.x)
        for w in range(2):
            for i in range(3):
                angle = base + w * 0.15 + (i - 1) * 0.1
                try:
                    self.scene.spawn_bullet(Bullet(
                        self.x, self.y + 30,
                        math.cos(angle) * 340, math.sin(angle) * 340,
                        friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
                    ))
                except Exception:
                    pass
        try:
            self.scene.audio.play("enemy_shoot")
        except Exception:
            pass

    def _attack_missiles(self):
        if self.scene is None:
            return
        for sign in (-1, 1):
            angle = math.pi / 2 + sign * 0.25
            try:
                self.scene.spawn_bullet(Bullet(
                    self.x + sign * 35, self.y + 20,
                    math.cos(angle) * 180, math.sin(angle) * 180,
                    friendly=False, kind=BulletKind.HOMING, scene=self.scene,
                    target=getattr(self.scene, "player", None), life=5.0,
                ))
            except Exception:
                pass
        try:
            self.scene.audio.play("enemy_shoot")
            self.scene.camera.shake(6.0)
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════════
    #  رسم — Battlecruiser افسانه‌ای
    # ═════════════════════════════════════════════════════════════════════

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = int(self.radius * 1.35)
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 110)
        darker = self._darker(base, 170)
        bright = self._lighter(base, 70)
        yellow = (255, 210, 60)

        # ---- ۱. سایه‌ی غول‌پیکر زیر ----
        sw, sh = int(r * 1.7), int(r * 0.5)
        shadow = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        for rr in range(sh, 0, -1):
            a = int(110 * (1 - rr / sh) ** 1.5)
            if a > 0:
                pygame.draw.ellipse(shadow, (0, 0, 0, a),
                                    (sw - rr, sh - rr, rr * 2, rr * 2))
        surface.blit(shadow, (cx - sw, cy + int(r * 0.6) - sh))

        # ---- ۲. هاله‌ی قرمز پشت (epic) ----
        aura_r = int(r * 1.4)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -6):
            a = int(35 * (1 - rr / aura_r) ** 2)
            if a > 0:
                pygame.draw.circle(aura, (255, 80, 40, a), (aura_r, aura_r), rr)
        surface.blit(aura, (cx - aura_r, cy - aura_r),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۳. بال‌های زره‌ای غول‌پیکر (لایه‌ی پشتی) ----
        for sign in (-1, 1):
            # لایه‌ی زیر (تیره‌تر، بزرگ‌تر)
            wing_back = [
                (cx + sign * int(r * 0.5), cy - int(r * 0.45)),
                (cx + sign * int(r * 1.65), cy - int(r * 0.6)),
                (cx + sign * int(r * 1.75), cy + int(r * 0.5)),
                (cx + sign * int(r * 0.95), cy + int(r * 0.7)),
                (cx + sign * int(r * 0.5), cy + int(r * 0.4)),
            ]
            draw_poly_alpha(surface, wing_back, (*darker, 255))
            draw_poly_alpha(surface, wing_back, (*bright, 255), width=3)

            # خط زرد-هشدار روی بال
            for i in range(4):
                t1 = i / 4
                t2 = (i + 0.35) / 4
                x1 = cx + sign * int(r * (1.0 + t1 * 0.7))
                x2 = cx + sign * int(r * (1.0 + t2 * 0.7))
                pygame.draw.line(surface, yellow,
                                 (x1, cy - int(r * 0.5)),
                                 (x2, cy - int(r * 0.5)), 3)

            # خطوط زره‌ای افقی روی بال (پنل‌ها)
            for i in range(3):
                ly = cy - int(r * 0.25) + i * int(r * 0.25)
                lx1 = cx + sign * int(r * 0.85)
                lx2 = cx + sign * int(r * 1.6 - i * 0.1 * r)
                pygame.draw.line(surface, dark,
                                 (lx1, ly), (lx2, ly), 2)

            # چراغ ناوبری روی نوک بال
            tip_x = cx + sign * int(r * 1.7)
            tip_y = cy - int(r * 0.05)
            blink = 0.5 + 0.5 * math.sin(self._t * 4 + (0 if sign < 0 else math.pi))
            a = int(220 * blink)
            if a > 0:
                color = (255, 60, 60) if sign < 0 else (60, 255, 100)
                g = pygame.Surface((18, 18), pygame.SRCALPHA)
                for rr in range(9, 0, -2):
                    aa = int(a * (1 - rr / 9))
                    if aa > 0:
                        pygame.draw.circle(g, (*color, aa), (9, 9), rr)
                surface.blit(g, (tip_x - 9, tip_y - 9),
                             special_flags=pygame.BLEND_RGBA_ADD)
                pygame.draw.circle(surface, color, (tip_x, tip_y), 4)

        # ---- ۴. بدنه‌ی اصلی (هشت‌ضلعی زره‌ای) ----
        rot = self._rotation * 0.08
        hull = []
        for i in range(8):
            angle = rot + i * math.tau / 8 - math.pi / 8
            hull.append((cx + math.cos(angle) * r * 0.85,
                         cy + math.sin(angle) * r * 0.85))

        # سایه‌ی بدنه
        draw_poly_alpha(surface, [(x, y + 5) for x, y in hull], (*darker, 255))
        # بدنه
        draw_poly_alpha(surface, hull, (*dark, 255))

        # لایه‌ی میانی روشن
        mid = []
        for i in range(6):
            angle = -rot + i * math.tau / 6
            mid.append((cx + math.cos(angle) * r * 0.65,
                        cy + math.sin(angle) * r * 0.65))
        draw_poly_alpha(surface, mid, (*base, 255))

        # خطوط نئونی
        draw_poly_alpha(surface, hull, (*bright, 255), width=3)
        draw_poly_alpha(surface, mid, (*bright, 255), width=2)

        # خطوط شعاعی بین رأس‌ها
        for i in range(8):
            angle = rot + i * math.tau / 8 - math.pi / 8
            x1 = cx + math.cos(angle) * r * 0.85
            y1 = cy + math.sin(angle) * r * 0.85
            x2 = cx + math.cos(angle) * r * 0.65
            y2 = cy + math.sin(angle) * r * 0.65
            draw_line_alpha(surface, (*bright, 200), (x1, y1), (x2, y2), 2)

        # ---- ۵. پیچ‌ها روی رأس‌های بدنه ----
        for i in range(8):
            angle = rot + i * math.tau / 8 - math.pi / 8
            bx = cx + math.cos(angle) * r * 0.78
            by = cy + math.sin(angle) * r * 0.78
            pygame.draw.circle(surface, dark, (int(bx), int(by)), 4)
            pygame.draw.circle(surface, bright, (int(bx), int(by)), 4, 1)
            pygame.draw.circle(surface, (255, 200, 100), (int(bx), int(by)), 1)

        # ---- ۶. حلقه‌ی چرخان بیرونی راکتور ----
        ring_r = int(r * 0.52)
        for i in range(8):
            a = self._ring_rot + i * math.tau / 8
            px = cx + int(math.cos(a) * ring_r)
            py = cy + int(math.sin(a) * ring_r)
            pulse = 0.5 + 0.5 * math.sin(self._t * 5 + i)
            size = 2 + int(pulse * 2)
            pygame.draw.circle(surface, (255, 200, 80), (px, py), size)
            # هاله
            g = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
            for rr in range(size * 3, 0, -1):
                aa = int(120 * (1 - rr / (size * 3)) * pulse)
                if aa > 0:
                    pygame.draw.circle(g, (255, 180, 60, aa),
                                       (size * 3, size * 3), rr)
            surface.blit(g, (px - size * 3, py - size * 3),
                         special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۷. هسته‌ی راکتور درخشان ----
        pulse = 0.7 + 0.3 * math.sin(self._t * 7)
        core_r = int(r * 0.22 * pulse)

        # هاله‌ی بزرگ قرمز
        for rr in range(int(r * 0.5), 0, -3):
            a = int(180 * (1 - rr / (r * 0.5)) * pulse)
            if a > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 100, 40, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, cy - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # هسته (سه لایه)
        pygame.draw.circle(surface, (255, 40, 20), (cx, cy), core_r + 3)
        pygame.draw.circle(surface, (255, 140, 60), (cx, cy), core_r + 1)
        pygame.draw.circle(surface, (255, 240, 200), (cx, cy), max(2, core_r - 2))

        # ---- ۸. دو چشم قرمز (کنار هسته) ----
        for sign in (-1, 1):
            ex = cx + sign * int(r * 0.38)
            ey = cy - int(r * 0.08)
            eye_r = max(4, int(r * 0.10))
            eye_pulse = 0.7 + 0.3 * math.sin(self._eye_pulse)

            # هاله
            for rr in range(eye_r * 3, 0, -1):
                aa = int(180 * (1 - rr / (eye_r * 3)) * eye_pulse)
                if aa > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (255, 40, 40, aa), (rr * 2, rr * 2), rr)
                    surface.blit(g, (ex - rr * 2, ey - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)

            # خود چشم
            pygame.draw.circle(surface, (255, 40, 40), (ex, ey), eye_r)
            pygame.draw.circle(surface, (255, 200, 200), (ex, ey), max(1, eye_r // 2))
            pygame.draw.circle(surface, (255, 255, 255), (ex - 1, ey - 1), max(1, eye_r // 4))

        # ---- ۹. دو توپ سنگین (جلو) ----
        for i, sign in enumerate((-1, 1)):
            recoil = self._cannon_recoil[i]
            tx = cx + sign * int(r * 0.55)
            ty = cy + int(r * 0.3) - int(recoil * 8)  # recoil به بالا
            tw = int(r * 0.22)
            th = int(r * 0.7)

            # بدنه (سه‌لایه)
            pygame.draw.rect(surface, darker,
                             (tx - tw - 3, ty + 3, (tw + 3) * 2, th))
            pygame.draw.rect(surface, dark, (tx - tw, ty, tw * 2, th))
            pygame.draw.rect(surface, bright, (tx - tw, ty, tw * 2, th), 3)

            # خطوط فنری روی توپ
            for j in range(4):
                ly = ty + int(th * (0.2 + j * 0.2))
                pygame.draw.line(surface, bright,
                                 (tx - tw, ly), (tx + tw, ly), 1)

            # نشانگر روی توپ (قرمز)
            pygame.draw.circle(surface, (255, 60, 60),
                               (tx, ty + th // 2), 3)

            # دهانه‌ی درخشان (پایین)
            tip_y = ty + th
            tip_r = int(tw * 0.85)

            # هاله‌ی بزرگ
            for rr in range(tip_r * 3, 0, -2):
                a = int(180 * (1 - rr / (tip_r * 3)) * (0.7 + recoil * 0.3))
                if a > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (255, 200, 80, a), (rr * 2, rr * 2), rr)
                    surface.blit(g, (tx - rr * 2, tip_y - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)

            # دهانه (لایه‌ها)
            pygame.draw.circle(surface, (200, 100, 30), (tx, tip_y), tip_r + 2)
            pygame.draw.circle(surface, (255, 160, 40), (tx, tip_y), tip_r)
            pygame.draw.circle(surface, (255, 240, 180), (tx, tip_y), max(2, tip_r // 2))

        # ---- ۱۰. تهویه‌های اگزوز (بالا) ----
        for sign in (-1, 1):
            vx = cx + sign * int(r * 0.42)
            vy = cy - int(r * 0.65)
            # بدنه‌ی تهویه
            pygame.draw.rect(surface, darker,
                             (vx - 10, vy - 6, 20, 14))
            pygame.draw.rect(surface, bright,
                             (vx - 10, vy - 6, 20, 14), 2)
            # خطوط
            for i in range(3):
                ly = vy - 3 + i * 4
                pygame.draw.line(surface, dark,
                                 (vx - 8, ly), (vx + 8, ly), 1)

            # دود نارنجی
            smoke_a = int(100 * (0.5 + 0.5 * math.sin(self._t * 8 + sign)))
            if smoke_a > 0:
                g = pygame.Surface((24, 24), pygame.SRCALPHA)
                for rr in range(12, 0, -2):
                    aa = int(smoke_a * (1 - rr / 12))
                    if aa > 0:
                        pygame.draw.circle(g, (255, 100, 40, aa), (12, 12), rr)
                surface.blit(g, (vx - 12, vy - 20),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۱۱. نوار HP ----
        if self.hp < self.max_hp:
            self._draw_hp_bar(surface, cx, cy, r)


__all__ = ["IronDreadnought"]