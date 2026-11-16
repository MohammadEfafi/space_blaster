"""
systems/audio.py
================

سیستم صدا (Audio System) برای SPACE BLASTER.

این ماژول مدیریت کامل صدا و موسیقی را بر عهده دارد:

    • Lazy Loading — فایل‌های صوتی فقط وقتی برای اولین بار پخش
      می‌شوند از دیسک لود می‌شوند. حافظه و زمان راه‌اندازی کمتر.
    • Channel-based Mixing — گروه‌های جداگانه برای موسیقی، UI،
      افکت‌های بازی، و شلیک. هر گروه صدای مستقل.
    • Volume Control — Master / Music / SFX / UI جداگانه + mute.
    • Cooldown — جلوگیری از پخش مکرر صدا در فریم‌های پشت سر هم
      (مثلاً وقتی ۲۰ گلوله در یک فریم شلیک می‌شود، صدا فقط یک‌بار).
    • Graceful Fallback — اگر mixer یا فایل صوتی موجود نبود،
      بازی بدون صدا ولی بدون کرش کار می‌کند.
    • Fade in/out برای موسیقی.
    • Pool کانال‌ها برای افکت‌های همزمان.

نکته‌ی مهم:
    هیچ فایل صوتی در این پروژه وجود ندارد. کدها وقتی صدا ندارند،
    در حالت silent کار می‌کنند. اگر بعداً فایل‌ها را به
    `data/sounds/` اضافه کردی، همین کد خودکار لود می‌کند.

استفاده:
    audio = AudioSystem()
    audio.play("player_shoot")
    audio.play_music("battle_theme", loop=True)
    audio.set_master_volume(0.8)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pygame

from core import settings as S


class Bus:
    """گروه‌های صوتی با کانال مستقل."""
    # هر Bus یک دسته‌ی مستقل از صداهاست که کانال‌ها و کنترل ولوم مخصوص خودش را دارد.
    # Each bus is an independent audio category with its own channels and volume control.
    MUSIC = "music"
    SFX   = "sfx"
    UI    = "ui"
    SHOOT = "shoot"



@dataclass
class _SoundDef:
    """
    تعریف یک صدا.
        path       — مسیر نسبت به data/sounds/ (بدون پسوند یا با پسوند)
        bus        — گروه صوتی
        volume     — ولوم اختصاصی (0..1)
        cooldown   — حداقل فاصله بین دو پخش (ثانیه)
        max_conc   — حداکثر تعداد پخش همزمان (روی کانال‌های مختلف)
    """
    path: str
    bus: str = Bus.SFX
    volume: float = 1.0
    cooldown: float = 0.0
    max_conc: int = 3


#  مسیر فایل‌ها را اینجا تعریف می‌کنیم. اگر فایل موجود نباشد،
#  بازی فقط بدون صدا اجرا می‌شود. پسوند‌های رایج (.wav، .ogg، .mp3)
#  به‌طور خودکار تست می‌شوند.

SOUND_REGISTRY: dict[str, _SoundDef] = {
    # ---- پلیر ----
    "player_shoot":     _SoundDef("player_shoot",  Bus.SHOOT, volume=0.55, cooldown=0.05),
    "player_hit":       _SoundDef("player_hit",    Bus.SFX,   volume=0.85),
    "player_explode":   _SoundDef("player_explode",Bus.SFX,   volume=1.0),

    # ---- دشمن‌ها ----
    "enemy_shoot":      _SoundDef("enemy_shoot",   Bus.SHOOT, volume=0.40, cooldown=0.06),
    "enemy_explode":    _SoundDef("enemy_explode", Bus.SFX,   volume=0.65, cooldown=0.03),

    # ---- موج ----
    "wave_start":       _SoundDef("wave_start",    Bus.UI,    volume=0.75),

    # ---- پاورآپ ----
    "powerup_pickup":   _SoundDef("powerup_pickup",Bus.UI,    volume=0.85),
    "powerup_spawn":    _SoundDef("powerup_spawn", Bus.UI,    volume=0.55),

    # ---- UI ----
    "ui_move":          _SoundDef("ui_move",       Bus.UI,    volume=0.5, cooldown=0.02),
    "ui_confirm":       _SoundDef("ui_confirm",    Bus.UI,    volume=0.7),
    "ui_cancel":        _SoundDef("ui_cancel",     Bus.UI,    volume=0.7),
    "ui_hover":         _SoundDef("ui_hover",      Bus.UI,    volume=0.35, cooldown=0.04),

    # ---- موسیقی ----
    "music_menu":       _SoundDef("music_menu",    Bus.MUSIC, volume=0.55),
    "music_battle":     _SoundDef("music_battle",  Bus.MUSIC, volume=0.55),
}

# پسوندهای رایج برای جست‌وجو
_EXTENSIONS: tuple[str, ...] = (".ogg", ".wav", ".mp3", ".flac")


class AudioSystem:
    """
    سیستم صدا با Lazy Loading و Bus ها.

    پارامترها:
        sounds_dir   — مسیر پوشه‌ی صداها (پیش‌فرض data/sounds/)
        master_volume— ولوم کل
        music_volume — ولوم موسیقی
        sfx_volume   — ولوم افکت‌ها
        ui_volume    — ولوم رابط کاربری
        enabled      — اگر False باشد، همه‌ی صداها بی‌اثر می‌شوند
    """

    # تعداد کانال‌های رزرو شده برای هر گروه
    _CHANNELS_PER_BUS: dict[str, int] = {
        Bus.MUSIC: 1,
        Bus.SFX:   8,
        Bus.UI:    4,
        Bus.SHOOT: 6,
    }

    def __init__(
        self,
        sounds_dir: Optional[Path] = None,
        *,
        master_volume: float = 1.0,
        music_volume:  float = 0.6,
        sfx_volume:    float = 1.0,
        ui_volume:     float = 0.9,
        enabled:       bool  = True,
    ) -> None:
        # ---- پیکربندی ----
        # مسیر پوشه‌ی صدا از ورودی یا تنظیمات اصلی پروژه گرفته می‌شود.
        # The sound directory comes from the argument or the project's main settings.
        self.sounds_dir: Path = Path(sounds_dir) if sounds_dir else S.SOUND_DIR

        # تمام ولوم‌های اولیه به بازه‌ی معتبر صفر تا یک محدود می‌شوند.
        # All initial volume levels are clamped to the valid zero-to-one range.
        self.master_volume: float = max(0.0, min(1.0, master_volume))
        self.music_volume:  float = max(0.0, min(1.0, music_volume))
        self.sfx_volume:    float = max(0.0, min(1.0, sfx_volume))
        self.ui_volume:     float = max(0.0, min(1.0, ui_volume))
        self.enabled: bool = enabled
        self.muted: bool = False

        # ---- وضعیت داخلی ----
        # کش، صدای بارگذاری‌شده یا نتیجه‌ی ناموفق بارگذاری را نگه می‌دارد تا جست‌وجو تکرار نشود.
        # The cache stores loaded sounds or failed-load results to avoid repeating lookups.
        self._initialized: bool = False
        self._cache: dict[str, Optional[pygame.mixer.Sound]] = {}
        self._last_play: dict[str, float] = {}

        # ولوم هر Bus جداگانه نگهداری می‌شود؛ گروه شلیک از ولوم SFX استفاده می‌کند.
        # Each bus maintains its own volume; the shooting bus shares the SFX volume.
        self._bus_volume: dict[str, float] = {
            Bus.MUSIC: self.music_volume,
            Bus.SFX:   self.sfx_volume,
            Bus.UI:    self.ui_volume,
            Bus.SHOOT: self.sfx_volume,
        }
        self._bus_channels: dict[str, list[pygame.mixer.Channel]] = {}
        self._current_music: Optional[str] = None
        self._music_fade_out_at: float = -1.0

        # ---- راه‌اندازی ----
        # راه‌اندازی mixer در یک مرحله‌ی محافظت‌شده انجام می‌شود تا نبودن سخت‌افزار صوتی مانع اجرای بازی نشود.
        # The mixer is initialized inside a guarded operation so missing audio hardware cannot prevent the game from running.
        self._init_mixer()


    def _init_mixer(self) -> None:
        """
        mixer را با تنظیمات باکیفیت راه‌اندازی می‌کند. اگر شکست خورد،
        در حالت silent ادامه می‌دهد.
        """
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(
                    frequency=44100,
                    size=-16,
                    channels=2,
                    buffer=512,
                )
                pygame.mixer.init()

            # تعداد کانال‌ها = مجموع همه‌ی busها + کمی اضافه
            # چهار کانال اضافی برای صداهایی در نظر گرفته شده‌اند که از تخصیص اختصاصی Busها استفاده نمی‌کنند.
            # Four extra channels are reserved for sounds that do not use the dedicated bus allocations.
            total = sum(self._CHANNELS_PER_BUS.values()) + 4
            pygame.mixer.set_num_channels(total)

            # تخصیص کانال‌ها به busها
            # کانال‌های متوالی به هر Bus اختصاص داده می‌شوند تا گروه‌های صوتی از یکدیگر جدا بمانند.
            # Consecutive channels are assigned to each bus to keep audio groups separate.
            channel_idx = 0
            for bus, count in self._CHANNELS_PER_BUS.items():
                channels: list[pygame.mixer.Channel] = []
                for _ in range(count):
                    channels.append(pygame.mixer.Channel(channel_idx))
                    channel_idx += 1
                self._bus_channels[bus] = channels

            # کانال صفر برای موسیقی رزرو (توسط pygame.mixer.music استفاده می‌شود)
            self._initialized = True
            print("[Audio] Mixer initialized successfully.")
        except Exception as exc:
            self._initialized = False
            print(f"[Audio] Mixer unavailable — running in silent mode. ({exc})")


    def _resolve_path(self, name: str) -> Optional[Path]:
        """
        مسیر فایل صوتی را پیدا می‌کند. اگر نام پسوند داشته باشد،
        فقط همان را چک می‌کند. وگرنه همه‌ی پسوندهای رایج را امتحان
        می‌کند.
        """
        base = self.sounds_dir / name

        # اگر نام پسوند داشت، مستقیم چک کن
        if base.suffix:
            return base if base.is_file() else None

        # وگرنه پسوندها را امتحان کن
        # در صورت مشخص نبودن پسوند، فایل‌ها به ترتیب تعریف‌شده در _EXTENSIONS بررسی می‌شوند.
        # If no extension is specified, files are checked in the order defined by _EXTENSIONS.
        for ext in _EXTENSIONS:
            candidate = base.with_suffix(ext)
            if candidate.is_file():
                return candidate
        return None

    def _load(self, name: str) -> Optional[pygame.mixer.Sound]:
        # نتیجه‌ی قبلی، حتی اگر بارگذاری ناموفق بوده باشد، مستقیماً از کش برگردانده می‌شود.
        # The previous result is returned directly from the cache, even when loading failed.
        if name in self._cache:
            return self._cache[name]

        # بدون mixer امکان ساخت Sound وجود ندارد؛ نتیجه‌ی ناموفق نیز کش می‌شود.
        # A Sound cannot be created without the mixer, so this failed result is cached as well.
        if not self._initialized:
            self._cache[name] = None
            return None

        path = self._resolve_path(name)
        if path is None:
            # No file on disk — try procedural synthesis
            # اگر فایل فیزیکی پیدا نشود، تولید برنامه‌ای صدا به‌عنوان مسیر جایگزین امتحان می‌شود.
            # If no physical audio file is found, procedural sound synthesis is attempted as a fallback.
            try:
                from systems.sound_synth import synthesize
                sound = synthesize(name)
            except Exception:
                sound = None
            self._cache[name] = sound
            return sound

        try:
            sound = pygame.mixer.Sound(str(path))
            # اعمال ولوم اختصاصی
            # ولوم تعریف‌شده برای هر صدا هنگام بارگذاری روی نمونه‌ی Sound اعمال می‌شود.
            # The volume defined for each sound is applied to the Sound instance when it is loaded.
            defn = SOUND_REGISTRY.get(name)
            if defn is not None:
                sound.set_volume(defn.volume)
            self._cache[name] = sound
            return sound
        except Exception as exc:
            print(f"[Audio] Failed to load '{name}': {exc}")
            self._cache[name] = None
            return None


    def play(
        self,
        name: str,
        *,
        loop: bool = False,
        bus: Optional[str] = None,
        volume: Optional[float] = None,
    ) -> bool:
        """
        پخش یک صدا. اگر صدا لود نشده باشد، ساکت رد می‌شود.

        پارامترها:
            name    — نام کلید در SOUND_REGISTRY
            loop    — تکرار بی‌پایان (برای موسیقی معمولاً از play_music)
            bus     — override گروه صوتی (اختیاری)
            volume  — override ولوم (اختیاری، 0..1)

        برمی‌گرداند: True اگر پخش شد، False در غیر این صورت.
        """
        # در حالت غیرفعال، mute یا نبود mixer، هیچ عملیات پخشی انجام نمی‌شود.
        # No playback operation is performed when audio is disabled, muted, or the mixer is unavailable.
        if not self.enabled or self.muted:
            return False
        if not self._initialized:
            return False

        defn = SOUND_REGISTRY.get(name)
        if defn is None:
            # صدای ناشناخته — بازی نباید کرش کند
            return False

        # ---- cooldown ----
        # زمان monotonic برای اندازه‌گیری فاصله‌ی واقعی بین پخش‌ها استفاده می‌شود و به تغییر ساعت سیستم وابسته نیست.
        # Monotonic time measures the actual interval between plays without depending on system clock changes.
        if defn.cooldown > 0.0:
            now = time.monotonic()
            last = self._last_play.get(name, -1e9)
            if now - last < defn.cooldown:
                return False
            self._last_play[name] = now

        # ---- لود ----
        # بارگذاری فقط هنگام اولین درخواست پخش انجام می‌شود و دفعات بعد از کش استفاده می‌شود.
        # Loading occurs only on the first playback request; subsequent requests use the cache.
        sound = self._load(name)
        if sound is None:
            return False

        # ---- ولوم نهایی ----
        # ولوم مؤثر از ضرب ولوم اصلی، ولوم Bus و ولوم اختصاصی صدا به دست می‌آید.
        # The effective volume is calculated by multiplying master, bus, and sound-specific volumes.
        bus_name = bus or defn.bus
        bus_vol = self._bus_volume.get(bus_name, 1.0)
        snd_vol = defn.volume if volume is None else volume
        effective = self.master_volume * bus_vol * snd_vol

        # اگر ولوم صفر است، پخش نکن
        if effective <= 0.0:
            return False

        # اعمال ولوم
        sound.set_volume(effective)

        # ---- پیدا کردن کانال آزاد در bus ----
        # ابتدا کانال آزاد همان Bus انتخاب می‌شود تا پخش صداهای هم‌گروه مستقل مدیریت شود.
        # An available channel from the same bus is selected first to manage sounds independently within that group.
        channels = self._bus_channels.get(bus_name)
        try:
            if channels:
                # اول دنبال کانال آزاد بگرد
                chosen = None
                for ch in channels:
                    if not ch.get_busy():
                        chosen = ch
                        break
                if chosen is None:
                    # همه مشغول — روی اولین کانال به‌عنوان fallback
                    # در صورت پر بودن تمام کانال‌ها، کانال اول برای پخش صدای جدید استفاده می‌شود.
                    # If every channel is busy, the first channel is reused for the new sound.
                    chosen = channels[0]
                chosen.play(sound, loops=-1 if loop else 0)
                return True
            else:
                # fallback به play سراسری
                # اگر برای Bus کانالی تخصیص نیافته باشد، از سازوکار پخش سراسری Sound استفاده می‌شود.
                # If no channel is assigned to the bus, Sound's global playback mechanism is used.
                sound.play(loops=-1 if loop else 0)
                return True
        except Exception:
            return False


    def play_music(
        self,
        name: str,
        *,
        loop: bool = True,
        fade_ms: int = 500,
    ) -> bool:
        """
        پخش موسیقی پس‌زمینه با fade-in.

        فقط یک آهنگ می‌تواند همزمان پخش شود. اگر آهنگی در حال پخش
        باشد، ابتدا fade-out و سپس آهنگ جدید پخش می‌شود.
        """
        if not self.enabled or not self._initialized:
            return False

        # اگر همین آهنگ در حال پخش است، کاری نکن
        if self._current_music == name and pygame.mixer.music.get_busy():
            return True

        path = self._resolve_path(name)
        if path is None:
            # فایل موسیقی وجود ندارد — ساکت ادامه بده
            self._current_music = name
            return False

        try:
            # موسیقی قبلی به‌تدریج محو می‌شود و سپس فایل جدید با fade-in پخش خواهد شد.
            # The previous track fades out before the new file is loaded and played with a fade-in.
            pygame.mixer.music.fadeout(max(0, int(fade_ms * 0.5)))
            pygame.mixer.music.load(str(path))
            effective = self.master_volume * self._bus_volume.get(Bus.MUSIC, 1.0)
            # موسیقی از طریق pygame.mixer.music پخش می‌شود؛ ولومش با set_volume
            pygame.mixer.music.set_volume(effective)
            pygame.mixer.music.play(loops=-1 if loop else 0, fade_ms=fade_ms)
            self._current_music = name
            return True
        except Exception:
            return False

    def stop_music(self, *, fade_ms: int = 500) -> None:
        if not self._initialized:
            return
        try:
            pygame.mixer.music.fadeout(max(0, fade_ms))
        except Exception:
            pass
        self._current_music = None

    def pause_music(self) -> None:
        if self._initialized:
            try:
                pygame.mixer.music.pause()
            except Exception:
                pass

    def resume_music(self) -> None:
        if self._initialized:
            try:
                pygame.mixer.music.unpause()
            except Exception:
                pass


    def set_master_volume(self, v: float) -> None:
        # مقدار ورودی محدود می‌شود تا ولوم از بازه‌ی پشتیبانی‌شده خارج نشود.
        # The input value is clamped to keep the volume within the supported range.
        self.master_volume = max(0.0, min(1.0, v))
        self._refresh_music_volume()

    def set_bus_volume(self, bus: str, v: float) -> None:
        self._bus_volume[bus] = max(0.0, min(1.0, v))
        # اعمال فوری روی موسیقی اگر bus موسیقی باشد
        if bus == Bus.MUSIC:
            self._refresh_music_volume()

    def set_music_volume(self, v: float) -> None:
        self.music_volume = max(0.0, min(1.0, v))
        self.set_bus_volume(Bus.MUSIC, v)

    def set_sfx_volume(self, v: float) -> None:
        self.sfx_volume = max(0.0, min(1.0, v))
        self.set_bus_volume(Bus.SFX, v)
        self.set_bus_volume(Bus.SHOOT, v)

    def set_ui_volume(self, v: float) -> None:
        self.ui_volume = max(0.0, min(1.0, v))
        self.set_bus_volume(Bus.UI, v)

    def _refresh_music_volume(self) -> None:
        if not self._initialized:
            return
        try:
            # تغییر ولوم Master یا Bus موسیقی بلافاصله روی موسیقی در حال پخش اعمال می‌شود.
            # Master or music-bus volume changes are immediately applied to the currently playing music.
            effective = self.master_volume * self._bus_volume.get(Bus.MUSIC, 1.0)
            pygame.mixer.music.set_volume(effective)
        except Exception:
            pass


    def mute(self) -> None:
        self.muted = True
        self.stop_music(fade_ms=200)

    def unmute(self) -> None:
        self.muted = False

    def toggle_mute(self) -> bool:
        if self.muted:
            self.unmute()
        else:
            self.mute()
        return self.muted


    def stop_all(self, *, fade_ms: int = 200) -> None:
        """توقف همه‌ی صداهای در حال پخش."""
        if not self._initialized:
            return

        # تمام کانال‌های اختصاص‌یافته به Busها با fade-out متوقف می‌شوند.
        # All channels assigned to the buses are stopped with a fade-out.
        for bus_channels in self._bus_channels.values():
            for ch in bus_channels:
                try:
                    ch.fadeout(max(0, fade_ms))
                except Exception:
                    pass

    def stop_bus(self, bus: str, *, fade_ms: int = 200) -> None:
        """توقف همه‌ی صداهای یک bus."""
        if not self._initialized:
            return
        for ch in self._bus_channels.get(bus, []):
            try:
                ch.fadeout(max(0, fade_ms))
            except Exception:
                pass


    @property
    def is_available(self) -> bool:
        return self._initialized and self.enabled

    @property
    def current_music(self) -> Optional[str]:
        return self._current_music

    def stats(self) -> dict[str, int]:
        """آمار سریع: تعداد صداهای کش‌شده، کانال‌های مشغول و …"""
        # آمار کش از تفکیک مقادیر موفق و ناموفق به دست می‌آید؛ کانال‌های مشغول نیز فقط در صورت فعال بودن mixer شمرده می‌شوند.
        # Cache statistics distinguish successful and failed loads; busy channels are counted only when the mixer is initialized.
        loaded = sum(1 for s in self._cache.values() if s is not None)
        missing = sum(1 for s in self._cache.values() if s is None)
        busy = 0
        if self._initialized:
            for bus_channels in self._bus_channels.values():
                for ch in bus_channels:
                    if ch.get_busy():
                        busy += 1
        return {
            "loaded_sounds": loaded,
            "missing_sounds": missing,
            "busy_channels": busy,
        }


__all__ = ["AudioSystem", "Bus", "SOUND_REGISTRY"]