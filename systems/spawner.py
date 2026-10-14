"""
systems/spawner.py
==================

سیستم مدیریت موج‌ها (Wave Spawner) برای SPACE BLASTER.

این ماژول ریتم بازی را کنترل می‌کند:

    • ساخت و زمان‌بندی دشمن‌ها در هر موج
    • تشخیص پایان موج (همه‌ی دشمن‌ها کشته شدند)
    • مکث دراماتیک بین موج‌ها (Wave Break)
    • پیام «WAVE X» با انیمیشن (announcement)
    • افزایش تدریجی سختی بر اساس شماره‌ی موج
    • پشتیبانی از «موج باس» (هر ۵ موج)
    • امکان spawn پله‌ای (staggered) برای حس طبیعی

معماری:
    Spawner مستقل از Scene است و فقط با یک «callback» دشمن می‌سازد
    و به لیست دشمن‌ها اضافه می‌کند. این باعث می‌شود تست و ریپلی آن
    ساده باشد.

    وضعیت‌های Spawner:
        IDLE        — بی‌کار (بین موج‌ها یا پایان)
        ANNOUNCING  — نمایش پیام «WAVE X»
        SPAWNING    — در حال تولید دشمن‌های موج
        FIGHTING    — منتظر کشته شدن همه‌ی دشمن‌ها
        BREAK       — مکث کوتاه پس از پایان موج
        BOSS_INTRO  — آماده‌سازی موج باس (آینده)
"""

from __future__ import annotations

import math
import random
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable, Optional

import pygame

from core import settings as S
from entities.enemy import Enemy, EnemyFactory

if TYPE_CHECKING:
    from scenes.gameplay import GameplayScene


# ═══════════════════════════════════════════════════════════════════════════
#  وضعیت‌های Spawner
# ═══════════════════════════════════════════════════════════════════════════

class SpawnState(Enum):
    IDLE       = auto()
    ANNOUNCING = auto()
    SPAWNING   = auto()
    FIGHTING   = auto()
    BREAK      = auto()


# ═══════════════════════════════════════════════════════════════════════════
#  پیکربندی زمان‌بندی
# ═══════════════════════════════════════════════════════════════════════════

class _Timing:
    """زمان‌بندی‌های موج (ثانیه)."""
    ANNOUNCE_DURATION: float = 1.6    # نمایش پیام WAVE X
    SPAWN_INTERVAL:    float = 0.28   # فاصله بین دو spawn
    BREAK_DURATION:    float = 1.6    # مکث بین موج‌ها
    FIRST_DELAY:       float = 0.8    # تاخیر اولیه قبل از شروع


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس WaveAnnouncement
# ═══════════════════════════════════════════════════════════════════════════

class WaveAnnouncement:
    """
    پیام «WAVE X» با انیمیشن ورود/خروج نرم.
    شامل یک خط تزئینی و متن پالسی است.
    """

    def __init__(self) -> None:
        self.wave: int = 0
        self.is_boss: bool = False
        self.t: float = 0.0
        self.duration: float = _Timing.ANNOUNCE_DURATION
        self.active: bool = False

    def start(self, wave: int, *, is_boss: bool = False) -> None:
        self.wave = wave
        self.is_boss = is_boss
        self.t = 0.0
        self.active = True

    def update(self, dt: float) -> None:
        if not self.active:
            return
        self.t += dt
        if self.t >= self.duration:
            self.active = False

    def draw(self, surface: pygame.Surface, font_big: pygame.font.Font) -> None:
        if not self.active:
            return

        # ---- alpha در ورود و خروج ----
        t = self.t / self.duration
        # نیمه‌ی اول: ورود نرم، نیمه‌ی دوم: محو شدن
        if t < 0.25:
            a = t / 0.25
        elif t < 0.75:
            a = 1.0
        else:
            a = 1.0 - (t - 0.75) / 0.25
        a = max(0.0, min(1.0, a))

        # ---- پالس ----
        pulse = 1.0 + 0.05 * math.sin(self.t * 8.0)

        # ---- رنگ ----
        if self.is_boss:
            color = S.Palette.ENEMY_BOSS
            text = f"⚠ BOSS WAVE {self.wave} ⚠"
        else:
            color = S.Palette.HUD_ACCENT
            text = f"WAVE {self.wave}"

        cx = S.Window.WIDTH // 2
        cy = S.Window.HEIGHT // 2 - 40

        # ---- متن با اسکیل ----
        img = font_big.render(text, True, color)
        w = int(img.get_width() * pulse)
        h = int(img.get_height() * pulse)
        img_scaled = pygame.transform.smoothscale(img, (w, h))
        if a < 1.0:
            img_scaled.set_alpha(int(255 * a))

        rect = img_scaled.get_rect(center=(cx, cy))

        # ---- هاله‌ی رنگی ----
        if a > 0.1:
            for layer in range(3, 0, -1):
                glow = pygame.transform.smoothscale(img, (w + layer * 14, h + layer * 14))
                glow_surf = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
                glow_surf.blit(glow, (0, 0))
                glow_surf.set_alpha(int(30 * a))
                surface.blit(
                    glow_surf,
                    glow_surf.get_rect(center=(cx, cy)),
                    special_flags=pygame.BLEND_RGBA_ADD,
                )

        surface.blit(img_scaled, rect)

        # ---- خط تزئینی زیر متن ----
        line_w = int(320 * min(1.0, a * 1.4))
        line_y = cy + 40
        if line_w > 4:
            x1 = cx - line_w // 2
            x2 = cx + line_w // 2
            pygame.draw.line(surface, color, (x1, line_y), (x2, line_y), 2)
            # نقطه‌های درخشان
            pygame.draw.circle(surface, color, (x1, line_y), 3)
            pygame.draw.circle(surface, color, (x2, line_y), 3)


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس Spawner
# ═══════════════════════════════════════════════════════════════════════════

