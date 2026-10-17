"""
entities/enemies/boss.py
========================

VOID SENTINEL — باس افسانه‌ای، نسخه‌ی بازطراحی‌شده.

دیزاین سینمایی:
    • هاله‌ی کیهانی غول‌پیکر (چند لایه)
    • تاج انرژی در بالای بدن
    • ۶ کریستال شناور در مدار
    • ۶ شاخک کیهانی موج‌دار
    • بدنه‌ی زره‌ای چندلایه (octagon + inner hexagon)
    • شکاف‌های درخشان روی بدن (رگ‌های انرژی)
    • یک چشم غول‌پیکر مرکزی (به بازیکن نگاه می‌کنه!)
    • شش‌ضلعی چرخان بیرونی
    • ۳ فاز رنگی (قرمز → نارنجی → بنفش)

حملات:
    1. Radial Burst (۱۶ گلوله)
    2. Aimed Spread (۵ گلوله)
    3. Summon با پورتال سینمایی
    4. LIGHTNING (فاز ۲+)
"""

from __future__ import annotations

import math
import random
import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies.base import Enemy, EnemyKind


class BossEnemy(Enemy):
    """VOID SENTINEL — نگهبان خلأ (نسخه‌ی نهایی)."""

    KIND = EnemyKind.BOSS

    HP           = 80
    RADIUS       = 80
    SPEED        = 0.0
    SCORE        = 500
    DROP_CHANCE  = 1.0
    BODY_COLOR   = (180, 60, 220)

    ENTRY_Y = 180
    SWAY_AMPLITUDE = 140
    SWAY_SPEED = 0.6

    PHASE_2_THRESHOLD = 0.50
    PHASE_3_THRESHOLD = 0.25

    ATTACK_INTERVAL_P1 = 2.2
    ATTACK_INTERVAL_P2 = 1.7
    ATTACK_INTERVAL_P3 = 1.2
    LIGHTNING_CHARGE_TIME = 0.85
    SUMMON_TIME = 1.0

    # ─────────────────────────────────────────────────────────────────────

    def __init__(self, x, y, scene=None, *, target_y=None):
        super().__init__(x, y, scene=scene, target_y=target_y)

        # ---- فاز و حمله ----
        self._phase = 1
        self._attack_timer = 1.5
        self._current_attack: str | None = None
        self._attack_progress = 0.0
        self._charge_pos: tuple[float, float] | None = None
        self._charge_particles_timer = 0.0

        # ---- احضار ----
        self._summon_targets: list[tuple[float, float]] = []

        # ---- انیمیشن ----
        self._rotation = 0.0
        self._outer_rotation = 0.0
        self._sway_phase = 0.0
        self._danger_flash = 0.0
        self._eye_look = (0.0, 0.0)   # جهت نگاه چشم
        self._eye_target = (0.0, 0.0)

        # ---- کریستال‌های شناور ----
        self._crystal_phases = [random.uniform(0, math.tau) for _ in range(6)]

        # ---- قفل Y ----
        self._locked_y = False

    # ─────────────────────────────────────────────────────────────────────
    #  حرکت
    # ─────────────────────────────────────────────────────────────────────

    def update_ai(self, dt: float) -> None:
        if not self._locked_y:
            if self.y < self.ENTRY_Y:
                self.y += 60 * dt
            else:
                self.y = self.ENTRY_Y
                self._locked_y = True
                self._base_x = self.x

        if self._locked_y:
            self._sway_phase += dt * self.SWAY_SPEED
            self.x = self._base_x + math.sin(self._sway_phase) * self.SWAY_AMPLITUDE

        # ---- چرخش‌ها ----
        self._rotation += dt * (0.6 + self._phase * 0.4)
        self._outer_rotation -= dt * (0.4 + self._phase * 0.2)

        # ---- چشم بازیکن رو دنبال می‌کنه ----
        player = getattr(self.scene, "player", None) if self.scene else None
        if player and player.alive:
            dx = player.x - self.x
            dy = player.y - self.y
            d = math.hypot(dx, dy) or 1.0
            self._eye_target = (dx / d, dy / d)
        # نرم‌سازی
        self._eye_look = (
            self._eye_look[0] + (self._eye_target[0] - self._eye_look[0]) * min(1.0, dt * 4.0),
            self._eye_look[1] + (self._eye_target[1] - self._eye_look[1]) * min(1.0, dt * 4.0),
        )

        # ---- danger flash ----
        if self._danger_flash > 0:
            self._danger_flash = max(0.0, self._danger_flash - dt * 3.0)

        # ---- فاز ----
        hp_ratio = self.hp / self.max_hp
        if hp_ratio <= self.PHASE_3_THRESHOLD:
            self._phase = 3
        elif hp_ratio <= self.PHASE_2_THRESHOLD:
            self._phase = 2
        else:
            self._phase = 1

        # ---- حملات ----
        if self._locked_y:
            self._update_attacks(dt)

    # ─────────────────────────────────────────────────────────────────────
    #  حملات
    # ─────────────────────────────────────────────────────────────────────

    def _update_attacks(self, dt: float) -> None:
        # ---- lightning در حال شارژ ----
        if self._current_attack == "lightning":
            self._attack_progress += dt / self.LIGHTNING_CHARGE_TIME
            self._emit_charge_particles(dt)
            if self._attack_progress >= 1.0:
                self._fire_lightning()
                self._reset_attack()
            return

        # ---- summon در حال انجام ----
        if self._current_attack == "summon":
            self._attack_progress += dt / self.SUMMON_TIME
            if self._attack_progress >= 1.0:
                self._complete_summon()
                self._reset_attack()
            return

        # ---- تایمر بین حملات ----
        self._attack_timer -= dt
        if self._attack_timer <= 0:
            self._pick_and_execute_attack()

    def _pick_and_execute_attack(self) -> None:
        attacks = ["radial", "aimed", "summon"]
        if self._phase >= 2:
            attacks += ["lightning", "lightning"]

        name = random.choice(attacks)
        if name == "radial":
            self._fire_radial()
        elif name == "aimed":
            self._fire_aimed()
        elif name == "summon":
            self._start_summon()
            return  # تایمر داخل summon مدیریت می‌شه
        elif name == "lightning":
            self._start_lightning()
            return  # تایمر داخل lightning مدیریت می‌شه

        self._attack_timer = self._get_attack_interval()

    def _get_attack_interval(self) -> float:
        base = self.ATTACK_INTERVAL_P3 if self._phase == 3 else (
            self.ATTACK_INTERVAL_P2 if self._phase == 2 else self.ATTACK_INTERVAL_P1
        )
        return base * random.uniform(0.9, 1.15)

    # ---- RADIAL ----
    def _fire_radial(self) -> None:
        if self.scene is None:
            return
        n = 16
        speed = 220
        for i in range(n):
            angle = (i / n) * math.tau + self._rotation
            b = Bullet(
                self.x, self.y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
            )
            try:
                self.scene.spawn_bullet(b)
            except Exception:
                pass
        try:
            self.scene.audio.play("enemy_shoot")
            self.scene.camera.shake(4.0)
        except Exception:
            pass

    # ---- AIMED ----
    def _fire_aimed(self) -> None:
        if self.scene is None:
            return
        player = getattr(self.scene, "player", None)
        if player is None:
            return
        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        speed = 280
        for spread in (-0.18, -0.09, 0.0, 0.09, 0.18):
            ca, sa = math.cos(spread), math.sin(spread)
            nx = ux * ca - uy * sa
            ny = ux * sa + uy * ca
            b = Bullet(
                self.x, self.y, nx * speed, ny * speed,
                friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
            )
            try:
                self.scene.spawn_bullet(b)
            except Exception:
                pass
        try:
            self.scene.audio.play("enemy_shoot")
        except Exception:
            pass

    # ---- SUMMON (جدید: با پورتال) ----
    def _start_summon(self) -> None:
        """شروع احضار با ۳ پورتال."""
        self._current_attack = "summon"
        self._attack_progress = 0.0
        self._summon_targets = []

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
        """پایان احضار: انفجار پورتال + spawn دشمن‌ها."""
        if self.scene is None:
            return
        try:
            from entities.enemies.normal import NormalEnemy
            from systems.particles import ParticleKind

            for (tx, ty) in self._summon_targets:
                # انفجار ذرات
                self.scene.particles.emit_burst(
                    tx, ty,
                    count=24,
                    color_start=(255, 200, 255),
                    color_end=(100, 30, 150),
                    speed_min=80, speed_max=250,
                    life_min=0.3, life_max=0.7,
                    size_min=2, size_max=5,
                    kind=ParticleKind.SPARK,
                    additive=True,
                )
                # حلقه‌ی انفجار
                self.scene.particles.emit_ring(
                    tx, ty,
                    count=16, radius=8, speed=200,
                    color=(220, 120, 255),
                    life=0.45, size=2,
                )

                # spawn دشمن
                minion = NormalEnemy(tx, ty, scene=self.scene)
                minion.set_entry(ty - 40, ty + 20)
                self.scene.add_enemy(minion)

            self.scene.camera.shake(6.0)
        except Exception as exc:
            print(f"[Boss] Summon failed: {exc}")

        self._summon_targets = []

    # ---- LIGHTNING ----
    def _start_lightning(self) -> None:
        self._current_attack = "lightning"
        self._attack_progress = 0.0
        self._charge_particles_timer = 0.0
        player = getattr(self.scene, "player", None) if self.scene else None
        if player and player.alive:
            self._charge_pos = (player.x, player.y)
        else:
            self._charge_pos = (self.x, self.y + 400)
        self._danger_flash = 1.0

    def _emit_charge_particles(self, dt: float) -> None:
        if self.scene is None:
            return
        self._charge_particles_timer -= dt
        if self._charge_particles_timer > 0:
            return
        self._charge_particles_timer = 0.04
        try:
            from systems.particles import ParticleKind
            self.scene.particles.emit_burst(
                self.x, self.y,
                count=3,
                color_start=(220, 150, 255),
                color_end=(255, 50, 200),
                speed_min=60, speed_max=180,
                life_min=0.2, life_max=0.5,
                size_min=2, size_max=4,
                kind=ParticleKind.SPARK,
                additive=True,
            )
        except Exception:
            pass

    def _fire_lightning(self) -> None:
        if self.scene is None or self._charge_pos is None:
            return
        x1, y1 = self.x, self.y
        x2, y2 = self._charge_pos

        # آسیب
        player = getattr(self.scene, "player", None)
        if player and player.alive and player.invuln_time <= 0:
            px, py = player.x, player.y
            line_len = math.hypot(x2 - x1, y2 - y1)
            if line_len > 0.001:
                t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_len ** 2)))
                cx = x1 + t * (x2 - x1)
                cy = y1 + t * (y2 - y1)
                if math.hypot(px - cx, py - cy) < player.radius + 25:
                    player.take_damage(1)

        # ذرات
        try:
            from systems.particles import ParticleKind
            steps = 30
            for i in range(steps + 1):
                t = i / steps
                bx = x1 + (x2 - x1) * t
                by = y1 + (y2 - y1) * t
                if 0 < i < steps:
                    offset_x = random.uniform(-25, 25) * (1 - abs(t - 0.5) * 2 + 0.3)
                    offset_y = random.uniform(-25, 25) * (1 - abs(t - 0.5) * 2 + 0.3)
                    bx += offset_x
                    by += offset_y
                self.scene.particles.emit_burst(
                    bx, by, count=5,
                    color_start=(220, 150, 255),
                    color_end=(100, 200, 255),
                    speed_min=40, speed_max=200,
                    life_min=0.15, life_max=0.4,
                    size_min=2, size_max=5,
                    kind=ParticleKind.SPARK, additive=True,
                )
        except Exception:
            pass

        try:
            self.scene.audio.play("player_explode")
            self.scene.camera.shake(14.0, aftershock=2)
        except Exception:
            pass

        self._charge_pos = None

    def _reset_attack(self) -> None:
        self._current_attack = None
        self._attack_progress = 0.0
        self._charge_pos = None
        self._danger_flash = 0.0
        self._attack_timer = self._get_attack_interval()

    # ─────────────────────────────────────────────────────────────────────
    #  مرگ
    # ─────────────────────────────────────────────────────────────────────

    def on_death(self) -> None:
        if self.scene is None:
            return
        try:
            self.scene.particles.preset_boss_explosion(self.x, self.y)
            self.scene.add_score(self.score_value)
            self.scene.audio.play("player_explode")
            self.scene.camera.shake(28.0, aftershock=4)
            self.scene.spawn_powerup(self.x, self.y)
            self.scene.spawn_powerup(self.x - 40, self.y)
            self.scene.spawn_powerup(self.x + 40, self.y)
            if hasattr(self.scene, "on_boss_defeated"):
                self.scene.on_boss_defeated()
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════════
    #  رسم — VOID SENTINEL (نسخه‌ی نهایی)
    # ═════════════════════════════════════════════════════════════════════

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = int(self.radius)
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 100)
        darker = self._darker(base, 160)
        bright = self._lighter(base, 80)

        # ---- لایه‌ها ----
        self._draw_cosmic_aura(surface, cx, cy, r)
        self._draw_tendrils(surface, cx, cy, r)
        self._draw_orbit_crystals(surface, cx, cy, r, bright)
        self._draw_outer_hexagram(surface, cx, cy, r, bright)
        self._draw_body_shape(surface, cx, cy, r, base, dark, bright)
        self._draw_cracks(surface, cx, cy, r)
        self._draw_eye(surface, cx, cy, r)
        self._draw_crown(surface, cx, cy, r, bright)

        # ---- پورتال‌های احضار ----
        if self._current_attack == "summon":
            self._draw_summon_portals(surface)

        # ---- شارژ lightning ----
        if self._current_attack == "lightning":
            self._draw_charge_effect(surface, cx, cy, r)

        # ---- HP bar ----
        if self.hp < self.max_hp:
            self._draw_hp_bar(surface, cx, cy, r)

        # ---- فید ----
        if alpha < 250:
            self._apply_fade(surface, cx, cy, r, alpha)

    # ─────────────────────────────────────────────────────────────────────

    def _draw_cosmic_aura(self, surface, cx, cy, r):
        """هاله‌ی کیهانی چندلایه."""
        aura_r = int(r * 1.8)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -6):
            a = int(30 * (1 - rr / aura_r) ** 2)
            if a <= 0:
                continue
            color = (150, 60, 220) if self._phase < 3 else (255, 80, 200)
            pygame.draw.circle(aura, (*color, a), (aura_r, aura_r), rr)
        surface.blit(aura, (cx - aura_r, cy - aura_r),
                     special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_tendrils(self, surface, cx, cy, r):
        """۶ شاخک کیهانی موج‌دار."""
        for i in range(6):
            base_angle = (i / 6) * math.tau + self._rotation * 0.3
            wave = math.sin(self._rotation * 2.0 + i) * 20

            # سه نقطه‌ی شاخک
            pts = []
            for seg in range(8):
                t = seg / 7
                # فاصله از مرکز
                dist = r * (1.0 + t * 0.8)
                # موج
                offset = wave * t
                perp_angle = base_angle + math.pi / 2
                px = cx + math.cos(base_angle) * dist + math.cos(perp_angle) * offset
                py = cy + math.sin(base_angle) * dist + math.sin(perp_angle) * offset
                pts.append((px, py))

            # رسم با آلفا
            for j in range(len(pts) - 1):
                t = j / (len(pts) - 1)
                width = max(1, int(3 * (1 - t * 0.7)))
                a = int(120 * (1 - t))
                if a <= 0:
                    continue
                line = pygame.Surface((30, 30), pygame.SRCALPHA)
                x1, y1 = pts[j]
                x2, y2 = pts[j + 1]
                ox = min(x1, x2) - 5
                oy = min(y1, y2) - 5
                pygame.draw.line(line, (200, 100, 255, a),
                                 (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), width)
                surface.blit(line, (ox, oy))

    def _draw_orbit_crystals(self, surface, cx, cy, r, bright):
        """۶ کریستال شناور در مدار."""
        orbit_r = r * 1.35
        for i in range(6):
            angle = (i / 6) * math.tau + self._rotation * 0.8
            wave = math.sin(self._rotation * 1.5 + self._crystal_phases[i]) * 8
            px = cx + math.cos(angle) * (orbit_r + wave)
            py = cy + math.sin(angle) * (orbit_r * 0.85 + wave)

            # اندازه‌ی کریستال
            size = 8 + int(2 * math.sin(self._rotation * 3 + i))
            # هاله
            for rr in range(size * 2, 0, -1):
                a = int(120 * (1 - rr / (size * 2)))
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 150, 240, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (int(px) - rr * 2, int(py) - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

            # کریستال (الماس)
            crystal = [
                (px, py - size),
                (px + size * 0.6, py),
                (px, py + size),
                (px - size * 0.6, py),
            ]
            _draw_poly_alpha(surface, crystal, (220, 130, 255, 255))
            _draw_poly_alpha(surface, crystal, (255, 240, 255, 255), width=1)

    def _draw_outer_hexagram(self, surface, cx, cy, r, bright):
        """شش‌ضلعی چرخان بیرونی."""
        rot = self._outer_rotation
        size = r * 1.2
        pts = []
        for i in range(6):
            angle = rot + i * math.tau / 6
            pts.append((
                cx + math.cos(angle) * size,
                cy + math.sin(angle) * size,
            ))

        # خطوط با آلفا
        for i in range(6):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % 6]
            _draw_line_alpha(surface, (220, 150, 255, 180),
                             (x1, y1), (x2, y2), 2)

        # نقاط درخشان روی رأس‌ها
        for i, (px, py) in enumerate(pts):
            pulse = 0.5 + 0.5 * math.sin(self._rotation * 3 + i)
            a = int(180 + 70 * pulse)
            g = pygame.Surface((12, 12), pygame.SRCALPHA)
            for rr in range(6, 0, -1):
                aa = int(a * (1 - rr / 6))
                if aa > 0:
                    pygame.draw.circle(g, (255, 200, 255, aa), (6, 6), rr)
            surface.blit(g, (int(px) - 6, int(py) - 6),
                         special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.circle(surface, (255, 240, 255), (int(px), int(py)), 2)

    def _draw_body_shape(self, surface, cx, cy, r, base, dark, bright):
        """بدنه‌ی زره‌ای چندلایه."""
        rot = self._rotation * 0.15

        # ---- لایه‌ی بیرونی (۸ ضلعی) ----
        outer = []
        for i in range(8):
            angle = rot + i * math.tau / 8 - math.pi / 8
            outer.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))

        _draw_poly_alpha(surface, [(x, y + 3) for x, y in outer],
                         (20, 5, 30, 255))
        _draw_poly_alpha(surface, outer, (*base, 255))

        # ---- لایه‌ی میانی (۶ ضلعی، چرخش مخالف) ----
        mid = []
        for i in range(6):
            angle = -rot + i * math.tau / 6
            mid.append((cx + math.cos(angle) * r * 0.75,
                        cy + math.sin(angle) * r * 0.75))
        _draw_poly_alpha(surface, mid, (*dark, 255))

        # ---- لایه‌ی داخلی (دایره) ----
        pygame.draw.circle(surface, brighter if False else self._lighter(dark, 40),
                           (cx, cy), int(r * 0.55))

        # ---- خطوط نئونی ----
        _draw_poly_alpha(surface, outer, (*bright, 255), width=3)
        _draw_poly_alpha(surface, mid, (*bright, 255), width=2)

    def _draw_cracks(self, surface, cx, cy, r):
        """شکاف‌های درخشان (رگ‌های انرژی) روی بدن."""
        rot = self._rotation * 0.15
        for i in range(6):
            angle = rot + i * math.tau / 6 + 0.3
            # نقطه‌ی شروع (از لبه به سمت مرکز)
            x1 = cx + math.cos(angle) * r * 0.85
            y1 = cy + math.sin(angle) * r * 0.85
            # نقطه‌ی میانی (با zigzag)
            mx_ang = angle + random.uniform(-0.2, 0.2)
            x2 = cx + math.cos(mx_ang) * r * 0.55
            y2 = cy + math.sin(mx_ang) * r * 0.55
            # نقطه‌ی انتهایی
            x3 = cx + math.cos(angle) * r * 0.35
            y3 = cy + math.sin(angle) * r * 0.35

            pulse = 0.5 + 0.5 * math.sin(self._rotation * 4 + i)
            a = int(120 + 100 * pulse)
            color = (255, 100, 255, a)

            _draw_line_alpha(surface, color, (x1, y1), (x2, y2), 2)
            _draw_line_alpha(surface, color, (x2, y2), (x3, y3), 1)

    def _draw_eye(self, surface, cx, cy, r):
        """چشم غول‌پیکر مرکزی — بازیکن رو دنبال می‌کنه."""
        eye_r = int(r * 0.32)

        # موقعیت چشم با توجه به نگاه
        look_x = self._eye_look[0] * r * 0.15
        look_y = self._eye_look[1] * r * 0.15
        ex = cx + int(look_x)
        ey = cy + int(look_y)

        # ---- هاله ----
        glow_size = eye_r * 3
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -3):
            a = int(150 * (1 - rr / glow_size))
            if a <= 0:
                continue
            color = (255, 60, 60) if self._phase == 1 else (
                (255, 140, 60) if self._phase == 2 else (255, 60, 200)
            )
            pygame.draw.circle(glow, (*color, a), (glow_size, glow_size), rr)
        surface.blit(glow, (ex - glow_size, ey - glow_size),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ---- سفیدی چشم ----
        pygame.draw.circle(surface, (240, 220, 240), (ex, ey), eye_r)

        # ---- رنگ چشم (فاز) ----
        iris_color = (255, 40, 40) if self._phase == 1 else (
            (255, 120, 40) if self._phase == 2 else (255, 60, 180)
        )
        pygame.draw.circle(surface, iris_color, (ex, ey), int(eye_r * 0.75))

        # ---- مردمک (به بازیکن نگاه می‌کنه) ----
        pupil_x = ex + int(self._eye_look[0] * eye_r * 0.35)
        pupil_y = ey + int(self._eye_look[1] * eye_r * 0.35)
        pupil_r = int(eye_r * 0.35)
        pygame.draw.circle(surface, (0, 0, 0), (pupil_x, pupil_y), pupil_r)

        # ---- برق چشم ----
        highlight_x = pupil_x - max(2, pupil_r // 3)
        highlight_y = pupil_y - max(2, pupil_r // 3)
        pygame.draw.circle(surface, (255, 255, 255),
                           (highlight_x, highlight_y), max(2, pupil_r // 3))

    def _draw_crown(self, surface, cx, cy, r, bright):
        """تاج انرژی بالای باس."""
        crown_y = cy - int(r * 1.05)
        num_spikes = 5
        base_w = int(r * 0.6)

        for i in range(num_spikes):
            t = i / (num_spikes - 1)
            x = cx - base_w + int(t * base_w * 2)
            # ارتفاع بر اساس موقعیت
            h = 15 if i % 2 == 0 else 10
            h += int(5 * math.sin(self._rotation * 3 + i))

            # هاله‌ی تاج
            for rr in range(h + 8, 0, -2):
                a = int(80 * (1 - rr / (h + 8)))
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 180, 255, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (x - rr * 2, crown_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

            # خود spike
            spike = [
                (x - 3, crown_y),
                (x, crown_y - h),
                (x + 3, crown_y),
            ]
            _draw_poly_alpha(surface, spike, (255, 200, 255, 255))
            _draw_poly_alpha(surface, spike, (255, 255, 255, 255), width=1)

    def _draw_summon_portals(self, surface):
        """پورتال‌های احضار (در حال رشد)."""
        progress = min(1.0, self._attack_progress)
        for i, (tx, ty) in enumerate(self._summon_targets):
            # اندازه‌ی پورتال
            portal_r = int(20 + 30 * progress)
            pulse = 0.7 + 0.3 * math.sin(self._rotation * 10 + i * 2)

            # هاله‌ی بیرونی
            for rr in range(portal_r * 2, 0, -3):
                a = int(140 * (1 - rr / (portal_r * 2)) * pulse)
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (200, 100, 255, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (int(tx) - rr * 2, int(ty) - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

            # حلقه‌ی چرخان
            for j in range(8):
                angle = self._rotation * 3 + (j / 8) * math.tau
                px = tx + math.cos(angle) * portal_r
                py = ty + math.sin(angle) * portal_r
                pygame.draw.circle(surface, (255, 200, 255),
                                   (int(px), int(py)), 2)

            # هسته
            core_a = int(200 * progress)
            if core_a > 0:
                pygame.draw.circle(surface, (255, 220, 255),
                                   (int(tx), int(ty)), int(portal_r * 0.4))

    def _draw_charge_effect(self, surface, cx, cy, r):
        """افکت شارژ رعد و برق."""
        progress = min(1.0, self._attack_progress)
        charge_r = int(r * 1.5 * progress)
        pulse = 0.7 + 0.3 * math.sin(self._rotation * 15.0)

        for rr in range(charge_r, 0, -4):
            a = int(120 * (1 - rr / max(1, charge_r)) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(surface, (200, 100, 255, a),
                               (cx, cy), rr, 2)

        if self._charge_pos is not None and progress > 0.3:
            tx, ty = self._charge_pos
            line_alpha = int(255 * (progress - 0.3) / 0.7)
            line_width = 2 + int(progress * 3)
            num_segments = 8
            prev_x, prev_y = cx, cy
            for i in range(1, num_segments + 1):
                t = i / num_segments
                bx = cx + (tx - cx) * t
                by = cy + (ty - cy) * t
                if i < num_segments:
                    bx += random.uniform(-15, 15)
                    by += random.uniform(-15, 15)
                line = pygame.Surface((abs(int(bx - prev_x)) + 6, abs(int(by - prev_y)) + 6),
                                      pygame.SRCALPHA)
                ox = min(prev_x, bx) - 3
                oy = min(prev_y, by) - 3
                pygame.draw.line(
                    line, (220, 150, 255, line_alpha),
                    (prev_x - ox, prev_y - oy), (bx - ox, by - oy), line_width,
                )
                surface.blit(line, (ox, oy))
                prev_x, prev_y = bx, by

    def _draw_hp_bar(self, surface, cx, cy, r):
        w = int(r * 2)
        h = 6
        x = cx - w // 2
        y = cy + int(r * 1.25)
        bg = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 200))
        surface.blit(bg, (x - 2, y - 2))
        ratio = max(0.0, self.hp / self.max_hp)
        color = (255, 60, 60) if ratio > 0.5 else (255, 150, 40) if ratio > 0.25 else (255, 80, 255)
        pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
        pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), 2)

    def _apply_fade(self, surface, cx, cy, r, alpha):
        a = 255 - alpha
        if a <= 0:
            return
        fade = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        fade.fill((0, 0, 0, int(a * 0.7)))
        surface.blit(fade, (cx - r * 2, cy - r * 2))

    @staticmethod
    def _darker(c, amount):
        return (max(0, c[0] - amount), max(0, c[1] - amount), max(0, c[2] - amount))

    @staticmethod
    def _lighter(c, amount):
        return (min(255, c[0] + amount), min(255, c[1] + amount), min(255, c[2] + amount))


# ═══════════════════════════════════════════════════════════════════════════
#  کمکی‌های رسم با آلفا
# ═══════════════════════════════════════════════════════════════════════════

def _draw_poly_alpha(surface, points, color, width=0):
    if not points:
        return
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = int(min(xs)) - 2, int(max(xs)) + 2
    min_y, max_y = int(min(ys)) - 2, int(max(ys)) + 2
    w = max_x - min_x
    h = max_y - min_y
    if w <= 0 or h <= 0:
        return
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    local = [(p[0] - min_x, p[1] - min_y) for p in points]
    if width > 0:
        pygame.draw.polygon(tmp, color, local, width)
    else:
        pygame.draw.polygon(tmp, color, local)
    surface.blit(tmp, (min_x, min_y))


def _draw_line_alpha(surface, color, p1, p2, width=1):
    x1, y1 = int(p1[0]), int(p1[1])
    x2, y2 = int(p2[0]), int(p2[1])
    ox = min(x1, x2) - 4
    oy = min(y1, y2) - 4
    w = abs(x2 - x1) + 8
    h = abs(y2 - y1) + 8
    if w <= 0 or h <= 0:
        return
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.line(tmp, color, (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), width)
    surface.blit(tmp, (ox, oy))


__all__ = ["BossEnemy"]