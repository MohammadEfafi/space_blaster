"""
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
        # چشم بازیکن رو دنبال می‌کنه
        player = getattr(self.scene, "player", None) if self.scene else None
        if player and player.alive:
            dx = player.x - self.x
            dy = player.y - self.y
            d = math.hypot(dx, dy) or 1.0
            self._eye_target = (dx / d, dy / d)
        blend = min(1.0, dt * 4.0)
        self._eye_look = (
            self._eye_look[0] + (self._eye_target[0] - self._eye_look[0]) * blend,
            self._eye_look[1] + (self._eye_target[1] - self._eye_look[1]) * blend,
        )

    # ─────────────────────────────────────────────────────────────────────
    #  حملات — با state اضافی
    # ─────────────────────────────────────────────────────────────────────

    def _update_attacks(self, dt: float) -> None:
        if self._current_attack == "lightning":
            self._attack_progress += dt / self.LIGHTNING_CHARGE_TIME
            self._emit_charge_particles(dt)
            if self._attack_progress >= 1.0:
                self._fire_lightning()
                self._reset_attack()
            return

        if self._current_attack == "summon":
            self._attack_progress += dt / self.SUMMON_TIME
            if self._attack_progress >= 1.0:
                self._complete_summon()
                self._reset_attack()
            return

        super()._update_attacks(dt)

    def _pick_and_execute_attack(self) -> None:
        attacks = ["radial", "aimed", "summon"]
        if self._phase >= 2:
            attacks += ["lightning", "lightning"]

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
        if self.scene is None:
            return
        try:
            from entities.enemies.normal import NormalEnemy
            from systems.particles import ParticleKind

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
        if self.scene is None or self._charge_pos is None:
            return
        x1, y1 = self.x, self.y
        x2, y2 = self._charge_pos

        player = getattr(self.scene, "player", None)
        if player and player.alive and not player.is_invulnerable:
            px, py = player.x, player.y
            line_len = math.hypot(x2 - x1, y2 - y1)
            if line_len > 0.001:
                t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_len ** 2)))
                cx = x1 + t * (x2 - x1)
                cy = y1 + t * (y2 - y1)
                if math.hypot(px - cx, py - cy) < player.radius + 25:
                    player.take_damage(1)

        try:
            from systems.particles import ParticleKind
            steps = 30
            for i in range(steps + 1):
                t = i / steps
                bx = x1 + (x2 - x1) * t
                by = y1 + (y2 - y1) * t
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

        try:
            self.scene.audio.play("player_explode")
            self.scene.camera.shake(14.0, aftershock=2)
        except Exception:
            pass

        self._charge_pos = None

    # ═════════════════════════════════════════════════════════════════════
    #  رسم
    # ═════════════════════════════════════════════════════════════════════

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = int(self.radius)
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 100)
        bright = self._lighter(base, 80)

        self._draw_cosmic_aura(surface, cx, cy, r)
        self._draw_tendrils(surface, cx, cy, r)
        self._draw_orbit_crystals(surface, cx, cy, r, bright)
        self._draw_outer_hexagram(surface, cx, cy, r, bright)
        self._draw_body_shape(surface, cx, cy, r, base, dark, bright)
        self._draw_cracks(surface, cx, cy, r)
        self._draw_eye(surface, cx, cy, r)
        self._draw_crown(surface, cx, cy, r, bright)

        if self._current_attack == "summon":
            self._draw_summon_portals(surface)
        if self._current_attack == "lightning":
            self._draw_charge_effect(surface, cx, cy, r)

        if alpha < 250:
            self._apply_fade(surface, cx, cy, r, alpha)

    def _draw_cosmic_aura(self, surface, cx, cy, r):
        aura_r = int(r * 1.8)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -6):
            a = int(30 * (1 - rr / aura_r) ** 2)
            if a <= 0:
                continue
            color = (150, 60, 220) if self._phase < 3 else (255, 80, 200)
            pygame.draw.circle(aura, (*color, a), (aura_r, aura_r), rr)
        surface.blit(aura, (cx - aura_r, cy - aura_r), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_tendrils(self, surface, cx, cy, r):
        for i in range(6):
            base_angle = (i / 6) * math.tau + self._rotation * 0.3
            wave = math.sin(self._rotation * 2.0 + i) * 20
            pts = []
            for seg in range(8):
                t = seg / 7
                dist = r * (1.0 + t * 0.8)
                offset = wave * t
                perp_angle = base_angle + math.pi / 2
                px = cx + math.cos(base_angle) * dist + math.cos(perp_angle) * offset
                py = cy + math.sin(base_angle) * dist + math.sin(perp_angle) * offset
                pts.append((px, py))
            for j in range(len(pts) - 1):
                t = j / (len(pts) - 1)
                width = max(1, int(3 * (1 - t * 0.7)))
                a = int(120 * (1 - t))
                if a <= 0:
                    continue
                draw_line_alpha(surface, (200, 100, 255, a), pts[j], pts[j + 1], width)

    def _draw_orbit_crystals(self, surface, cx, cy, r, bright):
        orbit_r = r * 1.35
        for i in range(6):
            angle = (i / 6) * math.tau + self._rotation * 0.8
            wave = math.sin(self._rotation * 1.5 + self._crystal_phases[i]) * 8
            px = cx + math.cos(angle) * (orbit_r + wave)
            py = cy + math.sin(angle) * (orbit_r * 0.85 + wave)
            size = 8 + int(2 * math.sin(self._rotation * 3 + i))
            for rr in range(size * 2, 0, -1):
                a = int(120 * (1 - rr / (size * 2)))
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 150, 240, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (int(px) - rr * 2, int(py) - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)
            crystal = [
                (px, py - size), (px + size * 0.6, py),
                (px, py + size), (px - size * 0.6, py),
            ]
            draw_poly_alpha(surface, crystal, (220, 130, 255, 255))
            draw_poly_alpha(surface, crystal, (255, 240, 255, 255), width=1)

    def _draw_outer_hexagram(self, surface, cx, cy, r, bright):
        rot = self._outer_rotation
        size = r * 1.2
        pts = [(cx + math.cos(rot + i * math.tau / 6) * size,
                cy + math.sin(rot + i * math.tau / 6) * size) for i in range(6)]
        for i in range(6):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % 6]
            draw_line_alpha(surface, (220, 150, 255, 180), (x1, y1), (x2, y2), 2)
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
        rot = self._rotation * 0.15
        outer = [(cx + math.cos(rot + i * math.tau / 8 - math.pi / 8) * r,
                  cy + math.sin(rot + i * math.tau / 8 - math.pi / 8) * r) for i in range(8)]
        draw_poly_alpha(surface, [(x, y + 3) for x, y in outer], (20, 5, 30, 255))
        draw_poly_alpha(surface, outer, (*base, 255))
        mid = [(cx + math.cos(-rot + i * math.tau / 6) * r * 0.75,
                cy + math.sin(-rot + i * math.tau / 6) * r * 0.75) for i in range(6)]
        draw_poly_alpha(surface, mid, (*dark, 255))
        pygame.draw.circle(surface, self._lighter(dark, 40), (cx, cy), int(r * 0.55))
        draw_poly_alpha(surface, outer, (*bright, 255), width=3)
        draw_poly_alpha(surface, mid, (*bright, 255), width=2)

    def _draw_cracks(self, surface, cx, cy, r):
        rot = self._rotation * 0.15
        for i in range(6):
            angle = rot + i * math.tau / 6 + 0.3
            x1 = cx + math.cos(angle) * r * 0.85
            y1 = cy + math.sin(angle) * r * 0.85
            mx_ang = angle + random.uniform(-0.2, 0.2)
            x2 = cx + math.cos(mx_ang) * r * 0.55
            y2 = cy + math.sin(mx_ang) * r * 0.55
            x3 = cx + math.cos(angle) * r * 0.35
            y3 = cy + math.sin(angle) * r * 0.35
            pulse = 0.5 + 0.5 * math.sin(self._rotation * 4 + i)
            a = int(120 + 100 * pulse)
            draw_line_alpha(surface, (255, 100, 255, a), (x1, y1), (x2, y2), 2)
            draw_line_alpha(surface, (255, 100, 255, a), (x2, y2), (x3, y3), 1)

    def _draw_eye(self, surface, cx, cy, r):
        eye_r = int(r * 0.32)
        ex = cx + int(self._eye_look[0] * r * 0.15)
        ey = cy + int(self._eye_look[1] * r * 0.15)
        glow_size = eye_r * 3
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -3):
            a = int(150 * (1 - rr / glow_size))
            if a <= 0:
                continue
            color = (255, 60, 60) if self._phase == 1 else (
                (255, 140, 60) if self._phase == 2 else (255, 60, 200))
            pygame.draw.circle(glow, (*color, a), (glow_size, glow_size), rr)
        surface.blit(glow, (ex - glow_size, ey - glow_size), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, (240, 220, 240), (ex, ey), eye_r)
        iris_color = (255, 40, 40) if self._phase == 1 else (
            (255, 120, 40) if self._phase == 2 else (255, 60, 180))
        pygame.draw.circle(surface, iris_color, (ex, ey), int(eye_r * 0.75))
        pupil_x = ex + int(self._eye_look[0] * eye_r * 0.35)
        pupil_y = ey + int(self._eye_look[1] * eye_r * 0.35)
        pupil_r = int(eye_r * 0.35)
        pygame.draw.circle(surface, (0, 0, 0), (pupil_x, pupil_y), pupil_r)
        pygame.draw.circle(surface, (255, 255, 255),
                           (pupil_x - max(2, pupil_r // 3), pupil_y - max(2, pupil_r // 3)),
                           max(2, pupil_r // 3))

    def _draw_crown(self, surface, cx, cy, r, bright):
        crown_y = cy - int(r * 1.05)
        num_spikes = 5
        base_w = int(r * 0.6)
        for i in range(num_spikes):
            t = i / (num_spikes - 1)
            x = cx - base_w + int(t * base_w * 2)
            h = 15 if i % 2 == 0 else 10
            h += int(5 * math.sin(self._rotation * 3 + i))
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
        progress = min(1.0, self._attack_progress)
        for i, (tx, ty) in enumerate(self._summon_targets):
            portal_r = int(20 + 30 * progress)
            pulse = 0.7 + 0.3 * math.sin(self._rotation * 10 + i * 2)
            for rr in range(portal_r * 2, 0, -3):
                a = int(140 * (1 - rr / (portal_r * 2)) * pulse)
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (200, 100, 255, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (int(tx) - rr * 2, int(ty) - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)
            for j in range(8):
                angle = self._rotation * 3 + (j / 8) * math.tau
                px = tx + math.cos(angle) * portal_r
                py = ty + math.sin(angle) * portal_r
                pygame.draw.circle(surface, (255, 200, 255), (int(px), int(py)), 2)
            if progress > 0:
                pygame.draw.circle(surface, (255, 220, 255),
                                   (int(tx), int(ty)), int(portal_r * 0.4))

    def _draw_charge_effect(self, surface, cx, cy, r):
        progress = min(1.0, self._attack_progress)
        charge_r = int(r * 1.5 * progress)
        pulse = 0.7 + 0.3 * math.sin(self._rotation * 15.0)
        for rr in range(charge_r, 0, -4):
            a = int(120 * (1 - rr / max(1, charge_r)) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(surface, (200, 100, 255, a), (cx, cy), rr, 2)
        if self._charge_pos is not None and progress > 0.3:
            tx, ty = self._charge_pos
            line_alpha = int(255 * (progress - 0.3) / 0.7)
            line_width = 2 + int(progress * 3)
            prev_x, prev_y = cx, cy
            num_segments = 8
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
        r = self.radius
        return [
            (self.x, self.y, r * 1.15),
        ]


__all__ = ["VoidSentinel"]