"""
entities/enemy.py
=================

سیستم دشمن‌ها (Enemies) برای SPACE BLASTER.

این ماژول شامل:

    • Enemy            — کلاس پایه با منطق مشترک (ورود، آسیب، فلاش، مرگ)
    • NormalEnemy      — دشمن سبک و سریع، بدون شلیک
    • TankEnemy        — دشمن سنگین که به سمت پلیر شلیک می‌کند
    • SpiralEnemy      — دشمن مارپیچ با حرکت سینوسی
    • EnemyFactory     — ساخت دشمن مناسب بر اساس شماره‌ی موج

طراحی:
    کلاس پایه تمام منطق مشترک را دارد. هر زیرکلاس فقط روی ظاهر و
    رفتار اختصاصی خودش تمرکز می‌کند. برای اضافه کردن Boss یا دشمن
    جدید، فقط یک زیرکلاس تازه + یک ورودی در Factory کافی است.

نکته‌ی مهم:
    دشمن‌ها هنگام spawn یک انیمیشن ورود (fade + fly-in) دارند تا
    ظاهر شدن‌شان ناگهانی و بی‌روح نباشد.
"""

from __future__ import annotations

import math
import random
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable, Optional

import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.entity import Entity

if TYPE_CHECKING:
    from scenes.gameplay import GameplayScene


# ═══════════════════════════════════════════════════════════════════════════
#  انواع دشمن
# ═══════════════════════════════════════════════════════════════════════════

class EnemyKind(Enum):
    NORMAL = auto()
    TANK   = auto()
    SPIRAL = auto()


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس پایه‌ی Enemy
# ═══════════════════════════════════════════════════════════════════════════

