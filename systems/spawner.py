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



class SpawnState(Enum):
    IDLE       = auto()
    ANNOUNCING = auto()
    SPAWNING   = auto()
    FIGHTING   = auto()
    BREAK      = auto()




class _Timing:
    """زمان‌بندی‌های موج (ثانیه)."""
    ANNOUNCE_DURATION: float = 1.6    # نمایش پیام WAVE X
    SPAWN_INTERVAL:    float = 0.28   # فاصله بین دو spawn
    BREAK_DURATION:    float = 1.6    # مکث بین موج‌ها
    FIRST_DELAY:       float = 0.8    # تاخیر اولیه قبل از شروع




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
        # مشخصات موج جدید برای انتخاب متن و ظاهر مناسب پیام ذخیره می‌شوند.
        # The new wave properties are stored to select the appropriate announcement text and appearance.
        self.wave = wave
        self.is_boss = is_boss
        self.is_elite = is_elite
        self.is_advanced = is_advanced
        self.active = True     # ← اضافه کن
        self.t = 0.0           # ← اضافه کن

    def update(self, dt: float) -> None:
        if not self.active:
            return
        # زمان انیمیشن با delta time افزایش می‌یابد تا مستقل از نرخ فریم باشد.
        # The animation timer advances by delta time so its duration is independent of the frame rate.
        self.t += dt
        if self.t >= self.duration:
            self.active = False

    def draw(self, surface: pygame.Surface, font_big: pygame.font.Font) -> None:
        if not self.active:
            return

        # ---- محاسبه‌ی alpha ----
        # مقدار شفافیت در ابتدای نمایش افزایش می‌یابد، در میانه ثابت می‌ماند و در پایان کاهش پیدا می‌کند.
        # Alpha increases at the beginning, remains constant in the middle, and decreases toward the end.
        t = self.t / self.duration
        if t < 0.2:
            a = t / 0.2
        elif t < 0.75:
            a = 1.0
        else:
            a = 1.0 - (t - 0.75) / 0.25
        # محدودسازی شفافیت از خروج مقدار آن از بازه‌ی معتبر جلوگیری می‌کند.
        # Clamping alpha prevents its value from exceeding the valid range.
        a = max(0.0, min(1.0, a))

        # ---- رنگ ----
        # نوع موج تعیین می‌کند که پیام با چه رنگ و متنی نمایش داده شود.
        # The wave type determines the color and text used by the announcement.
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

        # مرکز پیام نسبت به ابعاد پنجره محاسبه می‌شود تا در اندازه‌های مختلف صفحه وسط‌چین بماند.
        # The announcement center is calculated from the window dimensions to keep it centered at different screen sizes.
        cx = S.Window.WIDTH // 2
        cy = S.Window.HEIGHT // 2 - 60

        # ---- پس‌زمینه‌ی پنل ----
        panel_w = 520
        panel_h = 100
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)

        # گرادیان تیره
        # شفافیت ردیف‌های پنل بر اساس فاصله از لبه‌ها تغییر می‌کند تا پس‌زمینه حالت محوشونده داشته باشد.
        # Each panel row's transparency depends on its distance from the edges, creating a fading background effect.
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
        # چندضلعی فقط با ضخامت خط رسم می‌شود تا قاب تزئینی پنل بدون پوشاندن پس‌زمینه شکل بگیرد.
        # The polygon is drawn as an outline so the decorative panel frame does not cover its background.
        pygame.draw.polygon(panel, (*color, int(200 * a)), [
            (0, panel_h // 2), (30, 0), (panel_w - 30, 0), (panel_w, panel_h // 2),
            (panel_w - 30, panel_h), (30, panel_h),
        ], 2)

        panel_rect = panel.get_rect(center=(cx, cy))
        surface.blit(panel, panel_rect.topleft)

        # ---- متن ----
        # تابع سینوسی، اندازه‌ی متن را به‌آرامی تغییر می‌دهد تا جلوه‌ی ضربانی ایجاد شود.
        # The sine function gently varies the text size to create a pulsing effect.
        pulse = 1.0 + 0.05 * math.sin(self.t * 8.0)
        img = font_big.render(text, True, color)

        w = int(img.get_width() * pulse)
        h = int(img.get_height() * pulse)
        img_scaled = pygame.transform.smoothscale(img, (w, h))

        if a < 1.0:
            img_scaled.set_alpha(int(255 * a))

        rect = img_scaled.get_rect(center=(cx, cy))

        # ---- سایه‌ی متنی (Outline) برای خوانایی ----
        # متن مشکی در چند موقعیت اطراف متن اصلی رسم می‌شود تا حاشیه‌ای خوانا ایجاد کند.
        # Black text is drawn at several surrounding offsets to create a readable outline.
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
        # طول خطوط با شفافیت پیام هماهنگ می‌شود تا هنگام محوشدن پیام، خطوط نیز کوتاه شوند.
        # The line length follows the announcement's alpha so the lines also shrink as the message fades out.
        line_w = int(180 * a)
        if line_w > 5:
            line_y = cy + h // 2 + 15
            for sign in (-1, 1):
                x1 = cx + sign * (w // 2 + 20)
                x2 = cx + sign * (w // 2 + 20 + line_w)
                pygame.draw.line(surface, (*color, int(200 * a)), (x1, line_y), (x2, line_y), 2)

        surface.blit(img_scaled, rect)




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
        boss_every: int = S.WaveCfg.BOSS_EVERY,
        max_wave: int = 0,
        boss_min_wave: int = S.WaveCfg.BOSS_MIN_WAVE,
    ) -> None:
        self.boss_min_wave: int = boss_min_wave
        self._last_boss_wave: int = 0 
        self.scene = scene
        self.factory = EnemyFactory(scene)

        # --- callback ---
        # اگر callback مستقیماً داده نشده باشد، متد add_enemy از Scene به‌عنوان جایگزین استفاده می‌شود.
        # If no callback is provided explicitly, the Scene's add_enemy method is used as a fallback.
        if spawn_enemy is None and scene is not None:
            spawn_enemy = getattr(scene, "add_enemy", None)
        # در نبود هر دو گزینه، تابع بی‌اثری قرار می‌گیرد تا فراخوانی callback باعث خطا نشود.
        # If neither option is available, a no-op function is assigned to prevent callback calls from raising errors.
        self._spawn_enemy: Callable[[Enemy], None] = spawn_enemy or (lambda e: None)

        # --- پیکربندی ---
        self.boss_every: int = boss_every
        self.max_wave: int = max_wave

        # --- وضعیت ---
        # این فیلدها وضعیت فعلی چرخه‌ی موج و زمان‌بندی تولید دشمن‌ها را نگهداری می‌کنند.
        # These fields track the current wave cycle state and enemy spawning timers.
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



    def start(self) -> None:
        """شروع cycle موج‌ها از موج ۱."""
        # شمارنده‌ها و وضعیت چرخه بازنشانی می‌شوند تا اجرای موج‌ها از ابتدا آغاز شود.
        # The counters and cycle state are reset so wave progression can start from the beginning.
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
        # با ورود به وضعیت BREAK و صفرکردن تایمر، مسیر عادی شروع موج بعدی فعال می‌شود.
        # Entering the BREAK state and resetting its timer triggers the normal next-wave transition.
        self.state = SpawnState.BREAK
        self._state_timer = 0.0



    def _enemy_count_for_wave(self, wave: int) -> int:
        """تعداد دشمن‌های این موج — با سقف برای جلوگیری از شلوغی."""
        # تعداد پایه با توجه به شماره‌ی موج و ضریب رشد تنظیم‌شده افزایش پیدا می‌کند.
        # The base enemy count increases according to the wave number and the configured growth factor.
        base = S.WaveCfg.FIRST_ENEMIES
        growth = S.WaveCfg.GROWTH
        count = base + growth * (wave - 1)
        # رشد ملایم‌تر بعد از موج ۸
        if wave > 8:
            # پس از موج هشتم، افزایش تعداد با ضریب تدریجی ملایم‌تری اعمال می‌شود.
            # After wave eight, the enemy count receives a gentler progressive increase.
            count = int(count * (1.0 + (wave - 8) * 0.04))
        # سقف 19 دشمن (قبلاً بی‌نهایت بود)
        # نتیجه بین حداقل سه دشمن و حداکثر تعیین‌شده در تنظیمات محدود می‌شود.
        # The result is clamped between a minimum of three enemies and the configured maximum.
        return max(3, min(count, S.WaveCfg.MAX_ENEMIES_IN_WAVE))

    def _spawn_interval_for_wave(self, wave: int) -> float:
        """فاصله بین spawn تدریجاً کوتاه‌تر می‌شود (تا حد مشخص)."""
        # با افزایش شماره‌ی موج، فاصله‌ی تولید کاهش می‌یابد؛ اما مقدار کاهش و فاصله‌ی نهایی هر دو محدود هستند.
        # As the wave number increases, the spawn interval decreases, while both the reduction and final interval remain bounded.
        base = _Timing.SPAWN_INTERVAL
        speedup = min(0.55, (wave - 1) * 0.02)
        return max(0.12, base - speedup)

    def _is_boss_wave(self, wave: int) -> bool:
        """موج باس با شانس رندوم — کم و فاصله‌دار."""
        # حداقل ۷ موج قبل از اولین باس
        if wave < self.boss_min_wave:
            return False

        # بعد از هر باس، حداقل ۳ موج فاصله
        # فاصله‌ی موج فعلی از آخرین موج باس بررسی می‌شود تا باس‌ها بیش از حد نزدیک نباشند.
        # The distance from the last boss wave is checked to prevent boss waves from occurring too close together.
        if self._last_boss_wave > 0:
            if wave - self._last_boss_wave < S.WaveCfg.BOSS_MIN_GAP:
                return False

        # شانس خیلی کم: ۱۵% پایه، حداکثر ۴۵%
        # احتمال پایه با پیشروی موج‌ها افزایش می‌یابد، اما از سقف تعیین‌شده فراتر نمی‌رود.
        # The base probability increases as waves progress but never exceeds the configured cap.
        chance = min(0.45, 0.15 + (wave - self.boss_min_wave) * 0.04)
        result = random.random() < chance

        if result:
            self._last_boss_wave = wave

        return result



    def _start_next_wave(self) -> None:
        """موج جدید را راه‌اندازی می‌کند."""
        # شماره‌ی موج پیش از بررسی محدودیت نهایی افزایش پیدا می‌کند.
        # The wave number is incremented before checking the maximum wave limit.
        self.wave += 1

        # اگر سقف موج فعال باشد و از آن عبور کنیم، چرخه با وضعیت IDLE پایان می‌یابد.
        # If a maximum wave is configured and exceeded, the cycle finishes in the IDLE state.
        if self.max_wave > 0 and self.wave > self.max_wave:
            self.finished = True
            self.state = SpawnState.IDLE
            return

        # ---- اول باس (چون random داره) ----
        # ابتدا نوع باس بودن موج مشخص می‌شود تا موج‌های باس با انواع ویژه‌ی دیگر تداخل نداشته باشند.
        # Boss-wave status is determined first so boss waves do not overlap with other special wave types.
        self.is_boss_wave = self._is_boss_wave(self.wave)

          # ---- موج پیشرفته (Advanced) ----
        self.is_advanced_wave = False
        if not self.is_boss_wave:
            # موج معرفی به‌صورت قطعی پیشرفته است؛ موج‌های بالاتر از ۲۰ نیز طبق شرط و احتمال مشخص بررسی می‌شوند.
            # The introduction wave is always advanced; waves above 20 are also evaluated using the configured condition and probability.
            if self.wave == S.WaveCfg.ADVANCED_INTRO_WAVE:
                self.is_advanced_wave = True
            elif self.wave > 20 and self.wave % 4 != 0:
                # از لول ۲۱ به بعد با شانس ۲۵٪ (به جز موج‌های الیت)
                if random.random() < 0.25:
                    self.is_advanced_wave = True

        # ---- بعد الیت (فقط اگه باس یا ادونس نیست) ----
        # موج الیت فقط زمانی انتخاب می‌شود که موج فعلی باس یا پیشرفته نباشد.
        # An elite wave is selected only when the current wave is neither a boss wave nor an advanced wave.
        self.is_elite_wave = (
            not self.is_boss_wave
            and not self.is_advanced_wave
            and self.wave >= 4
            and self.wave % S.WaveCfg.ELITE_INTERVAL == 0
        )

        # ---- تعداد ----
        # تعداد دشمن‌ها بر اساس نوع موج تعیین می‌شود؛ موج باس تولید عادی ندارد و موج‌های ویژه تعداد مشخصی دارند.
        # The enemy count depends on the wave type; boss waves skip regular spawning, while special waves use dedicated counts.
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

        # شمارنده‌ی باقی‌مانده با تعداد کل موج همگام می‌شود و تایمرهای مربوط به موج جدید بازنشانی می‌شوند.
        # The remaining count is synchronized with the wave total, and timers associated with the new wave are reset.
        self.remaining_to_spawn = self.total_in_wave
        self._spawn_timer = 0.0
        self._state_timer = 0.0

        # ---- پیام ----
        # پیش از آغاز تولید دشمن‌ها، وضعیت نمایش پیام فعال می‌شود.
        # The announcement state is activated before enemy spawning begins.
        self.state = SpawnState.ANNOUNCING
        self.announcement.start(
            self.wave,
            is_boss=self.is_boss_wave,
            is_elite=self.is_elite_wave,
            is_advanced=self.is_advanced_wave,
        )

        # صدای شروع موج
        # افکت‌های صوتی و تصویری موج فقط در صورت وجود Scene اجرا می‌شوند.
        # Wave audio and visual effects are triggered only when a Scene is available.
        if self.scene is not None:
            try:
                self.scene.audio.play("wave_start")
                # افکت ویژه‌ی الیت
                if self.is_elite_wave:
                    self.scene.camera.shake(6.0)
                    # فلاش قرمز-نارنجی
                    # ذرات به‌صورت حلقه‌ای از مرکز صفحه منتشر می‌شوند تا شروع موج الیت برجسته شود.
                    # Particles are emitted in a ring from the screen center to emphasize the start of an elite wave.
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

            # انتخاب نوع دشمن به نوع موج وابسته است؛ موج‌های معمولی از مسیر پیش‌فرض Factory استفاده می‌کنند.
            # Enemy selection depends on the wave type; regular waves use the Factory's default spawning path.
            if self.is_advanced_wave:
                if self.wave == 20:
                    # موج معرفی لول ۲۰: دقیقاً یکی از هر کدوم
                    # شمارنده‌ی باقی‌مانده ترتیب انتخاب سه نوع دشمن معرفی‌شده را مشخص می‌کند.
                    # The remaining spawn count determines the selection order of the three introduced enemy types.
                    remaining = self.remaining_to_spawn
                    if remaining >= 3:
                        kind = EnemyKind.SENTINEL
                    elif remaining == 2:
                        kind = EnemyKind.SERPENT
                    else:
                        kind = EnemyKind.TITAN
                else:
                    # موج‌های بعدی: رندوم از بین ۳ تای جدید
                    # در موج‌های پیشرفته‌ی بعدی، یکی از سه نوع دشمن ویژه به‌صورت تصادفی انتخاب می‌شود.
                    # In later advanced waves, one of the three special enemy types is selected randomly.
                    kind = random.choice([
                        EnemyKind.SENTINEL,
                        EnemyKind.SERPENT,
                        EnemyKind.TITAN,
                    ])
                enemy = self.factory.spawn(self.wave, kind=kind)
            elif self.is_elite_wave:
                # دشمن‌های موج الیت از میان دو نوع مشخص انتخاب می‌شوند.
                # Elite-wave enemies are selected from two designated enemy types.
                kind = random.choice([EnemyKind.SPECTER, EnemyKind.BOMBARDIER])
                enemy = self.factory.spawn(self.wave, kind=kind)
            else:
                enemy = self.factory.spawn(self.wave)

            # دشمن ساخته‌شده از طریق callback به Scene یا مصرف‌کننده‌ی تعیین‌شده تحویل داده می‌شود.
            # The created enemy is passed to the Scene or designated consumer through the callback.
            self._spawn_enemy(enemy)
        except Exception as exc:
            print(f"[Spawner] Failed to spawn enemy: {exc}")

    def _spawn_boss(self) -> None:
        """ساخت ۱ تا ۳ باس رندوم (یا Omega از موج ۱۰+)."""
        # رجیستری باس‌ها به‌صورت محلی وارد می‌شود تا وابستگی آن فقط هنگام نیاز بارگذاری شود.
        # The boss registry is imported locally so its dependency is loaded only when needed.
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
        # احتمال انتخاب Omega از موج تعیین‌شده آغاز می‌شود و با افزایش موج تا سقف مشخص رشد می‌کند.
        # The chance of selecting Omega starts at the configured wave and increases with wave progression up to a fixed cap.
        omega_chance = 0.0
        if self.wave >= S.WaveCfg.BOSS_OMEGA_MIN_WAVE:
            omega_chance = min(
                0.35,
                0.10 + (self.wave - S.WaveCfg.BOSS_OMEGA_MIN_WAVE) * 0.04,
            )

        if random.random() < omega_chance:
            # Omega تنها می‌آید
            boss_classes = [OMEGA_CLASS]
            print(f"[Spawner] OMEGA CORE boss incoming!")
        else:
            # حالت عادی: ۱-۳ باس
            # در حالت عادی، تعداد باس‌ها ابتدا تعیین می‌شود و سپس برای هر جایگاه یک کلاس تصادفی انتخاب می‌شود.
            # In the regular case, the boss count is determined first, then a random class is selected for each position.
            count = self._pick_boss_count()
            boss_classes = [get_random_boss() for _ in range(count)]

        # جایگاه‌های حرکتی باس‌ها متناسب با تعداد انتخاب‌شده محاسبه می‌شوند.
        # Boss movement positions are calculated according to the selected boss count.
        positions = self._compute_boss_positions(len(boss_classes))

        for i, (x, sway, phase_offset) in enumerate(positions):
            if i >= len(boss_classes):
                break
            boss_cls = boss_classes[i]
            try:
                # باس خارج از بالای صفحه ساخته می‌شود و سپس اطلاعات ورود و حرکت نوسانی آن تنظیم می‌شود.
                # The boss is created above the screen, then its entry and oscillating movement properties are configured.
                boss = boss_cls(x, -150, scene=self.scene)
                boss.set_entry(-150, boss.ENTRY_Y)
                boss.sway_amplitude = sway
                boss.sway_phase_offset = phase_offset
                self._spawn_enemy(boss)
            except Exception as exc:
                print(f"[Spawner] Boss spawn failed ({x:.0f}): {exc}")

        # ریختن پاورآپ
        # تعداد پاورآپ‌های پشتیبانی‌شده به تعداد باس‌های موج وابسته است.
        # The number of power-ups provided depends on the number of bosses in the wave.
        self._drop_boss_wave_powerups(len(boss_classes))

    def _drop_boss_wave_powerups(self, boss_count: int) -> None:
        """پاورآپ زیاد هنگام شروع باس."""
        if self.scene is None:
            return
        try:
            from entities.powerup import Powerup

            # تعداد: ۳ پاورآپ + ۲ برای هر باس اضافه
            # جایگاه‌های افقی در بخش گسترده‌ای از عرض صفحه توزیع می‌شوند تا پاورآپ‌ها نزدیک به هم قرار نگیرند.
            # Horizontal positions are distributed across a broad portion of the screen to prevent power-ups from clustering together.
            num = 3 + (boss_count - 1) * 2

            positions = []
            for i in range(num):
                x = S.Window.WIDTH * (0.15 + 0.7 * (i / max(1, num - 1)))
                x += random.uniform(-30, 30)
                # بالاتر (بین ۲۵٪ تا ۵۰٪ ارتفاع) — پلیر راحت می‌گیره
                # موقعیت عمودی به‌صورت تصادفی در محدوده‌ای از ارتفاع صفحه انتخاب می‌شود.
                # The vertical position is selected randomly within a defined range of the screen height.
                y = random.uniform(S.Window.HEIGHT * 0.25, S.Window.HEIGHT * 0.50)
                positions.append((x, y))

            for (px, py) in positions:
                # آهسته می‌افتند (۱۰ px/s به جای ۹۵) — پلیر وقت داره
                # سرعت سقوط پایین‌تر باعث می‌شود بازیکن فرصت بیشتری برای جمع‌آوری پاورآپ‌ها داشته باشد.
                # The lower fall speed gives the player more time to collect the power-ups.
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
        # موج‌های ابتدایی فقط یک باس دارند؛ در موج‌های بالاتر احتمال حضور چند باس افزایش می‌یابد.
        # Early waves contain only one boss; the probability of multiple bosses increases in later waves.
        if wave < 10:
            return 1
        if wave < 15:
            return random.choices([1, 2], weights=[70, 30])[0]
        return random.choices([1, 2, 3], weights=[50, 35, 15])[0]

    def _compute_boss_positions(self, count: int) -> list[tuple[float, float, float]]:
        """موقعیت امن هر باس."""
        w = S.Window.WIDTH
        # با توجه به تعداد باس‌ها، موقعیت افقی، دامنه‌ی نوسان و اختلاف فاز برای هرکدام تعیین می‌شود.
        # Horizontal position, sway amplitude, and phase offset are assigned according to the number of bosses.
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



    def update(self, dt: float, *, alive_enemies: int) -> None:
        """
        به‌روزرسانی Spawner.

        پارامتر alive_enemies: تعداد دشمن‌های زنده‌ی روی صفحه.
        مسئولیت شمارش با Scene است چون Spawner نباید لیست‌ها را
        بپیماید.
        """
        # انیمیشن پیام مستقل از وضعیت فعلی تولید دشمن‌ها به‌روزرسانی می‌شود.
        # The announcement animation is updated independently of the current enemy-spawning state.
        self.announcement.update(dt)

        if self.finished:
            return

        # ---- تاخیر اولیه ----
        # تا پایان تأخیر اولیه، پردازش چرخه‌ی موج متوقف می‌ماند؛ با اتمام آن موج اول آغاز می‌شود.
        # Wave-cycle processing pauses during the initial delay; the first wave starts when it expires.
        if self._first_delay > 0.0:
            self._first_delay -= dt
            if self._first_delay <= 0.0:
                self._start_next_wave()
            return

        self._state_timer += dt

        # ---- ماشین حالت ----
        # بر اساس وضعیت فعلی، فقط منطق همان مرحله از چرخه‌ی موج اجرا می‌شود.
        # Only the logic belonging to the current wave-cycle state is executed.
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
        # تولید دشمن کمی پیش از پایان زمان نمایش پیام آغاز می‌شود تا دو مرحله هم‌پوشانی داشته باشند.
        # Enemy spawning begins shortly before the announcement ends, allowing the two phases to overlap.
        if self._state_timer >= _Timing.ANNOUNCE_DURATION * 0.7:
            # کمی قبل از پایان پیام، spawn شروع می‌شود
            self.state = SpawnState.SPAWNING
            self._state_timer = 0.0
            self._spawn_timer = 0.0

    # ── وضعیت: تولید دشمن ----
    def _update_spawning(self, dt: float) -> None:
        # ---- موج باس ----
        # در موج باس، همه‌ی باس‌ها در یک مرحله ساخته می‌شوند و Spawner مستقیماً وارد وضعیت انتظار می‌شود.
        # In a boss wave, all bosses are spawned in one operation, and the Spawner moves directly to the waiting state.
        if self.is_boss_wave:
            self._spawn_boss()
            self.state = SpawnState.FIGHTING
            self._state_timer = 0.0
            return

        # ---- زمان‌بندی اسپاون ----
        # فاصله‌ی تولید برای موج‌های پیشرفته و الیت ثابت است؛ موج‌های معمولی از مقدار وابسته به شماره‌ی موج استفاده می‌کنند.
        # Advanced and elite waves use fixed spawn intervals, while regular waves use an interval based on the wave number.
        if self.is_advanced_wave:
            # برای موج‌های ادونس کمی فاصله می‌دیم که کاربر گیج نشه
            interval = 1.2
        elif self.is_elite_wave:
            interval = 0.45
        else:
            interval = self._spawn_interval_for_wave(self.wave)

        # تایمر با delta time کاهش می‌یابد و پس از رسیدن به صفر، نوبت تولید دشمن بعدی فرا می‌رسد.
        # The timer decreases by delta time, and the next enemy is spawned when it reaches zero.
        self._spawn_timer -= dt
        if self._spawn_timer <= 0.0:
            if self.remaining_to_spawn > 0:
                self._spawn_one()
                self.remaining_to_spawn -= 1
                # تغییر تصادفی کوچک در فاصله‌ی تولید، از یکنواختی بیش از حد زمان‌بندی جلوگیری می‌کند.
                # A small random variation in the spawn interval prevents overly uniform timing.
                self._spawn_timer = interval * random.uniform(0.85, 1.15)

        # پس از ثبت آخرین دشمن برای تولید، Spawner منتظر پاک‌سازی دشمن‌های حاضر در صفحه می‌ماند.
        # Once the final enemy has been scheduled, the Spawner waits for all enemies on screen to be cleared.
        if self.remaining_to_spawn <= 0:
            self.state = SpawnState.FIGHTING
            self._state_timer = 0.0

    # ── وضعیت: منتظر پاک‌سازی ----
    def _update_fighting(self, alive: int) -> None:
        # پایان موج فقط زمانی تشخیص داده می‌شود که هیچ دشمن زنده‌ای روی صفحه باقی نمانده باشد.
        # The wave is considered complete only when no living enemies remain on the screen.
        if alive <= 0:
            # موج تموم شد
            self.state = SpawnState.BREAK
            self._state_timer = 0.0

    # ── وضعیت: مکث بین موج‌ها ----
    def _update_break(self) -> None:
        # پس از سپری‌شدن زمان مکث، راه‌اندازی موج بعدی انجام می‌شود.
        # The next wave is started once the break duration has elapsed.
        if self._state_timer >= _Timing.BREAK_DURATION:
            self._start_next_wave()



    def draw_announcement(
        self,
        surface: pygame.Surface,
        font_big: pygame.font.Font,
    ) -> None:
        """رسم پیام موج جاری (اگر فعال باشد)."""
        self.announcement.draw(surface, font_big)



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