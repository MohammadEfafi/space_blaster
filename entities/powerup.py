"""
entities/powerup.py
===================

سیستم پاورآپ‌ها (Power-Ups) برای SPACE BLASTER.

پاورآپ‌ها آیتم‌های موقتی هستند که با شانس از دشمن‌ها می‌افتند و در
صورت برخورد با پلیر، یک قابلیت ویژه را فعال می‌کنند.

انواع پاورآپ:
    • TRIPLE_SHOT   — شلیک سه‌گانه (موجود در Player)
    • HEAL          — ترمیم یک واحد جان
    • SHIELD        — سپر موقت که یک ضربه را جذب می‌کند
    • BOMB          — پاک‌سازی همه‌ی دشمن‌های روی صفحه
    • RAPID_FIRE    — افزایش سرعت شلیک

ویژگی‌ها:
    • انیمیشن چرخش + پالس (scale breathing)
    • جذب مغناطیسی به سمت پلیر وقتی نزدیک می‌شود
    • هاله‌ی رنگی نئون بر اساس نوع
    • آیکون هندسی متمایز برای هر نوع
    • حذف خودکار وقتی از پایین صفحه خارج شود
    • افکت محو شدن (fade-in) هنگام ظاهر شدن
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
#  پیکربندی ظاهری هر پاورآپ
# ═══════════════════════════════════════════════════════════════════════════

class _PowerupStyle:
    """رنگ‌ها و پارامترهای ظاهری هر نوع پاورآپ."""
    __slots__ = ("core_color", "glow_color", "letter", "weight")

    def __init__(
        self,
        core_color: tuple[int, int, int],
        glow_color: tuple[int, int, int],
        letter: str,
        weight: float = 1.0,
    ) -> None:
        self.core_color = core_color
        self.glow_color = glow_color
        self.letter = letter
        self.weight = weight


_STYLES: dict[PowerupKind, _PowerupStyle] = {
    PowerupKind.TRIPLE_SHOT: _PowerupStyle(
        core_color=(255, 220, 60),
        glow_color=(255, 150, 40),
        letter="T",
        weight=3.0,
    ),
    PowerupKind.HEAL: _PowerupStyle(
        core_color=(255, 90, 90),
        glow_color=(255, 40, 100),
        letter="+",
        weight=2.0,
    ),
    PowerupKind.SHIELD: _PowerupStyle(
        core_color=(60, 200, 255),
        glow_color=(60, 120, 255),
        letter="S",
        weight=2.0,
    ),
    PowerupKind.BOMB: _PowerupStyle(
        core_color=(255, 200, 240),
        glow_color=(255, 60, 160),
        letter="B",
        weight=0.8,
    ),
    PowerupKind.RAPID_FIRE: _PowerupStyle(
        core_color=(120, 255, 140),
        glow_color=(40, 200, 80),
        letter="R",
        weight=1.8,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس Powerup
# ═══════════════════════════════════════════════════════════════════════════

class Powerup(Entity):
    """
    یک آیتم قابل برداشت.

    پارامترها:
        kind        — نوع پاورآپ (None = انتخاب تصادفی وزنی)
        lifetime    — حداکثر زمان روی صفحه (ثانیه)؛ پس از آن نابود می‌شود
        magnet_range— فاصله‌ی فعال شدن جذب مغناطیسی به سمت پلیر
    """

    # ---- جذب مغناطیسی ----
    MAGNET_RANGE:  float = 110.0
    MAGNET_FORCE:  float = 520.0
    COLLECT_RANGE: float = 22.0

    # ─────────────────────────────────────────────────────────────────────
    #  سازنده
    # ─────────────────────────────────────────────────────────────────────

    def __init__(
        self,
        x: float,
        y: float,
        *,
        kind: Optional[PowerupKind] = None,
        scene: Optional["GameplayScene"] = None,
        lifetime: float = 12.0,
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
        self.style: _PowerupStyle = style
        self.lifetime: float = float(lifetime)
        self.max_lifetime: float = float(lifetime)

        # ---- مغناطیس ----
        self._magnet_active: bool = False

        # ---- ظاهر ----
        self._t: float = random.uniform(0, math.tau)   # فاز اولیه‌ی متفاوت
        self._rotation: float = random.uniform(0, 360)
        self._rotation_speed: float = random.uniform(80.0, 140.0) * random.choice((-1, 1))
        self._spawn_scale: float = 0.0   # 0..1 — انیمیشن ورود
        self._spawn_time: float = 0.35

    # ─────────────────────────────────────────────────────────────────────
    #  انتخاب تصادفی وزنی
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
        # ---- زمان ----
        self._t += dt
        self._rotation += self._rotation_speed * dt

        # ---- انیمیشن ورود ----
        if self._spawn_scale < 1.0:
            self._spawn_scale = min(1.0, self._spawn_scale + dt / self._spawn_time)

        # ---- عمر ----
        self.lifetime -= dt
        if self.lifetime <= 0.0:
            self.kill()
            return

        # ---- مغناطیس ----
        player = self._get_player()
        if player is not None and player.alive:
            self._handle_magnet(player, dt)
        else:
            # بدون پلیر، فقط به پایین می‌افتد
            self.y += S.PowerupCfg.FALL_SPEED * dt

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
            # هرچه نزدیک‌تر، قوی‌تر
            strength = 1.0 - (dist / self.MAGNET_RANGE)
            strength = max(0.15, strength)
            # نرمال + ضریب
            if dist > 0.001:
                ux, uy = dx / dist, dy / dist
                pull = self.MAGNET_FORCE * strength * dt
                self.x += ux * pull
                self.y += uy * pull
            # نزدیک‌تر از range جمع، برداشته شده
            if dist < self.COLLECT_RANGE:
                self._on_collect(player)
                return
        else:
            self._magnet_active = False
            # فقط سقوط عادی
            self.y += S.PowerupCfg.FALL_SPEED * dt

    # ─────────────────────────────────────────────────────────────────────
    #  برداشتن
    # ─────────────────────────────────────────────────────────────────────

    def _on_collect(self, player: "Player") -> None:
        """اعمال اثر پاورآپ روی پلیر و پاک شدن خود."""
        try:
            self._apply_effect(player)
        except Exception:
            pass

        # افکت بصری و صوتی
        if self.scene is not None:
            try:
                self.scene.spawn_powerup_burst(self.x, self.y, self.style.glow_color)
                self.scene.audio.play("powerup_pickup")
                self.scene.camera.shake(3.0)
            except Exception:
                pass

        self.kill()

    def _apply_effect(self, player: "Player") -> None:
        """اثر هر نوع پاورآپ روی پلیر."""
        kind = self.kind

        if kind == PowerupKind.TRIPLE_SHOT:
            player.grant_powerup(S.PowerupCfg.DURATION)

        elif kind == PowerupKind.HEAL:
            player.heal(1)

        elif kind == PowerupKind.SHIELD:
            # اگر Player متد grant_shield داشته باشد، صدا زده می‌شود
            fn: Optional[Callable] = getattr(player, "grant_shield", None)
            if callable(fn):
                fn(S.PowerupCfg.DURATION)

        elif kind == PowerupKind.BOMB:
            # پاک‌سازی همه‌ی دشمن‌های روی صفحه
            if self.scene is not None:
                try:
                    self.scene.trigger_screen_bomb(self.x, self.y)
                except Exception:
                    pass

        elif kind == PowerupKind.RAPID_FIRE:
            fn = getattr(player, "grant_rapid_fire", None)
            if callable(fn):
                fn(S.PowerupCfg.DURATION)

    # ─────────────────────────────────────────────────────────────────────
    #  رسم
    # ─────────────────────────────────────────────────────────────────────

    def draw_entity(self, surface: pygame.Surface) -> None:
        # ---- انیمیشن ورود: scale کوچک → بزرگ ----
        scale = self._ease_out_back(self._spawn_scale)

        # ---- محو شدن در ۲ ثانیه‌ی آخر ----
        fade_alpha = 255
        if self.lifetime < 2.0:
            fade_alpha = int(255 * (self.lifetime / 2.0))
            # چشمک‌زن سریع‌تر
            if int(self.lifetime * 8) % 2 == 0:
                fade_alpha = int(fade_alpha * 0.45)

        # ---- پالس breathing ----
        pulse = 1.0 + 0.12 * math.sin(self._t * 5.5)
        base_r = self.radius * scale * pulse

        # ---- هاله ----
        self._draw_glow(surface, base_r, fade_alpha)

        # ---- آیکون چرخان ----
        self._draw_icon(surface, base_r, fade_alpha)

    def _draw_glow(
        self,
        surface: pygame.Surface,
        r: float,
        alpha: int,
    ) -> None:
        glow_r = int(r * 2.8)
        if glow_r < 3:
            return
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        # لایه‌ی بیرونی (نرم)
        for rr in range(glow_r, 0, -2):
            t = rr / glow_r
            a = int(60 * (1 - t) ** 1.8 * (alpha / 255.0))
            if a <= 0:
                continue
            pygame.draw.circle(
                glow, (*self.style.glow_color, a),
                (glow_r, glow_r), rr,
            )
        surface.blit(
            glow, (self.x - glow_r, self.y - glow_r),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

    def _draw_icon(
        self,
        surface: pygame.Surface,
        r: float,
        alpha: int,
    ) -> None:
        cx, cy = self.x, self.y
        # ---- مثلث چرخان بیرونی ----
        rot = math.radians(self._rotation)
        for i in range(3):
            a = rot + i * math.tau / 3
            x1 = cx + math.cos(a) * r
            y1 = cy + math.sin(a) * r
            x2 = cx + math.cos(a + math.tau / 3) * r
            y2 = cy + math.sin(a + math.tau / 3) * r
            pygame.draw.line(
                surface, (*self.style.core_color, alpha),
                (int(x1), int(y1)), (int(x2), int(y2)), 2,
            )

        # ---- دایره‌ی میانی ----
        if alpha >= 250:
            pygame.draw.circle(surface, self.style.core_color, (int(cx), int(cy)), int(r * 0.7))
            pygame.draw.circle(surface, (255, 255, 255), (int(cx), int(cy)), int(r * 0.7), 2)
        else:
            tmp = pygame.Surface((int(r * 2 + 4), int(r * 2 + 4)), pygame.SRCALPHA)
            local_r = int(r + 2)
            pygame.draw.circle(
                tmp, (*self.style.core_color, alpha),
                (local_r, local_r), int(r * 0.7),
            )
            pygame.draw.circle(
                tmp, (255, 255, 255, alpha),
                (local_r, local_r), int(r * 0.7), 2,
            )
            surface.blit(tmp, (cx - local_r, cy - local_r))

        # ---- حرف داخل ----
        font_size = max(10, int(r * 1.1))
        font = pygame.font.SysFont(S.FontCfg.FAMILY, font_size, bold=True)
        letter_img = font.render(self.style.letter, True, (10, 10, 20))
        if alpha < 250:
            letter_img.set_alpha(alpha)
        rect = letter_img.get_rect(center=(int(cx), int(cy)))
        surface.blit(letter_img, rect)

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌های انیمیشن
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _ease_out_back(t: float) -> float:
        """تابع easing با کمی overshoot — پاورآپ با «پاپ» ظاهر می‌شود."""
        if t >= 1.0:
            return 1.0
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌های منطقی
    # ─────────────────────────────────────────────────────────────────────

    @property
    def magnet_active(self) -> bool:
        """آیا پاورآپ در حال جذب به سمت پلیر است؟"""
        return self._magnet_active


__all__ = ["Powerup", "PowerupKind"]