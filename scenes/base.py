"""
scenes/base.py
==============

کلاس پایه‌ی تمام صحنه‌های بازی (Scene Base Class).

هر صحنه‌ای در SPACE BLASTER — منو، گیم‌پلی، توقف، پایان بازی، تنظیمات،
جدول امتیازات — از این کلاس ارث می‌برد. هدف این است که منطق تکراری
(مدیریت ورودی، چرخه‌ی حیات، dt، پاک‌سازی) یک‌بار و فقط یک‌بار اینجا
نوشته شود و بقیه‌ی صحنه‌ها فقط روی *رفتار* خودشان تمرکز کنند.

ویژگی‌های کلیدی این طراحی:
    • مدیریت هوشمند ورودی: نگه‌داشته، تازه‌فشرده، تازه‌رها‌شده
    • dt (delta time) برای فیزیک مستقل از نرخ فریم
    • چرخه‌ی حیات کامل: enter / exit / pause / resume
    • Safety Net: هر خطای یک صحنه، بازی را کرش نمی‌کند
    • API تمیز برای زیرکلاس‌ها — فقط متدهای لازم را Override کن
"""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Any, Optional

import pygame

from core import settings as S
from core import settings

if TYPE_CHECKING:
    # جلوگیری از import چرخشی در زمان اجرا؛ فقط برای Type Hints
    from core.game import Game


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس پایه‌ی Scene
# ═══════════════════════════════════════════════════════════════════════════

