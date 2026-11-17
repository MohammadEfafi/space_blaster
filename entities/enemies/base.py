
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


# انواع دشمن برای شناسایی و انتخاب در سیستم Factory
# Enemy types used for identification and selection in the factory system
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


# کلاس پایه‌ی تمام دشمن‌ها و محل تعریف رفتارهای مشترک آن‌ها
# Base class for all enemies and the central definition of their shared behavior
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
    # نوع دشمن برای شناسایی و ثبت در سیستم Factory
    # Enemy type used for identification and registration in the factory system
    KIND: EnemyKind = EnemyKind.NORMAL

    # ---- پیکربندی پیش‌فرض (در زیرکلاس بازنویسی می‌شود) ----
    # مقادیر پیش‌فرضی که زیرکلاس‌ها می‌توانند بازنویسی کنند
    # Default values that subclasses can override
    HP:           int   = 1
    RADIUS:       float = 14.0
    SPEED:        float = 130.0
    SCORE:        int   = 10
    DROP_CHANCE:  float = 0.05
    ENTRY_TIME:   float = 0.55      # ثانیه — انیمیشن ورود
    SHOOT_CD:     float = 0.0       # 0 = بدون شلیک
    BULLET_SPEED: float = 260.0
    BODY_COLOR:   tuple[int, int, int] = S.Palette.ENEMY_NORMAL

    # سازنده و مقداردهی اولیه‌ی وضعیت اختصاصی هر دشمن
    # Constructor and initialization of each enemy's individual state
    def __init__(
        self,
        x: float,
        y: float,
        scene: Optional["GameplayScene"] = None,
        *,
        target_y: Optional[float] = None,
    ) -> None:
        # مقداردهی ویژگی‌های پایه از طریق کلاس والد
        # Initialize the base attributes through the parent class
        super().__init__(
            x, y,
            vx=0.0,
            vy=0.0,
            radius=self.RADIUS,
            hp=self.HP,
            scene=scene,
        )

        # ---- انیمیشن ورود ----
        # نگهداری وضعیت و مختصات موردنیاز برای انیمیشن ورود
        # Store the state and coordinates required for the entry animation
        self._entry_elapsed: float = 0.0
        self._entry_done: bool = False
        self._entry_start_x: float = x
        self._entry_start_y: float = y
        if target_y is None:
            target_y = y
        self._entry_target_y: float = target_y

        # ---- الگوی حرکت ----
        # متغیرهای زمانی و مکانی موردنیاز برای الگوهای حرکتی
        # Time and position variables required by movement patterns
        self._t: float = 0.0
        self._base_x: float = x          # برای الگوهای سینوسی
        self._vy: float = self.SPEED

        # ---- شلیک ----
        # مقداردهی زمان‌سنج شلیک با تأخیر اولیه‌ی تصادفی
        # Initialize the shooting timer with a randomized initial delay
        self._shoot_timer: float = self.SHOOT_CD
        if self.SHOOT_CD > 0:
            # تاخیر اولیه‌ی تصادفی تا دشمن‌ها همزمان شلیک نکنند
            self._shoot_timer = self.SHOOT_CD * random.uniform(0.5, 1.2)

        # ---- پاداش ----
        # ذخیره‌ی امتیاز و احتمال افت پاورآپ برای زمان نابودی دشمن
        # Store the score and power-up drop probability for enemy destruction
        self.score_value: int = self.SCORE
        self.drop_chance: float = self.DROP_CHANCE

        # ---- اجازه‌ی تنظیمات اختصاصی زیرکلاس ----
        # اجرای هوک تنظیمات اختصاصی زیرکلاس
        # Execute the subclass-specific configuration hook
        self._configure()

    # ---- هوک‌های قابل Override ----
    # نقاط توسعه‌ای که زیرکلاس‌ها می‌توانند متناسب با رفتار خود بازنویسی کنند
    # Extension hooks that subclasses can override for their specific behavior
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

    # به‌روزرسانی وضعیت و اجرای منطق اصلی دشمن
    # Update the enemy state and execute its main behavior
    def update_entity(self, dt: float) -> None:
        self._t += dt

        # ---- انیمیشن ورود ----
        # محاسبه‌ی پیشرفت انیمیشن و حرکت نرم دشمن به سمت موقعیت هدف
        # Calculate animation progress and smoothly move the enemy toward its target position
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
        # واگذاری به‌روزرسانی حرکت به منطق اختصاصی دشمن
        # Delegate movement updates to the enemy's specific AI implementation
        self.update_ai(dt)

        # ---- شلیک ----
        # بررسی زمان شلیک و اجرای آن در صورت آماده بودن زمان‌سنج
        # Check the shooting timer and fire when it reaches its trigger point
        if self.SHOOT_CD > 0.0 and self.scene is not None:
            self._shoot_timer -= dt
            if self._shoot_timer <= 0.0:
                self._shoot_timer = self.SHOOT_CD * random.uniform(0.85, 1.15)
                self._do_shoot()

        # ---- حذف خودکار وقتی از پایین خارج شد ----
        # علامت‌گذاری دشمن برای حذف پس از خروج کامل از پایین صفحه
        # Mark the enemy for removal after it moves beyond the bottom of the screen
        if self.y > S.Window.HEIGHT + self.radius + 30:
            self.alive = False
            self._pending_kill = True

    # ── شلیک به سمت پلیر ──
    # ایجاد و شلیک یک گلوله در جهت موقعیت فعلی بازیکن
    # Create and fire a bullet toward the player's current position
    def _do_shoot(self) -> list[Bullet]:
        """شلیک یک گلوله به سمت پلیر. زیرکلاس‌ها می‌توانند Override کنند."""
        if self.scene is None:
            return []
        player = getattr(self.scene, "player", None)
        if player is None or not player.alive:
            return []

        # محاسبه‌ی بردار جهت و نرمال‌سازی آن برای تعیین سرعت گلوله
        # Calculate and normalize the direction vector to determine bullet velocity
        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        vx = (dx / d) * self.BULLET_SPEED
        vy = (dy / d) * self.BULLET_SPEED

        # ساخت گلوله‌ی دشمن و ثبت آن در صحنه
        # Create an enemy bullet and register it with the scene
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

    # مرگ و آسیب
    # Death and damage handling
    def on_death(self) -> None:
        """انفجار + امتیاز + احتمال افت پاورآپ + لرزش دوربین."""
        if self.scene is None:
            return
        try:
            # اجرای جلوه‌های نابودی و اعمال پاداش‌های مربوط به دشمن
            # Trigger destruction effects and apply the enemy's associated rewards
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

    # رسم موجودیت و مدیریت شفافیت انیمیشن ورود
    # Render the entity and manage entry animation transparency
    def draw_entity(self, surface: pygame.Surface) -> None:
        """پوسته‌ی رسم — محاسبه‌ی alpha ورود و پاس دادن به زیرکلاس."""
        if not self._entry_done:
            t = min(1.0, self._entry_elapsed / self.ENTRY_TIME)
            alpha = int(60 + 195 * t)
        else:
            alpha = 255

        self.draw_body(surface, alpha)

    # ابزارهای کمکی
    # Helper methods
    def set_entry(self, start_y: float, target_y: float) -> None:
        """پیکربندی انیمیشن ورود (توسط Factory استفاده می‌شود)."""
        self.y = start_y
        self._entry_start_y = start_y
        self._entry_target_y = target_y
        self._entry_elapsed = 0.0
        self._entry_done = False

    # Helpers مشترک (که قبلاً در ۸ زیرکلاس تکرار شده بودن)
    # Shared helpers previously duplicated across eight subclasses
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
        # کاهش مقدار هر کانال رنگ برای تولید رنگ تیره‌تر
        # Reduce each color channel to produce a darker color
        return (
            max(0, c[0] - amount),
            max(0, c[1] - amount),
            max(0, c[2] - amount),
        )

    @staticmethod
    def _lighter(c: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
        # افزایش مقدار هر کانال رنگ برای تولید رنگ روشن‌تر
        # Increase each color channel to produce a lighter color
        return (
            min(255, c[0] + amount),
            min(255, c[1] + amount),
            min(255, c[2] + amount),
        )


__all__ = ["Enemy", "EnemyKind"]
