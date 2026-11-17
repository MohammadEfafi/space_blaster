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


# نگاشت شناسه‌ی هر سفینه به کلاس سازنده‌ی آن؛ مبنای ساخت نمونه‌ها در بازی.
# Maps each ship identifier to its class, providing the source for instance creation.
SHIP_CLASSES: dict[str, type[Player]] = {
    "interceptor": Interceptor,
    "vanguard":    Vanguard,
    "phantom":     Phantom,
    "devastator":  Devastator,
}


# ترتیب نمایش سفینه‌ها در رابط انتخاب؛ مستقل از ترتیب تعریف کلاس‌ها و اطلاعات آن‌ها.
# Defines the display order of ships in the selection UI, independently of their class and info definitions.
SHIP_LIST: list[str] = [
    "interceptor",
    "vanguard",
    "phantom",
    "devastator",
]


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


# اطلاعات مخصوص نمایش هر سفینه؛ این مقادیر برای رابط کاربری هستند و لزوماً آمار واقعی مبارزه نیستند.
# Stores display-specific information for each ship; these values are for the UI and do not necessarily represent actual combat stats.
SHIP_INFO: dict[str, ShipInfo] = {
    "interceptor": ShipInfo(
        key="interceptor",
        name="INTERCEPTOR",
        description="Fast and fragile. Outspeed them or die trying.",
        role="ASSAULT",
        speed=5,        # SPEED=480 (سریع‌ترین)
        hp=3,           # MAX_HP=3
        fire_rate=5,    # SHOOT_CD=0.07 (سریع‌ترین)
        damage=2,       # 1 damage (2 با pierce)
        agility=5,      # ACCEL=14 (چابک‌ترین)
        color=Interceptor.PRIMARY_COLOR,
        accent=Interceptor.ACCENT_COLOR,
        difficulty="HARD",       # بدون pierce، شکننده‌ست
    ),
    "vanguard": ShipInfo(
        key="vanguard",
        name="VANGUARD",
        description="Heavy armor, slow pace. Stand your ground.",
        role="DEFENSE",
        speed=2,        # SPEED=260 (کندترین)
        hp=6,           # MAX_HP=6 (نمایش 5 - سقف نوار)
        fire_rate=4,    # SHOOT_CD=0.15
        damage=3,       # 1 damage × 2 گلوله = 2
        agility=2,      # ACCEL=6
        color=Vanguard.PRIMARY_COLOR,
        accent=Vanguard.ACCENT_COLOR,
        difficulty="EASY",
    ),
    "phantom": ShipInfo(
        key="phantom",
        name="PHANTOM",
        description="Balanced power with a taste of the void.",
        role="ARCANE",
        speed=3,        # SPEED=360
        hp=2,           # MAX_HP=2
        fire_rate=3,    # SHOOT_CD=0.18
        damage=4,       # 1 damage × 3 گلوله = 3
        agility=4,      # ACCEL=10
        color=Phantom.PRIMARY_COLOR,
        accent=Phantom.ACCENT_COLOR,
        difficulty="HARD",
    ),
    "devastator": ShipInfo(
        key="devastator",
        name="DEVASTATOR",
        description="Every shot is a statement. Make them count.",
        role="HEAVY",
        speed=2,        # SPEED=290
        hp=4,           # MAX_HP=4
        fire_rate=3,    # SHOOT_CD=0.22
        damage=5,       # BULLET_DAMAGE=3 (بالاترین per-hit)
        agility=2,      # ACCEL=5.5
        color=Devastator.PRIMARY_COLOR,
        accent=Devastator.ACCENT_COLOR,
        difficulty="NORMAL",
    ),
}


# شناسه‌ی سفینه‌ای که در صورت نامعتبر بودن کلید ورودی، به‌عنوان گزینه‌ی جایگزین استفاده می‌شود.
# Identifies the fallback ship used when the requested key is invalid.
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
    # کلاس متناظر با شناسه‌ی ورودی را از رجیستری دریافت می‌کند.
    # Retrieves the class associated with the requested identifier from the registry.
    cls = SHIP_CLASSES.get(key)

    # اگر شناسه در رجیستری وجود نداشته باشد، کلاس سفینه‌ی پیش‌فرض انتخاب می‌شود.
    # Falls back to the default ship class if the requested identifier is not registered.
    if cls is None:
        cls = SHIP_CLASSES[DEFAULT_SHIP_KEY]

    # نمونه‌ی سفینه را با ارجاع اختیاری به صحنه‌ی بازی ایجاد می‌کند.
    # Instantiates the selected ship, passing the optional gameplay scene reference.
    return cls(scene)


def get_info(key: str) -> ShipInfo:
    """اطلاعات نمایشی سفینه. اگر پیدا نشد، پیش‌فرض برمی‌گرداند."""
    # اطلاعات نمایشی سفینه را بر اساس شناسه جست‌وجو می‌کند.
    # Looks up the ship's display information using its identifier.
    info = SHIP_INFO.get(key)

    # در صورت نبود اطلاعات برای شناسه‌ی ورودی، اطلاعات سفینه‌ی پیش‌فرض را برمی‌گرداند.
    # Returns the default ship's display information when the requested key is not found.
    if info is None:
        info = SHIP_INFO[DEFAULT_SHIP_KEY]

    return info


def next_ship_key(current_key: str) -> str:
    """شناسه‌ی سفینه‌ی بعدی در ترتیب نمایش."""
    try:
        # موقعیت سفینه‌ی فعلی را در ترتیب نمایش پیدا می‌کند.
        # Finds the current ship's position in the display order.
        idx = SHIP_LIST.index(current_key)
    except ValueError:
        # اگر شناسه در فهرست نباشد، حرکت از ابتدای فهرست آغاز می‌شود.
        # Starts from the beginning of the list if the identifier is not present.
        idx = 0

    # با پیمایش پیمانه‌ای، پس از آخرین سفینه دوباره به ابتدای فهرست می‌رسد.
    # Uses modulo indexing to wrap from the last ship back to the beginning.
    return SHIP_LIST[(idx + 1) % len(SHIP_LIST)]


def prev_ship_key(current_key: str) -> str:
    """شناسه‌ی سفینه‌ی قبلی در ترتیب نمایش."""
    try:
        # موقعیت سفینه‌ی فعلی را در ترتیب نمایش پیدا می‌کند.
        # Finds the current ship's position in the display order.
        idx = SHIP_LIST.index(current_key)
    except ValueError:
        # اگر شناسه در فهرست نباشد، موقعیت اولیه به‌عنوان نقطه‌ی شروع در نظر گرفته می‌شود.
        # Uses the initial position as the starting point if the identifier is not present.
        idx = 0

    # با پیمایش پیمانه‌ای، حرکت به عقب از ابتدای فهرست به آخرین سفینه می‌رسد.
    # Uses modulo indexing to wrap backward from the first ship to the last one.
    return SHIP_LIST[(idx - 1) % len(SHIP_LIST)]


# نمادهای عمومی ماژول را مشخص می‌کند تا فقط رابط موردنظر از بیرون در دسترس باشد.
# Defines the module's public interface, exposing only the intended symbols to external imports.
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