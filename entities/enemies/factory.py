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
from entities.enemies.specter import SpecterEnemy
from entities.enemies.bombardier import BombardierEnemy
from entities.enemies.sentinel import SentinelEnemy
from entities.enemies.serpent import SerpentEnemy
from entities.enemies.titan import TitanEnemy

if TYPE_CHECKING:
    from scenes.gameplay import GameplayScene


# نگاشت هر نوع دشمن به کلاس سازنده‌ی مربوط به آن؛ این نگاشت انتخاب کلاس را متمرکز می‌کند.
# Maps each enemy kind to its corresponding class, centralizing enemy class selection.
_KIND_TO_CLASS: dict[EnemyKind, type[Enemy]] = {
    EnemyKind.NORMAL: NormalEnemy,
    EnemyKind.TANK:   TankEnemy,
    EnemyKind.SPIRAL: SpiralEnemy,
    EnemyKind.SPECTER: SpecterEnemy,
    EnemyKind.BOMBARDIER: BombardierEnemy,
    EnemyKind.SENTINEL: SentinelEnemy,
    EnemyKind.SERPENT: SerpentEnemy,
    EnemyKind.TITAN: TitanEnemy,
}


class EnemyFactory:
    """
    کارخانه‌ی ساخت دشمن با توزیع وزن‌دار بر اساس موج.

    پارامترها:
        scene — رفرنس اختیاری به GameplayScene که به دشمن‌ها پاس داده می‌شود
    """

    # ---- نگاشت موج → وزن‌ها (Normal, Tank, Spiral) ----
    # ---- برای موج‌های بالاتر از آخرین ورودی، آخرین وزن‌ها استفاده می‌شود ----
    # هر ورودی از موج مشخص‌شده به بعد فعال است و وزن انتخاب انواع پایه را تعیین می‌کند.
    # Each entry applies from its specified wave onward and determines the selection weights of basic enemy types.
    _WAVE_WEIGHTS: list[tuple[int, tuple[int, int, int]]] = [
        (1, S.WaveCfg.WEIGHTS_WAVE_1),
        (2, S.WaveCfg.WEIGHTS_WAVE_2),
        (3, S.WaveCfg.WEIGHTS_WAVE_3),
        (4, S.WaveCfg.WEIGHTS_LATE),
    ]

    # ---- ترتیب ثابت انواع برای استفاده با weights ----
    # ترتیب این مجموعه باید با ترتیب وزن‌های تعریف‌شده در تنظیمات یکسان باشد.
    # The order of this tuple must match the order of the corresponding weights in the settings.
    _ORDERED_KINDS: tuple[EnemyKind, ...] = (
        EnemyKind.NORMAL,
        EnemyKind.TANK,
        EnemyKind.SPIRAL,
    )


    def __init__(self, scene: Optional["GameplayScene"] = None) -> None:
        # نگهداری ارجاع اختیاری به صحنه برای ارسال آن هنگام ساخت دشمن‌ها.
        # Stores an optional scene reference to pass to enemies during creation.
        self.scene = scene


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
        # در صورت مشخص نبودن نوع، انتخاب دشمن بر اساس وزن‌های موج انجام می‌شود.
        # If no enemy kind is specified, the type is selected using the wave's weights.
        if kind is None:
            kind = self._choose_kind(wave)

        # ---- موقعیت افقی ----
        # در صورت مشخص نبودن x، دشمن در محدوده‌ی افقی مجاز به‌صورت تصادفی قرار می‌گیرد.
        # If x is not specified, the enemy is placed randomly within the allowed horizontal range.
        margin = S.WaveCfg.ENEMY_MARGIN
        if x is None:
            x = random.uniform(margin, S.Window.WIDTH - margin)

        # ---- موقعیت عمودی ----
        # مقدار y مشخص‌شده مستقیماً استفاده می‌شود؛ در غیر این صورت ارتفاع شروع تصادفی است.
        # A supplied y value is used directly; otherwise, the starting height is randomized.
        if y is None:
            start_y = random.uniform(S.WaveCfg.SPAWN_Y_MIN, S.WaveCfg.SPAWN_Y_MAX)
        else:
            start_y = y

        # موقعیت هدف ورود (جایی که دشمن بهش می‌رسه)
        # ارتفاع مقصد جدا از ارتفاع شروع تعیین می‌شود تا انیمیشن ورود اجرا شود.
        # The destination height is chosen separately from the starting height to support the entry animation.
        target_y = random.uniform(-10.0, 40.0)

        # ---- ساخت ----
        # کلاس متناظر با نوع دشمن بازیابی می‌شود و در صورت نبود نگاشت، NormalEnemy جایگزین است.
        # The class mapped to the enemy kind is retrieved, falling back to NormalEnemy if no mapping exists.
        cls = _KIND_TO_CLASS.get(kind, NormalEnemy)
        enemy = cls(x, start_y, scene=self.scene)
        enemy.set_entry(start_y, target_y)
        return enemy

    def spawn_batch(self, wave: int, count: int) -> list[Enemy]:
        """
        چند دشمن می‌سازد.
        نکته: توزیع x رو یکنواخت نگه می‌داره که دشمن‌ها روی هم نیفتن.
        """
        # تعداد صفر یا منفی نباید باعث اجرای فرایند ساخت دشمن شود.
        # Zero or negative counts should not trigger the enemy creation process.
        if count <= 0:
            return []

        # موقعیت‌های x رو در بازه تقسیم می‌کنیم
        # عرض قابل استفاده به تعداد دشمن‌ها تقسیم می‌شود تا هر دشمن محدوده‌ی افقی مشخصی داشته باشد.
        # The usable width is divided by the enemy count so each enemy gets a distinct horizontal region.
        margin = S.WaveCfg.ENEMY_MARGIN
        usable_w = S.Window.WIDTH - 2 * margin
        step = usable_w / max(1, count)

        enemies: list[Enemy] = []
        for i in range(count):
            # با کمی jitter
            # جابه‌جایی تصادفی محدود، از قرارگیری بیش‌ازحد منظم دشمن‌ها جلوگیری می‌کند.
            # A small randomized offset prevents enemies from appearing in an overly uniform formation.
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
        # تانک‌ها با فاصله‌ی متقارن از مرکز صفحه در دو سمت قرار می‌گیرند.
        # Tanks are positioned symmetrically on both sides of the screen center.
        for side in (-1, 1):
            x = S.Window.WIDTH / 2 + side * S.Window.WIDTH * 0.25
            tank = self.spawn(wave, x=x, kind=EnemyKind.TANK)
            enemies.append(tank)

        # ۲ تا اسپیرال در وسط
        # اسپیرال‌ها در فاصله‌ی نزدیک‌تری به مرکز و در دو سمت آن ظاهر می‌شوند.
        # Spiral enemies spawn on both sides of the center, at a shorter distance.
        for side in (-1, 1):
            x = S.Window.WIDTH / 2 + side * S.Window.WIDTH * 0.10
            spiral = self.spawn(wave, x=x, kind=EnemyKind.SPIRAL)
            enemies.append(spiral)

        return enemies


    def _weights_for_wave(self, wave: int) -> tuple[int, int, int]:
        """وزن‌های توزیع بر اساس موج."""
        # وزن پیش‌فرض از اولین ورودی گرفته می‌شود و با عبور از آستانه‌های موج به‌روزرسانی می‌شود.
        # The default weights come from the first entry and are updated as wave thresholds are reached.
        result = self._WAVE_WEIGHTS[0][1]
        for min_wave, weights in self._WAVE_WEIGHTS:
            if wave >= min_wave:
                result = weights
            else:
                break
        return result

    def _choose_kind(self, wave: int) -> EnemyKind:
        """انتخاب نوع دشمن با توزیع وزن‌دار."""
        # ---- از موج ۲۰: دشمن‌های جدید هم وارد می‌شن ----
        # از موج ۲۰ به بعد، مجموعه‌ی انتخاب و وزن‌ها گسترش پیدا می‌کنند.
        # Starting from wave 20, the selection pool and its weights are expanded.
        if wave >= 20:
            kinds = [
                EnemyKind.NORMAL, EnemyKind.TANK, EnemyKind.SPIRAL,
                EnemyKind.SENTINEL, EnemyKind.SERPENT, EnemyKind.TITAN,
            ]
            weights = [3, 3, 3, 2, 2, 1]
            return random.choices(kinds, weights=weights, k=1)[0]

        # برای موج‌های پایین‌تر، وزن‌های متناسب با شماره‌ی موج از تنظیمات دریافت می‌شوند.
        # For earlier waves, the weights corresponding to the current wave are retrieved from the settings.
        weights = self._weights_for_wave(wave)
        if sum(weights) <= 0:
            return EnemyKind.NORMAL

        # انتخاب تصادفی با احتمال متناسب با وزن هر نوع انجام می‌شود.
        # Random selection is performed with probabilities proportional to each kind's weight.
        return random.choices(self._ORDERED_KINDS, weights=weights, k=1)[0]


__all__ = ["EnemyFactory"]