class Spawner:
    """
    مدیر موج‌های بازی.

    پارامترها:
        scene         — رفرنس به GameplayScene (برای دسترسی به لیست دشمن‌ها)
        spawn_enemy   — تابع callback برای افزودن دشمن (انعطاف‌پذیر برای تست)
        boss_every    — هر چند موج یک باس می‌آید (0 = بدون باس)
        max_wave      — سقف موج (0 = بی‌نهایت)

    استفاده:
        spawner = Spawner(scene, spawn_enemy=scene.add_enemy)
        spawner.start()
        # در هر فریم:
        spawner.update(dt, alive_enemies_count=len(scene.enemies))
    """

    def __init__(
        self,
        scene: Optional["GameplayScene"] = None,
        *,
        spawn_enemy: Optional[Callable[[Enemy], None]] = None,
        boss_every: int = 5,
        max_wave: int = 0,
    ) -> None:
        self.scene = scene
        self.factory = EnemyFactory(scene)

        # --- callback ---
        if spawn_enemy is None and scene is not None:
            spawn_enemy = getattr(scene, "add_enemy", None)
        self._spawn_enemy: Callable[[Enemy], None] = spawn_enemy or (lambda e: None)

        # --- پیکربندی ---
        self.boss_every: int = boss_every
        self.max_wave: int = max_wave

        # --- وضعیت ---
        self.state: SpawnState = SpawnState.IDLE
        self.wave: int = 0
        self.remaining_to_spawn: int = 0
        self.total_in_wave: int = 0
        self._spawn_timer: float = 0.0
        self._state_timer: float = 0.0
        self._first_delay: float = _Timing.FIRST_DELAY

        # --- انیمیشن پیام ---
        self.announcement = WaveAnnouncement()

        # --- فلگ‌ها ---
        self.finished: bool = False    # اگر به سقف موج رسیدیم
        self.is_boss_wave: bool = False

    # ─────────────────────────────────────────────────────────────────────
    #  API عمومی
    # ─────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """شروع cycle موج‌ها از موج ۱."""
        self.wave = 0
        self.state = SpawnState.IDLE
        self.finished = False
        self._first_delay = _Timing.FIRST_DELAY
        self._state_timer = 0.0
        self.announcement.active = False

    def stop(self) -> None:
        """توقف کامل."""
        self.state = SpawnState.IDLE
        self.finished = True

    def force_next_wave(self) -> None:
        """
        برای دیباگ: پرش به موج بعدی بدون نیاز به کشتن همه‌ی دشمن‌ها.
        """
        self.state = SpawnState.BREAK
        self._state_timer = 0.0

    # ─────────────────────────────────────────────────────────────────────
    #  محاسبه‌ی سختی
    # ─────────────────────────────────────────────────────────────────────

    def _enemy_count_for_wave(self, wave: int) -> int:
        """تعداد دشمن‌های این موج با فرمول رشد تدریجی."""
        base = S.WaveCfg.FIRST_ENEMIES
        growth = S.WaveCfg.GROWTH
        # رشد خطی برای موج‌های پایین، سپس کمی تندتر
        count = base + growth * (wave - 1)
        # موج‌های بالاتر یه ضریب کوچیک می‌خورن
        if wave > 8:
            count = int(count * (1.0 + (wave - 8) * 0.08))
        return max(3, count)

    def _spawn_interval_for_wave(self, wave: int) -> float:
        """فاصله بین spawn تدریجاً کوتاه‌تر می‌شود (تا حد مشخص)."""
        base = _Timing.SPAWN_INTERVAL
        speedup = min(0.55, (wave - 1) * 0.02)
        return max(0.12, base - speedup)

    def _is_boss_wave(self, wave: int) -> bool:
        return self.boss_every > 0 and wave > 0 and wave % self.boss_every == 0

    # ─────────────────────────────────────────────────────────────────────
    #  جریان موج
    # ─────────────────────────────────────────────────────────────────────

    def _start_next_wave(self) -> None:
        """موج جدید را راه‌اندازی می‌کند."""
        self.wave += 1

        # سقف موج
        if self.max_wave > 0 and self.wave > self.max_wave:
            self.finished = True
            self.state = SpawnState.IDLE
            return

        self.is_boss_wave = self._is_boss_wave(self.wave)

        # تعداد
        self.total_in_wave = self._enemy_count_for_wave(self.wave)
        if self.is_boss_wave:
            # موج باس: دشمن‌های کمتری از معمول، ولی باس وسطشون
            self.total_in_wave = max(3, self.total_in_wave // 2)

        self.remaining_to_spawn = self.total_in_wave
        self._spawn_timer = 0.0
        self._state_timer = 0.0

        # نمایش پیام
        self.state = SpawnState.ANNOUNCING
        self.announcement.start(self.wave, is_boss=self.is_boss_wave)

        # صدای شروع موج
        if self.scene is not None:
            try:
                self.scene.audio.play("wave_start")
            except Exception:
                pass

    def _spawn_one(self) -> None:
        """یک دشمن از موج فعلی می‌سازد."""
        try:
            enemy = self.factory.spawn(self.wave)
            self._spawn_enemy(enemy)
        except Exception as exc:
            # در صورت بروز خطا، فقط لاگ می‌کنیم
            print(f"[Spawner] Failed to spawn enemy: {exc}")

    def _spawn_boss(self) -> None:
        """
        Hook برای ساخت باس. تا زمانی که Boss کلاس نداشته باشیم،
        فقط یک Tank خیلی قوی می‌سازیم (placeholder).
        """
        # TODO: وقتی entities/boss.py ساخته شد، از Boss استفاده کن.
        try:
            # فعلاً ۳ تا Tank سخت جای باس
            for _ in range(3):
                tank = self.factory.spawn(self.wave, kind=None)
                self._spawn_enemy(tank)
        except Exception as exc:
            print(f"[Spawner] Failed to spawn boss: {exc}")

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update(self, dt: float, *, alive_enemies: int) -> None:
        """
        به‌روزرسانی Spawner.

        پارامتر alive_enemies: تعداد دشمن‌های زنده‌ی روی صفحه.
        مسئولیت شمارش با Scene است چون Spawner نباید لیست‌ها را
        بپیماید.
        """
        self.announcement.update(dt)

        if self.finished:
            return

        # ---- تاخیر اولیه ----
        if self._first_delay > 0.0:
            self._first_delay -= dt
            if self._first_delay <= 0.0:
                self._start_next_wave()
            return

        self._state_timer += dt

        # ---- ماشین حالت ----
        if self.state == SpawnState.ANNOUNCING:
            self._update_announcing()
        elif self.state == SpawnState.SPAWNING:
            self._update_spawning(dt)
        elif self.state == SpawnState.FIGHTING:
            self._update_fighting(alive_enemies)
        elif self.state == SpawnState.BREAK:
            self._update_break()

    # ── وضعیت: نمایش پیام ----
    def _update_announcing(self) -> None:
        if self._state_timer >= _Timing.ANNOUNCE_DURATION * 0.7:
            # کمی قبل از پایان پیام، spawn شروع می‌شود
            self.state = SpawnState.SPAWNING
            self._state_timer = 0.0
            self._spawn_timer = 0.0

    # ── وضعیت: تولید دشمن ----
    def _update_spawning(self, dt: float) -> None:
        interval = self._spawn_interval_for_wave(self.wave)

        self._spawn_timer -= dt
        if self._spawn_timer <= 0.0:
            # در موج باس، وقتی نیمی spawn شد، باس ظاهر می‌شود
            if self.is_boss_wave:
                half = self.total_in_wave // 2
                if self.remaining_to_spawn == self.total_in_wave - half:
                    self._spawn_boss()

            if self.remaining_to_spawn > 0:
                self._spawn_one()
                self.remaining_to_spawn -= 1
                self._spawn_timer = interval * random.uniform(0.75, 1.25)

        if self.remaining_to_spawn <= 0:
            self.state = SpawnState.FIGHTING
            self._state_timer = 0.0

    # ── وضعیت: منتظر پاک‌سازی ----
    def _update_fighting(self, alive: int) -> None:
        if alive <= 0:
            # موج تموم شد
            self.state = SpawnState.BREAK
            self._state_timer = 0.0

    # ── وضعیت: مکث بین موج‌ها ----
    def _update_break(self) -> None:
        if self._state_timer >= _Timing.BREAK_DURATION:
            self._start_next_wave()

    # ─────────────────────────────────────────────────────────────────────
    #  رندر
    # ─────────────────────────────────────────────────────────────────────

    def draw_announcement(
        self,
        surface: pygame.Surface,
        font_big: pygame.font.Font,
    ) -> None:
        """رسم پیام موج جاری (اگر فعال باشد)."""
        self.announcement.draw(surface, font_big)

    # ─────────────────────────────────────────────────────────────────────
    #  اطلاعات وضعیت (برای HUD)
    # ─────────────────────────────────────────────────────────────────────

    @property
    def current_wave(self) -> int:
        return max(1, self.wave)

    @property
    def is_between_waves(self) -> bool:
        return self.state in (SpawnState.BREAK, SpawnState.ANNOUNCING)

    @property
    def enemies_left_in_wave(self) -> int:
        return self.remaining_to_spawn


__all__ = ["Spawner", "SpawnState", "WaveAnnouncement"]