class Enemy(Entity):
    """
    کلاس پایه‌ی تمام دشمن‌ها.

    منطق مشترک:
        • انیمیشن ورود (fade-in + حرکت به موقعیت هدف)
        • حرکت به سمت پایین صفحه
        • شلیک برنامه‌ریزی‌شده (اختیاری — با shoot_cd)
        • حذف خودکار وقتی از پایین صفحه خارج شود
        • امتیاز و شانس افت پاورآپ
        • فلاش روی ضربه (از Entity به ارث می‌رسد)

    زیرکلاس‌ها فقط این‌ها را Override می‌کنند:
        _configure()      — مقداردهی اولیه‌ی پارامترها
        update_ai(dt)     — منطق حرکت اختصاصی (اختیاری)
        draw_body(surf)   — رسم ظاهر اختصاصی
    """

    # ---- برای Factory ----
    KIND: EnemyKind = EnemyKind.NORMAL

    # ---- پیکربندی پیش‌فرض (در زیرکلاس بازنویسی می‌شود) ----
    HP:           int   = 1
    RADIUS:       float = 14.0
    SPEED:        float = 130.0
    SCORE:        int   = 10
    DROP_CHANCE:  float = 0.05
    ENTRY_TIME:   float = 0.55      # ثانیه — انیمیشن ورود
    SHOOT_CD:     float = 0.0       # 0 = بدون شلیک
    BULLET_SPEED: float = 260.0
    BODY_COLOR:   tuple[int, int, int] = S.Palette.ENEMY_NORMAL

    # ─────────────────────────────────────────────────────────────────────
    #  سازنده
    # ─────────────────────────────────────────────────────────────────────

    def __init__(
        self,
        x: float,
        y: float,
        scene: Optional["GameplayScene"] = None,
        *,
        target_y: Optional[float] = None,
    ) -> None:
        # موقعیت و مشخصات از روی پیکربندی کلاس
        super().__init__(
            x, y,
            vx=0.0,
            vy=0.0,
            radius=self.RADIUS,
            hp=self.HP,
            scene=scene,
        )

        # ---- هدف ورود ----
        self._entry_elapsed: float = 0.0
        self._entry_done: bool = False
        # موقعیت اولیه برای درون‌یابی ورود
        self._entry_start_x: float = x
        self._entry_start_y: float = y

        # در صورت نبود target_y، از موقعیت فعلی استفاده می‌شود
        # در این حالت دشمن از بالا ظاهر می‌شود و به آرامی وارد می‌شود
        if target_y is None:
            target_y = y
        self._entry_target_y: float = target_y

        # ---- الگوی حرکت ----
        self._t: float = 0.0
        self._base_x: float = x          # برای Spiral
        self._vy: float = self.SPEED

        # ---- شلیک ----
        self._shoot_timer: float = self.SHOOT_CD
        # مقداری تصادفی برای اینکه دشمن‌ها همزمان شلیک نکنند
        if self.SHOOT_CD > 0:
            self._shoot_timer = self.SHOOT_CD * random.uniform(0.5, 1.2)

        # ---- پاداش ----
        self.score_value: int = self.SCORE
        self.drop_chance: float = self.DROP_CHANCE

        # ---- اجازه‌ی تنظیمات اختصاصی در زیرکلاس ----
        self._configure()

    # ─────────────────────────────────────────────────────────────────────
    #  هوک‌های قابل Override
    # ─────────────────────────────────────────────────────────────────────

    def _configure(self) -> None:
        """زیرکلاس‌ها می‌توانند پارامترهای اختصاصی خود را اینجا تنظیم کنند."""
        pass

    def update_ai(self, dt: float) -> None:
        """منطق حرکت اختصاصی. پیش‌فرض: حرکت مستقیم به پایین."""
        self.y += self._vy * dt

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        """رسم بدنه. زیرکلاس‌ها Override می‌کنند."""
        # پیش‌فرض: یک مثلث ساده
        r = self.radius
        cx, cy = self.pos_int
        pts = [(cx, cy + r), (cx - r, cy - r), (cx + r, cy - r)]
        color = self.tint(self.BODY_COLOR) if alpha >= 250 else self.BODY_COLOR
        if alpha >= 250:
            pygame.draw.polygon(surface, color, pts)
        else:
            tmp = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
            local = [(r + r // 2, r * 2), (r // 2, 0), (r + r * 2, 0)]
            pygame.draw.polygon(tmp, (*color, alpha), local)
            surface.blit(tmp, (cx - r - r // 2, cy - r))

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update_entity(self, dt: float) -> None:
        self._t += dt

        # ---- انیمیشن ورود ----
        if not self._entry_done:
            self._entry_elapsed += dt
            t = min(1.0, self._entry_elapsed / self.ENTRY_TIME)
            # easing (ساده و نرم): ease-out quadratic
            te = 1.0 - (1.0 - t) * (1.0 - t)
            self.y = self._entry_start_y + (self._entry_target_y - self._entry_start_y) * te
            if t >= 1.0:
                self._entry_done = True
            # در حین ورود، شلیک نمی‌کند و بیرون نمی‌رود
            return

        # ---- حرکت اختصاصی ----
        self.update_ai(dt)

        # ---- شلیک ----
        if self.SHOOT_CD > 0.0 and self.scene is not None:
            self._shoot_timer -= dt
            if self._shoot_timer <= 0.0:
                self._shoot_timer = self.SHOOT_CD * random.uniform(0.85, 1.15)
                self._do_shoot()

        # ---- حذف خودکار وقتی از پایین خارج شد ----
        if self.y > S.Window.HEIGHT + self.radius + 30:
            self.alive = False
            self._pending_kill = True

    # ── شلیک به سمت پلیر ──
    def _do_shoot(self) -> list[Bullet]:
        if self.scene is None:
            return []
        player = getattr(self.scene, "player", None)
        if player is None or not player.alive:
            return []
        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        vx = (dx / d) * self.BULLET_SPEED
        vy = (dy / d) * self.BULLET_SPEED

        bullet = Bullet(
            self.x, self.y + self.radius * 0.6,
            vx, vy,
            friendly=False,
            kind=BulletKind.ENEMY,
            scene=self.scene,
        )
        try:
            self.scene.spawn_bullet(bullet)
            self.scene.audio.play("enemy_shoot")
        except Exception:
            pass
        return [bullet]

    # ─────────────────────────────────────────────────────────────────────
    #  مرگ و آسیب
    # ─────────────────────────────────────────────────────────────────────

    def on_death(self) -> None:
        """انفجار + احتمال افت پاورآپ."""
        if self.scene is None:
            return
        try:
            self.scene.spawn_enemy_explosion(
                self.x, self.y, self.radius, self.BODY_COLOR
            )
            # امتیاز
            self.scene.add_score(self.score_value)
            # احتمال افت پاورآپ
            if random.random() < self.drop_chance:
                self.scene.spawn_powerup(self.x, self.y)
            # صدای انفجار
            self.scene.audio.play("enemy_explode")
            # لرزش کوچک
            self.scene.camera.shake(S.FxCfg.SHAKE_ON_KILL * 0.6)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    #  رسم
    # ─────────────────────────────────────────────────────────────────────

    def draw_entity(self, surface: pygame.Surface) -> None:
        # اگر در حین ورود است، شفافیت را کم کن
        if not self._entry_done:
            t = min(1.0, self._entry_elapsed / self.ENTRY_TIME)
            alpha = int(60 + 195 * t)
        else:
            alpha = 255

        # هاله‌ی glow (با flash ترکیب می‌شود)
        self._draw_glow(surface)

        # بدنه (زیرکلاس می‌کشد)
        self.draw_body(surface, alpha)

    def _draw_glow(self, surface: pygame.Surface) -> None:
        """هاله‌ی نرم پشت دشمن."""
        r = int(self.radius * 1.9)
        if r < 2:
            return
        glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        base = self.tint(self.BODY_COLOR)
        for rr in range(r, 0, -2):
            a = int(50 * (1 - rr / r))
            pygame.draw.circle(glow, (*base, a), (r, r), rr)
        surface.blit(glow, (self.x - r, self.y - r),
                     special_flags=pygame.BLEND_RGBA_ADD)

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌ها
    # ─────────────────────────────────────────────────────────────────────

    def set_entry(self, start_y: float, target_y: float) -> None:
        """پیکربندی انیمیشن ورود."""
        self.y = start_y
        self._entry_start_y = start_y
        self._entry_target_y = target_y
        self._entry_elapsed = 0.0
        self._entry_done = False


# ═══════════════════════════════════════════════════════════════════════════
#  دشمن ① — Normal (سریع، شکننده)
# ═══════════════════════════════════════════════════════════════════════════

class NormalEnemy(Enemy):
    """
    دشمن سبک با شکل مثلثی ساده.
    سریع حرکت می‌کند و با یک ضربه نابود می‌شود.
    """

    KIND = EnemyKind.NORMAL

    HP           = S.EnemyCfg.Normal.HP
    RADIUS       = S.EnemyCfg.Normal.RADIUS
    SPEED        = S.EnemyCfg.Normal.SPEED
    SCORE        = S.EnemyCfg.Normal.SCORE
    DROP_CHANCE  = S.EnemyCfg.Normal.DROP_CHANCE
    BODY_COLOR   = S.Palette.ENEMY_NORMAL

    def update_ai(self, dt: float) -> None:
        self.y += self.SPEED * dt

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = self.radius
        cx, cy = self.x, self.y
        color = self.tint(self.BODY_COLOR)

        pts_outer = [
            (cx, cy + r),           # نوک پایین (به سمت پلیر)
            (cx - r, cy - r * 0.6),
            (cx - r * 0.5, cy - r),
            (cx + r * 0.5, cy - r),
            (cx + r, cy - r * 0.6),
        ]
        pts_inner = [
            (cx, cy + r * 0.4),
            (cx - r * 0.55, cy - r * 0.35),
            (cx + r * 0.55, cy - r * 0.35),
        ]

        if alpha >= 250:
            pygame.draw.polygon(surface, color, pts_outer)
            pygame.draw.polygon(surface, S.Palette.WHITE, pts_outer, 1)
            pygame.draw.polygon(surface, (255, 240, 240), pts_inner)
            # چشم
            pygame.draw.circle(surface, S.Palette.BLACK, (int(cx), int(cy - r * 0.4)), 2)
        else:
            self._draw_with_alpha(surface, pts_outer, pts_inner, color, alpha)

    def _draw_with_alpha(
        self,
        surface: pygame.Surface,
        outer: list[tuple[float, float]],
        inner: list[tuple[float, float]],
        color: tuple[int, int, int],
        alpha: int,
    ) -> None:
        # رسم با آلفا روی سطح موقت
        r = int(self.radius * 2.5)
        tmp = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        ox = self.x - r
        oy = self.y - r
        local_outer = [(p[0] - ox, p[1] - oy) for p in outer]
        local_inner = [(p[0] - ox, p[1] - oy) for p in inner]
        pygame.draw.polygon(tmp, (*color, alpha), local_outer)
        pygame.draw.polygon(tmp, (255, 255, 255, alpha), local_outer, 1)
        pygame.draw.polygon(tmp, (255, 240, 240, alpha), local_inner)
        surface.blit(tmp, (ox, oy))


# ═══════════════════════════════════════════════════════════════════════════
#  دشمن ② — Tank (سنگین، شلیک‌کننده)
# ═══════════════════════════════════════════════════════════════════════════

class TankEnemy(Enemy):
    """
    دشمن سنگین با چند HP.
    به سمت پلیر شلیک می‌کند و کندتر حرکت می‌کند.
    """

    KIND = EnemyKind.TANK

    HP           = S.EnemyCfg.Tank.HP
    RADIUS       = S.EnemyCfg.Tank.RADIUS
    SPEED        = S.EnemyCfg.Tank.SPEED
    SCORE        = S.EnemyCfg.Tank.SCORE
    DROP_CHANCE  = S.EnemyCfg.Tank.DROP_CHANCE
    SHOOT_CD     = S.EnemyCfg.Tank.SHOOT_CD
    BULLET_SPEED = S.EnemyCfg.Tank.BULLET_SPEED
    BODY_COLOR   = S.Palette.ENEMY_TANK

    def update_ai(self, dt: float) -> None:
        self.y += self.SPEED * dt
        # کمی نوسان افقی برای زنده‌تر شدن
        self.x = self._base_x + math.sin(self._t * 0.9) * 12.0

    def _do_shoot(self) -> list[Bullet]:
        """Tank دو گلوله‌ی موازی شلیک می‌کند."""
        if self.scene is None:
            return []
        player = getattr(self.scene, "player", None)
        if player is None or not player.alive:
            return []
        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        # عمود بر جهت
        px, py = -uy, ux

        bullets: list[Bullet] = []
        for side in (-1.0, 1.0):
            bx = self.x + px * 8 * side
            by = self.y + py * 8 * side
            b = Bullet(
                bx, by,
                ux * self.BULLET_SPEED, uy * self.BULLET_SPEED,
                friendly=False,
                kind=BulletKind.ENEMY,
                scene=self.scene,
            )
            bullets.append(b)
        try:
            for b in bullets:
                self.scene.spawn_bullet(b)
            self.scene.audio.play("enemy_shoot")
        except Exception:
            pass
        return bullets

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = self.radius
        cx, cy = self.x, self.y
        color = self.tint(self.BODY_COLOR)

        # بدنه‌ی شش‌ضلعی
        pts_hex = []
        for i in range(6):
            a = math.pi / 3 * i - math.pi / 2
            pts_hex.append((cx + math.cos(a) * r, cy + math.sin(a) * r))

        # لایه‌ی بیرونی
        pygame.draw.polygon(surface, color, pts_hex)
        pygame.draw.polygon(surface, S.Palette.WHITE, pts_hex, 2)

        # دایره‌ی میانی
        pygame.draw.circle(surface, S.Palette.WHITE, (int(cx), int(cy)), int(r * 0.55))
        pygame.draw.circle(surface, color, (int(cx), int(cy)), int(r * 0.42))

        # چشم مرکزی (با تپش)
        pulse = 2 + int(1.5 * math.sin(self._t * 6.0))
        pygame.draw.circle(surface, S.Palette.RED, (int(cx), int(cy)), 2 + pulse, 1)

        # ----- نوار HP روی دشمن -----
        if self.max_hp > 1 and self.hp < self.max_hp:
            self._draw_hp_bar(surface, cx, cy - r - 8)

    def _draw_hp_bar(self, surface: pygame.Surface, cx: float, cy: float) -> None:
        w = int(self.radius * 2)
        h = 3
        x = int(cx - w / 2)
        y = int(cy)
        pygame.draw.rect(surface, (40, 10, 40), (x, y, w, h))
        ratio = self.hp / self.max_hp
        color = S.Palette.HUD_HP if ratio > 0.34 else S.Palette.YELLOW
        pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
        pygame.draw.rect(surface, S.Palette.WHITE, (x, y, w, h), 1)


# ═══════════════════════════════════════════════════════════════════════════
#  دشمن ③ — Spiral (مسیر سینوسی)
# ═══════════════════════════════════════════════════════════════════════════

class SpiralEnemy(Enemy):
    """
    دشمن با حرکت مارپیچ (سینوسی).
    غیرقابل پیش‌بینی و چالش‌برانگیز.
    """

    KIND = EnemyKind.SPIRAL

    HP           = S.EnemyCfg.Spiral.HP
    RADIUS       = S.EnemyCfg.Spiral.RADIUS
    SPEED        = S.EnemyCfg.Spiral.SPEED
    SCORE        = S.EnemyCfg.Spiral.SCORE
    DROP_CHANCE  = S.EnemyCfg.Spiral.DROP_CHANCE
    AMPLITUDE    = S.EnemyCfg.Spiral.AMPLITUDE
    FREQUENCY    = S.EnemyCfg.Spiral.FREQUENCY
    BODY_COLOR   = S.Palette.ENEMY_SPIRAL

    def _configure(self) -> None:
        self._phase = random.uniform(0, math.tau)

    def update_ai(self, dt: float) -> None:
        self.y += self.SPEED * dt
        self.x = self._base_x + math.sin(self._t * self.FREQUENCY + self._phase) * self.AMPLITUDE
        # زاویه‌ی چرخش برای افکت بصری
        self.angle = self._t * 180.0

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = self.radius
        cx, cy = self.x, self.y
        color = self.tint(self.BODY_COLOR)

        # بدنه‌ی ستاره‌ای شکل (شش‌پر) با چرخش
        pts_outer = []
        pts_inner = []
        for i in range(6):
            a_out = self.angle * math.pi / 180 + i * math.pi / 3
            a_in = a_out + math.pi / 6
            pts_outer.append((cx + math.cos(a_out) * r, cy + math.sin(a_out) * r))
            pts_inner.append((cx + math.cos(a_in) * r * 0.45, cy + math.sin(a_in) * r * 0.45))

        # ترکیب دو آرایه
        star_pts = []
        for i in range(6):
            star_pts.append(pts_outer[i])
            star_pts.append(pts_inner[i])

        pygame.draw.polygon(surface, color, star_pts)
        pygame.draw.polygon(surface, S.Palette.WHITE, star_pts, 1)

        # مرکز روشن
        pygame.draw.circle(surface, S.Palette.WHITE, (int(cx), int(cy)), 3)
        pygame.draw.circle(surface, S.Palette.GREEN, (int(cx), int(cy)), 2)

        # ذرات دنباله (اختیاری، سبک)
        # اینجا انجام نمی‌شود تا perf حفظ شود؛ scene خودش می‌تواند
        # بر اساس نوع دشمن ذره spawn کند.


# ═══════════════════════════════════════════════════════════════════════════
#  Factory — ساخت دشمن بر اساس موج
# ═══════════════════════════════════════════════════════════════════════════

class EnemyFactory:
    """
    کارخانه‌ی ساخت دشمن.

    بر اساس شماره‌ی موج، یک توزیع احتمال انتخاب می‌کند و دشمن مناسب
    را با موقعیت تصادفی بالای صفحه می‌سازد و انیمیشن ورودش را تنظیم
    می‌کند.

    استفاده:
        factory = EnemyFactory(scene)
        enemy = factory.spawn(wave=3)
    """

    # نگاشت وزن موج → توزیع انواع دشمن
    # (Normal, Tank, Spiral)
    _WAVES: list[tuple[int, tuple[int, int, int]]] = [
        (1, S.WaveCfg.WEIGHTS_WAVE_1),
        (2, S.WaveCfg.WEIGHTS_WAVE_2),
        (3, S.WaveCfg.WEIGHTS_WAVE_3),
        (4, S.WaveCfg.WEIGHTS_LATE),
        (5, S.WaveCfg.WEIGHTS_LATE),
    ]

    _KIND_MAP: dict[EnemyKind, type[Enemy]] = {
        EnemyKind.NORMAL: NormalEnemy,
        EnemyKind.TANK:   TankEnemy,
        EnemyKind.SPIRAL: SpiralEnemy,
    }

    def __init__(self, scene: Optional["GameplayScene"] = None) -> None:
        self.scene = scene

    # ─────────────────────────────────────────────────────────────────────

    def _weights_for_wave(self, wave: int) -> tuple[int, int, int]:
        """وزن‌ها را بر اساس موج برمی‌گرداند. برای موج‌های بالا، last استفاده می‌شود."""
        result = S.WaveCfg.WEIGHTS_WAVE_1
        for min_wave, weights in self._WAVES:
            if wave >= min_wave:
                result = weights
            else:
                break
        return result

    def _choose_kind(self, wave: int) -> EnemyKind:
        w = self._weights_for_wave(wave)
        # اگر همه‌ی وزن‌ها صفر باشند، به Normal fallback کن
        if sum(w) == 0:
            return EnemyKind.NORMAL
        kinds = [EnemyKind.NORMAL, EnemyKind.TANK, EnemyKind.SPIRAL]
        chosen = random.choices(kinds, weights=w, k=1)[0]
        return chosen

    # ─────────────────────────────────────────────────────────────────────

    def spawn(
        self,
        wave: int,
        *,
        x: Optional[float] = None,
        kind: Optional[EnemyKind] = None,
    ) -> Enemy:
        """
        یک دشمن جدید می‌سازد و برمی‌گرداند.
        انتخاب نوع بر اساس موج، مگر اینکه kind صریحاً داده شود.
        """
        if kind is None:
            kind = self._choose_kind(wave)

        # موقعیت افقی
        margin = S.WaveCfg.ENEMY_MARGIN
        if x is None:
            x = random.uniform(margin, S.Window.WIDTH - margin)

        # موقعیت عمودی شروع (بالای صفحه)
        start_y = random.uniform(S.WaveCfg.SPAWN_Y_MIN, S.WaveCfg.SPAWN_Y_MAX)
        # موقعیت هدف ورود: کمی پایین‌تر از بالای صفحه
        target_y = random.uniform(-10, 40)

        cls = self._KIND_MAP.get(kind, NormalEnemy)
        enemy = cls(x, start_y, scene=self.scene)
        enemy.set_entry(start_y, target_y)
        return enemy

    def spawn_batch(self, wave: int, count: int) -> list[Enemy]:
        """چند دشمن برای یک موج می‌سازد."""
        return [self.spawn(wave) for _ in range(count)]


__all__ = [
    "Enemy", "EnemyKind",
    "NormalEnemy", "TankEnemy", "SpiralEnemy",
    "EnemyFactory",
]