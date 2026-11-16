
"""
entities/enemies
================

پکیج دشمن‌های بازی SPACE BLASTER.
Enemy package for SPACE BLASTER.

این پکیج تمام انواع دشمن‌ها، کلاس پایه، و کارخانه‌ی ساخت را
یک‌جا export می‌کند تا import از بیرون تمیز و کوتاه باشد.

This package re-exports enemy types, base classes, and the enemy
factory through a single entry point for clean and concise imports.

استفاده:
Usage:
    from entities.enemies import Enemy, EnemyFactory, EnemyKind
    from entities.enemies import NormalEnemy, TankEnemy, SpiralEnemy

معماری:
Architecture:
    base.py                  → کلاس پایه‌ی Enemy و Enum نوع‌ها
                             → Enemy base class and type enumeration
    normal.py                → دشمن سبک (زنبور مهاجم)
                             → Light enemy (attacking bee)
    tank.py                  → دشمن سنگین (قلعه‌ی پرنده)
                             → Heavy enemy (flying fortress)
    spiral.py                → دشمن مارپیچ (کریستال چرخان)
                             → Spiral enemy (rotating crystal)
    factory.py               → کارخانه‌ی ساخت دشمن بر اساس موج
                             → Wave-based enemy factory
    boss_base.py             → کلاس پایه‌ی باس‌ها
                             → Boss base class
    boss_*.py                → پیاده‌سازی انواع باس‌ها
                             → Boss type implementations
    boss_registry.py         → ثبت کلاس‌های باس و انتخاب باس تصادفی
                             → Boss class registry and random boss selection
    sentinel.py              → دشمن Sentinel
                             → Sentinel enemy
    serpent.py               → دشمن Serpent
                             → Serpent enemy
    specter.py               → دشمن Specter
                             → Specter enemy
    bombardier.py            → دشمن Bombardier
                             → Bombardier enemy
    titan.py                 → دشمن Titan
                             → Titan enemy

"""

# کلاس پایه و شناسه انواع دشمن‌ها
# Enemy base class and enemy type identifiers.
from entities.enemies.base import Enemy, EnemyKind

# کلاس پایه و پیاده‌سازی انواع باس‌ها
# Boss base class and individual boss implementations.
from entities.enemies.boss_base import BossBase
from entities.enemies.boss_dreadnought import IronDreadnought
from entities.enemies.boss_omega import OmegaCore
from entities.enemies.boss_void_sentinel import VoidSentinel
from entities.enemies.boss_wraith import PlasmaWraith

# پیاده‌سازی انواع دشمن‌های معمولی
# Standard enemy implementations.
from entities.enemies.bombardier import BombardierEnemy
from entities.enemies.normal import NormalEnemy
from entities.enemies.sentinel import SentinelEnemy
from entities.enemies.serpent import SerpentEnemy
from entities.enemies.specter import SpecterEnemy
from entities.enemies.spiral import SpiralEnemy
from entities.enemies.tank import TankEnemy
from entities.enemies.titan import TitanEnemy

# کارخانه تولید دشمن‌ها بر اساس منطق موج‌های بازی
# Enemy factory driven by the game's wave logic.
from entities.enemies.factory import EnemyFactory

# رجیستری باس‌ها و ابزارهای انتخاب آن‌ها
# Boss registry and boss selection utilities.
from entities.enemies.boss_registry import (
    BOSS_CLASSES, OMEGA_CLASS, get_random_boss,
)

# رابط عمومی پکیج؛ فقط نام‌های فهرست‌شده از طریق import * صادر می‌شوند
# Package public API; only the listed names are exported via import *.
__all__ = [
    "Enemy", "EnemyKind",
    "NormalEnemy", "TankEnemy", "SpiralEnemy",
    "SpecterEnemy", "BombardierEnemy",
    "SentinelEnemy", "SerpentEnemy", "TitanEnemy",
    "BossBase", "VoidSentinel", "IronDreadnought", "PlasmaWraith", "OmegaCore",
    "EnemyFactory", "BOSS_CLASSES", "OMEGA_CLASS", "get_random_boss",
]
