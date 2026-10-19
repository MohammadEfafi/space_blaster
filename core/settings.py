"""
core/settings.py
================

مرکز تنظیمات پروژه‌ی SPACE BLASTER.

تمام ثابت‌های بازی (ابعاد پنجره، رنگ‌ها، سرعت‌ها، مسیرها، پیکربندی دشمن‌ها و …)
فقط و فقط در همین فایل تعریف می‌شوند. هیچ عدد جادویی (magic number) نباید در
جای دیگری از پروژه ظاهر شود — این قاعده، بالانس کردن بازی را از یک کابوس به
یک تجربه‌ی لذت‌بخش تبدیل می‌کند.

نکته‌ی مهم:
    این فایل هیچ وابستگی داخلی به بقیه‌ی ماژول‌ها ندارد و می‌تواند
    از هر جای پروژه با خیال راحت import شود.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Final

import pygame


# ═══════════════════════════════════════════════════════════════════════════
#  ①  مسیرهای پروژه (Paths)
# ═══════════════════════════════════════════════════════════════════════════
#  از pathlib استفاده می‌کنیم تا مسیرها روی ویندوز/مک/لینوکس یکسان کار کنند.
#  ROOT_DIR از روی محل همین فایل محاسبه می‌شود، پس هرجای دیسک هم که پروژه
#  کپی شود، همه چیز خودکار درست می‌ماند.
# ═══════════════════════════════════════════════════════════════════════════

ROOT_DIR:  Final[Path] = Path(__file__).resolve().parent.parent
DATA_DIR:  Final[Path] = ROOT_DIR / "data"
IMG_DIR:   Final[Path] = DATA_DIR / "images"
SOUND_DIR: Final[Path] = DATA_DIR / "sounds"
FONT_DIR:  Final[Path] = DATA_DIR / "fonts"
LEVEL_DIR: Final[Path] = DATA_DIR / "levels"
SAVE_DIR:  Final[Path] = ROOT_DIR / "saves"


# ═══════════════════════════════════════════════════════════════════════════
#  ②  پنجره و حلقه‌ی اصلی (Window & Loop)
# ═══════════════════════════════════════════════════════════════════════════

class Window:
    TITLE:     Final[str]  = "SPACE BLASTER"
    WIDTH:     Final[int]  = 1920   
    HEIGHT:    Final[int]  = 1080   
    FPS:       Final[int]  = 60
    VSYNC:     Final[int]  = 1
    RESIZABLE: Final[bool] = True    

# ═══════════════════════════════════════════════════════════════════════════
#  ③  پالت رنگ (Palette)
# ═══════════════════════════════════════════════════════════════════════════
#  تمام رنگ‌ها به صورت tuple[int, int, int] ذخیره می‌شوند تا مستقیماً به
#  pygame قابل پاس دادن باشند. اگر خواستی تم بازی را عوض کنی، فقط همین‌جاست.
# ═══════════════════════════════════════════════════════════════════════════

class Palette:
    # ---- پس‌زمینه ----
    BG_DEEP:   Final[tuple[int, int, int]] = (5, 8, 20)
    BG_MID:    Final[tuple[int, int, int]] = (12, 18, 38)
    STAR_NEAR: Final[tuple[int, int, int]] = (200, 210, 255)
    STAR_FAR:  Final[tuple[int, int, int]] = (90, 90, 130)

    # ---- رنگ‌های پایه ----
    WHITE:  Final[tuple[int, int, int]] = (255, 255, 255)
    BLACK:  Final[tuple[int, int, int]] = (0, 0, 0)
    GREY:   Final[tuple[int, int, int]] = (140, 140, 160)
    RED:    Final[tuple[int, int, int]] = (255, 70, 70)
    CYAN:   Final[tuple[int, int, int]] = (60, 220, 255)
    YELLOW: Final[tuple[int, int, int]] = (255, 220, 60)
    GREEN:  Final[tuple[int, int, int]] = (80, 255, 140)
    ORANGE: Final[tuple[int, int, int]] = (255, 150, 40)
    PURPLE: Final[tuple[int, int, int]] = (190, 90, 255)
    PINK:   Final[tuple[int, int, int]] = (255, 90, 200)

    # ---- پلیر ----
    PLAYER_BODY:        Final[tuple[int, int, int]] = (60, 220, 255)
    PLAYER_HULL:        Final[tuple[int, int, int]] = (235, 245, 255)
    PLAYER_FLAME:       Final[tuple[int, int, int]] = (255, 150, 40)
    PLAYER_FLAME_INNER: Final[tuple[int, int, int]] = (255, 240, 120)

    # ---- گلوله‌ها ----
    BULLET_PLAYER: Final[tuple[int, int, int]] = (120, 240, 255)
    BULLET_ENEMY:  Final[tuple[int, int, int]] = (255, 90, 90)
    BULLET_BOSS:   Final[tuple[int, int, int]] = (255, 40, 120)

    # ---- دشمن‌ها ----
    ENEMY_NORMAL: Final[tuple[int, int, int]] = (255, 90, 90)
    ENEMY_TANK:   Final[tuple[int, int, int]] = (190, 90, 255)
    ENEMY_SPIRAL: Final[tuple[int, int, int]] = (80, 255, 140)
    ENEMY_BOSS:   Final[tuple[int, int, int]] = (255, 60, 160)

    # ---- افکت انفجار ----
    EXPLOSION_HOT:  Final[tuple[int, int, int]] = (255, 240, 160)
    EXPLOSION_MID:  Final[tuple[int, int, int]] = (255, 150, 40)
    EXPLOSION_COOL: Final[tuple[int, int, int]] = (255, 60, 60)

    # ---- پاورآپ ----
    POWERUP_CORE: Final[tuple[int, int, int]] = (255, 220, 60)
    POWERUP_GLOW: Final[tuple[int, int, int]] = (255, 150, 40)

    # ---- رابط کاربری (HUD) ----
    HUD_TEXT:   Final[tuple[int, int, int]] = (235, 240, 255)
    HUD_ACCENT: Final[tuple[int, int, int]] = (60, 220, 255)
    HUD_WARN:   Final[tuple[int, int, int]] = (255, 90, 90)
    HUD_HP:     Final[tuple[int, int, int]] = (255, 70, 70)
    MENU_TITLE: Final[tuple[int, int, int]] = (60, 220, 255)
    MENU_HINT:  Final[tuple[int, int, int]] = (200, 220, 255)


# ═══════════════════════════════════════════════════════════════════════════
#  ④  فونت‌ها (Fonts)
# ═══════════════════════════════════════════════════════════════════════════

class FontCfg:
    """نام خانواده و اندازه‌های استاندارد فونت."""
    FAMILY: Final[str] = "bahnschrift"   # بعداً می‌توانی فایل .ttf بدهی
    TINY:   Final[int] = 14
    SMALL:  Final[int] = 18
    NORMAL: Final[int] = 22
    LARGE:  Final[int] = 32
    BIG:    Final[int] = 48
    HUGE:   Final[int] = 72


# ═══════════════════════════════════════════════════════════════════════════
#  ⑤  پیکربندی پلیر (Player)
# ═══════════════════════════════════════════════════════════════════════════

class PlayerCfg:
    SPEED:        Final[float] = 340.0   # پیکسل بر ثانیه
    RADIUS:       Final[int]   = 20      # شعاع هیت‌باکس
    MAX_HP:       Final[int]   = 3
    INVULN_TIME:  Final[float] = 1.6     # ثانیه نامیرایی بعد از ضربه
    SHOOT_CD:     Final[float] = 0.16    # فاصله بین دو شلیک (ثانیه)
    BULLET_SPEED: Final[float] = 780.0
    BULLET_DMG:   Final[int]   = 1
    RESPAWN_Y:    Final[int]   = 90      # فاصله از پایین صفحه برای ظاهر شدن


# ═══════════════════════════════════════════════════════════════════════════
#  ⑥  پیکربندی دشمن‌ها (Enemies)
# ═══════════════════════════════════════════════════════════════════════════
#  هر نوع دشمن یک کلاس تودرتو دارد. این ساختار افزودن دشمن جدید را
#  بسیار ساده می‌کند: کافی‌ست یک کلاس تازه اینجا اضافه شود و از آن در
#  entities/enemies/ ارث‌بری شود.
# ═══════════════════════════════════════════════════════════════════════════

class EnemyCfg:

    class Normal:
        """دشمن ساده و سریع — یک ضربه و نابود."""
        HP:          Final[int]   = 1
        RADIUS:      Final[int]   = 14
        SPEED:       Final[float] = 130.0
        SCORE:       Final[int]   = 10
        DROP_CHANCE: Final[float] = 0.12

    class Tank:
        """دشمن سنگین — به سمت پلیر شلیک می‌کند."""
        HP:           Final[int]   = 4
        RADIUS:       Final[int]   = 22
        SPEED:        Final[float] = 70.0
        SCORE:        Final[int]   = 30
        DROP_CHANCE:  Final[float] = 0.22
        SHOOT_CD:     Final[float] = 1.8       # ثانیه بین دو شلیک
        BULLET_SPEED: Final[float] = 260.0

    class Spiral:
        """دشمن مارپیچ — مسیر سینوسی حرکت می‌کند."""
        HP:          Final[int]   = 2
        RADIUS:      Final[int]   = 16
        SPEED:       Final[float] = 160.0
        SCORE:       Final[int]   = 20
        DROP_CHANCE: Final[float] = 0.10
        AMPLITUDE:   Final[float] = 70.0       # دامنه‌ی نوسان (پیکسل)
        FREQUENCY:   Final[float] = 2.6        # بسامد (رادیان بر ثانیه)


# ═══════════════════════════════════════════════════════════════════════════
#  ⑦  موج‌ها و Spawn (Wave Config)
# ═══════════════════════════════════════════════════════════════════════════

class WaveCfg:
    FIRST_ENEMIES: Final[int]   = 4     # تعداد دشمن در موج اول
    GROWTH:        Final[int]   = 1     # افزایش هر موج
    WAVE_BREAK:    Final[float] = 1.6   # مکث بین موج‌ها (ثانیه)
    ENEMY_MARGIN:  Final[int]   = 60    # حاشیه از دیواره‌ها برای Spawn
    SPAWN_Y_MIN:   Final[int]   = -220  # بازه‌ی عمودی Spawn بالای صفحه
    SPAWN_Y_MAX:   Final[int]   = -40

    # وزن انتخاب نوع دشمن بر اساس شماره‌ی موج.
    # ترتیب: (ساده، تانک، مارپیچ)
    WEIGHTS_WAVE_1: Final[tuple[int, int, int]] = (10, 0, 0)
    WEIGHTS_WAVE_2: Final[tuple[int, int, int]] = (8, 1, 3)
    WEIGHTS_WAVE_3: Final[tuple[int, int, int]] = (6, 2, 4)
    WEIGHTS_LATE:   Final[tuple[int, int, int]] = (5, 3, 5)


# ═══════════════════════════════════════════════════════════════════════════
#  ⑧  افکت‌های بصری (Effects / FX)
# ═══════════════════════════════════════════════════════════════════════════

class FxCfg:
    # ---- ذرات انفجار ----
    PARTICLE_MIN_LIFE:  Final[float] = 0.28   # ثانیه
    PARTICLE_MAX_LIFE:  Final[float] = 0.85
    PARTICLE_MIN_SPEED: Final[float] = 60.0
    PARTICLE_MAX_SPEED: Final[float] = 460.0
    PARTICLE_FRICTION:  Final[float] = 0.92

    # ---- لرزش صفحه ----
    SHAKE_DECAY:        Final[float] = 0.86
    SHAKE_MIN:          Final[float] = 0.6
    SHAKE_ON_HIT:       Final[float] = 14.0
    SHAKE_ON_KILL:      Final[float] = 4.5
    SHAKE_ON_BOSS_KILL: Final[float] = 26.0

    # ---- ستاره‌های پس‌زمینه ----
    STAR_COUNT:     Final[int]   = 160
    STAR_SPEED_MIN: Final[float] = 8.0
    STAR_SPEED_MAX: Final[float] = 55.0


# ═══════════════════════════════════════════════════════════════════════════
#  ⑨  پاورآپ‌ها (Powerups)
# ═══════════════════════════════════════════════════════════════════════════

class PowerupCfg:
    FALL_SPEED: Final[float] = 95.0
    RADIUS:     Final[int]   = 14
    DURATION:   Final[float] = 8.0    # مدت اثر هر پاورآپ (ثانیه)


# ═══════════════════════════════════════════════════════════════════════════
#  ⑩  نام صحنه‌ها (Scene Names)
# ═══════════════════════════════════════════════════════════════════════════

class SceneName(str, Enum):
    """از Enum استفاده می‌کنیم تا از غلط‌املایی و رشته‌های جادویی جلوگیری شود."""
    MENU        = "menu"
    SHIP_SELECT  = "ship_select"
    GAMEPLAY    = "gameplay"
    PAUSE       = "pause"
    GAME_OVER   = "game_over"
    SETTINGS    = "settings"
    LEADERBOARD = "leaderboard"


# ═══════════════════════════════════════════════════════════════════════════
#  ⑪  نقشه‌ی ورودی‌ها (Input Map)
# ═══════════════════════════════════════════════════════════════════════════
#  هر دستور یک tuple از کلیدهای جایگزین است. این‌طوری پشتیبانی از WASD و
#  کلیدهای جهت‌دار همزمان، و بعداً Rebind کردن کلیدها، بسیار ساده می‌شود.
# ═══════════════════════════════════════════════════════════════════════════

class Keys:
    UP:      Final[tuple[int, ...]] = (pygame.K_w, pygame.K_UP)
    DOWN:    Final[tuple[int, ...]] = (pygame.K_s, pygame.K_DOWN)
    LEFT:    Final[tuple[int, ...]] = (pygame.K_a, pygame.K_LEFT)
    RIGHT:   Final[tuple[int, ...]] = (pygame.K_d, pygame.K_RIGHT)
    SHOOT:   Final[tuple[int, ...]] = (pygame.K_SPACE,)
    PAUSE:   Final[tuple[int, ...]] = (pygame.K_p, pygame.K_PAUSE)
    QUIT:    Final[tuple[int, ...]] = (pygame.K_ESCAPE,)
    RESTART: Final[tuple[int, ...]] = (pygame.K_r, pygame.K_RETURN)
    CONFIRM: Final[tuple[int, ...]] = (pygame.K_RETURN, pygame.K_SPACE)


# ═══════════════════════════════════════════════════════════════════════════
#  ⑫  پرچم‌های دیباگ (Debug Flags)
# ═══════════════════════════════════════════════════════════════════════════

class Debug:
    SHOW_FPS:     Final[bool] = True    # نمایش FPS گوشه‌ی صفحه
    GOD_MODE:     Final[bool] = False   # پلیر نامیرا (برای تست)
    SHOW_HITBOX:  Final[bool] = False   # نمایش هیت‌باکس‌ها
    LOG_EVENTS:   Final[bool] = False   # چاپ رویدادها در کنسول


__all__ = [
    "ROOT_DIR", "DATA_DIR", "IMG_DIR", "SOUND_DIR", "FONT_DIR",
    "LEVEL_DIR", "SAVE_DIR",
    "Window", "Palette", "FontCfg", "PlayerCfg", "EnemyCfg",
    "WaveCfg", "FxCfg", "PowerupCfg", "SceneName", "Keys", "Debug",
]