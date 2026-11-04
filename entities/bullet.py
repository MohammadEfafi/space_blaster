"""
entities/bullet.py
==================

سیستم گلوله‌ها (Bullets) برای SPACE BLASTER.

یک کلاس واحد که می‌تواند انواع مختلف گلوله را با پارامترهای متفاوت
مدیریت کند — از گلوله‌ی ساده‌ی پلیر تا شلیک سنگین باس. تفاوت‌ها فقط
در پیکربندی است، نه در کد.

ویژگی‌ها:
    • انواع گلوله با Enum (PLAYER, ENEMY, LASER, PLASMA, BOSS, HOMING)
    • دنباله‌ی درخشان (Trail) که به‌صورت خودکار و با عمر کم رسم می‌شود
    • هاله‌ی نور (Glow) با gradient ساده برای افکت نئونی
    • پشتیبانی از گلوله‌ی هدف‌گیر (Homing) با چرخش نرم
    • اندازه‌ی دینامیک، رنگ قابل تنظیم و damage قابل تعیین
    • بهینه‌سازی شده برای صدها گلوله‌ی همزمان در صفحه
"""

from __future__ import annotations

import math
from collections import deque
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

import pygame

from core import settings as S
from entities.entity import Entity

if TYPE_CHECKING:
    from scenes.gameplay import GameplayScene


# ═══════════════════════════════════════════════════════════════════════════
#  انواع گلوله
# ═══════════════════════════════════════════════════════════════════════════

class BulletKind(Enum):
    """دسته‌بندی گلوله‌ها برای رفتار و ظاهر متفاوت."""
    PLAYER  = auto()   # گلوله‌ی ساده‌ی پلیر
    ENEMY   = auto()   # گلوله‌ی معمولی دشمن
    LASER   = auto()   # خط پرسرعت، دمی بلند
    PLASMA  = auto()   # توپ پلاسما، کند ولی بزرگ
    BOSS    = auto()   # سنگین و درخشان
    HOMING  = auto()   # هدف‌گیر با چرخش نرم


# ═══════════════════════════════════════════════════════════════════════════
#  پیکربندی هر نوع گلوله
# ═══════════════════════════════════════════════════════════════════════════

class _BulletPreset:
    """مقادیر پیش‌فرض برای هر نوع گلوله."""
    __slots__ = (
        "radius", "damage", "color_core", "color_glow",
        "trail_len", "trail_alpha", "homing_rate", "trail_width",
    )

    def __init__(
        self,
        radius: float,
        damage: int,
        color_core: tuple[int, int, int],
        color_glow: tuple[int, int, int],
        trail_len: int,
        trail_alpha: int,
        trail_width: int,
        homing_rate: float = 0.0,
    ) -> None:
        self.radius = radius
        self.damage = damage
        self.color_core = color_core
        self.color_glow = color_glow
        self.trail_len = trail_len
        self.trail_alpha = trail_alpha
        self.trail_width = trail_width
        self.homing_rate = homing_rate


