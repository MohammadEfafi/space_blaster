
"""
core/log.py
===========

گزارش خطای مشترک برای کل پروژه.
Shared error reporting utility for the entire project.

استفاده:
Usage:
    from core.log import report_error
    try:
        ...
    except Exception:
        report_error("Player.update_entity")
"""

from __future__ import annotations

import sys
import traceback


def report_error(where: str) -> None:
    """
    یک استثنا را به‌صورت امن لاگ می‌کند (بازی کرش نمی‌کند).
    Safely logs an exception without crashing the game.

    پارامتر where باید شکل "ClassName.method" داشته باشد تا در لاگ
    راحت پیدا شود.

    The `where` parameter should follow the "ClassName.method" format
    to make the error easy to identify in the logs.

    این تابع عمداً استثنا را raise نمی‌کند — فرض بر این است که
    فراخوان در یک except block است و بازی باید ادامه بدهد.

    This function intentionally does not re-raise the exception.
    It is expected to be called from an except block where the game
    should continue running.
    """
    # ساخت سربرگ خطا با مشخص‌کردن محل وقوع آن
    # Build the error header identifying where the exception occurred.
    header = f"\n[ERROR] {where}"

    # چاپ سربرگ و جداکننده‌ها در جریان خطای استاندارد
    # Write the error header and separators to the standard error stream.
    print(header, file=sys.stderr)
    print("-" * len(header), file=sys.stderr)

    # ثبت کامل اطلاعات استثنای فعال، شامل traceback
    # Print the full traceback of the currently handled exception.
    traceback.print_exc()

    # پایان گزارش خطا با جداکننده‌ای هم‌اندازه سربرگ
    # Terminate the error report with a separator matching the header width.
    print("-" * len(header), file=sys.stderr)


__all__ = ["report_error"]
