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


# ─────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────

def _env(i: int, n: int, attack_s: float, decay_s: float,
         curve: float = 2.0) -> float:
    """AD envelope — attack then exponential-ish decay."""
    t = i / SAMPLE_RATE
    a = attack_s
    if t < a:
        return t / a if a > 0 else 1.0
    d = (t - a) / max(decay_s, 1e-6)
    if d >= 1.0:
        return 0.0
    return (1.0 - d) ** curve


def _to_sound(samples: list[float], volume: float = 1.0) -> pygame.mixer.Sound:
    """Convert float samples [-1, 1] to a stereo pygame Sound."""
    buf = array.array("h")
    for s in samples:
        v = max(-1.0, min(1.0, s * volume))
        iv = int(v * 32767)
        buf.append(iv)  # left
        buf.append(iv)  # right
    return pygame.mixer.Sound(buffer=buf.tobytes())


# ─────────────────────────────────────────────────────────────────────
#  Individual synths
# ─────────────────────────────────────────────────────────────────────

def synth_player_shoot() -> pygame.mixer.Sound:
    n = int(0.08 * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = 880.0 - 440.0 * (i / n)
        e = _env(i, n, 0.001, 0.08)
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
        freq = 120.0 - 80.0 * (i / n)
        rumble = math.sin(2 * math.pi * freq * t) * 0.5
        out.append((noise + rumble) * e)
    return _to_sound(out, 0.85)


def synth_enemy_shoot() -> pygame.mixer.Sound:
    n = int(0.10 * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = 440.0 - 220.0 * (i / n)
        e = _env(i, n, 0.001, 0.10)
        out.append(math.sin(2 * math.pi * freq * t) * 0.6 * e)
    return _to_sound(out, 0.35)


def synth_enemy_explode() -> pygame.mixer.Sound:
    n = int(0.4 * SAMPLE_RATE)
    out = []
    for i in range(n):
        e = _env(i, n, 0.001, 0.4, 2.0)
        out.append(random.uniform(-1, 1) * 0.7 * e)
    return _to_sound(out, 0.55)


def synth_wave_start() -> pygame.mixer.Sound:
    n = int(0.5 * SAMPLE_RATE)
    freqs = [523.25, 659.25, 783.99, 1046.50]  # C E G C
    seg = n // len(freqs)
    out = []
    for i in range(n):
        f = freqs[min(i // seg, len(freqs) - 1)]
        t = i / SAMPLE_RATE
        e = _env(i, n, 0.001, 0.5, 1.5)
        out.append(math.sin(2 * math.pi * f * t) * 0.5 * e)
    return _to_sound(out, 0.55)


def synth_powerup_pickup() -> pygame.mixer.Sound:
    n = int(0.3 * SAMPLE_RATE)
    freqs = [659.25, 880.0, 1318.51]  # E A E (arpeggio)
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
    seg = n // 2
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
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


# ─────────────────────────────────────────────────────────────────────
#  Registry
# ─────────────────────────────────────────────────────────────────────

SYNTH_REGISTRY: dict[str, callable] = {
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
    fn = SYNTH_REGISTRY.get(name)
    if fn is None:
        return None
    try:
        return fn()
    except Exception as exc:
        print(f"[sound_synth] failed to synthesize '{name}': {exc}")
        return None


__all__ = ["SYNTH_REGISTRY", "synthesize"]