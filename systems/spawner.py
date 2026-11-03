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
from entities.enemies import Enemy, EnemyFactory

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
        self.is_elite: bool = False
        self.is_advanced: bool = False
        self.t: float = 0.0
        self.duration: float = _Timing.ANNOUNCE_DURATION
        self.active: bool = False

    def start(self, wave: int, *, is_boss: bool = False, is_elite: bool = False, is_advanced: bool = False) -> None:
        self.wave = wave
        self.is_boss = is_boss
        self.is_elite = is_elite
        self.is_advanced = is_advanced

    def update(self, dt: float) -> None:
        if not self.active:
            return
        self.t += dt
        if self.t >= self.duration:
            self.active = False

    def draw(self, surface: pygame.Surface, font_big: pygame.font.Font) -> None:
        if not self.active:
            return

        # ---- محاسبه‌ی alpha ----
        t = self.t / self.duration
        if t < 0.2:
            a = t / 0.2
        elif t < 0.75:
            a = 1.0
        else:
            a = 1.0 - (t - 0.75) / 0.25
        a = max(0.0, min(1.0, a))

        # ---- رنگ ----
        if self.is_boss:
            color = S.Palette.ENEMY_BOSS
            text = f"!!  BOSS WAVE {self.wave}  !!"
        elif self.is_advanced:
            color = (255, 100, 255)  # بنفش
            text = f"ADVANCED WAVE {self.wave:02d}"
        elif self.is_elite:
            color = (255, 150, 100)
            text = f"ELITE WAVE {self.wave:02d}"
        else:
            color = S.Palette.HUD_ACCENT
            text = f"WAVE {self.wave:02d}"

        cx = S.Window.WIDTH // 2
        cy = S.Window.HEIGHT // 2 - 60

        # ---- پس‌زمینه‌ی پنل ----
        panel_w = 520
        panel_h = 100
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        
        # گرادیان تیره
        for y in range(panel_h):
            edge_dist = min(y, panel_h - y)
            alpha_factor = min(1.0, edge_dist / 20.0)
            row_alpha = int(180 * alpha_factor * a)
            if row_alpha <= 0:
                continue
            pygame.draw.line(
                panel, (5, 10, 20, row_alpha),
                (0, y), (panel_w, y),
            )
        
        # گوشه‌ها (برشخورده)
        pygame.draw.polygon(panel, (*color, int(200 * a)), [
            (0, panel_h // 2), (30, 0), (panel_w - 30, 0), (panel_w, panel_h // 2),
            (panel_w - 30, panel_h), (30, panel_h),
        ], 2)

        panel_rect = panel.get_rect(center=(cx, cy))
        surface.blit(panel, panel_rect.topleft)

        # ---- متن ----
        pulse = 1.0 + 0.05 * math.sin(self.t * 8.0)
        img = font_big.render(text, True, color)
        
        w = int(img.get_width() * pulse)
        h = int(img.get_height() * pulse)
        img_scaled = pygame.transform.smoothscale(img, (w, h))
        
        if a < 1.0:
            img_scaled.set_alpha(int(255 * a))

        rect = img_scaled.get_rect(center=(cx, cy))

        # ---- سایه‌ی متنی (Outline) برای خوانایی ----
        outline = font_big.render(text, True, (0, 0, 0))
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            shadow = pygame.transform.smoothscale(
                outline, 
                (int(w * 1.02), int(h * 1.02))
            )
            if a < 1.0:
                shadow.set_alpha(int(255 * a))
            surface.blit(shadow, (rect.x - 1 + dx, rect.y - 1 + dy))

        # ---- خطوط تزئینی کناری ----
        line_w = int(180 * a)
        if line_w > 5:
            line_y = cy + h // 2 + 15
            for sign in (-1, 1):
                x1 = cx + sign * (w // 2 + 20)
                x2 = cx + sign * (w // 2 + 20 + line_w)
                pygame.draw.line(surface, (*color, int(200 * a)), (x1, line_y), (x2, line_y), 2)

        surface.blit(img_scaled, rect)


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
        boss_min_wave: int = 7,
    ) -> None:
        self.boss_min_wave: int = boss_min_wave
        self._last_boss_wave: int = 0 
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
        self.finished: bool = False
        self.is_boss_wave: bool = False
        self.is_elite_wave: bool = False
        self.is_advanced_wave: bool = False

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
        """تعداد دشمن‌های این موج — با سقف برای جلوگیری از شلوغی."""
        base = S.WaveCfg.FIRST_ENEMIES
        growth = S.WaveCfg.GROWTH
        count = base + growth * (wave - 1)
        # رشد ملایم‌تر بعد از موج ۸
        if wave > 8:
            count = int(count * (1.0 + (wave - 8) * 0.04))
        # سقف 19 دشمن (قبلاً بی‌نهایت بود)
        return max(3, min(count, 19))

    def _spawn_interval_for_wave(self, wave: int) -> float:
        """فاصله بین spawn تدریجاً کوتاه‌تر می‌شود (تا حد مشخص)."""
        base = _Timing.SPAWN_INTERVAL
        speedup = min(0.55, (wave - 1) * 0.02)
        return max(0.12, base - speedup)

    def _is_boss_wave(self, wave: int) -> bool:
        """موج باس با شانس رندوم — کم و فاصله‌دار."""
        # حداقل ۷ موج قبل از اولین باس
        if wave < self.boss_min_wave:
            return False

        # بعد از هر باس، حداقل ۳ موج فاصله
        if self._last_boss_wave > 0:
            if wave - self._last_boss_wave < 3:
                return False

        # شانس خیلی کم: ۱۵% پایه، حداکثر ۴۵%
        chance = min(0.45, 0.15 + (wave - self.boss_min_wave) * 0.04)
        result = random.random() < chance

        if result:
            self._last_boss_wave = wave

        return result

    # ─────────────────────────────────────────────────────────────────────
    #  جریان موج
    # ─────────────────────────────────────────────────────────────────────

    def _start_next_wave(self) -> None:
        """موج جدید را راه‌اندازی می‌کند."""
        self.wave += 1

        if self.max_wave > 0 and self.wave > self.max_wave:
            self.finished = True
            self.state = SpawnState.IDLE
            return

        # ---- اول باس (چون random داره) ----
        self.is_boss_wave = self._is_boss_wave(self.wave)

          # ---- موج پیشرفته (Advanced) ----
        self.is_advanced_wave = False
        if not self.is_boss_wave:
            if self.wave == 20:
                self.is_advanced_wave = True  # معرفی در لول ۲۰
            elif self.wave > 20 and self.wave % 4 != 0:
                # از لول ۲۱ به بعد با شانس ۲۵٪ (به جز موج‌های الیت)
                if random.random() < 0.25:
                    self.is_advanced_wave = True

        # ---- بعد الیت (فقط اگه باس یا ادونس نیست) ----
        self.is_elite_wave = (
            not self.is_boss_wave
            and not self.is_advanced_wave
            and self.wave >= 4
            and self.wave % 4 == 0
        )

        # ---- تعداد ----
        if self.is_boss_wave:
            self.total_in_wave = 0
        elif self.wave == 20:
            self.total_in_wave = 3  # معرفی: دقیقا ۳ تا
        elif self.is_advanced_wave:
            self.total_in_wave = random.randint(3, 4)  # رندوم: ۳ یا ۴ تا
        elif self.is_elite_wave:
            self.total_in_wave = random.randint(5, 6)
        else:
            self.total_in_wave = self._enemy_count_for_wave(self.wave)

        self.remaining_to_spawn = self.total_in_wave
        self._spawn_timer = 0.0
        self._state_timer = 0.0

        # ---- پیام ----
        self.state = SpawnState.ANNOUNCING
        self.announcement.start(
            self.wave,
            is_boss=self.is_boss_wave,
            is_elite=self.is_elite_wave,
            is_advanced=self.is_advanced_wave,
        )

        # صدای شروع موج
        if self.scene is not None:
            try:
                self.scene.audio.play("wave_start")
                # افکت ویژه‌ی الیت
                if self.is_elite_wave:
                    self.scene.camera.shake(6.0)
                    # فلاش قرمز-نارنجی
                    from systems.particles import ParticleKind
                    self.scene.particles.emit_ring(
                        S.Window.WIDTH // 2, S.Window.HEIGHT // 2,
                        count=30, radius=20, speed=400,
                        color=(255, 150, 100), life=0.8, size=3,
                    )
            except Exception:
                pass

    def _spawn_one(self) -> None:
        """یک دشمن از موج فعلی می‌سازد."""
        try:
            from entities.enemies.base import EnemyKind

            if self.is_advanced_wave:
                if self.wave == 20:
                    # موج معرفی لول ۲۰: دقیقاً یکی از هر کدوم
                    remaining = self.remaining_to_spawn
                    if remaining >= 3:
                        kind = EnemyKind.SENTINEL
                    elif remaining == 2:
                        kind = EnemyKind.SERPENT
                    else:
                        kind = EnemyKind.TITAN
                else:
                    # موج‌های بعدی: رندوم از بین ۳ تای جدید
                    kind = random.choice([
                        EnemyKind.SENTINEL,
                        EnemyKind.SERPENT,
                        EnemyKind.TITAN,
                    ])
                enemy = self.factory.spawn(self.wave, kind=kind)
            elif self.is_elite_wave:
                kind = random.choice([EnemyKind.SPECTER, EnemyKind.BOMBARDIER])
                enemy = self.factory.spawn(self.wave, kind=kind)
            else:
                enemy = self.factory.spawn(self.wave)

            self._spawn_enemy(enemy)
        except Exception as exc:
            print(f"[Spawner] Failed to spawn enemy: {exc}")

    def _spawn_boss(self) -> None:
        """ساخت ۱ تا ۳ باس رندوم (یا Omega از موج ۱۰+)."""
        try:
            from entities.enemies.boss_registry import (
                BOSS_CLASSES, OMEGA_CLASS, get_random_boss,
            )
            if not BOSS_CLASSES:
                return
        except Exception as exc:
            print(f"[Spawner] Boss registry missing: {exc}")
            return

        # ---- شانس Omega (فقط از موج ۱۰) ----
        omega_chance = 0.0
        if self.wave >= 10:
            omega_chance = min(0.35, 0.10 + (self.wave - 10) * 0.04)

        if random.random() < omega_chance:
            # Omega تنها می‌آید
            boss_classes = [OMEGA_CLASS]
            print(f"[Spawner] OMEGA CORE boss incoming!")
        else:
            # حالت عادی: ۱-۳ باس
            count = self._pick_boss_count()
            boss_classes = [get_random_boss() for _ in range(count)]

        positions = self._compute_boss_positions(len(boss_classes))

        for i, (x, sway, phase_offset) in enumerate(positions):
            if i >= len(boss_classes):
                break
            boss_cls = boss_classes[i]
            try:
                boss = boss_cls(x, -150, scene=self.scene)
                boss.set_entry(-150, 0)
                boss.sway_amplitude = sway
                boss.sway_phase_offset = phase_offset
                self._spawn_enemy(boss)
            except Exception as exc:
                print(f"[Spawner] Boss spawn failed ({x:.0f}): {exc}")

        # ریختن پاورآپ
        self._drop_boss_wave_powerups(len(boss_classes))

    def _drop_boss_wave_powerups(self, boss_count: int) -> None:
        """پاورآپ زیاد هنگام شروع باس."""
        if self.scene is None:
            return
        try:
            from entities.powerup import Powerup

            # تعداد: ۳ پاورآپ + ۲ برای هر باس اضافه
            num = 3 + (boss_count - 1) * 2

            positions = []
            for i in range(num):
                x = S.Window.WIDTH * (0.15 + 0.7 * (i / max(1, num - 1)))
                x += random.uniform(-30, 30)
                # بالاتر (بین ۲۵٪ تا ۵۰٪ ارتفاع) — پلیر راحت می‌گیره
                y = random.uniform(S.Window.HEIGHT * 0.25, S.Window.HEIGHT * 0.50)
                positions.append((x, y))

            for (px, py) in positions:
                # آهسته می‌افتند (۱۰ px/s به جای ۹۵) — پلیر وقت داره
                pu = Powerup(px, py, scene=self.scene, fall_speed=12.0)
                self.scene.add_powerup(pu)

            try:
                self.scene.audio.play("powerup_spawn")
            except Exception:
                pass

            print(f"[Spawner] Dropped {num} powerups for boss wave")
        except Exception as exc:
            print(f"[Spawner] Failed to drop powerups: {exc}")

    def _pick_boss_count(self) -> int:
        """تعداد باس بر اساس موج — سختی منطقی."""
        wave = self.wave
        if wave < 10:
            return 1
        if wave < 15:
            return random.choices([1, 2], weights=[70, 30])[0]
        return random.choices([1, 2, 3], weights=[50, 35, 15])[0]

    def _compute_boss_positions(self, count: int) -> list[tuple[float, float, float]]:
        """موقعیت امن هر باس."""
        w = S.Window.WIDTH
        if count == 1:
            return [(w / 2, 140.0, 0.0)]
        if count == 2:
            return [
                (w * 0.30, 90.0, 0.0),
                (w * 0.70, 90.0, math.pi),
            ]
        return [
            (w * 0.20, 70.0, 0.0),
            (w * 0.50, 70.0, math.tau / 3),
            (w * 0.80, 70.0, 2 * math.tau / 3),
        ]

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
        # ---- موج باس ----
        if self.is_boss_wave:
            self._spawn_boss()
            self.state = SpawnState.FIGHTING
            self._state_timer = 0.0
            return

        # ---- زمان‌بندی اسپاون ----
        if self.is_advanced_wave:
            # برای موج‌های ادونس کمی فاصله می‌دیم که کاربر گیج نشه
            interval = 1.2
        elif self.is_elite_wave:
            interval = 0.45
        else:
            interval = self._spawn_interval_for_wave(self.wave)

        self._spawn_timer -= dt
        if self._spawn_timer <= 0.0:
            if self.remaining_to_spawn > 0:
                self._spawn_one()
                self.remaining_to_spawn -= 1
                self._spawn_timer = interval * random.uniform(0.85, 1.15)

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