_PRESETS: dict[BulletKind, _BulletPreset] = {
    BulletKind.PLAYER: _BulletPreset(
        radius=4.0, damage=1,
        color_core=(240, 255, 255), color_glow=S.Palette.BULLET_PLAYER,
        trail_len=10, trail_alpha=170, trail_width=2,
    ),
    BulletKind.ENEMY: _BulletPreset(
        radius=4.5, damage=1,
        color_core=(255, 220, 220), color_glow=S.Palette.BULLET_ENEMY,
        trail_len=8, trail_alpha=150, trail_width=2,
    ),
    BulletKind.LASER: _BulletPreset(
        radius=3.0, damage=1,
        color_core=(255, 255, 255), color_glow=(120, 255, 240),
        trail_len=18, trail_alpha=200, trail_width=3,
    ),
    BulletKind.PLASMA: _BulletPreset(
        radius=7.0, damage=2,
        color_core=(255, 255, 220), color_glow=(255, 180, 40),
        trail_len=10, trail_alpha=140, trail_width=4,
    ),
    BulletKind.BOSS: _BulletPreset(
        radius=6.0, damage=1,
        color_core=(255, 230, 255), color_glow=S.Palette.BULLET_BOSS,
        trail_len=14, trail_alpha=180, trail_width=3,
    ),
    BulletKind.HOMING: _BulletPreset(
        radius=4.0, damage=1,
        color_core=(240, 255, 240), color_glow=(120, 255, 140),
        trail_len=14, trail_alpha=170, trail_width=2,
        homing_rate=4.5,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس Bullet
# ═══════════════════════════════════════════════════════════════════════════

class Bullet(Entity):
    """
    یک گلوله‌ی قابل استفاده توسط پلیر یا دشمن.

    پارامترهای کلیدی:
        friendly    — True اگر به دشمن آسیب بزند (پلیر)؛ False اگر به پلیر
        kind        — نوع گلوله؛ پیش‌فرض بر اساس friendly
        damage      — مقدار آسیب؛ اگر None باشد از preset استفاده می‌شود
        target      — (اختیاری) هدف برای گلوله‌های HOMING
        pierce      — چند موجودیت را می‌تواند رد کند (0 = یکی و تمام)
        life        — حداکثر عمر (ثانیه)؛ پس از آن خودکار نابود می‌شود
    """

    # کش سراسری برای جلوگیری از ساخت مکرر Surface در هر فریم
    _glow_cache: dict[tuple[int, int], pygame.Surface] = {}

    # ─────────────────────────────────────────────────────────────────────
    #  سازنده
    # ─────────────────────────────────────────────────────────────────────

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        *,
        friendly: bool = True,
        kind: Optional[BulletKind] = None,
        damage: Optional[int] = None,
        scene: "GameplayScene | None" = None,
        target: Optional[Entity] = None,
        pierce: int = 0,
        life: float = 3.2,
    ) -> None:
        # انتخاب نوع پیش‌فرض بر اساس friendly
        if kind is None:
            kind = BulletKind.PLAYER if friendly else BulletKind.ENEMY

        preset = _PRESETS[kind]

        super().__init__(
            x, y,
            vx=vx, vy=vy,
            radius=preset.radius,
            hp=1,
            scene=scene,
        )

        self.kind: BulletKind = kind
        self.friendly: bool = friendly
        self.damage: int = preset.damage if damage is None else damage
        self.pierce: int = pierce
        self.life: float = float(life)
        self.max_life: float = float(life)

        # ---- هدف برای گلوله‌ی HOMING ----
        self.target: Optional[Entity] = target

        # ---- دنباله‌ی درخشان ----
        # deque با maxlen ثابت — خودکار قدیمی‌ترین را حذف می‌کند
        self._trail: deque[tuple[float, float]] = deque(maxlen=preset.trail_len)
        self._trail_alpha: int = preset.trail_alpha
        self._trail_width: int = preset.trail_width

        # ---- کش رنگ‌ها ----
        self._color_core: tuple[int, int, int] = preset.color_core
        self._color_glow: tuple[int, int, int] = preset.color_glow

        # ---- homing ----
        self._homing_rate: float = preset.homing_rate

    # ─────────────────────────────────────────────────────────────────────
    #  هوک‌ها
    # ─────────────────────────────────────────────────────────────────────

    def on_spawn(self) -> None:
        """در لحظه‌ی ساخت، زاویه را از روی سرعت تعیین می‌کند."""
        if self.speed > 0.001:
            self.angle = math.degrees(math.atan2(self.vy, self.vx))

    def on_death(self) -> None:
        """هنگام نابودی، یک انفجار کوچک ذره‌ای در محل تولد می‌سازد."""
        if self.scene is not None:
            try:
                self.scene.spawn_bullet_impact(
                    self.x, self.y, self._color_glow, is_friendly=self.friendly
                )
            except Exception:
                pass

    def update_entity(self, dt: float) -> None:
        # ---- شمارش عمر ----
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return

        # ---- homing ----
        if self.kind == BulletKind.HOMING and self.target is not None and self.target.alive:
            self._steer_toward_target(dt)

        # ---- دنباله ----
        self._trail.append((self.x, self.y))

        # ---- خارج از صفحه ----
        if self.offscreen(margin=40):
            self.kill()
            return

        # ---- زاویه ----
        if self.speed > 0.001:
            self.angle = math.degrees(math.atan2(self.vy, self.vx))

    def _steer_toward_target(self, dt: float) -> None:
        """چرخش نرم سرعت به سمت هدف (Homing)."""
        if self.target is None:
            return
        desired_x = self.target.x - self.x
        desired_y = self.target.y - self.y
        d = math.hypot(desired_x, desired_y)
        if d < 0.001:
            return
        desired_x /= d
        desired_y /= d

        sp = self.speed
        if sp < 0.001:
            return
        cur_x = self.vx / sp
        cur_y = self.vy / sp

        # میان‌یابی خطی بین جهت فعلی و جهت مطلوب
        t = min(1.0, self._homing_rate * dt)
        nx = cur_x + (desired_x - cur_x) * t
        ny = cur_y + (desired_y - cur_y) * t
        n = math.hypot(nx, ny) or 1.0
        self.vx = (nx / n) * sp
        self.vy = (ny / n) * sp

    # ─────────────────────────────────────────────────────────────────────
    #  رسم
    # ─────────────────────────────────────────────────────────────────────

    def draw_entity(self, surface: pygame.Surface) -> None:
        # اگر عمر گلوله داره تموم می‌شه، کمی محو شو (fade-out نرم)
        fade = 1.0
        if self.life < 0.35:
            fade = max(0.0, self.life / 0.35)
        alpha = int(255 * fade)

        # ---- دنباله ----
        self._draw_trail(surface, alpha)

        # ---- هاله ----
        self._draw_glow(surface, alpha)

        # ---- هسته ----
        core_color = self.tint(self._color_core)
        r = max(1, int(round(self.radius)))
        cx, cy = self.pos_int
        if alpha >= 250:
            pygame.draw.circle(surface, core_color, (cx, cy), r)
        else:
            # رسم نیمه‌شفاف با استفاده از Surface موقت
            size = r * 2 + 4
            tmp = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (*core_color, alpha), (size // 2, size // 2), r)
            surface.blit(tmp, (cx - size // 2, cy - size // 2))

    def _draw_trail(self, surface: pygame.Surface, base_alpha: int) -> None:
        if len(self._trail) < 2:
            return

        pts = list(self._trail)
        n = len(pts)

        # bound box محاسبه کن
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        pad = self._trail_width + 4
        min_x = int(min(xs)) - pad
        min_y = int(min(ys)) - pad
        max_x = int(max(xs)) + pad
        max_y = int(max(ys)) + pad
        w = max_x - min_x
        h = max_y - min_y
        if w <= 0 or h <= 0:
            return

        tmp = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(n - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            t = (i + 1) / (n - 1)
            a = int(self._trail_alpha * t * (base_alpha / 255.0))
            if a <= 0:
                continue
            lw = max(1, int(self._trail_width * t))
            color = (*self._color_glow, a)
            pygame.draw.line(
                tmp, color,
                (int(x1 - min_x), int(y1 - min_y)),
                (int(x2 - min_x), int(y2 - min_y)),
                lw,
            )
        surface.blit(tmp, (min_x, min_y))

    def _draw_glow(self, surface: pygame.Surface, alpha: int) -> None:
        """رسم هاله‌ی نرم با استفاده از کش سطح."""
        r = int(self.radius * 2.6)
        if r < 2:
            return
        key = (r, hash(self._color_glow))
        glow = Bullet._glow_cache.get(key)
        if glow is None:
            size = r * 2
            glow = pygame.Surface((size, size), pygame.SRCALPHA)
            for rr in range(r, 0, -1):
                a = int(80 * (1 - rr / r) ** 1.6)
                pygame.draw.circle(glow, (*self._color_glow, a), (r, r), rr)
            Bullet._glow_cache[key] = glow

        if alpha >= 250:
            surface.blit(
                glow, (self.x - r, self.y - r),
                special_flags=pygame.BLEND_RGBA_ADD,
            )
        else:
            # اعمال کاهش شفافیت بدون دست‌زدن به کش
            tmp = glow.copy()
            tmp.set_alpha(alpha)
            surface.blit(tmp, (self.x - r, self.y - r),
                         special_flags=pygame.BLEND_RGBA_ADD)

    @staticmethod
    def _draw_line_alpha(
        surface: pygame.Surface,
        color: tuple[int, int, int, int],
        p1: tuple[float, float],
        p2: tuple[float, float],
        width: int,
    ) -> None:
        """رسم خط با شفافیت، چون pygame.draw.line آلفا را نادیده می‌گیرد."""
        x1, y1 = int(p1[0]), int(p1[1])
        x2, y2 = int(p2[0]), int(p2[1])
        # کوتاه‌ترین مسیر
        length = max(abs(x2 - x1), abs(y2 - y1), 1)
        if length > 64:
            # خط خیلی بلند، ساده‌سازی با خط تک‌رنگ
            pygame.draw.line(surface, color[:3], (x1, y1), (x2, y2), width)
            return
        tmp = pygame.Surface((abs(x2 - x1) + width * 2 + 2,
                              abs(y2 - y1) + width * 2 + 2), pygame.SRCALPHA)
        ox = min(x1, x2) - width
        oy = min(y1, y2) - width
        pygame.draw.line(
            tmp, color,
            (x1 - ox, y1 - oy),
            (x2 - ox, y2 - oy),
            width,
        )
        surface.blit(tmp, (ox, oy))

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌های منطقی
    # ─────────────────────────────────────────────────────────────────────

    def deals_damage_to(self, entity: Entity) -> bool:
        """آیا این گلوله به موجودیت داده‌شده آسیب می‌زند؟ (بر اساس friendly)"""
        if not self.friendly:
            # گلوله‌ی دشمن به پلیر آسیب می‌زند، نه به دشمن‌ها
            from entities.player import Player
            return isinstance(entity, Player)
        else:
            # گلوله‌ی پلیر به دشمن‌ها آسیب می‌زند
            from entities.player import Player
            return not isinstance(entity, Player)

    def consume_hit(self) -> bool:
        """
        پس از برخورد با یک هدف، Pierce را کم می‌کند.
        اگر Pierce تمام شود، گلوله نابود می‌شود و True برمی‌گرداند.
        """
        if self.pierce <= 0:
            self.kill()
            return True
        self.pierce -= 1
        return False


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس Bomb — گلوله‌ی بمب با ظاهر و انفجار اختصاصی
# ═══════════════════════════════════════════════════════════════════════════

class Bomb(Bullet):
    """بمب Bombardier — آروم، درخشان، با فیوز و انفجار."""

    def __init__(self, x, y, vx=0, vy=100, *, scene=None):
        super().__init__(
            x, y, vx, vy,
            friendly=False,
            kind=BulletKind.ENEMY,
            scene=scene,
            life=4.0,
        )
        self._bomb_age = 0.0
        self._bomb_rotation = 0.0

    def update_entity(self, dt: float) -> None:
        super().update_entity(dt)
        self._bomb_age += dt
        self._bomb_rotation += dt * 3.0

    def draw_entity(self, surface: pygame.Surface) -> None:
        # ---- محاسبه‌ی alpha (نزدیک انفجار قرمزتر می‌شه) ----
        warn = min(1.0, self._bomb_age / 3.0)
        pulse = 0.5 + 0.5 * math.sin(self._bomb_age * 15)

        cx, cy = self.pos_int

        # ---- هاله‌ی نارنجی بزرگ ----
        glow_r = int(14 + 8 * pulse * warn)
        for rr in range(glow_r, 0, -2):
            a = int(120 * (1 - rr / glow_r) * (0.5 + warn * 0.5))
            if a > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 150, 60, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, cy - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # ---- بدنه‌ی بمب (بیضی چرخان) ----
        body_r = 8
        # سایه
        pygame.draw.circle(surface, (20, 20, 30), (cx + 1, cy + 1), body_r)
        # بدنه
        pygame.draw.circle(surface, (40, 40, 55), (cx, cy), body_r)
        # حلقه‌ی روشن
        pygame.draw.circle(surface, (255, 130, 40), (cx, cy), body_r, 2)
        # خط عمودی روی بمب (شکاف)
        pygame.draw.line(surface, (255, 200, 100),
                         (cx, cy - body_r + 2), (cx, cy + body_r - 2), 1)

        # ---- فیوز بالای بمب (با جرقه) ----
        fuse_y = cy - body_r - 4
        pygame.draw.line(surface, (100, 100, 80),
                         (cx, cy - body_r), (cx, fuse_y), 2)

        # جرقه‌ی فیوز (رنگ با پالس)
        spark_r = int(2 + 2 * pulse)
        spark_color = (255, int(180 + 75 * pulse), int(80 + 100 * pulse))
        for rr in range(spark_r * 3, 0, -1):
            a = int(200 * (1 - rr / (spark_r * 3)))
            if a > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (*spark_color, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, fuse_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, spark_color, (cx, fuse_y), spark_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, fuse_y), max(1, spark_r // 2))

        # ---- نشانگر انفجار نزدیک ----
        if warn > 0.7:
            progress = (warn - 0.7) / 0.3
            ring_r = int(15 + progress * 10)
            pygame.draw.circle(surface, (255, 80, 40),
                               (cx, cy), ring_r, 2)

    def on_death(self) -> None:
        """انفجار بمب هنگام از بین رفتن."""
        if self.scene is not None:
            try:
                from systems.particles import ParticleKind
                # ذرات انفجار نارنجی
                self.scene.particles.emit_burst(
                    self.x, self.y,
                    count=18,
                    color_start=(255, 240, 180),
                    color_end=(255, 60, 20),
                    speed_min=100, speed_max=320,
                    life_min=0.3, life_max=0.7,
                    size_min=2, size_max=5,
                    kind=ParticleKind.SPARK,
                    additive=True,
                )
                # حلقه‌ی انفجار
                self.scene.particles.emit_ring(
                    self.x, self.y,
                    count=14, radius=6, speed=240,
                    color=(255, 180, 80), life=0.4, size=2,
                )
            except Exception:
                pass


__all__ = ["Bullet", "BulletKind", "Bomb"]