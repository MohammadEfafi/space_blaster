
"""
entities/enemies/boss_registry.py
===========================

رجیستری باس‌ها — انتخاب تصادفی.
"""
from __future__ import annotations

import random

from entities.enemies.boss_void_sentinel import VoidSentinel
from entities.enemies.boss_dreadnought import IronDreadnought
from entities.enemies.boss_wraith import PlasmaWraith
from entities.enemies.boss_omega import OmegaCore


# باس‌های عادی
# Regular bosses
BOSS_CLASSES = [VoidSentinel, IronDreadnought, PlasmaWraith]

# باس ویژه (از موج ۱۰+)
# Special boss (available from wave 10 onward)
OMEGA_CLASS = OmegaCore


def get_random_boss():
    """انتخاب تصادفی باس عادی."""
    # انتخاب تصادفی یکی از کلاس‌های باس عادی
    # Randomly select one of the regular boss classes
    return random.choice(BOSS_CLASSES)


__all__ = ["BOSS_CLASSES", "OMEGA_CLASS", "get_random_boss"]
