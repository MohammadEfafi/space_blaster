"""
entities/enemies/factory.py
===========================

کارخانه‌ی ساخت دشمن (Enemy Factory) برای SPACE BLASTER.

این ماژول بر اساس شماره‌ی موج، نوع دشمن مناسب رو انتخاب می‌کنه،
موقعیت تصادفی رو تعیین می‌کنه، و انیمیشن ورود رو پیکربندی می‌کنه.

ویژگی‌ها:
    • توزیع احتمال وزن‌دار بر اساس موج
    • ثبت دشمن‌ها در Registry برای دسترسی راحت
    • پشتیبانی از Boss (هر N موج)
    • امکان spawn تکی، گروهی، یا با نوع مشخص
    • کراس‌پلتفرم و بدون وابستگی به Scene

استفاده:
    factory = EnemyFactory(scene)
    enemy = factory.spawn(wave=3)

    # یا با نوع مشخص:
    enemy = factory.spawn(wave=3, kind=EnemyKind.TANK)

    # برای موج باس:
    enemies = factory.spawn_boss_wave(wave=5)
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

from core import settings as S
from entities.enemies.base import Enemy, EnemyKind
from entities.enemies.normal import NormalEnemy
from entities.enemies.spiral import SpiralEnemy
from entities.enemies.tank import TankEnemy

if TYPE_CHECKING:
    from scenes.gameplay import GameplayScene


# ═══════════════════════════════════════════════════════════════════════════
#  Registry — نگاشت نوع به کلاس
# ═══════════════════════════════════════════════════════════════════════════

_KIND_TO_CLASS: dict[EnemyKind, type[Enemy]] = {
    EnemyKind.NORMAL: NormalEnemy,
    EnemyKind.TANK:   TankEnemy,
    EnemyKind.SPIRAL: SpiralEnemy,
}


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس EnemyFactory
# ═══════════════════════════════════════════════════════════════════════════

class EnemyFactory:
    """
    کارخانه‌ی ساخت دشمن با توزیع وزن‌دار بر اساس موج.

    پارامترها:
        scene — رفرنس اختیاری به GameplayScene که به دشمن‌ها پاس داده می‌شود
    """

    # ---- نگاشت موج → وزن‌ها (Normal, Tank, Spiral) ----
    # ---- برای موج‌های بالاتر از آخرین ورودی، آخرین وزن‌ها استفاده می‌شود ----
    _WAVE_WEIGHTS: list[tuple[int, tuple[int, int, int]]] = [
        (1, S.WaveCfg.WEIGHTS_WAVE_1),
        (2, S.WaveCfg.WEIGHTS_WAVE_2),
        (3, S.WaveCfg.WEIGHTS_WAVE_3),
        (4, S.WaveCfg.WEIGHTS_LATE),
    ]

    # ---- ترتیب ثابت انواع برای استفاده با weights ----
    _ORDERED_KINDS: tuple[EnemyKind, ...] = (
        EnemyKind.NORMAL,
        EnemyKind.TANK,
        EnemyKind.SPIRAL,
    )

    # ─────────────────────────────────────────────────────────────────────
    #  سازنده
    # ─────────────────────────────────────────────────────────────────────

    def __init__(self, scene: Optional["GameplayScene"] = None) -> None:
        self.scene = scene

    # ─────────────────────────────────────────────────────────────────────
    #  API عمومی
    # ─────────────────────────────────────────────────────────────────────

    def spawn(
        self,
        wave: int,
        *,
        x: Optional[float] = None,
        y: Optional[float] = None,
        kind: Optional[EnemyKind] = None,
    ) -> Enemy:
        """
        یک دشمن جدید می‌سازد.

        پارامترها:
            wave — شماره‌ی موج (برای انتخاب نوع و سختی)
            x    — موقعیت افقی دلخواه (None = تصادفی)
            y    — موقعیت عمودی شروع (None = بالای صفحه)
            kind — نوع دشمن دلخواه (None = انتخاب وزنی)

        برمی‌گرداند: نمونه‌ی Enemy آماده‌ی استفاده.
        """
        # ---- انتخاب نوع ----
        if kind is None:
            kind = self._choose_kind(wave)

        # ---- موقعیت افقی ----
        margin = S.WaveCfg.ENEMY_MARGIN
        if x is None:
            x = random.uniform(margin, S.Window.WIDTH - margin)

        # ---- موقعیت عمودی ----
        if y is None:
            start_y = random.uniform(S.WaveCfg.SPAWN_Y_MIN, S.WaveCfg.SPAWN_Y_MAX)
        else:
            start_y = y

        # موقعیت هدف ورود (جایی که دشمن بهش می‌رسه)
        target_y = random.uniform(-10.0, 40.0)

        # ---- ساخت ----
        cls = _KIND_TO_CLASS.get(kind, NormalEnemy)
        enemy = cls(x, start_y, scene=self.scene)
        enemy.set_entry(start_y, target_y)
        return enemy

    def spawn_batch(self, wave: int, count: int) -> list[Enemy]:
        """
        چند دشمن می‌سازد.
        نکته: توزیع x رو یکنواخت نگه می‌داره که دشمن‌ها روی هم نیفتن.
        """
        if count <= 0:
            return []

        # موقعیت‌های x رو در بازه تقسیم می‌کنیم
        margin = S.WaveCfg.ENEMY_MARGIN
        usable_w = S.Window.WIDTH - 2 * margin
        step = usable_w / max(1, count)

        enemies: list[Enemy] = []
        for i in range(count):
            # با کمی jitter
            base_x = margin + i * step + step * 0.5
            jitter = step * 0.3 * (random.random() - 0.5)
            x = max(margin, min(S.Window.WIDTH - margin, base_x + jitter))

            enemies.append(self.spawn(wave, x=x))
        return enemies

    def spawn_boss_wave(self, wave: int) -> list[Enemy]:
        """
        دشمن‌های موج باس رو می‌سازد.

        تا زمانی که کلاس Boss ساخته نشده، این متد از دشمن‌های موجود
        با آرایش و تعداد مشخص استفاده می‌کند.

        پارامترها:
            wave — شماره‌ی موج فعلی (معمولاً مضرب boss_every)
        """
        enemies: list[Enemy] = []

        # ۲ تا تانک در دو طرف
        for side in (-1, 1):
            x = S.Window.WIDTH / 2 + side * S.Window.WIDTH * 0.25
            tank = self.spawn(wave, x=x, kind=EnemyKind.TANK)
            enemies.append(tank)

        # ۲ تا اسپیرال در وسط
        for side in (-1, 1):
            x = S.Window.WIDTH / 2 + side * S.Window.WIDTH * 0.10
            spiral = self.spawn(wave, x=x, kind=EnemyKind.SPIRAL)
            enemies.append(spiral)

        return enemies

    # ─────────────────────────────────────────────────────────────────────
    #  انتخاب وزنی
    # ─────────────────────────────────────────────────────────────────────

    def _weights_for_wave(self, wave: int) -> tuple[int, int, int]:
        """وزن‌های توزیع بر اساس موج."""
        result = self._WAVE_WEIGHTS[0][1]
        for min_wave, weights in self._WAVE_WEIGHTS:
            if wave >= min_wave:
                result = weights
            else:
                break
        return result

    def _choose_kind(self, wave: int) -> EnemyKind:
        """انتخاب نوع دشمن با توزیع وزن‌دار."""
        weights = self._weights_for_wave(wave)

        # اگر همه‌ی وزن‌ها صفر بودن، fallback به Normal
        if sum(weights) <= 0:
            return EnemyKind.NORMAL

        return random.choices(self._ORDERED_KINDS, weights=weights, k=1)[0]


__all__ = ["EnemyFactory"]