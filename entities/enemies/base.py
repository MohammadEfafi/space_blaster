"""
entities/enemies/base.py
========================

کلاس پایه‌ی تمام دشمن‌ها (Enemy Base Class).

این ماژول شامل:

    • EnemyKind   — Enum انواع دشمن برای انتخاب در Factory
    • Enemy       — کلاس پایه با منطق مشترک تمام دشمن‌ها

منطق مشترک کلاس پایه:
    • انیمیشن ورود (fade-in + fly-in نرم)
    • حرکت پیش‌فرض به سمت پایین
    • شلیک برنامه‌ریزی‌شده (اختیاری — با SHOOT_CD)
    • حذف خودکار وقتی از پایین صفحه خارج شد
    • امتیاز و شانس افت پاورآپ در مرگ
    • فلاش روی ضربه (ارثی از Entity)

زیرکلاس‌ها فقط این‌ها را Override می‌کنند:
    _configure()      — مقداردهی اولیه‌ی پارامترهای اختصاصی
    update_ai(dt)     — منطق حرکت اختصاصی
    draw_body(surf)   — رسم ظاهر اختصاصی
"""

from __future__ import annotations

import math
import random
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

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
    BOSS   = auto()
    SPECTER = auto()
    BOMBARDIER = auto()
    SENTINEL = auto()
    SERPENT = auto()
    TITAN = auto()


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس پایه‌ی Enemy
# ═══════════════════════════════════════════════════════════════════════════

class Enemy(Entity):
    """
    کلاس پایه‌ی تمام دشمن‌ها.

    برای ساختن دشمن جدید:
        ①  این کلاس را ارث‌بری کن
        ②  KIND، HP، RADIUS، SPEED، SCORE و BODY_COLOR را ست کن
        ③  update_ai() و draw_body() را در صورت نیاز Override کن
        ④  دشمن را به EnemyFactory اضافه کن
    """

    # ---- برای Factory / Registry ----
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
        super().__init__(
            x, y,
            vx=0.0,
            vy=0.0,
            radius=self.RADIUS,
            hp=self.HP,
            scene=scene,
        )

        # ---- انیمیشن ورود ----
        self._entry_elapsed: float = 0.0
        self._entry_done: bool = False
        self._entry_start_x: float = x
        self._entry_start_y: float = y
        if target_y is None:
            target_y = y
        self._entry_target_y: float = target_y

        # ---- الگوی حرکت ----
        self._t: float = 0.0
        self._base_x: float = x          # برای الگوهای سینوسی
        self._vy: float = self.SPEED

        # ---- شلیک ----
        self._shoot_timer: float = self.SHOOT_CD
        if self.SHOOT_CD > 0:
            # تاخیر اولیه‌ی تصادفی تا دشمن‌ها همزمان شلیک نکنند
            self._shoot_timer = self.SHOOT_CD * random.uniform(0.5, 1.2)

        # ---- پاداش ----
        self.score_value: int = self.SCORE
        self.drop_chance: float = self.DROP_CHANCE

        # ---- اجازه‌ی تنظیمات اختصاصی زیرکلاس ----
        self._configure()

    # ─────────────────────────────────────────────────────────────────────
    #  هوک‌های قابل Override
    # ─────────────────────────────────────────────────────────────────────

    def _configure(self) -> None:
        """زیرکلاس‌ها پارامترهای اختصاصی خود را اینجا تنظیم می‌کنند."""
        pass

    def update_ai(self, dt: float) -> None:
        """منطق حرکت اختصاصی. پیش‌فرض: حرکت مستقیم به پایین."""
        self.y += self._vy * dt

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        """
        رسم بدنه. زیرکلاس‌ها Override می‌کنند.
        پیش‌فرض: یک مثلث ساده رو به پایین.
        """
        r = int(self.radius)
        cx, cy = int(self.x), int(self.y)
        color = self.tint(self.BODY_COLOR) if alpha >= 250 else self.BODY_COLOR
        pts = [(cx, cy + r), (cx - r, cy - r), (cx + r, cy - r)]
        pygame.draw.polygon(surface, color, pts)

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update_entity(self, dt: float) -> None:
        self._t += dt

        # ---- انیمیشن ورود ----
        if not self._entry_done:
            self._entry_elapsed += dt
            t = min(1.0, self._entry_elapsed / self.ENTRY_TIME)
            # easing: ease-out quadratic
            te = 1.0 - (1.0 - t) * (1.0 - t)
            self.y = self._entry_start_y + (self._entry_target_y - self._entry_start_y) * te
            if t >= 1.0:
                self._entry_done = True
            # در حین ورود، شلیک نمی‌کند
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
        """شلیک یک گلوله به سمت پلیر. زیرکلاس‌ها می‌توانند Override کنند."""
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
        """انفجار + امتیاز + احتمال افت پاورآپ + لرزش دوربین."""
        if self.scene is None:
            return
        try:
            self.scene.spawn_enemy_explosion(
                self.x, self.y, self.radius, self.BODY_COLOR,
            )
            self.scene.add_score(self.score_value)
            if random.random() < self.drop_chance:
                self.scene.spawn_powerup(self.x, self.y)
            self.scene.audio.play("enemy_explode")
            self.scene.camera.shake(S.FxCfg.SHAKE_ON_KILL * 0.6)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    #  رسم
    # ─────────────────────────────────────────────────────────────────────

    def draw_entity(self, surface: pygame.Surface) -> None:
        """پوسته‌ی رسم — محاسبه‌ی alpha ورود و پاس دادن به زیرکلاس."""
        if not self._entry_done:
            t = min(1.0, self._entry_elapsed / self.ENTRY_TIME)
            alpha = int(60 + 195 * t)
        else:
            alpha = 255

        self.draw_body(surface, alpha)

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌ها
    # ─────────────────────────────────────────────────────────────────────

    def set_entry(self, start_y: float, target_y: float) -> None:
        """پیکربندی انیمیشن ورود (توسط Factory استفاده می‌شود)."""
        self.y = start_y
        self._entry_start_y = start_y
        self._entry_target_y = target_y
        self._entry_elapsed = 0.0
        self._entry_done = False


    # ─────────────────────────────────────────────────────────────────────
    #  Helpers مشترک (که قبلاً در ۸ زیرکلاس تکرار شده بودن)
    # ─────────────────────────────────────────────────────────────────────

    def _apply_fade(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        alpha: int,
    ) -> None:
        """محو کردن بدنه با یک مربع نیمه‌شفاف سیاه (برای انیمیشن ورود)."""
        a = 255 - alpha
        if a <= 0:
            return
        fade = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        fade.fill((0, 0, 0, int(a * 0.7)))
        surface.blit(fade, (cx - r * 2, cy - r * 2))

    @staticmethod
    def _darker(c: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
        return (
            max(0, c[0] - amount),
            max(0, c[1] - amount),
            max(0, c[2] - amount),
        )

    @staticmethod
    def _lighter(c: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
        return (
            min(255, c[0] + amount),
            min(255, c[1] + amount),
            min(255, c[2] + amount),
        )

__all__ = ["Enemy", "EnemyKind"]