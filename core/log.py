"""
core/log.py
===========

گزارش خطای مشترک برای کل پروژه.

قبلاً هر لایه (Entity، Scene، SceneManager) متد `_report` خودش رو داشت
با کد تقریباً یکسان. این ماژول یک نقطه‌ی واحد فراهم می‌کنه.

استفاده:
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

    پارامتر where باید شکل "ClassName.method" داشته باشد تا در لاگ
    راحت پیدا شود.

    این تابع عمداً استثنا را raise نمی‌کند — فرض بر این است که
    فراخوان در یک except block است و بازی باید ادامه بدهد.
    """
    header = f"\n[ERROR] {where}"
    print(header, file=sys.stderr)
    print("-" * len(header), file=sys.stderr)
    traceback.print_exc()
    print("-" * len(header), file=sys.stderr)


__all__ = ["report_error"]