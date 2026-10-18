"""
OMEGA CORE — هسته‌ی امگا (باس افسانه‌ای).

دیزاین:
    • هاله‌ی غول‌پیکر (رنگ با فاز عوض می‌شه: نارنجی → قرمز → سفید-بنفش)
    • ۱۲ کریستال شناور در مدار با trail
    • ۳ حلقه‌ی چرخان در زوایای مختلف
    • ۴ شاخک انرژی موج‌دار
    • بدنه‌ی تیره با شکاف‌های درخشان (رگ‌های انرژی)
    • هسته‌ی مرکزی پالسی غول‌پیکر

حملات:
    1. Spiral Storm  — دو-دستی چرخان
    2. Meteor Shower — بارش شهاب از بالا
    3. Nova          — انفجار شعاعی ۲۴ گلوله
    4. Aimed Spread  — ۷ گلوله هدایت‌شده

فاز ۲ (۶۶٪): Fast Spiral (۴ دستی)
فاز ۳ (۳۳٪): Hyper Nova (۳۲ شعاعی + ۵ هدایت‌شده)

ظهور: از موج ۱۰، شانس ۱۰-۳۵٪ (بسته به موج)
"""

from __future__ import annotations

import math
import random
import pygame

from entities.bullet import Bullet, BulletKind
from entities.enemies.boss_base import BossBase, draw_poly_alpha, draw_line_alpha


