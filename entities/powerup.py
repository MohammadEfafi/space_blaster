"""
entities/powerup.py
===================

سیستم پاورآپ‌ها (Power-Ups) برای SPACE BLASTER — بازطراحی کامل.

دیزاین جدید:
    • هر پاورآپ شکل هندسی منحصر به فرد خودش را دارد (بدون دایره)
    • درخشش نرم زیرش (نه هاله‌ی دایره‌ای)
    • سایه‌ی تیره برای عمق
    • چرخش/پالس اختصاصی برای هر نوع
    • انیمیشن ورود (pop) و خروج (fade)
    • ذرات ریز چرخان دور آیکون (نقطه‌ای، نه دایره)
    • جذب مغناطیسی نرم به سمت پلیر

طراحی هر نوع:
    • TRIPLE_SHOT : سفینه‌ی کوچیک با سه پرتوی شلیک
    • HEAL        : صلیب پزشکی با ضربان
    • SHIELD      : شش‌ضلعی زره‌ای با خطوط شبکه
    • BOMB        : مین دندانه‌دار با جرقه‌های چشمک‌زن
    • RAPID_FIRE  : صاعقه با خطوط سرعت کناری
"""

from __future__ import annotations

import math
import random
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable, Optional

import pygame

from core import settings as S
from entities.entity import Entity

if TYPE_CHECKING:
    from entities.player import Player
    from scenes.gameplay import GameplayScene


# ═══════════════════════════════════════════════════════════════════════════
#  انواع پاورآپ
# ═══════════════════════════════════════════════════════════════════════════

class PowerupKind(Enum):
    TRIPLE_SHOT = auto()
    HEAL        = auto()
    SHIELD      = auto()
    BOMB        = auto()
    RAPID_FIRE  = auto()


# ═══════════════════════════════════════════════════════════════════════════
#  پیکربندی ظاهری
# ═══════════════════════════════════════════════════════════════════════════

class _Style:
    """رنگ‌ها و پارامترهای ظاهری هر نوع پاورآپ."""
    __slots__ = (
        "primary", "secondary", "accent",
        "glow", "weight",
    )

    def __init__(
        self,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
        glow: tuple[int, int, int],
        weight: float = 1.0,
    ) -> None:
        self.primary = primary
        self.secondary = secondary
        self.accent = accent
        self.glow = glow
        self.weight = weight


