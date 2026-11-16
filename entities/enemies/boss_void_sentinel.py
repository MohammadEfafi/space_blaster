"""
entities/enemies/boss_void_sentinel.py
===========================

VOID SENTINEL — نگهبان خلأ (باس کیهانی).
"""
from __future__ import annotations

import math
import random
import pygame

from entities.enemies.base import EnemyKind
from entities.enemies.boss_base import BossBase, draw_poly_alpha, draw_line_alpha


class VoidSentinel(BossBase):
    """VOID SENTINEL — باس کیهانی با ۳ فاز و رعد و برق."""

    KIND = EnemyKind.BOSS
    HP = 80
    RADIUS = 80
    BODY_COLOR = (180, 60, 220)
    boss_name = "VOID SENTINEL"

    LIGHTNING_CHARGE_TIME = 0.85
    SUMMON_TIME = 1.0

    def __init__(self, x, y, scene=None, *, target_y=None):
        super().__init__(x, y, scene=scene, target_y=target_y)
        self._eye_look = (0.0, 0.0)
        self._eye_target = (0.0, 0.0)
        self._crystal_phases = [random.uniform(0, math.tau) for _ in range(6)]

    def update_ai(self, dt: float) -> None:
        super().update_ai(dt)
        # جهت نگاه چشم بر اساس موقعیت بازیکن تعیین می‌شود.
        # The eye direction is determined by the player's position.
        player = getattr(self.scene, "player", None) if self.scene else None
        if player and player.alive:
            dx = player.x - self.x
            dy = player.y - self.y
            d = math.hypot(dx, dy) or 1.0
            self._eye_target = (dx / d, dy / d)
        # تغییر جهت نگاه به‌صورت تدریجی انجام می‌شود تا حرکت چشم نرم باشد.
        # The eye direction changes gradually to produce smooth movement.
        blend = min(1.0, dt * 4.0)
        self._eye_look = (
            self._eye_look[0] + (self._eye_target[0] - self._eye_look[0]) * blend,
            self._eye_look[1] + (self._eye_target[1] - self._eye_look[1]) * blend,
        )

    def _update_attacks(self, dt: float) -> None:
        # حمله صاعقه تا پایان زمان شارژ به‌روزرسانی می‌شود.
        # The lightning attack is updated until its charge duration completes.
        if self._current_attack == "lightning":
            self._attack_progress += dt / self.LIGHTNING_CHARGE_TIME
            self._emit_charge_particles(dt)
            if self._attack_progress >= 1.0:
                self._fire_lightning()
                self._reset_attack()
            return

        # احضار دشمنان پس از تکمیل نوار پیشرفت اجرا می‌شود.
        # Enemy summoning is executed when the progress reaches completion.
        if self._current_attack == "summon":
            self._attack_progress += dt / self.SUMMON_TIME
            if self._attack_progress >= 1.0:
                self._complete_summon()
                self._reset_attack()
            return

        super()._update_attacks(dt)

    def _pick_and_execute_attack(self) -> None:
        # حملات پایه همیشه در دسترس‌اند و صاعقه از فاز دوم اضافه می‌شود.
        # Basic attacks are always available, while lightning is added from phase two.
        attacks = ["radial", "aimed", "summon"]
        if self._phase >= 2:
            attacks += ["lightning", "lightning"]

        # تکرار نام صاعقه در فهرست، احتمال انتخاب آن را افزایش می‌دهد.
        # Duplicating lightning in the list increases its selection probability.
        name = random.choice(attacks)
        if name == "radial":
            self._fire_radial(16, 220)
            self._attack_timer = self._get_attack_interval()
        elif name == "aimed":
            self._fire_aimed(5, 280)
            self._attack_timer = self._get_attack_interval()
        elif name == "summon":
            self._start_summon()
        elif name == "lightning":
            self._start_lightning()

    # ---- SUMMON ----
    def _start_summon(self) -> None:
        # وضعیت حمله احضار و میزان پیشرفت آن از ابتدا تنظیم می‌شود.
        # The summon attack state and its progress are initialized.
        self._current_attack = "summon"
        self._attack_progress = 0.0
        self._summon_targets = []

        # سه نقطه با زاویه و فاصله تصادفی در اطراف باس انتخاب می‌شوند.
        # Three positions are selected at random angles and distances around the boss.
        for i in range(3):
            angle = (i / 3) * math.tau + random.uniform(-0.3, 0.3)
            dist = 130 + random.uniform(-20, 20)
            tx = self.x + math.cos(angle) * dist
            ty = self.y + math.sin(angle) * dist
            self._summon_targets.append((tx, ty))

        self._danger_flash = 1.0
        try:
            self.scene.audio.play("powerup_spawn")
        except Exception:
            pass

    def _complete_summon(self) -> None:
        # بدون صحنه بازی، امکان ایجاد دشمن و افکت وجود ندارد.
        # Enemies and effects cannot be created without an active scene.
        if self.scene is None:
            return
        try:
            from entities.enemies.normal import NormalEnemy
            from systems.particles import ParticleKind

            # در هر نقطه انتخاب‌شده، افکت ظهور و یک دشمن معمولی ایجاد می‌شود.
            # A spawn effect and a normal enemy are created at each selected position.
            for (tx, ty) in self._summon_targets:
                self.scene.particles.emit_burst(
                    tx, ty, count=24,
                    color_start=(255, 200, 255), color_end=(100, 30, 150),
                    speed_min=80, speed_max=250,
                    life_min=0.3, life_max=0.7,
                    size_min=2, size_max=5,
                    kind=ParticleKind.SPARK, additive=True,
                )
                self.scene.particles.emit_ring(
                    tx, ty, count=16, radius=8, speed=200,
                    color=(220, 120, 255), life=0.45, size=2,
                )
                minion = NormalEnemy(tx, ty, scene=self.scene)
                minion.set_entry(ty - 40, ty + 20)
                self.scene.add_enemy(minion)

            # لرزش دوربین هنگام تکمیل احضار، شدت رویداد را بیشتر می‌کند.
            # Camera shake emphasizes the summoning event when it completes.
            self.scene.camera.shake(6.0)
        except Exception as exc:
            print(f"[Boss] Summon failed: {exc}")

        # فهرست موقعیت‌ها پس از پایان عملیات پاک می‌شود.
        # The target position list is cleared after the operation completes.
        self._summon_targets = []

    # ---- LIGHTNING ----
    def _start_lightning(self) -> None:
        # وضعیت شارژ صاعقه و زمان‌سنج تولید ذرات بازنشانی می‌شوند.
        # The lightning charge state and particle timer are reset.
        self._current_attack = "lightning"
        self._attack_progress = 0.0
        self._charge_particles_timer = 0.0
        player = getattr(self.scene, "player", None) if self.scene else None
        # موقعیت فعلی بازیکن به‌عنوان مقصد صاعقه ثبت می‌شود.
        # The player's current position is stored as the lightning target.
        if player and player.alive:
            self._charge_pos = (player.x, player.y)
        else:
            self._charge_pos = (self.x, self.y + 400)
        self._danger_flash = 1.0

    def _emit_charge_particles(self, dt: float) -> None:
        # در نبود صحنه بازی، تولید ذرات شارژ انجام نمی‌شود.
        # Charge particles are not emitted when the game scene is unavailable.
        if self.scene is None:
            return
        self._charge_particles_timer -= dt
        if self._charge_particles_timer > 0:
            return
        # فاصله زمانی تولید ذرات برای محدودکردن تعداد آن‌ها تنظیم می‌شود.
        # The particle interval is set to control how frequently particles are emitted.
        self._charge_particles_timer = 0.04
        try:
            from systems.particles import ParticleKind
            self.scene.particles.emit_burst(
                self.x, self.y, count=3,
                color_start=(220, 150, 255), color_end=(255, 50, 200),
                speed_min=60, speed_max=180,
                life_min=0.2, life_max=0.5,
                size_min=2, size_max=4,
                kind=ParticleKind.SPARK, additive=True,
            )
        except Exception:
            pass

    def _fire_lightning(self) -> None:
        # اجرای صاعقه به وجود صحنه و مقصد معتبر نیاز دارد.
        # Firing lightning requires an active scene and a valid target position.
        if self.scene is None or self._charge_pos is None:
            return
        x1, y1 = self.x, self.y
        x2, y2 = self._charge_pos

        player = getattr(self.scene, "player", None)
        # بازیکن آسیب‌ناپذیر از بررسی برخورد صاعقه مستثنا می‌شود.
        # An invulnerable player is excluded from the lightning collision check.
        if player and player.alive and not player.is_invulnerable:
            px, py = player.x, player.y
            line_len = math.hypot(x2 - x1, y2 - y1)
            if line_len > 0.001:
                # نزدیک‌ترین نقطه روی پاره‌خط صاعقه برای سنجش فاصله از بازیکن محاسبه می‌شود.
                # The closest point on the lightning segment is calculated to measure its distance from the player.
                t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_len ** 2)))
                cx = x1 + t * (x2 - x1)
                cy = y1 + t * (y2 - y1)
                if math.hypot(px - cx, py - cy) < player.radius + 25:
                    player.take_damage(1)

        # ذرات در طول مسیر صاعقه پخش می‌شوند تا جلوه برخورد ایجاد شود.
        # Particles are distributed along the lightning path to create the strike effect.
        try:
            from systems.particles import ParticleKind
            steps = 30
            for i in range(steps + 1):
                t = i / steps
                bx = x1 + (x2 - x1) * t
                by = y1 + (y2 - y1) * t
                # نقاط میانی با جابه‌جایی تصادفی، مسیر شکسته صاعقه را شبیه‌سازی می‌کنند.
                # Random offsets at intermediate points simulate the lightning's jagged path.
                if 0 < i < steps:
                    bx += random.uniform(-25, 25) * (1 - abs(t - 0.5) * 2 + 0.3)
                    by += random.uniform(-25, 25) * (1 - abs(t - 0.5) * 2 + 0.3)
                self.scene.particles.emit_burst(
                    bx, by, count=5,
                    color_start=(220, 150, 255), color_end=(100, 200, 255),
                    speed_min=40, speed_max=200,
                    life_min=0.15, life_max=0.4,
                    size_min=2, size_max=5,
                    kind=ParticleKind.SPARK, additive=True,
                )
        except Exception:
            pass

        # صدای انفجار و لرزش دوربین، برخورد صاعقه را همراهی می‌کنند.
        # An explosion sound and camera shake accompany the lightning strike.
        try:
            self.scene.audio.play("player_explode")
            self.scene.camera.shake(14.0, aftershock=2)
        except Exception:
            pass

        # مقصد شارژ پس از اجرای حمله پاک می‌شود.
        # The charge target is cleared after the attack is fired.
        self._charge_pos = None

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        # اندازه و مرکز بدنه برای محاسبات رسم به مقادیر صحیح تبدیل می‌شوند.
        # The body size and center are converted to integers for drawing calculations.
        r = int(self.radius)
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 100)
        bright = self._lighter(base, 80)

        # اجزای بصری باس به‌ترتیب لایه‌بندی و روی سطح رسم می‌شوند.
        # The boss's visual components are layered and drawn onto the surface in sequence.
        self._draw_cosmic_aura(surface, cx, cy, r)
        self._draw_tendrils(surface, cx, cy, r)
        self._draw_orbit_crystals(surface, cx, cy, r, bright)
        self._draw_outer_hexagram(surface, cx, cy, r, bright)
        self._draw_body_shape(surface, cx, cy, r, base, dark, bright)
        self._draw_cracks(surface, cx, cy, r)
        self._draw_eye(surface, cx, cy, r)
        self._draw_crown(surface, cx, cy, r, bright)

        # افکت اختصاصی حمله فعال، روی بدنه باس نمایش داده می‌شود.
        # The visual effect of the active attack is displayed over the boss's body.
        if self._current_attack == "summon":
            self._draw_summon_portals(surface)
        if self._current_attack == "lightning":
            self._draw_charge_effect(surface, cx, cy, r)

        # هنگام محوشدن باس، شفافیت نهایی روی تصویر اعمال می‌شود.
        # During the boss fade-out, the final alpha is applied to the image.
        if alpha < 250:
            self._apply_fade(surface, cx, cy, r, alpha)

    def _draw_cosmic_aura(self, surface, cx, cy, r):
        # سطح جداگانه‌ای برای ساخت هاله با شفافیت تدریجی ایجاد می‌شود.
        # A separate surface is created to build the aura with gradual transparency.
        aura_r = int(r * 1.8)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        # دایره‌های هم‌مرکز، شدت هاله را از بیرون به مرکز افزایش می‌دهند.
        # Concentric circles increase the aura intensity from the outside toward the center.
        for rr in range(aura_r, 0, -6):
            a = int(30 * (1 - rr / aura_r) ** 2)
            if a <= 0:
                continue
            # رنگ هاله با تغییر فاز باس عوض می‌شود.
            # The aura color changes with the boss's phase.
            color = (150, 60, 220) if self._phase < 3 else (255, 80, 200)
            pygame.draw.circle(aura, (*color, a), (aura_r, aura_r), rr)
        # ترکیب افزایشی، نور هاله را به سطح اصلی اضافه می‌کند.
        # Additive blending adds the aura's light to the main surface.
        surface.blit(aura, (cx - aura_r, cy - aura_r), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_tendrils(self, surface, cx, cy, r):
        # شش شاخک با زاویه‌های متفاوت و حرکت موجی پیرامون بدنه رسم می‌شوند.
        # Six tendrils are drawn around the body at different angles with wave-like motion.
        for i in range(6):
            base_angle = (i / 6) * math.tau + self._rotation * 0.3
            wave = math.sin(self._rotation * 2.0 + i) * 20
            pts = []
            # مسیر هر شاخک با هشت نقطه از مرکز به سمت بیرون ساخته می‌شود.
            # Each tendril path is constructed from eight points extending outward.
            for seg in range(8):
                t = seg / 7
                dist = r * (1.0 + t * 0.8)
                offset = wave * t
                perp_angle = base_angle + math.pi / 2
                px = cx + math.cos(base_angle) * dist + math.cos(perp_angle) * offset
                py = cy + math.sin(base_angle) * dist + math.sin(perp_angle) * offset
                pts.append((px, py))
            # ضخامت و شفافیت خطوط در امتداد شاخک به‌تدریج کاهش می‌یابد.
            # Line width and opacity gradually decrease along each tendril.
            for j in range(len(pts) - 1):
                t = j / (len(pts) - 1)
                width = max(1, int(3 * (1 - t * 0.7)))
                a = int(120 * (1 - t))
                if a <= 0:
                    continue
                draw_line_alpha(surface, (200, 100, 255, a), pts[j], pts[j + 1], width)

    def _draw_orbit_crystals(self, surface, cx, cy, r, bright):
        # شش کریستال در مدار بیضوی اطراف باس حرکت می‌کنند.
        # Six crystals move along an elliptical orbit around the boss.
        orbit_r = r * 1.35
        for i in range(6):
            angle = (i / 6) * math.tau + self._rotation * 0.8
            # موج مستقل هر کریستال، فاصله آن را از مرکز مدار تغییر می‌دهد.
            # Each crystal's individual wave changes its distance from the orbit center.
            wave = math.sin(self._rotation * 1.5 + self._crystal_phases[i]) * 8
            px = cx + math.cos(angle) * (orbit_r + wave)
            py = cy + math.sin(angle) * (orbit_r * 0.85 + wave)
            size = 8 + int(2 * math.sin(self._rotation * 3 + i))
            # حلقه‌های نورانی با شعاع کاهشی، درخشش اطراف کریستال را می‌سازند.
            # Shrinking glowing circles create the light around each crystal.
            for rr in range(size * 2, 0, -1):
                a = int(120 * (1 - rr / (size * 2)))
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 150, 240, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (int(px) - rr * 2, int(py) - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)
            # شکل چهارضلعی کریستال با دو لایه رنگی رسم می‌شود.
            # Each crystal is drawn as a quadrilateral with two color layers.
            crystal = [
                (px, py - size), (px + size * 0.6, py),
                (px, py + size), (px - size * 0.6, py),
            ]
            draw_poly_alpha(surface, crystal, (220, 130, 255, 255))
            draw_poly_alpha(surface, crystal, (255, 240, 255, 255), width=1)

    def _draw_outer_hexagram(self, surface, cx, cy, r, bright):
        # شش رأس شکل هندسی بیرونی با چرخش مستقل باس محاسبه می‌شوند.
        # The six vertices of the outer geometric shape are calculated using the boss's rotation.
        rot = self._outer_rotation
        size = r * 1.2
        pts = [(cx + math.cos(rot + i * math.tau / 6) * size,
                cy + math.sin(rot + i * math.tau / 6) * size) for i in range(6)]
        # رأس‌ها با خطوط نیمه‌شفاف به یکدیگر متصل می‌شوند.
        # The vertices are connected with semi-transparent lines.
        for i in range(6):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % 6]
            draw_line_alpha(surface, (220, 150, 255, 180), (x1, y1), (x2, y2), 2)
        # نور هر رأس با حرکت سینوسی به‌صورت ضربانی تغییر می‌کند.
        # The light at each vertex pulses according to a sine wave.
        for i, (px, py) in enumerate(pts):
            pulse = 0.5 + 0.5 * math.sin(self._rotation * 3 + i)
            a = int(180 + 70 * pulse)
            g = pygame.Surface((12, 12), pygame.SRCALPHA)
            for rr in range(6, 0, -1):
                aa = int(a * (1 - rr / 6))
                if aa > 0:
                    pygame.draw.circle(g, (255, 200, 255, aa), (6, 6), rr)
            surface.blit(g, (int(px) - 6, int(py) - 6), special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.circle(surface, (255, 240, 255), (int(px), int(py)), 2)

    def _draw_body_shape(self, surface, cx, cy, r, base, dark, bright):
        # چندضلعی بیرونی با چرخش آهسته، فرم اصلی بدنه را تشکیل می‌دهد.
        # A slowly rotating outer polygon forms the main body shape.
        rot = self._rotation * 0.15
        outer = [(cx + math.cos(rot + i * math.tau / 8 - math.pi / 8) * r,
                  cy + math.sin(rot + i * math.tau / 8 - math.pi / 8) * r) for i in range(8)]
        # لایه تیره زیر بدنه برای ایجاد عمق بصری رسم می‌شود.
        # A dark layer is drawn beneath the body to create visual depth.
        draw_poly_alpha(surface, [(x, y + 3) for x, y in outer], (20, 5, 30, 255))
        draw_poly_alpha(surface, outer, (*base, 255))
        # چندضلعی داخلی با جهت چرخش مخالف، بخش مرکزی بدنه را می‌سازد.
        # An inner polygon with the opposite rotation forms the central body section.
        mid = [(cx + math.cos(-rot + i * math.tau / 6) * r * 0.75,
                cy + math.sin(-rot + i * math.tau / 6) * r * 0.75) for i in range(6)]
        draw_poly_alpha(surface, mid, (*dark, 255))
        pygame.draw.circle(surface, self._lighter(dark, 40), (cx, cy), int(r * 0.55))
        # خطوط پیرامونی روشن، مرز لایه‌های بدنه را مشخص می‌کنند.
        # Bright outlines define the boundaries of the body layers.
        draw_poly_alpha(surface, outer, (*bright, 255), width=3)
        draw_poly_alpha(surface, mid, (*bright, 255), width=2)

    def _draw_cracks(self, surface, cx, cy, r):
        # شش ترک نورانی از لبه بدنه به سمت مرکز امتداد پیدا می‌کنند.
        # Six glowing cracks extend from the body edge toward its center.
        rot = self._rotation * 0.15
        for i in range(6):
            angle = rot + i * math.tau / 6 + 0.3
            x1 = cx + math.cos(angle) * r * 0.85
            y1 = cy + math.sin(angle) * r * 0.85
            # انحراف تصادفی نقطه میانی، مسیر ترک‌ها را نامنظم می‌کند.
            # Randomly offsetting the middle point makes the cracks irregular.
            mx_ang = angle + random.uniform(-0.2, 0.2)
            x2 = cx + math.cos(mx_ang) * r * 0.55
            y2 = cy + math.sin(mx_ang) * r * 0.55
            x3 = cx + math.cos(angle) * r * 0.35
            y3 = cy + math.sin(angle) * r * 0.35
            # شدت نور ترک‌ها با حرکت سینوسی تغییر می‌کند.
            # The crack brightness changes with a sine-wave pulse.
            pulse = 0.5 + 0.5 * math.sin(self._rotation * 4 + i)
            a = int(120 + 100 * pulse)
            draw_line_alpha(surface, (255, 100, 255, a), (x1, y1), (x2, y2), 2)
            draw_line_alpha(surface, (255, 100, 255, a), (x2, y2), (x3, y3), 1)

    def _draw_eye(self, surface, cx, cy, r):
        # اندازه و موقعیت چشم با توجه به شعاع بدنه و جهت نگاه تعیین می‌شود.
        # The eye size and position are determined by the body radius and look direction.
        eye_r = int(r * 0.32)
        ex = cx + int(self._eye_look[0] * r * 0.15)
        ey = cy + int(self._eye_look[1] * r * 0.15)
        glow_size = eye_r * 3
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        # هاله چشم با دایره‌های نیمه‌شفاف و رنگ وابسته به فاز ساخته می‌شود.
        # The eye glow is built from semi-transparent circles with a phase-dependent color.
        for rr in range(glow_size, 0, -3):
            a = int(150 * (1 - rr / glow_size))
            if a <= 0:
                continue
            color = (255, 60, 60) if self._phase == 1 else (
                (255, 140, 60) if self._phase == 2 else (255, 60, 200))
            pygame.draw.circle(glow, (*color, a), (glow_size, glow_size), rr)
        surface.blit(glow, (ex - glow_size, ey - glow_size), special_flags=pygame.BLEND_RGBA_ADD)
        # سفیدی چشم، عنبیه و مردمک به‌ترتیب روی هم رسم می‌شوند.
        # The eye white, iris, and pupil are drawn in sequence.
        pygame.draw.circle(surface, (240, 220, 240), (ex, ey), eye_r)
        iris_color = (255, 40, 40) if self._phase == 1 else (
            (255, 120, 40) if self._phase == 2 else (255, 60, 180))
        pygame.draw.circle(surface, iris_color, (ex, ey), int(eye_r * 0.75))
        # مردمک نیز متناسب با جهت نگاه جابه‌جا می‌شود.
        # The pupil also shifts according to the eye's look direction.
        pupil_x = ex + int(self._eye_look[0] * eye_r * 0.35)
        pupil_y = ey + int(self._eye_look[1] * eye_r * 0.35)
        pupil_r = int(eye_r * 0.35)
        pygame.draw.circle(surface, (0, 0, 0), (pupil_x, pupil_y), pupil_r)
        # انعکاس کوچک نور، ظاهر براق چشم را ایجاد می‌کند.
        # A small light reflection gives the eye a glossy appearance.
        pygame.draw.circle(surface, (255, 255, 255),
                           (pupil_x - max(2, pupil_r // 3), pupil_y - max(2, pupil_r // 3)),
                           max(2, pupil_r // 3))

    def _draw_crown(self, surface, cx, cy, r, bright):
        # تاج در بالای بدنه و با پنج تیغه عمودی ساخته می‌شود.
        # The crown is constructed above the body using five vertical spikes.
        crown_y = cy - int(r * 1.05)
        num_spikes = 5
        base_w = int(r * 0.6)
        for i in range(num_spikes):
            t = i / (num_spikes - 1)
            x = cx - base_w + int(t * base_w * 2)
            # ارتفاع تیغه‌ها به‌صورت یکی‌درمیان متفاوت است و اندکی نوسان دارد.
            # Spike heights alternate and vary slightly over time.
            h = 15 if i % 2 == 0 else 10
            h += int(5 * math.sin(self._rotation * 3 + i))
            # حلقه‌های نورانی اطراف هر تیغه، درخشش آن را ایجاد می‌کنند.
            # Glowing circles around each spike create its luminous effect.
            for rr in range(h + 8, 0, -2):
                a = int(80 * (1 - rr / (h + 8)))
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 180, 255, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (x - rr * 2, crown_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)
            spike = [(x - 3, crown_y), (x, crown_y - h), (x + 3, crown_y)]
            draw_poly_alpha(surface, spike, (255, 200, 255, 255))
            draw_poly_alpha(surface, spike, (255, 255, 255, 255), width=1)

    def _draw_summon_portals(self, surface):
        # میزان پیشرفت احضار، اندازه پورتال‌ها را به‌تدریج افزایش می‌دهد.
        # Summoning progress gradually increases the portal sizes.
        progress = min(1.0, self._attack_progress)
        for i, (tx, ty) in enumerate(self._summon_targets):
            portal_r = int(20 + 30 * progress)
            pulse = 0.7 + 0.3 * math.sin(self._rotation * 10 + i * 2)
            # حلقه‌های شفاف با شدت ضربانی، هاله هر پورتال را تشکیل می‌دهند.
            # Transparent rings with pulsing intensity form each portal's glow.
            for rr in range(portal_r * 2, 0, -3):
                a = int(140 * (1 - rr / (portal_r * 2)) * pulse)
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (200, 100, 255, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (int(tx) - rr * 2, int(ty) - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)
            # هشت نقطه نورانی در مدار پورتال حرکت می‌کنند.
            # Eight glowing points move around the portal's circumference.
            for j in range(8):
                angle = self._rotation * 3 + (j / 8) * math.tau
                px = tx + math.cos(angle) * portal_r
                py = ty + math.sin(angle) * portal_r
                pygame.draw.circle(surface, (255, 200, 255), (int(px), int(py)), 2)
            # پس از شروع پیشرفت، مرکز پورتال نیز روشن می‌شود.
            # Once progress begins, the center of the portal also lights up.
            if progress > 0:
                pygame.draw.circle(surface, (255, 220, 255),
                                   (int(tx), int(ty)), int(portal_r * 0.4))

    def _draw_charge_effect(self, surface, cx, cy, r):
        # شعاع حلقه شارژ متناسب با پیشرفت حمله افزایش پیدا می‌کند.
        # The charge ring radius increases in proportion to attack progress.
        progress = min(1.0, self._attack_progress)
        charge_r = int(r * 1.5 * progress)
        pulse = 0.7 + 0.3 * math.sin(self._rotation * 15.0)
        # حلقه‌های هم‌مرکز با شفافیت متغیر، انرژی در حال جمع‌شدن را نمایش می‌دهند.
        # Concentric rings with varying opacity represent the gathering energy.
        for rr in range(charge_r, 0, -4):
            a = int(120 * (1 - rr / max(1, charge_r)) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(surface, (200, 100, 255, a), (cx, cy), rr, 2)
        # پس از عبور پیشرفت از آستانه، مسیر هدف به‌صورت خطی نورانی نمایش داده می‌شود.
        # Once progress passes the threshold, the target path appears as a glowing line.
        if self._charge_pos is not None and progress > 0.3:
            tx, ty = self._charge_pos
            line_alpha = int(255 * (progress - 0.3) / 0.7)
            line_width = 2 + int(progress * 3)
            prev_x, prev_y = cx, cy
            num_segments = 8
            # جابه‌جایی تصادفی نقاط میانی، ظاهر شکستگی مسیر صاعقه را ایجاد می‌کند.
            # Random offsets at intermediate points create the jagged lightning path.
            for i in range(1, num_segments + 1):
                t = i / num_segments
                bx = cx + (tx - cx) * t
                by = cy + (ty - cy) * t
                if i < num_segments:
                    bx += random.uniform(-15, 15)
                    by += random.uniform(-15, 15)
                draw_line_alpha(surface, (220, 150, 255, line_alpha),
                                (prev_x, prev_y), (bx, by), line_width)
                prev_x, prev_y = bx, by


    def get_hitcircles(self):
        """بدن اصلی، کمی بزرگ‌تر."""
        # محدوده برخورد بدنه کمی بزرگ‌تر از شعاع ظاهری آن در نظر گرفته می‌شود.
        # The body collision area is slightly larger than its visual radius.
        r = self.radius
        return [
            (self.x, self.y, r * 1.15),
        ]


__all__ = ["VoidSentinel"]