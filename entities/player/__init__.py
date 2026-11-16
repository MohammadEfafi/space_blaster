"""
entities.player
===============

پکیج سفینه‌های قابل‌انتخاب بازیکن (Player Ships) برای SPACE BLASTER.

این پکیج تمام سفینه‌ها، کلاس پایه، و رجیستری را یک‌جا export می‌کند
تا import از بیرون تمیز و کوتاه باشد.

استفاده:
    from entities.player import Player, Interceptor, Phantom
    from entities.player import SHIP_CLASSES, SHIP_LIST, SHIP_INFO
    from entities.player import build_ship, get_info

معماری:
    base.py         → کلاس پایه‌ی Player (منطق مشترک)
    interceptor.py  → سفینه‌ی سریع و شکننده
    vanguard.py     → سفینه‌ی سنگین و مقاوم
    phantom.py      → سفینه‌ی متعادل با پاورآپ ۲ برابر
    devastator.py   → سفینه‌ی ویرانگر با سلاح پلاسما
    registry.py     → ثبت، ساخت، و اطلاعات نمایشی
"""

# ---- کلاس پایه ----
# کلاس پایه برای دسترسی مستقیم از پکیج اصلی در دسترس قرار می‌گیرد.
# The base class is exposed directly through the main package.
from entities.player.base import Player

# ---- سفینه‌ها ----
# کلاس‌های سفینه‌ها برای import مستقیم از این پکیج در دسترس هستند.
# Ship classes are available for direct import from this package.
from entities.player.devastator import Devastator
from entities.player.interceptor import Interceptor
from entities.player.phantom import Phantom
from entities.player.vanguard import Vanguard

# ---- رجیستری و API ----
# رجیستری و توابع مرتبط، رابط عمومی مدیریت سفینه‌ها را تشکیل می‌دهند.
# The registry and related functions form the public ship-management API.
from entities.player.registry import (
    DEFAULT_SHIP_KEY,
    SHIP_CLASSES,
    SHIP_INFO,
    SHIP_LIST,
    ShipInfo,
    build_ship,
    get_info,
    next_ship_key,
    prev_ship_key,
)


__all__ = [
    # ---- پایه ----
    "Player",
    # ---- سفینه‌ها ----
    "Interceptor",
    "Vanguard",
    "Phantom",
    "Devastator",
    # ---- رجیستری ----
    "SHIP_CLASSES",
    "SHIP_LIST",
    "SHIP_INFO",
    "ShipInfo",
    "DEFAULT_SHIP_KEY",
    # ---- توابع ----
    "build_ship",
    "get_info",
    "next_ship_key",
    "prev_ship_key",
]