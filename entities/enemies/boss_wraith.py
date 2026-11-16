"""
entities/enemies/boss_wraith.py
===========================

PLASMA WRAITH — شبح پلاسما (نسخه‌ی افسانه‌ای).
"""
from __future__ import annotations
import math
import random
import pygame
from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies.boss_base import BossBase, draw_poly_alpha, draw_line_alpha


class PlasmaWraith(BossBase):
    """PLASMA WRAITH — شبح پلاسما با ۶ شاخک و ۵ چشم."""

    HP = 50
    RADIUS = 65
    BODY_COLOR = (100, 240, 255)
    boss_name = "PLASMA WRAITH"
    ATTACK_INTERVAL_P1 = 2.4
    ATTACK_INTERVAL_P2 = 1.9
    ATTACK_INTERVAL_P3 = 1.4

    TELEPORT_WARN_TIME = 0.55
    TELEPORT_OUT_TIME = 0.3
    TELEPORT_IN_TIME = 0.3

    def __init__(self, x, y, scene=None, *, target_y=None):
        super().__init__(x, y, scene=scene, target_y=target_y)
        # وضعیت و میزان پیشرفت هر مرحله‌ی تلپورت و شفافیت بدنه نگهداری می‌شود.
        # The teleport state, progress of each phase, and body opacity are tracked.
        self._tp_state = "idle"
        self._tp_progress = 0.0
        self._tp_target_x = 0.0
        self._tp_alpha = 1.0
        # فازهای موج شاخک‌ها
        self._tentacle_phases = [random.uniform(0, math.tau) for _ in range(6)]
        # ذرات شناور
        self._wisp_phases = [random.uniform(0, math.tau) for _ in range(8)]
        self._wisp_radius = [random.uniform(0.6, 1.3) for _ in range(8)]
        # چشم‌ها
        self._eye_blink_timer = 0.0
        self._eye_blinking = False



    def update_ai(self, dt: float) -> None:
        super().update_ai(dt)

        # ---- تلپورت ----
        # تلپورت در سه مرحله‌ی هشدار، محو شدن و ظاهر شدن اجرا می‌شود.
        # Teleporting runs through three phases: warning, disappearance, and reappearance.
        if self._tp_state == "warn":
            self._tp_progress += dt / self.TELEPORT_WARN_TIME
            if self._tp_progress >= 1.0:
                self._tp_state = "out"
                self._tp_progress = 0.0
        elif self._tp_state == "out":
            self._tp_progress += dt / self.TELEPORT_OUT_TIME
            self._tp_alpha = max(0.0, 1.0 - self._tp_progress)
            if self._tp_progress >= 1.0:
                # پس از محو شدن کامل، مختصات پایه به مقصد جدید منتقل می‌شود.
                # Once fully faded out, the base position is moved to the new destination.
                self._base_x = self._tp_target_x
                self._sway_phase = 0.0
                self.x = self._base_x
                self._tp_state = "in"
                self._tp_progress = 0.0
        elif self._tp_state == "in":
            self._tp_progress += dt / self.TELEPORT_IN_TIME
            self._tp_alpha = min(1.0, self._tp_progress)
            if self._tp_progress >= 1.0:
                self._tp_state = "idle"
                self._tp_progress = 0.0
                self._tp_alpha = 1.0

        # ---- چشمک چشم‌ها ----
        # زمان چشمک به‌صورت تصادفی تعیین می‌شود و مدت بسته ماندن چشم‌ها کوتاه است.
        # Blink intervals are randomized, while the eyes remain closed only briefly.
        self._eye_blink_timer += dt
        if not self._eye_blinking and self._eye_blink_timer > random.uniform(2, 4):
            self._eye_blinking = True
            self._eye_blink_timer = 0.0
        elif self._eye_blinking and self._eye_blink_timer > 0.15:
            self._eye_blinking = False
            self._eye_blink_timer = 0.0



    def _pick_and_execute_attack(self):
        # هنگام اجرای تلپورت، انتخاب حمله‌ی جدید به تعویق می‌افتد.
        # Starting a new attack is postponed while teleporting is in progress.
        if self._tp_state != "idle":
            self._attack_timer = 0.5
            return
        try:
            name = random.choice(["beam", "nova", "dash"])
            if name == "beam":
                self._attack_beam()
            elif name == "nova":
                self._attack_nova()
            elif name == "dash":
                self._attack_teleport()
        except Exception as exc:
            print(f"[Wraith] Attack failed: {exc}")
        finally:
            self._attack_timer = self._get_attack_interval()

    def _attack_beam(self):
        if self.scene is None:
            return
        player = getattr(self.scene, "player", None)
        if player is None:
            return
        # جهت پرتو با بردار موقعیت بازیکن نسبت به باس تعیین و نرمال‌سازی می‌شود.
        # The beam direction is determined and normalized from the player's position relative to the boss.
        dx, dy = player.x - self.x, player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        # هشت گلوله با فاصله‌ی ثابت روی مسیر پرتو ایجاد می‌شوند.
        # Eight bullets are spawned at fixed intervals along the beam path.
        for i in range(8):
            try:
                self.scene.spawn_bullet(Bullet(
                    self.x + ux * i * 10, self.y + uy * i * 10,
                    ux * 360, uy * 360,
                    friendly=False, kind=BulletKind.BOSS, scene=self.scene,
                ))
            except Exception:
                pass
        try:
            self.scene.audio.play("enemy_shoot")
            self.scene.camera.shake(3.0)
        except Exception:
            pass

    def _attack_nova(self):
        if self.scene is None:
            return
        n = 16
        # گلوله‌ها با فاصله‌ی زاویه‌ای یکسان، یک الگوی انفجاری دایره‌ای می‌سازند.
        # Bullets are evenly spaced by angle to form a circular burst pattern.
        for i in range(n):
            angle = (i / n) * math.tau + self._rotation
            try:
                self.scene.spawn_bullet(Bullet(
                    self.x, self.y,
                    math.cos(angle) * 220, math.sin(angle) * 220,
                    friendly=False, kind=BulletKind.BOSS, scene=self.scene,
                ))
            except Exception:
                pass
        try:
            self.scene.audio.play("enemy_shoot")
            self.scene.camera.shake(4.0)
        except Exception:
            pass

    def _attack_teleport(self):
        if self.scene is None:
            return
        w = S.Window.WIDTH
        # مقصد تلپورت به‌صورت تصادفی در محدوده‌ی افقی امن صفحه انتخاب می‌شود.
        # The teleport destination is randomized within the screen's safe horizontal range.
        self._tp_target_x = random.uniform(w * 0.15, w * 0.85)
        self._tp_state = "warn"
        self._tp_progress = 0.0
        self._tp_alpha = 1.0
        self._danger_flash = 1.0
        try:
            self.scene.audio.play("powerup_spawn")
        except Exception:
            pass
        # حلقه‌ای از ذرات در محل فعلی باس، آغاز تلپورت را نمایش می‌دهد.
        # A particle ring at the boss's current position signals the start of teleporting.
        try:
            from systems.particles import ParticleKind
            self.scene.particles.emit_ring(
                self.x, self.y,
                count=16, radius=8, speed=180,
                color=(150, 220, 255), life=0.4, size=2,
            )
        except Exception:
            pass



    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        # هنگام محو شدن یا ظاهر شدن، شفافیت بدنه از پیشرفت تلپورت گرفته می‌شود.
        # During disappearance or reappearance, body opacity is derived from teleport progress.
        if self._tp_state in ("out", "in"):
            a = self._tp_alpha
            if a <= 0.01:
                return
        else:
            a = 1.0

        r = int(self.radius * 1.3)
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 100)
        bright = self._lighter(base, 80)
        white = (240, 255, 255)

        # در حالت هشدار، رنگ بدنه به‌صورت ضربانی به سمت قرمز تغییر می‌کند.
        # During the warning state, the body color pulses toward red.
        is_warning = self._tp_state == "warn"
        if is_warning:
            flicker = 0.5 + 0.5 * math.sin(self._t * 30)
            base = (
                int(255 * flicker + base[0] * (1 - flicker)),
                int(80 * flicker + base[1] * (1 - flicker)),
                int(80 * flicker + base[2] * (1 - flicker)),
            )
            bright = (255, 180, 180)

        # ---- ۱. هاله‌ی غول‌پیکر ----
        # با کاهش شعاع حلقه‌ها، شفافیت آن‌ها بیشتر می‌شود تا هاله‌ای نرم شکل بگیرد.
        # Ring opacity increases as their radius decreases, creating a smooth aura.
        aura_r = int(r * 2.0)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -5):
            aa = int(45 * (1 - rr / aura_r) ** 1.8 * a)
            if aa > 0:
                color = (255, 100, 100) if is_warning else (100, 220, 255)
                pygame.draw.circle(aura, (*color, aa), (aura_r, aura_r), rr)
        surface.blit(aura, (cx - aura_r, cy - aura_r),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۲. ذرات شناور دور بدنه ----
        # هر ذره با فاز و شعاع مستقل روی مسیری بیضوی پیرامون باس حرکت می‌کند.
        # Each particle moves along an elliptical path around the boss using its own phase and radius.
        for i in range(8):
            phase = self._wisp_phases[i] + self._t * 0.8
            wr = r * self._wisp_radius[i]
            wx = cx + int(math.cos(phase) * wr)
            wy = cy + int(math.sin(phase) * wr * 0.8)
            size = 2 + int(math.sin(self._t * 3 + i) * 1)
            if size > 0 and a > 0.3:
                g = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
                for rr in range(size * 3, 0, -1):
                    aa = int(120 * (1 - rr / (size * 3)) * a)
                    if aa > 0:
                        pygame.draw.circle(g, (*bright, aa),
                                           (size * 3, size * 3), rr)
                surface.blit(g, (wx - size * 3, wy - size * 3),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۳. شش شاخک (پشت، بلند، موج‌دار) ----
        # شاخک‌ها پشت بدنه رسم می‌شوند و طول آن‌ها به‌صورت یکی‌درمیان تغییر می‌کند.
        # The tentacles are drawn behind the body, with alternating lengths.
        for i in range(6):
            base_angle = (i / 6) * math.tau + math.pi / 2
            phase = self._tentacle_phases[i] + self._t * 2.5

            # طول شاخک
            max_len = r * (1.6 + (i % 2) * 0.5)

            # نقاط شاخک (zigzag)
            # نقاط مسیر با ترکیب جهت اصلی و جابه‌جایی عمود بر آن ساخته می‌شوند.
            # Path points combine the main direction with perpendicular displacement.
            pts = []
            segs = 10
            for seg in range(segs + 1):
                t = seg / segs
                # فاصله از مرکز
                dist = r * 0.7 + max_len * t
                # موج
                wave = math.sin(phase + t * 4) * r * 0.25 * t
                perp = base_angle + math.pi / 2
                px = cx + math.cos(base_angle) * dist + math.cos(perp) * wave
                py = cy + math.sin(base_angle) * dist + math.sin(perp) * wave
                pts.append((px, py))

            # رسم با آلفا (ضخامت کاهشی)
            # با نزدیک شدن به نوک شاخک، ضخامت و شفافیت خطوط کاهش پیدا می‌کند.
            # Line thickness and opacity decrease toward the tentacle tip.
            for j in range(len(pts) - 1):
                t = j / (len(pts) - 1)
                width = max(1, int(5 * (1 - t * 0.7)))
                aa = int(180 * (1 - t * 0.9) * a)
                if aa <= 0:
                    continue
                draw_line_alpha(surface, (*bright, aa), pts[j], pts[j + 1], width)

            # هاله‌ی نوک شاخک
            # درخشش انتهایی شاخک فقط زمانی رسم می‌شود که بدنه به‌اندازه‌ی کافی قابل مشاهده باشد.
            # The tentacle tip glow is drawn only when the body is sufficiently visible.
            if a > 0.3:
                tip_x, tip_y = pts[-1]
                for rr in range(8, 0, -2):
                    aa = int(80 * (1 - rr / 8) * a)
                    if aa > 0:
                        g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                        pygame.draw.circle(g, (*bright, aa), (rr * 2, rr * 2), rr)
                        surface.blit(g, (int(tip_x) - rr * 2, int(tip_y) - rr * 2),
                                     special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۴. بدنه‌ی شبح چندلایه ----
        # چندضلعی‌های چرخان با اندازه‌های متفاوت، ساختار چندلایه‌ی بدنه را ایجاد می‌کنند.
        # Rotating polygons of different sizes create the body's layered structure.
        rot = self._rotation * 0.2

        # لایه‌ی بیرونی (خارج، موج‌دار)
        outer_pts = []
        for i in range(16):
            angle = rot + i * math.tau / 16
            wobble = 1.0 + 0.2 * math.sin(self._t * 3 + i * 0.7)
            outer_pts.append((
                cx + math.cos(angle) * r * 0.95 * wobble,
                cy + math.sin(angle) * r * 0.9 * wobble,
            ))
        draw_poly_alpha(surface, outer_pts, (*base, int(140 * a)))

        # لایه‌ی میانی
        mid_pts = []
        for i in range(12):
            angle = -rot * 0.6 + i * math.tau / 12
            wobble = 1.0 + 0.12 * math.sin(self._t * 4 + i * 1.2)
            mid_pts.append((
                cx + math.cos(angle) * r * 0.7 * wobble,
                cy + math.sin(angle) * r * 0.65 * wobble,
            ))
        draw_poly_alpha(surface, mid_pts, (*dark, int(220 * a)))

        # لایه‌ی داخلی
        inner_pts = []
        for i in range(8):
            angle = rot * 0.9 + i * math.tau / 8
            inner_pts.append((
                cx + math.cos(angle) * r * 0.42,
                cy + math.sin(angle) * r * 0.42,
            ))
        draw_poly_alpha(surface, inner_pts, (*self._lighter(base, 20), int(200 * a)))

        # خطوط نئونی
        # خطوط روشن روی مرز چندضلعی‌ها، لبه‌های هر لایه را برجسته می‌کنند.
        # Bright outlines along the polygons emphasize the edges of each layer.
        draw_poly_alpha(surface, outer_pts, (*bright, int(230 * a)), width=2)
        draw_poly_alpha(surface, mid_pts, (*bright, int(180 * a)), width=1)

        # ---- ۵. ۵ چشم در قوس ----
        # هنگام چشمک زدن، رسم هر پنج چشم موقتاً متوقف می‌شود.
        # All five eyes are temporarily hidden while the boss is blinking.
        if not self._eye_blinking:
            for i in range(5):
                # موقعیت در قوس بالا
                angle = -math.pi / 2 + (i - 2) * 0.35
                ex = cx + int(math.cos(angle) * r * 0.45)
                ey = cy + int(math.sin(angle) * r * 0.45)
                eye_r = max(2, int(r * 0.08))

                # هاله‌ی چشم
                # هاله با چند دایره‌ی نیمه‌شفاف ساخته می‌شود تا درخشش تدریجی داشته باشد.
                # The glow is built from translucent circles to produce a gradual light effect.
                for rr in range(eye_r * 5, 0, -1):
                    aa = int(180 * (1 - rr / (eye_r * 5)) * a)
                    if aa <= 0:
                        continue
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    color = (255, 120, 120) if is_warning else (255, 255, 255)
                    pygame.draw.circle(g, (*color, aa), (rr * 2, rr * 2), rr)
                    surface.blit(g, (ex - rr * 2, ey - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)

                # خود چشم
                if a > 0.2:
                    pygame.draw.circle(surface, (255, 255, 255),
                                       (ex, ey), max(1, int(eye_r * a)))
                    pupil = (255, 80, 80) if is_warning else (60, 160, 220)
                    pygame.draw.circle(surface, pupil,
                                       (ex, ey), max(1, int(eye_r * 0.5 * a)))

        # ---- ۶. هسته‌ی مرکزی غول‌پیکر ----
        # شدت روشنایی هسته با تابع سینوسی تغییر می‌کند تا حالت تپش ایجاد شود.
        # The core brightness changes sinusoidally to create a pulsing effect.
        pulse = 0.7 + 0.3 * math.sin(self._t * 6)
        core_r = int(r * 0.30 * pulse)

        # هاله‌ی بزرگ
        for rr in range(int(r * 0.7), 0, -3):
            aa = int(200 * (1 - rr / (r * 0.7)) ** 1.5 * pulse * a)
            if aa > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                color = (255, 200, 200) if is_warning else (200, 250, 255)
                pygame.draw.circle(g, (*color, aa), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, cy - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # هسته (سه لایه)
        # سه دایره‌ی تو‌در‌تو، از رنگ تیره‌تر تا روشن‌ترین نقطه‌ی مرکزی رسم می‌شوند.
        # Three nested circles are drawn from the darker outer layer to the brightest center.
        if a > 0.1:
            pygame.draw.circle(surface, (100, 220, 255),
                               (cx, cy), max(1, int(core_r * 1.2 * a)))
            pygame.draw.circle(surface, (200, 250, 255),
                               (cx, cy), max(1, int(core_r * a)))
            pygame.draw.circle(surface, (255, 255, 255),
                               (cx, cy), max(1, int(core_r * 0.5 * a)))

        # ---- ۷. حلقه‌های چرخان دور هسته ----
        # دو حلقه با جهت و سرعت چرخش متفاوت، ذرات نورانی را پیرامون هسته حرکت می‌دهند.
        # Two rings with different rotation directions and speeds move glowing particles around the core.
        if a > 0.3:
            for ring_idx, (ring_r_ratio, speed, col) in enumerate([
                (0.5, 1.5, (100, 220, 255)),
                (0.65, -1.0, (200, 250, 255)),
            ]):
                ring_r = int(r * ring_r_ratio)
                for i in range(6):
                    angle = self._t * speed + i * math.tau / 6
                    px = cx + int(math.cos(angle) * ring_r)
                    py = cy + int(math.sin(angle) * ring_r * 0.85)
                    size = 2 if ring_idx == 0 else 3
                    aa = int(180 * a)
                    g = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
                    for rr in range(size * 3, 0, -1):
                        aa2 = int(aa * (1 - rr / (size * 3)))
                        if aa2 > 0:
                            pygame.draw.circle(g, (*col, aa2),
                                               (size * 3, size * 3), rr)
                    surface.blit(g, (px - size * 3, py - size * 3),
                                 special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۸. نشانگر مقصد تلپورت ----
        # مقصد آینده‌ی باس با حلقه‌ی هشدار و خطی زیگزاگ از موقعیت فعلی مشخص می‌شود.
        # The boss's next position is indicated by a warning ring and a zigzag line from its current location.
        if self._tp_state == "warn" and self.scene is not None:
            target_x = self._tp_target_x
            target_y = self.ENTRY_Y
            pulse_r = int(r * 0.5 + 40 * self._tp_progress)
            for rr in range(pulse_r, 0, -3):
                aa = int(160 * (1 - rr / pulse_r))
                if aa > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (255, 100, 100, aa), (rr * 2, rr * 2), rr, 3)
                    surface.blit(g, (int(target_x) - rr * 2, int(target_y) - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)

            # خط زیگزاگ از باس به مقصد
            # نقاط میانی مسیر به‌صورت تصادفی جابه‌جا می‌شوند تا خط ظاهری نامنظم داشته باشد.
            # Intermediate points are randomly displaced to give the line an irregular appearance.
            line_alpha = int(120 * self._tp_progress)
            if line_alpha > 0:
                prev_x, prev_y = cx, cy
                segs = 6
                for j in range(1, segs + 1):
                    t = j / segs
                    bx = cx + (target_x - cx) * t
                    by = cy + (target_y - cy) * t
                    if j < segs:
                        bx += random.uniform(-20, 20)
                        by += random.uniform(-20, 20)
                    draw_line_alpha(surface, (255, 120, 120, line_alpha),
                                    (prev_x, prev_y), (bx, by), 2)
                    prev_x, prev_y = bx, by

    def get_hitcircles(self):
        """یک hitbox بزرگ‌تر که با بدن شبح هماهنگه."""
        # شعاع برخورد با ضریب ۱٫۳ محاسبه می‌شود تا محدوده‌ی برخورد از بدنه‌ی اصلی بزرگ‌تر باشد.
        # The collision radius is scaled by 1.3, making it larger than the main body.
        r = self.radius
        return [
            (self.x, self.y, r * 1.3),
        ]


__all__ = ["PlasmaWraith"]