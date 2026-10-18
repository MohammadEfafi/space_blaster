"""رجیستری باس‌ها — انتخاب تصادفی."""
from __future__ import annotations

import random

from entities.enemies.boss_void_sentinel import VoidSentinel
from entities.enemies.boss_dreadnought import IronDreadnought
from entities.enemies.boss_wraith import PlasmaWraith
from entities.enemies.boss_omega import OmegaCore


# باس‌های عادی
BOSS_CLASSES = [VoidSentinel, IronDreadnought, PlasmaWraith]

# باس ویژه (از موج ۱۰+)
OMEGA_CLASS = OmegaCore


def get_random_boss():
    """انتخاب تصادفی باس عادی."""
    return random.choice(BOSS_CLASSES)


__all__ = ["BOSS_CLASSES", "OMEGA_CLASS", "get_random_boss"]