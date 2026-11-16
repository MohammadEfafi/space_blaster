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

# تنظیم کیفیت مقیاس‌گذاری تصویر برای رندر نرم‌تر در حالت SDL_SCALED
# Configure image scaling quality for smoother rendering with SDL_SCALED
# ---- کیفیت smooth برای pygame.SCALED ----
os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"   # 1=linear, 2=anisotropic


# تعیین حداقل نسخه پایتون موردنیاز برای اجرای بازی
# Define the minimum Python version required to run the game
MIN_PYTHON: tuple[int, int] = (3, 11)
"""حداقل نسخه‌ی پایتون لازم. از 3.11 به بعد برای تایپ‌هینت‌های مدرن."""


def _check_python_version() -> None:
    # مقایسه نسخه فعلی مفسر با حداقل نسخه پشتیبانی‌شده
    # Compare the current interpreter version against the minimum supported version
    if sys.version_info < MIN_PYTHON:
        # نمایش نسخه موردنیاز و نسخه نصب‌شده برای راهنمایی کاربر
        # Display the required and installed versions to guide the user
        sys.stderr.write(
            f"\n[SPACE BLASTER] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required.\n"
            f"                 You are running {sys.version.split()[0]}.\n"
            f"                 Please upgrade Python and try again.\n\n"
        )
        sys.exit(1)


def _check_pygame() -> None:
    # بررسی نصب بودن pygame پیش از شروع فرایند راه‌اندازی بازی
    # Verify that pygame is installed before starting the game initialization
    try:
        import pygame  # noqa: F401
    except ImportError:
        # ارائه دستور نصب در صورت در دسترس نبودن کتابخانه
        # Provide the installation command when the dependency is unavailable
        sys.stderr.write(
            "\n[SPACE BLASTER] pygame is not installed.\n"
            "                 Install it with:\n"
            "                     pip install pygame-ce\n\n"
        )
        sys.exit(1)




def resource_path(relative: str | Path) -> Path:
    """
    مسیر یک منبع (data/, assets/, …) را چه هنگام اجرای مستقیم و چه هنگام
    اجرای exe برمی‌گرداند.

    در حالت exe، PyInstaller محتویات را در پوشه‌ی موقت sys._MEIPASS باز
    می‌کند. هنگام اجرای مستقیم، مسیر نسبت به ریشه‌ی پروژه محاسبه می‌شود.
    """
    # تشخیص مسیر موقت منابع در نسخه بسته‌بندی‌شده توسط PyInstaller
    # Detect the temporary resource directory used by PyInstaller
    base = getattr(sys, "_MEIPASS", None)
    if base is not None:
        # استفاده از مسیر استخراج‌شده توسط PyInstaller در حالت exe
        # Use the directory extracted by PyInstaller when running as an executable
        # حالت exe
        return Path(base) / relative

    # استفاده از محل فایل main.py به‌عنوان ریشه منابع در اجرای مستقیم
    # Use the location of main.py as the resource root during direct execution
    # حالت اجرای مستقیم
    return Path(__file__).resolve().parent / relative



def _bootstrap_env() -> None:
    """
    آماده‌سازی محیط اجرا:
        • مسیر ریشه‌ی پروژه به sys.path اضافه می‌شود تا importهای
          core/، scenes/، entities/ و … همیشه درست کار کنند.
        • پوشه‌های ضروری (data/، saves/) در اولین اجرا ساخته می‌شوند.
        • متغیرهای محیطی مفید برای pygame و درایورها تنظیم می‌شوند.
    """
    # اضافه کردن ریشه پروژه به مسیر جست‌وجوی ماژول‌های پایتون
    # Add the project root to Python's module search path
    # ---- sys.path ----
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # ایجاد ساختار پوشه‌های موردنیاز، بدون خطا در صورت وجود قبلی آن‌ها
    # Create the required directory structure without failing if directories already exist
    # ---- پوشه‌های ضروری ----
    required_dirs = [
        "data", "data/images", "data/sounds", "data/fonts", "data/levels",
        "saves",
    ]
    for rel in required_dirs:
        (project_root / rel).mkdir(parents=True, exist_ok=True)

    # تنظیم متغیرهای محیطی پیش از راه‌اندازی pygame
    # Configure environment variables before initializing pygame
    # ---- متغیرهای محیطی مفید ----
    # جلوگیری از باز شدن پنجره‌ی کنسول اضافی در ویندوز (برای حالت بسته‌بندی)
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    # برای برخی درایورهای لینوکس که با ALSA مشکل دارند
    os.environ.setdefault("SDL_AUDIODRIVER", "directsound" if os.name == "nt" else "pulse")



def _parse_args() -> argparse.Namespace:
    # تعریف رابط خط فرمان و گزینه‌های قابل استفاده هنگام اجرای بازی
    # Define the command-line interface and options available when launching the game
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



def main() -> int:
    # اجرای بررسی پیش‌نیازها و آماده‌سازی محیط پیش از import ماژول‌های داخلی
    # Check prerequisites and prepare the environment before importing internal modules
    # ---- پیش‌نیازها ----
    _check_python_version()
    _check_pygame()
    _bootstrap_env()

    # دریافت و پردازش آرگومان‌های ارسال‌شده از خط فرمان
    # Retrieve and parse the arguments passed through the command line
    # ---- خط فرمان ----
    args = _parse_args()

    # وارد کردن ماژول‌های داخلی پس از تنظیم مسیرهای محیط اجرا
    # Import internal modules after configuring the runtime environment
    # ---- import های داخلی (بعد از bootstrap) ----
    from core import settings as S
    from core.game import Game

    # اعمال تنظیمات اختیاری دریافت‌شده از خط فرمان
    # Apply optional settings provided through command-line arguments
    # ---- اعمال گزینه‌های خط فرمان ----
    if args.debug:
        S.Debug.SHOW_FPS = True
        S.Debug.LOG_EVENTS = True
        S.Debug.SHOW_HITBOX = True
    if args.scene:
        # نام صحنه را روی خود ماژول ست می‌کنیم — Game موقع ساخت آن را می‌خواند
        S.__dict__["_START_SCENE"] = args.scene

    # ایجاد نمونه بازی و آغاز حلقه اصلی اجرا
    # Instantiate the game and start its main execution loop
    # ---- ساخت و اجرای بازی ----
    try:
        game = Game()
        game.run()
    except SystemExit:
        # حفظ رفتار عادی خروج برنامه و جلوگیری از تبدیل آن به خطای عمومی
        # Preserve normal process-exit behavior instead of treating it as a generic error
        raise
    except Exception:
        # ثبت جزئیات خطای پیش‌بینی‌نشده و بازگرداندن کد خروج ناموفق
        # Report unexpected errors and return a failure exit code
        _fatal_error()
        return 1
    return 0


def _fatal_error() -> None:
    """نمایش پیام خطای خوانا در صورت وقوع خطای غیرقابل‌بازیابی."""
    # نمایش گزارش کامل استثنا برای کمک به عیب‌یابی خطاهای زمان اجرا
    # Display the full exception traceback to assist with runtime debugging
    print("\n" + "═" * 68)
    print("  SPACE BLASTER — UNHANDLED ERROR")
    print("═" * 68)
    traceback.print_exc()
    print("═" * 68)
    print("  لطفاً متن بالا را برای توسعه‌دهنده ارسال کنید.")
    print("═" * 68 + "\n")



# اجرای main فقط زمانی که این فایل مستقیماً اجرا شده باشد
# Run main only when this file is executed directly
if __name__ == "__main__":
    sys.exit(main())