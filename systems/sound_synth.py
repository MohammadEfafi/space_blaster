"""
systems/sound_synth.py
======================
Procedural sound synthesis — every SFX is generated at runtime.
No .wav / .ogg files needed. Works out of the box on GitHub.

Uses only the Python standard library + pygame.mixer.
"""
from __future__ import annotations

import array
import math
import random

import pygame


SAMPLE_RATE = 44100



def _env(i: int, n: int, attack_s: float, decay_s: float,
         curve: float = 2.0) -> float:
    """AD envelope — attack then exponential-ish decay."""
    # زمان نمونه به ثانیه تبدیل می‌شود تا موقعیت آن در فاز حمله و افت پوش مشخص شود.
    # The sample index is converted to seconds to determine its position in the envelope's attack and decay phases.
    t = i / SAMPLE_RATE
    a = attack_s
    if t < a:
        # در مرحله‌ی حمله، دامنه به‌صورت خطی از صفر به مقدار کامل افزایش پیدا می‌کند.
        # During the attack phase, the amplitude increases linearly from zero to its full value.
        return t / a if a > 0 else 1.0
    # زمان سپری‌شده از پایان حمله نسبت به مدت افت محاسبه می‌شود.
    # The time elapsed since the end of the attack is normalized against the decay duration.
    d = (t - a) / max(decay_s, 1e-6)
    if d >= 1.0:
        return 0.0
    # منحنی توان، افت تدریجی دامنه را کنترل می‌کند و مقدار آن را در انتهای بازه به صفر می‌رساند.
    # The power curve controls the gradual amplitude decay and brings it to zero at the end of the interval.
    return (1.0 - d) ** curve


def _to_sound(samples: list[float], volume: float = 1.0) -> pygame.mixer.Sound:
    """Convert float samples [-1, 1] to a stereo pygame Sound."""
    buf = array.array("h")
    for s in samples:
        # دامنه‌ی هر نمونه پیش از تبدیل به عدد صحیح ۱۶ بیتی، در محدوده‌ی مجاز محدود می‌شود.
        # Each sample's amplitude is clamped to the valid range before conversion to a 16-bit integer.
        v = max(-1.0, min(1.0, s * volume))
        iv = int(v * 32767)
        buf.append(iv)  # left
        buf.append(iv)  # right
    # هر نمونه در هر دو کانال چپ و راست قرار گرفته است؛ بنابراین خروجی استریو با صدای یکسان در دو کانال ساخته می‌شود.
    # Each sample is written to both the left and right channels, producing stereo output with identical audio in both channels.
    return pygame.mixer.Sound(buffer=buf.tobytes())



