"""
entities/player/registry.py
===========================

ثبت سفینه‌های قابل‌انتخاب (Ship Registry) برای SPACE BLASTER.

این ماژول یه نگاشت مرکزی از شناسه‌ی هر سفینه به کلاس و آمار
نمایشی اون فراهم می‌کنه. صفحه‌ی انتخاب سفینه (ShipSelectScene) از
همین رجیستری استفاده می‌کنه.

ویژگی‌ها:
    • افزودن سفینه‌ی جدید = یک خط در SHIP_LIST
    • آمار نمایشی جدا از آمار بازی (برای صفحه‌ی انتخاب)
    • تابع کمکی برای ساخت سفینه بر اساس شناسه
    • بدون وابستگی به Scene یا Game
    • ترتیب نمایش قابل کنترل

استفاده:
    from entities.player.registry import SHIP_CLASSES, SHIP_LIST, build_ship

    # ساخت سفینه:
    ship = build_ship("interceptor", scene)

    # اطلاعات نمایشی:
    info = SHIP_INFO["interceptor"]
    print(info.name, info.description)

    # لیست مرتب برای صفحه‌ی انتخاب:
    for key in SHIP_LIST:
        ...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from entities.player.base import Player
from entities.player.devastator import Devastator
from entities.player.interceptor import Interceptor
from entities.player.phantom import Phantom
from entities.player.vanguard import Vanguard

if TYPE_CHECKING:
    from scenes.gameplay import GameplayScene


# ═══════════════════════════════════════════════════════════════════════════
#  نگاشت شناسه → کلاس
# ═══════════════════════════════════════════════════════════════════════════

SHIP_CLASSES: dict[str, type[Player]] = {
    "interceptor": Interceptor,
    "vanguard":    Vanguard,
    "phantom":     Phantom,
    "devastator":  Devastator,
}


# ═══════════════════════════════════════════════════════════════════════════
#  ترتیب نمایش در صفحه‌ی انتخاب
# ═══════════════════════════════════════════════════════════════════════════

SHIP_LIST: list[str] = [
    "interceptor",
    "vanguard",
    "phantom",
    "devastator",
]


# ═══════════════════════════════════════════════════════════════════════════
#  اطلاعات نمایشی هر سفینه
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ShipInfo:
    """
    اطلاعات نمایشی سفینه برای صفحه‌ی انتخاب.

    فیلدها:
        key         — شناسه (همان کلید در SHIP_CLASSES)
        name        — نام نمایشی
        description — توضیح کوتاه (انگلیسی، برای استایل)
        role        — نقش کلی (ASSAULT / DEFENSE / …)
        speed       — آمار سرعت (۱ تا ۵) برای نمایش نوار
        hp          — آمار جان
        fire_rate   — نرخ شلیک
        damage      — قدرت هر شلیک
        agility     — چابکی/شتاب
        color       — رنگ اصلی (برای هاله و UI)
        accent      — رنگ تأکید
        difficulty  — درجه‌ی سختی (EASY / NORMAL / HARD)
    """
    key:         str
    name:        str
    description: str
    role:        str
    speed:       int
    hp:          int
    fire_rate:   int
    damage:      int
    agility:     int
    color:       tuple[int, int, int]
    accent:      tuple[int, int, int]
    difficulty:  str


SHIP_INFO: dict[str, ShipInfo] = {
    "interceptor": ShipInfo(
        key="interceptor",
        name="INTERCEPTOR",
        description="Fast and fragile. Outspeed them or die trying.",
        role="ASSAULT",
        speed=5,
        hp=2,
        fire_rate=5,
        damage=3,
        agility=5,
        color=Interceptor.PRIMARY_COLOR,
        accent=Interceptor.ACCENT_COLOR,
        difficulty="HARD",
    ),
    "vanguard": ShipInfo(
        key="vanguard",
        name="VANGUARD",
        description="Heavy armor, slow pace. Stand your ground.",
        role="DEFENSE",
        speed=2,
        hp=5,
        fire_rate=3,
        damage=4,
        agility=2,
        color=Vanguard.PRIMARY_COLOR,
        accent=Vanguard.ACCENT_COLOR,
        difficulty="EASY",
    ),
    "phantom": ShipInfo(
        key="phantom",
        name="PHANTOM",
        description="Balanced power with a taste of the void.",
        role="ARCANE",
        speed=4,
        hp=2,             
        fire_rate=3,      
        damage=3,         
        agility=4,
        color=Phantom.PRIMARY_COLOR,
        accent=Phantom.ACCENT_COLOR,
        difficulty="HARD",
    ),
    "devastator": ShipInfo(
        key="devastator",
        name="DEVASTATOR",
        description="Every shot is a statement. Make them count.",
        role="HEAVY",
        speed=2,
        hp=4,
        fire_rate=2,
        damage=5,
        agility=2,
        color=Devastator.PRIMARY_COLOR,
        accent=Devastator.ACCENT_COLOR,
        difficulty="NORMAL",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
#  API عمومی
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_SHIP_KEY: str = "phantom"


def build_ship(
    key: str,
    scene: Optional["GameplayScene"] = None,
) -> Player:
    """
    ساخت یک نمونه‌ی سفینه بر اساس شناسه.

    پارامترها:
        key   — شناسه‌ی سفینه (مثلاً "interceptor")
        scene — رفرنس اختیاری به GameplayScene

    در صورت نبود شناسه، از سفینه‌ی پیش‌فرض استفاده می‌شود.
    """
    cls = SHIP_CLASSES.get(key)
    if cls is None:
        cls = SHIP_CLASSES[DEFAULT_SHIP_KEY]
    return cls(scene)


def get_info(key: str) -> ShipInfo:
    """اطلاعات نمایشی سفینه. اگر پیدا نشد، پیش‌فرض برمی‌گرداند."""
    info = SHIP_INFO.get(key)
    if info is None:
        info = SHIP_INFO[DEFAULT_SHIP_KEY]
    return info


def next_ship_key(current_key: str) -> str:
    """شناسه‌ی سفینه‌ی بعدی در ترتیب نمایش."""
    try:
        idx = SHIP_LIST.index(current_key)
    except ValueError:
        idx = 0
    return SHIP_LIST[(idx + 1) % len(SHIP_LIST)]


def prev_ship_key(current_key: str) -> str:
    """شناسه‌ی سفینه‌ی قبلی در ترتیب نمایش."""
    try:
        idx = SHIP_LIST.index(current_key)
    except ValueError:
        idx = 0
    return SHIP_LIST[(idx - 1) % len(SHIP_LIST)]


__all__ = [
    "SHIP_CLASSES",
    "SHIP_LIST",
    "SHIP_INFO",
    "ShipInfo",
    "DEFAULT_SHIP_KEY",
    "build_ship",
    "get_info",
    "next_ship_key",
    "prev_ship_key",
]