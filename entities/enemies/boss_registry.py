"""رجیستری باس‌ها — انتخاب تصادفی."""
from __future__ import annotations

from entities.enemies.boss_void_sentinel import VoidSentinel
from entities.enemies.boss_dreadnought import IronDreadnought
from entities.enemies.boss_wraith import PlasmaWraith


BOSS_CLASSES = [VoidSentinel, IronDreadnought, PlasmaWraith]


def get_random_boss():
    import random
    return random.choice(BOSS_CLASSES)


__all__ = ["BOSS_CLASSES", "get_random_boss"]