def synth_player_shoot() -> pygame.mixer.Sound:
    n = int(0.08 * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # فرکانس از ۸۸۰ به ۴۴۰ هرتز کاهش می‌یابد تا صدای شلیک حالت نزولی پیدا کند.
        # The frequency decreases from 880 to 440 Hz to give the shooting sound a descending pitch.
        freq = 880.0 - 440.0 * (i / n)
        e = _env(i, n, 0.001, 0.08)
        # موج سینوسی، صدای اصلی شلیک را می‌سازد و نویز تصادفی به آن بافتی تیزتر اضافه می‌کند.
        # The sine wave forms the main shooting sound, while random noise adds a sharper texture.
        val = math.sin(2 * math.pi * freq * t) * 0.7 * e
        val += random.uniform(-1, 1) * 0.1 * e
        out.append(val)
    return _to_sound(out, 0.45)


def synth_player_hit() -> pygame.mixer.Sound:
    n = int(0.15 * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        e = _env(i, n, 0.001, 0.15, 3.0)
        # ترکیب نویز گسترده با موج سینوسی ۸۰ هرتزی، صدایی ضربه‌ای با مؤلفه‌ی بم ایجاد می‌کند.
        # Combining broadband noise with an 80 Hz sine wave creates an impact sound with a low-frequency component.
        noise = random.uniform(-1, 1) * 0.7
        low = math.sin(2 * math.pi * 80.0 * t) * 0.4
        out.append((noise + low) * e)
    return _to_sound(out, 0.65)


def synth_player_explode() -> pygame.mixer.Sound:
    n = int(0.9 * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        e = _env(i, n, 0.001, 0.9, 1.5)
        noise = random.uniform(-1, 1) * 0.8
        # فرکانس مؤلفه‌ی بم در طول صدا کاهش می‌یابد تا حس فرونشستن و سنگین‌شدن انفجار ایجاد شود.
        # The low-frequency component decreases in frequency over time to create a sinking, heavy explosion effect.
        freq = 120.0 - 80.0 * (i / n)
        rumble = math.sin(2 * math.pi * freq * t) * 0.5
        out.append((noise + rumble) * e)
    return _to_sound(out, 0.85)


def synth_enemy_shoot() -> pygame.mixer.Sound:
    n = int(0.10 * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # کاهش تدریجی فرکانس، صدای شلیک دشمن را از شلیک بازیکن متمایز می‌کند.
        # The gradual frequency decrease helps distinguish the enemy shooting sound from the player's shot.
        freq = 440.0 - 220.0 * (i / n)
        e = _env(i, n, 0.001, 0.10)
        out.append(math.sin(2 * math.pi * freq * t) * 0.6 * e)
    return _to_sound(out, 0.35)


def synth_enemy_explode() -> pygame.mixer.Sound:
    n = int(0.4 * SAMPLE_RATE)
    out = []
    for i in range(n):
        e = _env(i, n, 0.001, 0.4, 2.0)
        # این افکت فقط از نویز تصادفی شکل می‌گیرد و پوش دامنه، شدت آن را در طول زمان کاهش می‌دهد.
        # This effect is generated entirely from random noise, while the amplitude envelope reduces its intensity over time.
        out.append(random.uniform(-1, 1) * 0.7 * e)
    return _to_sound(out, 0.55)


def synth_wave_start() -> pygame.mixer.Sound:
    n = int(0.5 * SAMPLE_RATE)
    freqs = [523.25, 659.25, 783.99, 1046.50]  # C E G C
    # تعداد نمونه‌های هر بخش از تقسیم کل نمونه‌ها بر تعداد نت‌ها به دست می‌آید.
    # The number of samples per segment is calculated by dividing the total sample count by the number of notes.
    seg = n // len(freqs)
    out = []
    for i in range(n):
        # با تقسیم اندیس نمونه بر اندازه‌ی هر بخش، نت فعال انتخاب می‌شود.
        # Dividing the sample index by the segment size selects the currently active note.
        f = freqs[min(i // seg, len(freqs) - 1)]
        t = i / SAMPLE_RATE
        e = _env(i, n, 0.001, 0.5, 1.5)
        out.append(math.sin(2 * math.pi * f * t) * 0.5 * e)
    return _to_sound(out, 0.55)


def synth_powerup_pickup() -> pygame.mixer.Sound:
    n = int(0.3 * SAMPLE_RATE)
    freqs = [659.25, 880.0, 1318.51]  # E A E (arpeggio)
    # مدت هر بخش با توجه به تعداد نت‌ها تعیین می‌شود تا نت‌ها به‌ترتیب پخش شوند.
    # Each segment's duration is determined by the number of notes so they play in sequence.
    seg = n // len(freqs)
    out = []
    for i in range(n):
        f = freqs[min(i // seg, len(freqs) - 1)]
        t = i / SAMPLE_RATE
        e = _env(i, n, 0.001, 0.3)
        out.append(math.sin(2 * math.pi * f * t) * 0.5 * e)
    return _to_sound(out, 0.55)


def synth_powerup_spawn() -> pygame.mixer.Sound:
    n = int(0.2 * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # افزایش تدریجی فرکانس از ۴۰۰ به ۱۲۰۰ هرتز، حس بالا رفتن صدا هنگام ظاهرشدن پاورآپ را ایجاد می‌کند.
        # The gradual frequency increase from 400 to 1200 Hz creates a rising sound as the power-up appears.
        freq = 400.0 + 800.0 * (i / n)
        e = _env(i, n, 0.001, 0.2)
        out.append(math.sin(2 * math.pi * freq * t) * 0.4 * e)
    return _to_sound(out, 0.4)


def synth_ui_move() -> pygame.mixer.Sound:
    n = int(0.03 * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        e = _env(i, n, 0.001, 0.03)
        out.append(math.sin(2 * math.pi * 1200.0 * t) * e)
    return _to_sound(out, 0.25)


def synth_ui_confirm() -> pygame.mixer.Sound:
    n = int(0.15 * SAMPLE_RATE)
    # طول هر بخش، توالی دو نت تأیید را به دو قسمت هم‌اندازه تقسیم می‌کند.
    # The segment length divides the two-note confirmation sequence into two equal parts.
    seg = n // 2
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # نت دوم فرکانس بالاتری دارد و پس از پایان نیمه‌ی اول پخش می‌شود.
        # The second note has a higher frequency and plays after the first half ends.
        f = 880.0 if i < seg else 1318.51
        e = _env(i, n, 0.001, 0.15)
        out.append(math.sin(2 * math.pi * f * t) * 0.5 * e)
    return _to_sound(out, 0.5)


def synth_ui_cancel() -> pygame.mixer.Sound:
    n = int(0.15 * SAMPLE_RATE)
    seg = n // 2
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # نت دوم با فرکانس پایین‌تر، صدای لغو را از صدای تأیید متمایز می‌کند.
        # The second note uses a lower frequency to distinguish the cancellation sound from the confirmation sound.
        f = 440.0 if i < seg else 220.0
        e = _env(i, n, 0.001, 0.15)
        out.append(math.sin(2 * math.pi * f * t) * 0.5 * e)
    return _to_sound(out, 0.5)


def synth_ui_hover() -> pygame.mixer.Sound:
    n = int(0.02 * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        e = _env(i, n, 0.001, 0.02)
        out.append(math.sin(2 * math.pi * 800.0 * t) * e)
    return _to_sound(out, 0.15)



SYNTH_REGISTRY: dict[str, callable] = {
    # نگاشت نام هر افکت به تابع سازنده‌ی آن، امکان درخواست افکت‌ها را از طریق یک شناسه‌ی متنی فراهم می‌کند.
    # Mapping each effect name to its generator function allows effects to be requested through a string identifier.
    "player_shoot":   synth_player_shoot,
    "player_hit":     synth_player_hit,
    "player_explode": synth_player_explode,
    "enemy_shoot":    synth_enemy_shoot,
    "enemy_explode":  synth_enemy_explode,
    "wave_start":     synth_wave_start,
    "powerup_pickup": synth_powerup_pickup,
    "powerup_spawn":  synth_powerup_spawn,
    "ui_move":        synth_ui_move,
    "ui_confirm":     synth_ui_confirm,
    "ui_cancel":      synth_ui_cancel,
    "ui_hover":       synth_ui_hover,
}


def synthesize(name: str):
    """Return a pygame Sound for the given name, or None if unknown."""
    # ابتدا تابع سازنده با استفاده از نام افکت در رجیستری جست‌وجو می‌شود.
    # The generator function is first looked up in the registry using the effect name.
    fn = SYNTH_REGISTRY.get(name)
    if fn is None:
        return None
    try:
        return fn()
    except Exception as exc:
        # خطای ساخت افکت ثبت می‌شود و به‌جای متوقف‌کردن بازی، مقدار None برگردانده می‌شود.
        # A synthesis error is logged, and None is returned instead of interrupting the game.
        print(f"[sound_synth] failed to synthesize '{name}': {exc}")
        return None


__all__ = ["SYNTH_REGISTRY", "synthesize"]