class Scene:
    """
    کلاس پایه برای تمام صحنه‌های بازی.

    زیرکلاس‌ها معمولاً فقط باید این متدها را Override کنند:
        on_enter()       — وقتی صحنه فعال می‌شود (آماده‌سازی، لود منابع)
        on_exit()        — وقتی صحنه ترک می‌شود (پاک‌سازی)
        on_pause()       — وقتی صحنه موقتاً متوقف می‌شود
        on_resume()      — وقتی صحنه از حالت توقف برمی‌گردد
        handle_event(e)  — رویدادهای pygame (کیبورد، ماوس، …)
        update(dt)       — منطق بازی، dt بر حسب ثانیه
        draw(surface)    — رسم روی صفحه

    امکانات آماده‌ای که در اختیار زیرکلاس‌ها قرار می‌گیرد:
        self.game        — رفرنس به نمونه‌ی Game (دسترسی به scene manager و …)
        self.screen      — سطح اصلی پنجره (میان‌بر برای self.game.screen)
        self.time        — زمان سپری‌شده از ورود به این صحنه (ثانیه)
        self.keys        — وضعیت لحظه‌ای کلیدها (نگه‌داشته‌شده)
        self.mouse_pos   — موقعیت فعلی ماوس
        self.paused      — آیا صحنه در حالت توقف است؟
        self.active      — آیا صحنه در حال حاضر فعال است؟
    """

    # ─────────────────────────────────────────────────────────────────────
    #  سازنده
    # ─────────────────────────────────────────────────────────────────────

    def __init__(self, game: "Game") -> None:
        self.game: "Game" = game
        self.screen: pygame.Surface = game.screen

        # ---- وضعیت داخلی ----
        self.active: bool = False
        self.paused: bool = False
        self.time: float = 0.0            # ثانیه از ورود به صحنه
        self.frame: int = 0               # شمارنده‌ی فریم‌ها

        # ---- ورودی ----
        # keys: وضعیت لحظه‌ای هر کلید (True اگر نگه داشته شده)
        # just_pressed: در همین فریم فشرده شده
        # just_released: در همین فریم رها شده
        self.keys: pygame.key.ScancodeWrapper | dict[int, bool] = {}
        self.just_pressed: set[int] = set()
        self.just_released: set[int] = set()
        self.mouse_pos: tuple[int, int] = (0, 0)
        self.mouse_buttons: tuple[bool, bool, bool] = (False, False, False)

    # ─────────────────────────────────────────────────────────────────────
    #  چرخه‌ی حیات (Lifecycle) — توسط SceneManager فراخوانی می‌شوند
    # ─────────────────────────────────────────────────────────────────────

    def _enter(self) -> None:
        """ورود امن به صحنه — فقط از طرف SceneManager صدا زده می‌شود."""
        self.active = True
        self.paused = False
        self.time = 0.0
        self.frame = 0
        self.just_pressed.clear()
        self.just_released.clear()
        try:
            self.on_enter()
        except Exception:
            self._crash_report("on_enter")

    def _exit(self) -> None:
        """خروج امن از صحنه — فقط از طرف SceneManager صدا زده می‌شود."""
        self.active = False
        try:
            self.on_exit()
        except Exception:
            self._crash_report("on_exit")

    def _pause(self) -> None:
        self.paused = True
        try:
            self.on_pause()
        except Exception:
            self._crash_report("on_pause")

    def _resume(self) -> None:
        self.paused = False
        try:
            self.on_resume()
        except Exception:
            self._crash_report("on_resume")

    # ─────────────────────────────────────────────────────────────────────
    #  متدهای قابل Override توسط زیرکلاس‌ها
    # ─────────────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        """وقتی صحنه برای اولین بار فعال می‌شود. برای لود منابع، تنظیم فونت و …"""
        pass

    def on_exit(self) -> None:
        """وقتی صحنه ترک می‌شود. برای آزادسازی منابع."""
        pass

    def on_pause(self) -> None:
        """وقتی صحنه موقتاً متوقف می‌شود (مثلاً باز شدن منوی Pause)."""
        pass

    def on_resume(self) -> None:
        """وقتی صحنه از حالت توقف برمی‌گردد."""
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        """دریافت یک رویداد pygame (KEYDOWN، MOUSEBUTTONDOWN، …)."""
        pass

    def update(self, dt: float) -> None:
        """به‌روزرسانی منطق. dt بر حسب ثانیه. اگر paused است، صدا زده نمی‌شود."""
        pass

    def draw(self, surface: pygame.Surface) -> None:
        """رسم محتوای صحنه روی سطح داده‌شده."""
        pass

    # ─────────────────────────────────────────────────────────────────────
    #  حلقه‌ی درونی — فقط از طرف SceneManager صدا زده می‌شود
    # ─────────────────────────────────────────────────────────────────────

    def _process_event(self, event: pygame.event.Event) -> None:
        """پردازش ورودی و به‌روزرسانی وضعیت کلید/ماوس، سپس فراخوانی handle_event."""
        # --- به‌روزرسانی وضعیت کلیدها برای این فریم ---
        self.just_pressed.clear()
        self.just_released.clear()

        if event.type == pygame.KEYDOWN:
            self.just_pressed.add(event.key)
        elif event.type == pygame.KEYUP:
            self.just_released.add(event.key)

        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.mouse_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONUP:
            self.mouse_pos = event.pos

        # --- پاس دادن به زیرکلاس ---
        try:
            self.handle_event(event)
        except Exception:
            self._crash_report("handle_event")

    def _tick(self, dt: float) -> None:
        """یک گام از به‌روزرسانی. dt بر حسب ثانیه."""
        self.time += dt
        self.frame += 1

        # به‌روزرسانی وضعیت لحظه‌ای کلیدها و ماوس
        self.keys = pygame.key.get_pressed()
        self.mouse_pos = pygame.mouse.get_pos()
        self.mouse_buttons = pygame.mouse.get_pressed(3)

        if self.paused:
            return

        try:
            self.update(dt)
        except Exception:
            self._crash_report("update")

    def _render(self, surface: pygame.Surface) -> None:
        """رسم صحنه. حتی اگر خطا بدهد، بازی متوقف نمی‌شود."""
        try:
            self.draw(surface)
        except Exception:
            self._crash_report("draw")

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌های ورودی — برای استفاده‌ی راحت در زیرکلاس‌ها
    # ─────────────────────────────────────────────────────────────────────

    def is_held(self, key: int) -> bool:
        """آیا کلید در همین لحظه نگه داشته شده؟ (از self.keys)"""
        if not self.keys:
            return False
        try:
            return bool(self.keys[key])
        except (KeyError, IndexError):
            return False

    def any_held(self, keys: tuple[int, ...] | list[int]) -> bool:
        """آیا هیچ‌کدام از کلیدهای داده‌شده نگه داشته شده‌اند؟"""
        return any(self.is_held(k) for k in keys)

    def was_pressed(self, key: int) -> bool:
        """آیا کلید در همین فریم تازه فشرده شده؟"""
        return key in self.just_pressed

    def was_released(self, key: int) -> bool:
        """آیا کلید در همین فریم تازه رها شده؟"""
        return key in self.just_released

    def any_pressed(self, keys: tuple[int, ...] | list[int]) -> bool:
        """آیا هیچ‌کدام از کلیدها در همین فریم فشرده شده‌اند؟"""
        return any(k in self.just_pressed for k in keys)

    def axis(self, negative: tuple[int, ...], positive: tuple[int, ...]) -> float:
        """
        یک محور نرمال‌شده برمی‌گرداند: -1, 0, یا +1.
        مثال: axis(Keys.LEFT, Keys.RIGHT) برای محور افقی.
        """
        neg = 1.0 if self.any_held(negative) else 0.0
        pos = 1.0 if self.any_held(positive) else 0.0
        return pos - neg

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌های رندر — میان‌برهای متداول
    # ─────────────────────────────────────────────────────────────────────

    def draw_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        pos: tuple[int, int],
        center: bool = False,
    ) -> pygame.Rect:
        """
        متن را روی سطح می‌کشد و rect آن را برمی‌گرداند.
        اگر center=True باشد، pos به‌عنوان مرکز در نظر گرفته می‌شود.
        """
        img = font.render(text, True, color)
        rect = img.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        surface.blit(img, rect)
        return rect

    def draw_centered(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        y: int,
    ) -> pygame.Rect:
        """متن را وسط‌چین افقی در ارتفاع y می‌کشد."""
        return self.draw_text(
            surface, text, font, color,
            (S.Window.WIDTH // 2, y), center=True,
        )

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی: درخواست تعویض صحنه
    # ─────────────────────────────────────────────────────────────────────

    def go_to(self, name: str) -> None:
        """میان‌بر برای رفتن به صحنه‌ی دیگر از داخل همین صحنه."""
        self.game.scenes.go_to(name)

    def quit_game(self) -> None:
        """بستن کل بازی به شکل تمیز."""
        self.game.running = False

    # ─────────────────────────────────────────────────────────────────────
    #  گزارش خطا — جلوگیری از کرش کامل بازی
    # ─────────────────────────────────────────────────────────────────────

    def _crash_report(self, where: str) -> None:
        """اگر خطایی در یک متد بیفتد، اینجا لاگ می‌شود و بازی ادامه می‌دهد."""
        header = f"\n[SCENE ERROR] in {self.__class__.__name__}.{where}()"
        print(header)
        print("-" * len(header))
        traceback.print_exc()
        print("-" * len(header))
        # در صورت نیاز، اینجا می‌توانی بعداً به منوی اصلی برگردی:
        # self.game.scenes.go_to(S.SceneName.MENU)


__all__ = ["Scene"]