_STYLES: dict[PowerupKind, _Style] = {
    PowerupKind.TRIPLE_SHOT: _Style(
        primary=(255, 220, 90),
        secondary=(200, 130, 30),
        accent=(255, 255, 220),
        glow=(255, 180, 60),
        weight=3.0,
    ),
    PowerupKind.HEAL: _Style(
        primary=(120, 255, 150),
        secondary=(40, 140, 70),
        accent=(255, 255, 255),
        glow=(80, 220, 120),
        weight=2.0,
    ),
    PowerupKind.SHIELD: _Style(
        primary=(90, 220, 255),
        secondary=(30, 110, 180),
        accent=(220, 250, 255),
        glow=(60, 180, 255),
        weight=2.0,
    ),
    PowerupKind.BOMB: _Style(
        primary=(255, 110, 90),
        secondary=(160, 30, 30),
        accent=(255, 240, 180),
        glow=(255, 80, 60),
        weight=0.8,
    ),
    PowerupKind.RAPID_FIRE: _Style(
        primary=(255, 250, 120),
        secondary=(200, 130, 20),
        accent=(255, 255, 255),
        glow=(255, 220, 80),
        weight=1.8,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس Powerup
# ═══════════════════════════════════════════════════════════════════════════

class Powerup(Entity):

    # ---- جذب مغناطیسی ----
    MAGNET_RANGE:  float = 130.0
    MAGNET_FORCE:  float = 620.0
    COLLECT_RANGE: float = 24.0

    # ─────────────────────────────────────────────────────────────────────

    def __init__(
        self,
        x: float,
        y: float,
        *,
        kind: Optional[PowerupKind] = None,
        scene: Optional["GameplayScene"] = None,
        lifetime: float = 12.0,
        fall_speed: Optional[float] = None,
    ) -> None:
        if kind is None:
            kind = self._random_kind()

        style = _STYLES[kind]

        super().__init__(
            x, y,
            vx=0.0,
            vy=S.PowerupCfg.FALL_SPEED,
            radius=S.PowerupCfg.RADIUS,
            hp=1,
            scene=scene,
        )

        self.kind: PowerupKind = kind
        self.style: _Style = style
        self.lifetime: float = float(lifetime)
        self.max_lifetime: float = float(lifetime)
        self.fall_speed: float = (
            S.PowerupCfg.FALL_SPEED if fall_speed is None else float(fall_speed)
        )

        # ---- مغناطیس ----
        self._magnet_active: bool = False

        # ---- انیمیشن ----
        self._t: float = random.uniform(0, math.tau)
        self._rotation: float = random.uniform(0, 360)
        self._rotation_speed: float = random.uniform(30.0, 55.0) * random.choice((-1, 1))
        self._spawn_scale: float = 0.0
        self._spawn_time: float = 0.42

        # ---- ذرات چرخان دور ----
        self._orbit_dots: list[dict] = [
            {
                "angle": random.uniform(0, math.tau),
                "speed": random.uniform(1.8, 2.8),
                "radius": random.uniform(1.3, 1.55),   # نسبت به radius
                "size": random.uniform(1.2, 2.0),
                "phase": random.uniform(0, math.tau),
            }
            for _ in range(4)
        ]

    # ─────────────────────────────────────────────────────────────────────
    #  انتخاب تصادفی
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _random_kind() -> PowerupKind:
        kinds = list(_STYLES.keys())
        weights = [_STYLES[k].weight for k in kinds]
        return random.choices(kinds, weights=weights, k=1)[0]

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update_entity(self, dt: float) -> None:
        self._t += dt
        self._rotation = (self._rotation + self._rotation_speed * dt) % 360

        # ---- انیمیشن ورود ----
        if self._spawn_scale < 1.0:
            self._spawn_scale = min(1.0, self._spawn_scale + dt / self._spawn_time)

        # ---- ذرات چرخان ----
        for d in self._orbit_dots:
            d["angle"] += d["speed"] * dt

        # ---- عمر ----
        self.lifetime -= dt
        if self.lifetime <= 0.0:
            self.kill()
            return

        # ---- مغناطیس / سقوط ----
        player = self._get_player()
        if player is not None and player.alive:
            self._handle_magnet(player, dt)
        else:
            self.y += self.fall_speed * dt

        # ---- خروج از پایین ----
        if self.y > S.Window.HEIGHT + self.radius + 20:
            self.alive = False
            self._pending_kill = True

    def _get_player(self) -> Optional["Player"]:
        if self.scene is None:
            return None
        return getattr(self.scene, "player", None)

    def _handle_magnet(self, player: "Player", dt: float) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        if dist < self.MAGNET_RANGE:
            self._magnet_active = True
            strength = 1.0 - (dist / self.MAGNET_RANGE)
            strength = max(0.15, strength)
            if dist > 0.001:
                ux, uy = dx / dist, dy / dist
                pull = self.MAGNET_FORCE * strength * dt
                self.x += ux * pull
                self.y += uy * pull
            if dist < self.COLLECT_RANGE:
                self._on_collect(player)
                return
        else:
            self._magnet_active = False
            self.y += self.fall_speed * dt

    # ─────────────────────────────────────────────────────────────────────
    #  برداشتن
    # ─────────────────────────────────────────────────────────────────────

    def _on_collect(self, player: "Player") -> None:
        try:
            self._apply_effect(player)
        except Exception:
            pass

        if self.scene is not None:
            try:
                self.scene.spawn_powerup_burst(self.x, self.y, self.style.glow)
                self.scene.audio.play("powerup_pickup")
                self.scene.camera.shake(3.0)
            except Exception:
                pass

        self.kill()

    def _apply_effect(self, player: "Player") -> None:
        kind = self.kind

        if kind == PowerupKind.TRIPLE_SHOT:
            player.grant_powerup(S.PowerupCfg.DURATION)

        elif kind == PowerupKind.HEAL:
            player.heal(1)

        elif kind == PowerupKind.SHIELD:
            fn: Optional[Callable] = getattr(player, "grant_shield", None)
            if callable(fn):
                fn(S.PowerupCfg.DURATION)

        elif kind == PowerupKind.BOMB:
            if self.scene is not None:
                try:
                    self.scene.trigger_screen_bomb(self.x, self.y)
                except Exception:
                    pass

        elif kind == PowerupKind.RAPID_FIRE:
            fn = getattr(player, "grant_rapid_fire", None)
            if callable(fn):
                fn(S.PowerupCfg.DURATION)

    # ═════════════════════════════════════════════════════════════════════
    #  رسم
    # ═════════════════════════════════════════════════════════════════════

    def draw_entity(self, surface: pygame.Surface) -> None:
        # ---- محو شدن در ۲ ثانیه‌ی آخر ----
        fade_alpha = 255
        if self.lifetime < 2.0:
            fade_alpha = int(255 * (self.lifetime / 2.0))
            if int(self.lifetime * 8) % 2 == 0:
                fade_alpha = int(fade_alpha * 0.5)

        # ---- scale ورود (ease-out-back) ----
        scale = self._ease_out_back(self._spawn_scale)

        # ---- پالس breathing ----
        pulse = 1.0 + 0.08 * math.sin(self._t * 4.5)
        base_r = self.radius * scale * pulse

        cx = int(self.x)
        cy = int(self.y)

        # ---- لایه‌ها (به ترتیب) ----
        # ۱. درخشش نرم (خیلی کم، پشت همه)
        self._draw_soft_glow(surface, cx, cy, base_r, fade_alpha)

        # ۲. ذرات چرخان دور
        self._draw_orbit_dots(surface, cx, cy, base_r, fade_alpha)

        # ۳. سایه‌ی زیر (عمق)
        self._draw_ground_shadow(surface, cx, cy, base_r, fade_alpha)

        # ۴. آیکون اختصاصی
        self._draw_icon(surface, cx, cy, int(base_r), fade_alpha)

    # ─────────────────────────────────────────────────────────────────────
    #  لایه‌های مشترک
    # ─────────────────────────────────────────────────────────────────────

    def _draw_soft_glow(
        self,
        surface: pygame.Surface,
        cx: int, cy: int,
        r: float,
        alpha: int,
    ) -> None:
        """درخشش نرم خیلی کم — نه هاله‌ی دایره‌ای."""
        glow_r = int(r * 2.0)
        if glow_r < 4:
            return
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        base_a = int(35 * (alpha / 255.0))
        for rr in range(glow_r, 0, -3):
            a = int(base_a * (1 - rr / glow_r) ** 2.2)
            if a <= 0:
                continue
            pygame.draw.circle(glow, (*self.style.glow, a), (glow_r, glow_r), rr)
        surface.blit(
            glow, (cx - glow_r, cy - glow_r),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

    def _draw_orbit_dots(
        self,
        surface: pygame.Surface,
        cx: int, cy: int,
        r: float,
        alpha: int,
    ) -> None:
        """ذرات ریز چرخان دور آیکون (نقطه‌ای)."""
        for d in self._orbit_dots:
            a = d["angle"]
            rr = r * d["radius"]
            px = cx + math.cos(a) * rr
            py = cy + math.sin(a) * rr

            twinkle = 0.5 + 0.5 * math.sin(self._t * 6.0 + d["phase"])
            dot_a = int((100 + 120 * twinkle) * (alpha / 255.0))
            if dot_a <= 0:
                continue

            size = int(d["size"]) + 1
            dot_surf = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
            pygame.draw.circle(dot_surf, (*self.style.accent, dot_a),
                               (size * 3, size * 3), size * 2)
            pygame.draw.circle(dot_surf, (*self.style.glow, dot_a),
                               (size * 3, size * 3), size)
            surface.blit(
                dot_surf, (int(px - size * 3), int(py - size * 3)),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    def _draw_ground_shadow(
        self,
        surface: pygame.Surface,
        cx: int, cy: int,
        r: float,
        alpha: int,
    ) -> None:
        """سایه‌ی بیضوی نرم زیر آیکون."""
        sw = int(r * 1.2)
        sh = int(r * 0.35)
        if sw < 3:
            return
        shadow = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        for rr in range(sh, 0, -1):
            a = int(70 * (1 - rr / sh) ** 1.6 * (alpha / 255.0))
            if a <= 0:
                continue
            pygame.draw.ellipse(
                shadow, (0, 0, 0, a),
                (sw - rr, sh - rr, rr * 2, rr * 2),
            )
        surface.blit(shadow, (cx - sw, cy - sh))

    # ─────────────────────────────────────────────────────────────────────
    #  آیکون اختصاصی هر نوع
    # ─────────────────────────────────────────────────────────────────────

    def _draw_icon(
        self,
        surface: pygame.Surface,
        cx: int, cy: int,
        r: int,
        alpha: int,
    ) -> None:
        kind = self.kind
        if kind == PowerupKind.TRIPLE_SHOT:
            self._icon_triple_shot(surface, cx, cy, r, alpha)
        elif kind == PowerupKind.HEAL:
            self._icon_heal(surface, cx, cy, r, alpha)
        elif kind == PowerupKind.SHIELD:
            self._icon_shield(surface, cx, cy, r, alpha)
        elif kind == PowerupKind.BOMB:
            self._icon_bomb(surface, cx, cy, r, alpha)
        elif kind == PowerupKind.RAPID_FIRE:
            self._icon_rapid_fire(surface, cx, cy, r, alpha)

    # ── TRIPLE_SHOT: سفینه‌ی کوچیک با سه پرتو ──
    def _icon_triple_shot(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
        s = self.style
        rot = math.radians(self._rotation * 0.4)   # چرخش ملایم

        # هاله‌ی طلایی (خط‌های شلیک)
        for offset_deg in (-18, 0, 18):
            a = -math.pi / 2 + math.radians(offset_deg) + rot
            # خط از مرکز به بیرون
            x1 = cx + math.cos(a) * (r * 0.45)
            y1 = cy + math.sin(a) * (r * 0.45)
            x2 = cx + math.cos(a) * (r * 1.15)
            y2 = cy + math.sin(a) * (r * 1.15)

            # خط درخشان
            line_surf = pygame.Surface((int(abs(x2 - x1)) + 8, int(abs(y2 - y1)) + 8),
                                       pygame.SRCALPHA)
            ox = min(x1, x2) - 4
            oy = min(y1, y2) - 4
            pygame.draw.line(
                line_surf, (*s.primary, alpha),
                (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), 3,
            )
            pygame.draw.line(
                line_surf, (*s.accent, alpha),
                (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), 1,
            )
            surface.blit(line_surf, (ox, oy))

            # نقطه‌ی نور در نوک
            tx = cx + math.cos(a) * (r * 1.1)
            ty = cy + math.sin(a) * (r * 1.1)
            dot = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(dot, (*s.accent, alpha), (4, 4), 3)
            pygame.draw.circle(dot, (*s.primary, alpha), (4, 4), 2)
            surface.blit(dot, (int(tx - 4), int(ty - 4)))

        # ---- بدنه‌ی سفینه (مثلث کوچک) ----
        tip = (cx, cy - int(r * 0.55))
        bl = (cx - int(r * 0.55), cy + int(r * 0.55))
        br = (cx + int(r * 0.55), cy + int(r * 0.55))

        # سایه‌ی بدنه
        pygame.draw.polygon(surface, s.secondary, [
            (tip[0], tip[1] + 2),
            (bl[0], bl[1] + 2),
            (br[0], br[1] + 2),
        ])
        # بدنه
        pygame.draw.polygon(surface, s.primary, [tip, bl, br])
        # خط دور
        pygame.draw.polygon(surface, s.accent, [tip, bl, br], 2)

        # کابین درخشان وسط
        cab_r = max(2, r // 5)
        pygame.draw.circle(surface, s.accent, (cx, cy - int(r * 0.05)), cab_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy - int(r * 0.05)), max(1, cab_r - 1))

    # ── HEAL: صلیب پزشکی ──
    def _icon_heal(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
        s = self.style
        # ضربان قلب (پالس قوی‌تر)
        beat = 1.0 + 0.12 * math.sin(self._t * 7.0)
        size = r * beat

        # ابعاد صلیب
        arm = int(size * 0.9)
        thick = int(size * 0.32)

        # سایه
        self._draw_cross(surface, cx + 2, cy + 2, arm, thick, s.secondary, alpha)
        # صلیب اصلی
        self._draw_cross(surface, cx, cy, arm, thick, s.primary, alpha)
        # خط روشن داخلی
        self._draw_cross_outline(surface, cx, cy, arm, thick, s.accent, alpha)

        # خط افقی روشن وسط
        pygame.draw.line(
            surface, s.accent,
            (cx - arm + 3, cy), (cx + arm - 3, cy), 1,
        )
        pygame.draw.line(
            surface, s.accent,
            (cx, cy - arm + 3), (cx, cy + arm - 3), 1,
        )

    def _draw_cross(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, arm: int, thick: int,
        color: tuple[int, int, int], alpha: int,
    ) -> None:
        # عمودی
        pygame.draw.rect(
            surface, color,
            (cx - thick // 2, cy - arm, thick, arm * 2),
        )
        # افقی
        pygame.draw.rect(
            surface, color,
            (cx - arm, cy - thick // 2, arm * 2, thick),
        )

    def _draw_cross_outline(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, arm: int, thick: int,
        color: tuple[int, int, int], alpha: int,
    ) -> None:
        # فقط لبه‌های داخلی برای حس شیشه‌ای
        rect_v = pygame.Rect(cx - thick // 2, cy - arm, thick, arm * 2)
        rect_h = pygame.Rect(cx - arm, cy - thick // 2, arm * 2, thick)
        pygame.draw.rect(surface, color, rect_v, 1)
        pygame.draw.rect(surface, color, rect_h, 1)

    # ── SHIELD: شش‌ضلعی زره‌ای ──
    def _icon_shield(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
        s = self.style
        # چرخش آرام شش‌ضلعی
        rot = math.radians(self._rotation * 0.3)
        pulse = 0.5 + 0.5 * math.sin(self._t * 3.0)

        # ---- شش‌ضلعی بیرونی ----
        outer = []
        for i in range(6):
            a = rot + i * math.tau / 6 - math.pi / 2
            outer.append((
                cx + math.cos(a) * r,
                cy + math.sin(a) * r,
            ))

        # سایه‌ی شش‌ضلعی
        shadow = [(p[0], p[1] + 2) for p in outer]
        pygame.draw.polygon(surface, s.secondary, shadow)

        # بدنه‌ی شش‌ضلعی
        pygame.draw.polygon(surface, s.primary, outer)
        pygame.draw.polygon(surface, s.accent, outer, 2)

        # ---- شش‌ضلعی داخلی ----
        inner = []
        for i in range(6):
            a = rot + i * math.tau / 6 - math.pi / 2
            inner.append((
                cx + math.cos(a) * r * 0.62,
                cy + math.sin(a) * r * 0.62,
            ))
        pygame.draw.polygon(surface, s.secondary, inner)
        pygame.draw.polygon(surface, s.accent, inner, 1)

        # ---- خطوط شبکه (به رأس‌ها) ----
        for i in range(6):
            a = rot + i * math.tau / 6 - math.pi / 2
            x1 = cx + math.cos(a) * r * 0.62
            y1 = cy + math.sin(a) * r * 0.62
            x2 = cx + math.cos(a) * r
            y2 = cy + math.sin(a) * r
            pygame.draw.line(surface, s.accent,
                             (int(x1), int(y1)), (int(x2), int(y2)), 1)

        # ---- هسته‌ی درخشان وسط ----
        core_r = max(2, int(r * 0.22 * (0.85 + 0.15 * pulse)))
        pygame.draw.circle(surface, s.accent, (cx, cy), core_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(1, core_r - 1))

    # ── BOMB: مین دندانه‌دار ──
    def _icon_bomb(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
        s = self.style
        pulse = 0.5 + 0.5 * math.sin(self._t * 8.0)

        # ---- خارهای بیرونی (۸ تا) ----
        num_spikes = 8
        spike_len = r * 0.35
        spike_base = r * 0.85
        for i in range(num_spikes):
            a = (i / num_spikes) * math.tau + math.radians(self._rotation * 0.5)
            x1 = cx + math.cos(a) * spike_base
            y1 = cy + math.sin(a) * spike_base
            x2 = cx + math.cos(a) * (spike_base + spike_len)
            y2 = cy + math.sin(a) * (spike_base + spike_len)
            pygame.draw.line(
                surface, s.primary,
                (int(x1), int(y1)), (int(x2), int(y2)), 3,
            )
            # نوک درخشان
            pygame.draw.circle(surface, s.accent, (int(x2), int(y2)), 2)

        # ---- بدنه‌ی دایره‌ای ----
        body_r = int(spike_base)
        # سایه
        pygame.draw.circle(surface, s.secondary, (cx, cy + 2), body_r)
        # بدنه
        pygame.draw.circle(surface, s.primary, (cx, cy), body_r)
        # حلقه‌ی روشن
        pygame.draw.circle(surface, s.accent, (cx, cy), body_r, 2)
        pygame.draw.circle(surface, s.secondary, (cx, cy), int(body_r * 0.7), 2)

        # ---- هسته‌ی چشمک‌زن (چشم مین) ----
        core_r = max(2, int(r * 0.28 * (0.7 + 0.3 * pulse)))
        # درخشش مرکزی
        for rr in range(core_r + 4, 0, -1):
            a = int(120 * (1 - rr / (core_r + 4)) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(surface, (*s.accent, a), (cx, cy), rr)
        pygame.draw.circle(surface, s.accent, (cx, cy), core_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(1, core_r - 1))

    # ── RAPID_FIRE: صاعقه ──
    def _icon_rapid_fire(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
        s = self.style
        pulse = 0.5 + 0.5 * math.sin(self._t * 9.0)

        # ---- خطوط سرعت کناری ----
        for sign in (-1, 1):
            for i in range(3):
                ly = cy - int(r * 0.4) + i * int(r * 0.4)
                lx1 = cx + sign * int(r * 0.7)
                lx2 = cx + sign * int(r * 1.0)
                line_a = int(alpha * (0.4 + 0.6 * (1 - i / 3)))
                pygame.draw.line(
                    surface, (*s.primary, line_a),
                    (lx1, ly), (lx2, ly), 2,
                )

        # ---- بدنه‌ی صاعقه (zigzag) ----
        bolt = [
            (cx + int(r * 0.15), cy - int(r * 0.95)),
            (cx - int(r * 0.45), cy - int(r * 0.10)),
            (cx + int(r * 0.05), cy - int(r * 0.10)),
            (cx - int(r * 0.15), cy + int(r * 0.95)),
            (cx + int(r * 0.50), cy - int(r * 0.05)),
            (cx + int(r * 0.00), cy - int(r * 0.05)),
        ]

        # سایه‌ی صاعقه
        shadow = [(p[0], p[1] + 2) for p in bolt]
        pygame.draw.polygon(surface, s.secondary, shadow)

        # بدنه
        pygame.draw.polygon(surface, s.primary, bolt)
        pygame.draw.polygon(surface, s.accent, bolt, 2)

        # ---- درخشش روی بدنه (وسط) ----
        if pulse > 0.5:
            inner_bolt = [
                (cx + int(r * 0.08), cy - int(r * 0.55)),
                (cx - int(r * 0.15), cy - int(r * 0.05)),
                (cx + int(r * 0.08), cy - int(r * 0.05)),
                (cx + int(r * 0.00), cy + int(r * 0.35)),
            ]
            pygame.draw.polygon(surface, (255, 255, 255), inner_bolt)

        # ---- جرقه‌های اطراف ----
        for _ in range(3):
            spark_a = (self._t * 5.0 + random.uniform(0, 6.28)) % math.tau
            spark_r = r * (0.9 + random.uniform(0, 0.15))
            sx = cx + math.cos(spark_a) * spark_r
            sy = cy + math.sin(spark_a) * spark_r
            spark_size = random.randint(1, 2)
            pygame.draw.circle(
                surface, s.accent,
                (int(sx), int(sy)), spark_size,
            )

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _ease_out_back(t: float) -> float:
        """easing با overshoot — پاورآپ با «پاپ» ظاهر می‌شود."""
        if t >= 1.0:
            return 1.0
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2

    @property
    def magnet_active(self) -> bool:
        return self._magnet_active


__all__ = ["Powerup", "PowerupKind"]