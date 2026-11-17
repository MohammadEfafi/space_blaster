"""
utils
=====

استفاده:
    from utils import lerp, clamp, color_lerp
"""

from utils.helpers import (
    # توابع ریاضی برای درون‌یابی و محدودسازی مقادیر
    # Math utilities for interpolation and value clamping
    # math
    lerp, clamp, clamp01,

    # توابع هموارسازی برای ایجاد حرکت و تغییرات طبیعی‌تر
    # Easing functions for smoother and more natural transitions
    # easing
    ease_out_cubic, ease_in_cubic, ease_in_out_cubic, ease_out_back,

    # توابع درون‌یابی و تنظیم روشنایی رنگ‌ها
    # Color interpolation and brightness adjustment utilities
    # color
    color_lerp, color_darker, color_lighter,
)

# مشخص کردن توابع و نام‌هایی که از طریق این ماژول در دسترس هستند
# Define the public API exposed by this module
__all__ = [
    "lerp", "clamp", "clamp01",
    "ease_out_cubic", "ease_in_cubic", "ease_in_out_cubic", "ease_out_back",
    "color_lerp", "color_darker", "color_lighter",
]