class OmegaCore(BossBase):
    """OMEGA CORE — قلب مکانیکی کیهان."""

    HP = 180
    RADIUS = 110
    BODY_COLOR = (255, 140, 40)
    boss_name = "OMEGA CORE"

    # ---- زمان‌بندی ----
    ATTACK_INTERVAL_P1 = 2.0
    ATTACK_INTERVAL_P2 = 1.5
    ATTACK_INTERVAL_P3 = 1.0
    ENTRY_Y = 220
    SWAY_AMPLITUDE = 200
    SWAY_SPEED = 0.5

    # ---- فاز ----
    PHASE_2_THRESHOLD = 0.66
    PHASE_3_THRESHOLD = 0.33

    def __init__(self, x, y, scene=None, *, target_y=None):
        super().__init__(x, y, scene=scene, target_y=target_y)
        # ---- انیمیشن ----
        self._ring_rot = [0.0, 0.0, 0.0]
        self._crystal_phases = [random.uniform(0, math.tau) for _ in range(12)]
        self._crystal_orbit_radius = [random.uniform(0.85, 1.05) for _ in range(12)]
        self._tendril_phases = [random.uniform(0, math.tau) for _ in range(4)]
        self._core_pulse = 0.0
        self._crack_angles = [random.uniform(0, math.tau) for _ in range(10)]
        self._phase_flash = 0.0

        # ---- spiral state ----
        self._spiral_angle = 0.0
        self._spiral_timer = 0.0
        self._spiral_duration = 1.5
        self._spiral_arms = 2
        self._spiral_speed = 180

        # ---- زاویه‌ی بدنه (برای تنوع بیشتر) ----
        self._body_rot = 0.0
        self._eye_look = (0.0, 0.0)
        self._eye_target = (0.0, 0.0)

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update_ai(self, dt: float) -> None:
        # ---- قبل از صدا زدن super، فاز قبلی رو ذخیره کن ----
        prev_phase = self._phase

        super().update_ai(dt)

        # ---- چرخش‌ها ----
        self._ring_rot[0] += dt * 0.6
        self._ring_rot[1] -= dt * 0.8
        self._ring_rot[2] += dt * 1.1
        self._core_pulse += dt * 5.0
        self._body_rot += dt * (0.15 + self._phase * 0.1)

        # ---- چشم بازیکن رو دنبال می‌کنه ----
        player = getattr(self.scene, "player", None) if self.scene else None
        if player and player.alive:
            dx = player.x - self.x
            dy = player.y - self.y
            d = math.hypot(dx, dy) or 1.0
            self._eye_target = (dx / d, dy / d)
        blend = min(1.0, dt * 3.0)
        self._eye_look = (
            self._eye_look[0] + (self._eye_target[0] - self._eye_look[0]) * blend,
            self._eye_look[1] + (self._eye_target[1] - self._eye_look[1]) * blend,
        )

        # ---- phase flash decay ----
        if self._phase_flash > 0:
            self._phase_flash = max(0.0, self._phase_flash - dt * 2.0)

        # ---- تشخیص تغییر فاز ----
        if self._phase > prev_phase:
            self._on_phase_change()

    def _on_phase_change(self) -> None:
        """وقتی فاز عوض می‌شه، افکت قوی."""
        self._phase_flash = 1.0
        try:
            if self.scene is not None:
                self.scene.camera.shake(18.0, aftershock=3)
                self.scene.audio.play("player_explode")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    #  حمله‌ها
    # ─────────────────────────────────────────────────────────────────────

    def _update_attacks(self, dt: float) -> None:
        if self._current_attack == "spiral":
            self._update_spiral(dt)
            return
        super()._update_attacks(dt)

    def _pick_and_execute_attack(self) -> None:
        if self._phase == 1:
            attacks = ["spiral", "meteor", "nova", "aimed"]
        elif self._phase == 2:
            attacks = ["spiral", "meteor", "nova", "aimed", "fast_spiral"]
        else:
            attacks = ["spiral", "meteor", "nova", "aimed", "fast_spiral", "hyper_nova"]

        name = random.choice(attacks)

        if name == "spiral":
            self._start_spiral(arms=2, duration=1.5, speed=180)
        elif name == "fast_spiral":
            self._start_spiral(arms=4, duration=2.0, speed=160)
        elif name == "meteor":
            self._attack_meteor()
            self._attack_timer = self._get_attack_interval()
        elif name == "nova":
            self._fire_radial(24, 240)
            self._attack_timer = self._get_attack_interval()
        elif name == "aimed":
            self._fire_aimed(7, 320)
            self._attack_timer = self._get_attack_interval()
        elif name == "hyper_nova":
            self._fire_radial(32, 280)
            self._fire_aimed(5, 340)
            self._attack_timer = self._get_attack_interval() * 1.3

    # ---- SPIRAL ----
    def _start_spiral(self, arms: int = 2, duration: float = 1.5, speed: float = 180) -> None:
        self._current_attack = "spiral"
        self._attack_progress = 0.0
        self._spiral_angle = random.uniform(0, math.tau)
        self._spiral_timer = 0.0
        self._spiral_duration = duration
        self._spiral_arms = arms
        self._spiral_speed = speed

    def _update_spiral(self, dt: float) -> None:
        self._attack_progress += dt / self._spiral_duration
        self._spiral_timer -= dt

        if self._spiral_timer <= 0:
            self._spiral_timer = 0.05
            if self.scene is not None:
                for arm in range(self._spiral_arms):
                    angle = self._spiral_angle + arm * math.tau / self._spiral_arms
                    try:
                        self.scene.spawn_bullet(Bullet(
                            self.x, self.y,
                            math.cos(angle) * self._spiral_speed,
                            math.sin(angle) * self._spiral_speed,
                            friendly=False, kind=BulletKind.ENEMY,
                            scene=self.scene,
                        ))
                    except Exception:
                        pass
            self._spiral_angle += 0.18 + self._phase * 0.03

        if self._attack_progress >= 1.0:
            self._reset_attack()

    # ---- METEOR ----
    def _attack_meteor(self) -> None:
        if self.scene is None:
            return
        try:
            W = self.scene.screen.get_width()
        except Exception:
            W = 1280

        for _ in range(10):
            x = random.uniform(60, W - 60)
            y = random.uniform(-120, -20)
            speed = random.uniform(240, 340)
            try:
                b = Bullet(
                    x, y, 0, speed,
                    friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
                )
                b.radius = 8
                self.scene.spawn_bullet(b)
            except Exception:
                pass

        try:
            self.scene.audio.play("enemy_shoot")
            self.scene.camera.shake(5.0)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    #  رسم
    # ─────────────────────────────────────────────────────────────────────

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = int(self.radius * 1.25)
        cx, cy = int(self.x), int(self.y)

        # ---- رنگ بر اساس فاز ----
        if self._phase == 1:
            primary = (255, 150, 40)
            secondary = (200, 60, 20)
            glow = (255, 200, 100)
        elif self._phase == 2:
            primary = (255, 70, 40)
            secondary = (150, 20, 20)
            glow = (255, 120, 100)
        else:
            primary = (240, 180, 255)
            secondary = (120, 40, 180)
            glow = (255, 220, 255)

        # اگه در حال phase flash، رنگ سفید بشه
        if self._phase_flash > 0:
            t = self._phase_flash
            primary = tuple(int(p * (1-t) + 255 * t) for p in primary)
            glow = (255, 255, 255)

        # ---- ۱. هاله‌ی غول‌پیکر ----
        aura_r = int(r * 1.9)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -6):
            a = int(40 * (1 - rr / aura_r) ** 2)
            if a > 0:
                pygame.draw.circle(aura, (*primary, a), (aura_r, aura_r), rr)
        surface.blit(aura, (cx - aura_r, cy - aura_r),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۲. ۱۲ کریستال شناور در مدار ----
        for i in range(12):
            base_angle = self._t * 0.7 + i * math.tau / 12 + self._crystal_phases[i]
            orbit_r = r * self._crystal_orbit_radius[i]
            orbit_r += math.sin(self._t * 1.2 + i) * 8
            px = cx + math.cos(base_angle) * orbit_r
            py = cy + math.sin(base_angle) * orbit_r * 0.65

            # trail (سه نقطه قبل)
            for trail_i in range(3, 0, -1):
                ta = base_angle - trail_i * 0.12
                tpx = cx + math.cos(ta) * orbit_r
                tpy = cy + math.sin(ta) * orbit_r * 0.65
                t_alpha = int(100 * (1 - trail_i / 4))
                if t_alpha > 0:
                    pygame.draw.circle(surface, (*primary, t_alpha),
                                       (int(tpx), int(tpy)),
                                       max(1, 4 - trail_i))

            # خود کریستال (الماس کوچک)
            size = 4 + int(2 * math.sin(self._t * 3 + i))
            crystal = [
                (px, py - size), (px + size * 0.6, py),
                (px, py + size), (px - size * 0.6, py),
            ]
            draw_poly_alpha(surface, crystal, (*glow, 255))
            draw_poly_alpha(surface, crystal, (255, 255, 255, 255), width=1)

        # ---- ۳. ۴ شاخک انرژی ----
        for i in range(4):
            base_angle = (i / 4) * math.tau + self._t * 0.2 + math.pi / 4
            phase = self._tendril_phases[i] + self._t * 2.5
            max_len = r * 1.5

            pts = []
            segs = 8
            for seg in range(segs + 1):
                t = seg / segs
                dist = r * 0.9 + max_len * t
                wave = math.sin(phase + t * 5) * 18 * t
                perp = base_angle + math.pi / 2
                px = cx + math.cos(base_angle) * dist + math.cos(perp) * wave
                py = cy + math.sin(base_angle) * dist + math.sin(perp) * wave
                pts.append((px, py))

            for j in range(len(pts) - 1):
                t = j / (len(pts) - 1)
                width = max(1, int(4 * (1 - t * 0.7)))
                a = int(160 * (1 - t * 0.85))
                if a > 0:
                    draw_line_alpha(surface, (*primary, a), pts[j], pts[j+1], width)

            # هاله‌ی نوک
            tip_x, tip_y = pts[-1]
            for rr in range(8, 0, -2):
                a = int(80 * (1 - rr / 8))
                if a > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (*glow, a), (rr * 2, rr * 2), rr)
                    surface.blit(g, (int(tip_x) - rr * 2, int(tip_y) - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۴. ۳ حلقه‌ی چرخان (نقاط درخشان) ----
        for ring_idx, (ring_r_ratio, rot_speed, color) in enumerate([
            (1.55, 1.0, primary),
            (1.40, -0.7, glow),
            (1.25, 1.3, primary),
        ]):
            ring_r = int(r * ring_r_ratio)
            num_dots = 20 if ring_idx == 0 else 16
            for i in range(num_dots):
                angle = self._ring_rot[ring_idx] + i * math.tau / num_dots
                px = cx + int(math.cos(angle) * ring_r)
                py = cy + int(math.sin(angle) * ring_r * 0.88)
                pulse = 0.5 + 0.5 * math.sin(self._t * 5 + i + ring_idx * 2)
                size = 1 + int(pulse * 2)
                # هاله‌ی نقطه
                g = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
                for rr in range(size * 3, 0, -1):
                    aa = int(120 * (1 - rr / (size * 3)) * pulse)
                    if aa > 0:
                        pygame.draw.circle(g, (*color, aa),
                                           (size * 3, size * 3), rr)
                surface.blit(g, (px - size * 3, py - size * 3),
                             special_flags=pygame.BLEND_RGBA_ADD)
                pygame.draw.circle(surface, color, (px, py), size)

        # ---- ۵. بدنه‌ی اصلی (کره) ----
        # سایه (عمق)
        pygame.draw.circle(surface, self._darker(secondary, 60),
                           (cx + 4, cy + 4), r)
        # بدنه‌ی بیرونی
        pygame.draw.circle(surface, secondary, (cx, cy), r)
        # لایه‌ی میانی
        pygame.draw.circle(surface, self._lighter(secondary, 20),
                           (cx, cy), int(r * 0.9))
        # بدنه‌ی اصلی روشن‌تر
        pygame.draw.circle(surface, primary, (cx, cy), int(r * 0.78))

        # ---- ۶. شکاف‌های درخشان (رگ‌های انرژی) ----
        num_cracks = 8 + self._phase * 3  # ۱۱ تا در فاز ۳
        for i in range(num_cracks):
            angle = self._crack_angles[i % len(self._crack_angles)] + self._body_rot
            # شکاف zigzag از مرکز به لبه
            start_r = r * 0.25
            end_r = r * (0.75 + 0.1 * math.sin(self._t * 2 + i))
            x1 = cx + math.cos(angle) * start_r
            y1 = cy + math.sin(angle) * start_r
            mid_angle = angle + random.uniform(-0.15, 0.15)
            mid_r = (start_r + end_r) / 2
            x2 = cx + math.cos(mid_angle) * mid_r
            y2 = cy + math.sin(mid_angle) * mid_r
            x3 = cx + math.cos(angle) * end_r
            y3 = cy + math.sin(angle) * end_r

            pulse = 0.5 + 0.5 * math.sin(self._t * 6 + i)
            a = int(140 + 100 * pulse)
            width = 2 if self._phase < 3 else 3
            draw_line_alpha(surface, (*glow, a), (x1, y1), (x2, y2), width)
            draw_line_alpha(surface, (*glow, a), (x2, y2), (x3, y3), width)

        # ---- ۷. هاله‌ی درونی (حلقه‌ی نازک روی بدنه) ----
        for rr in range(r - 2, int(r * 0.85), -2):
            a = int(60 * (1 - (r - rr) / (r * 0.15)))
            if a > 0:
                pygame.draw.circle(surface, (*glow, a), (cx, cy), rr, 1)

        # ---- ۸. هسته‌ی مرکزی پالسی ----
        pulse = 0.7 + 0.3 * math.sin(self._core_pulse)
        core_r = int(r * 0.30 * pulse)

        # هاله‌ی غول‌پیکر هسته
        for rr in range(int(r * 0.7), 0, -3):
            a = int(200 * (1 - rr / (r * 0.7)) ** 1.5 * pulse)
            if a > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (*glow, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, cy - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # هسته (سه لایه)
        pygame.draw.circle(surface, primary, (cx, cy), core_r + 3)
        pygame.draw.circle(surface, glow, (cx, cy), core_r + 1)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(2, core_r - 2))

        # ---- ۹. چشم مرکزی (بازیکن رو دنبال می‌کنه) ----
        eye_r = int(r * 0.15)
        ex = cx + int(self._eye_look[0] * r * 0.08)
        ey = cy + int(self._eye_look[1] * r * 0.08)

        # مردمک (به بازیکن نگاه می‌کنه)
        pupil_x = ex + int(self._eye_look[0] * eye_r * 0.4)
        pupil_y = ey + int(self._eye_look[1] * eye_r * 0.4)
        pygame.draw.circle(surface, (30, 10, 10), (pupil_x, pupil_y),
                           int(eye_r * 0.6))

        # برق چشم
        pygame.draw.circle(surface, (255, 255, 255),
                           (pupil_x - 2, pupil_y - 2), max(1, eye_r // 4))

        # ---- ۱۰. حلقه‌ی فاز (نشانگر) ----
        phase_ring_r = int(r * 1.05)
        phase_arc = (self.hp / self.max_hp) * math.tau
        for i in range(int(phase_arc / 0.05)):
            angle = -math.pi / 2 + i * 0.05
            px = cx + math.cos(angle) * phase_ring_r
            py = cy + math.sin(angle) * phase_ring_r
            pygame.draw.circle(surface, glow, (int(px), int(py)), 2)

        # ---- ۱۱. phase flash (اثر تغییر فاز) ----
        if self._phase_flash > 0:
            t = self._phase_flash
            flash_r = int(r * (1.5 + (1 - t) * 2.0))
            for rr in range(flash_r, int(r * 1.2), -3):
                a = int(180 * t * (1 - (rr - r * 1.2) / (flash_r - r * 1.2)))
                if a > 0:
                    pygame.draw.circle(surface, (255, 255, 255, a),
                                       (cx, cy), rr, 3)

        # ---- ۱۲. نوار HP ----
        if self.hp < self.max_hp:
            self._draw_hp_bar(surface, cx, cy, r)


__all__ = ["OmegaCore"]