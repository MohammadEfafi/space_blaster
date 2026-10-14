"""
main.py
=======

نقطه‌ی ورود (Entry Point) بازی SPACE BLASTER.

این فایل مسئول موارد زیر است:

  ①  بررسی نسخه‌ی پایتون و اینکه pygame در دسترس است
  ②  تنظیم محیط اجرایی (Environment Bootstrapping)
  ③  سازگاری کامل با PyInstaller (بسته‌بندی به exe)
  ④  مدیریت خطای سراسری و نمایش پیام قابل‌فهم
  ⑤  ساخت پوشه‌های ضروری در اولین اجرا
  ⑥  اجرای Game با پارامترهای اختیاری خط فرمان

نکته‌ی مهم برای بسته‌بندی:
    توابع resource_path() و _bootstrap_env() طوری طراحی شده‌اند که هم
    هنگام اجرای مستقیم (python main.py) و هم هنگام اجرا به‌صورت exe
    (که PyInstaller فایل‌ها را در پوشه‌ی موقت _MEIPASS باز می‌کند)
    درست کار کنند.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
#  ①  بررسی پیش‌نیازهای اجرا
# ═══════════════════════════════════════════════════════════════════════════

MIN_PYTHON: tuple[int, int] = (3, 11)
"""حداقل نسخه‌ی پایتون لازم. از 3.11 به بعد برای تایپ‌هینت‌های مدرن."""


def _check_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        sys.stderr.write(
            f"\n[SPACE BLASTER] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required.\n"
            f"                 You are running {sys.version.split()[0]}.\n"
            f"                 Please upgrade Python and try again.\n\n"
        )
        sys.exit(1)


def _check_pygame() -> None:
    try:
        import pygame  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "\n[SPACE BLASTER] pygame is not installed.\n"
            "                 Install it with:\n"
            "                     pip install pygame-ce\n\n"
        )
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
#  ②  مدیریت مسیر منابع (PyInstaller-compatible)
# ═══════════════════════════════════════════════════════════════════════════

def resource_path(relative: str | Path) -> Path:
    """
    مسیر یک منبع (data/, assets/, …) را چه هنگام اجرای مستقیم و چه هنگام
    اجرای exe برمی‌گرداند.

    در حالت exe، PyInstaller محتویات را در پوشه‌ی موقت sys._MEIPASS باز
    می‌کند. هنگام اجرای مستقیم، مسیر نسبت به ریشه‌ی پروژه محاسبه می‌شود.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is not None:
        # حالت exe
        return Path(base) / relative
    # حالت اجرای مستقیم
    return Path(__file__).resolve().parent / relative


# ═══════════════════════════════════════════════════════════════════════════
#  ③  بوت‌استرپ محیط اجرایی
# ═══════════════════════════════════════════════════════════════════════════

def _bootstrap_env() -> None:
    """
    آماده‌سازی محیط اجرا:
        • مسیر ریشه‌ی پروژه به sys.path اضافه می‌شود تا importهای
          core/، scenes/، entities/ و … همیشه درست کار کنند.
        • پوشه‌های ضروری (data/، saves/) در اولین اجرا ساخته می‌شوند.
        • متغیرهای محیطی مفید برای pygame و درایورها تنظیم می‌شوند.
    """
    # ---- sys.path ----
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # ---- پوشه‌های ضروری ----
    required_dirs = [
        "data", "data/images", "data/sounds", "data/fonts", "data/levels",
        "saves",
    ]
    for rel in required_dirs:
        (project_root / rel).mkdir(parents=True, exist_ok=True)

    # ---- متغیرهای محیطی مفید ----
    # جلوگیری از باز شدن پنجره‌ی کنسول اضافی در ویندوز (برای حالت بسته‌بندی)
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    # برای برخی درایورهای لینوکس که با ALSA مشکل دارند
    os.environ.setdefault("SDL_AUDIODRIVER", "directsound" if os.name == "nt" else "pulse")


# ═══════════════════════════════════════════════════════════════════════════
#  ④  خط فرمان (اختیاری)
# ═══════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="space_blaster",
        description="SPACE BLASTER — a fast-paced top-down space shooter.",
    )
    parser.add_argument(
        "--scene", "-s",
        default=None,
        help="شروع از صحنه‌ی مشخص (menu, gameplay, …). پیش‌فرض: menu",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="فعال‌سازی حالت دیباگ (نمایش FPS و لاگ رویدادها).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="SPACE BLASTER 0.1.0",
    )
    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════════════════
#  ⑤  اجرای اصلی
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    # ---- پیش‌نیازها ----
    _check_python_version()
    _check_pygame()
    _bootstrap_env()

    # ---- خط فرمان ----
    args = _parse_args()

    # ---- import های داخلی (بعد از bootstrap) ----
    from core import settings as S
    from core.game import Game

    # ---- اعمال گزینه‌های خط فرمان ----
    if args.debug:
        S.Debug.SHOW_FPS = True
        S.Debug.LOG_EVENTS = True
        S.Debug.SHOW_HITBOX = True
    if args.scene:
        # نام صحنه را روی خود ماژول ست می‌کنیم — Game موقع ساخت آن را می‌خواند
        S.__dict__["_START_SCENE"] = args.scene

    # ---- ساخت و اجرای بازی ----
    try:
        game = Game()
        game.run()
    except SystemExit:
        raise
    except Exception:
        _fatal_error()
        return 1
    return 0


def _fatal_error() -> None:
    """نمایش پیام خطای خوانا در صورت وقوع خطای غیرقابل‌بازیابی."""
    print("\n" + "═" * 68)
    print("  SPACE BLASTER — UNHANDLED ERROR")
    print("═" * 68)
    traceback.print_exc()
    print("═" * 68)
    print("  لطفاً متن بالا را برای توسعه‌دهنده ارسال کنید.")
    print("═" * 68 + "\n")


# ═══════════════════════════════════════════════════════════════════════════
#  اجرای مستقیم
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.exit(main())