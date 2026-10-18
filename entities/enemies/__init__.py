"""
entities/enemies
================

پکیج دشمن‌های بازی SPACE BLASTER.

این پکیج تمام انواع دشمن‌ها، کلاس پایه، و کارخانه‌ی ساخت را
یک‌جا export می‌کند تا import از بیرون تمیز و کوتاه باشد.

استفاده:
    from entities.enemies import Enemy, EnemyFactory, EnemyKind
    from entities.enemies import NormalEnemy, TankEnemy, SpiralEnemy

معماری:
    base.py      → کلاس پایه‌ی Enemy و Enum نوع‌ها
    normal.py    → دشمن سبک (زنبور مهاجم)
    tank.py      → دشمن سنگین (قلعه‌ی پرنده)
    spiral.py    → دشمن مارپیچ (کریستال چرخان)
    factory.py   → کارخانه‌ی ساخت دشمن بر اساس موج
"""

from entities.enemies.base import Enemy, EnemyKind
from entities.enemies.boss_base import BossBase
from entities.enemies.boss_dreadnought import IronDreadnought
from entities.enemies.boss_omega import OmegaCore
from entities.enemies.boss_void_sentinel import VoidSentinel
from entities.enemies.boss_wraith import PlasmaWraith
from entities.enemies.bombardier import BombardierEnemy
from entities.enemies.factory import EnemyFactory
from entities.enemies.normal import NormalEnemy
from entities.enemies.specter import SpecterEnemy
from entities.enemies.spiral import SpiralEnemy
from entities.enemies.tank import TankEnemy

__all__ = [
    "Enemy", "EnemyKind",
    "NormalEnemy", "TankEnemy", "SpiralEnemy",
    "SpecterEnemy", "BombardierEnemy",
    "BossBase", "VoidSentinel", "IronDreadnought", "PlasmaWraith", "OmegaCore",
    "EnemyFactory",
]