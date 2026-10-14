"""
core/game.py
============

هسته‌ی مرکزی بازی SPACE BLASTER.

این ماژول مسئول موارد زیر است:

  ①  راه‌اندازی pygame و ساخت پنجره‌ی اصلی
  ②  ساخت SceneManager و ثبت اولیه‌ی همه‌ی صحنه‌ها
  ③  اجرای حلقه‌ی اصلی بازی (Main Loop)
  ④  مدیریت dt (Delta Time) برای فیزیک مستقل از نرخ فریم
  ⑤  نمایش FPS در حالت Debug
  ⑥  خروج تمیز و ایمن در هر شرایطی

طراحی به گونه‌ای است که:
    • Game فقط «میزبان» است — هیچ منطق بازی داخلش نیست.
    • هر صحنه (Scene) مسئول رفتار خودش است.
    • اضافه کردن صحنه‌ی جدید فقط یک خط register لازم دارد.
"""

from __future__ import annotations

import sys
import time
import traceback
from typing import Final

import pygame

from core import settings as S
from core.scene_manager import SceneManager


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس Game
# ═══════════════════════════════════════════════════════════════════════════

class Game:
    """
    میزبان اصلی بازی.

    یک نمونه از این کلاس ساخته می‌شود، run() صدا زده می‌شود، و تا زمانی
    که self.running == True باشد حلقه ادامه دارد. تمام منطق بازی توسط
    SceneManager به صحنه‌های فعال واگذار می‌شود.

    ویژگی‌های عمومی برای صحنه‌ها:
        game.screen         — سطح اصلی پنجره
        game.clock          — pygame.time.Clock
        game.scenes         — SceneManager
        game.running        — وضعیت حلقه (برای خروج تمیز)
        game.dt             — آخرین dt محاسبه‌شده (ثانیه)
        game.fps            — FPS لحظه‌ای
        game.total_time     — کل زمان اجرای بازی (ثانیه)
        game.frame_count    — شمارنده‌ی کل فریم‌ها
    """

    # ─────────────────────────────────────────────────────────────────────
    #  سازنده
    # ─────────────────────────────────────────────────────────────────────

    def __init__(self) -> None:
        # ---- راه‌اندازی pygame ----
        # این کار باید پیش از هر فراخوانی pygame دیگری انجام شود.
        pygame.init()
        pygame.display.set_caption(S.Window.TITLE)

        # ---- پنجره ----
        flags = 0
        if S.Window.RESIZABLE:
            flags |= pygame.RESIZABLE
        try:
            self.screen: pygame.Surface = pygame.display.set_mode(
                (S.Window.WIDTH, S.Window.HEIGHT),
                flags,
                vsync=S.Window.VSYNC,
            )
        except pygame.error:
            # برخی درایورها از vsync پشتیبانی نمی‌کنند؛ در این حالت بدون vsync
            self.screen = pygame.display.set_mode(
                (S.Window.WIDTH, S.Window.HEIGHT),
                flags,
            )

        # ---- ساعت و زمان ----
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.dt: float = 0.0
        self.fps: float = 0.0
        self.total_time: float = 0.0
        self.frame_count: int = 0

        # ---- وضعیت اجرا ----
        self.running: bool = True

        # ---- مدیر صحنه‌ها ----
        self.scenes: SceneManager = SceneManager(self)
        self._register_scenes()

        # ---- آماده‌سازی FPS نمایشی ----
        self._fps_font: pygame.font.Font | None = None
        self._fps_accum: float = 0.0
        self._fps_frames: int = 0
        self._fps_display: float = 0.0

        # ---- ورود به صحنه‌ی اولیه ----
        self.scenes.go_to(S.SceneName.MENU.value)
        self.scenes.apply_pending()

    # ─────────────────────────────────────────────────────────────────────
    #  ثبت صحنه‌ها
    # ─────────────────────────────────────────────────────────────────────
    #  تمام صحنه‌ها اینجا مونتاژ می‌شوند. اضافه کردن صحنه‌ی جدید =
    #  یک خط register. import ها داخل همین متد انجام می‌شوند تا از
    #  import چرخشی در بالای فایل جلوگیری شود.
    # ─────────────────────────────────────────────────────────────────────

    def _register_scenes(self) -> None:
        from scenes.menu import MenuScene
        from scenes.gameplay import GameplayScene
        from scenes.pause import PauseScene
        from scenes.gameover import GameOverScene

        self.scenes.register(S.SceneName.MENU.value,      MenuScene(self))
        self.scenes.register(S.SceneName.GAMEPLAY.value,  GameplayScene(self))
        self.scenes.register(S.SceneName.PAUSE.value,     PauseScene(self))
        self.scenes.register(S.SceneName.GAME_OVER.value, GameOverScene(self))

    # ─────────────────────────────────────────────────────────────────────
    #  حلقه‌ی اصلی
    # ─────────────────────────────────────────────────────────────────────

    def run(self) -> None:
        """
        اجرای حلقه‌ی اصلی بازی.

        مراحل هر فریم:
            ①  محاسبه‌ی dt (delta time) و محدود کردن FPS
            ②  پردازش رویدادهای pygame (QUIT، KEYDOWN، …)
            ③  به‌روزرسانی منطق صحنه‌ی فعلی با dt
            ④  پاک کردن صفحه
            ⑤  رندر صحنه‌ی فعلی
            ⑥  اعمال تغییرات صف‌شده‌ی صحنه‌ها
            ⑦  نمایش نتیجه روی صفحه
        """
        try:
            while self.running:
                # ① زمان
                raw_ms = self.clock.tick(S.Window.FPS)
                # محدودکردن dt برای جلوگیری از پرش‌های بزرگ (window drag, lag)
                self.dt = min(raw_ms / 1000.0, 0.05)
                self.total_time += self.dt
                self.frame_count += 1
                self._update_fps(raw_ms)

                # ② رویدادها
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        break
                    self.scenes.handle_event(event)

                if not self.running:
                    break

                # ③ به‌روزرسانی
                self.scenes.update(self.dt)

                # ④ پاک کردن صفحه
                self.screen.fill(S.Palette.BG_DEEP)

                # ⑤ رندر
                self.scenes.draw(self.screen)

                # ⑥ اعمال تعویض‌های صف‌شده
                self.scenes.apply_pending()

                # ⑦ نمایش FPS
                if S.Debug.SHOW_FPS:
                    self._draw_fps(self.screen)

                pygame.display.flip()

        except KeyboardInterrupt:
            # خروج تمیز با Ctrl+C در کنسول
            print("\n[Game] Interrupted by user.")
        except Exception:
            # در صورت وقوع خطای غیرمنتظره، اطلاعات مفید چاپ می‌شود
            print("\n[Game] Unhandled exception in main loop:")
            traceback.print_exc()
        finally:
            self._shutdown()

    # ─────────────────────────────────────────────────────────────────────
    #  FPS
    # ─────────────────────────────────────────────────────────────────────

    def _update_fps(self, raw_ms: int) -> None:
        """
        به‌روزرسانی نرم FPS برای نمایش. مقدار نمایشی هر ۰.۲۵ ثانیه
        یک‌بار به‌روز می‌شود تا چشم را اذیت نکند.
        """
        self._fps_accum += raw_ms / 1000.0
        self._fps_frames += 1
        if self._fps_accum >= 0.25:
            self._fps_display = self._fps_frames / self._fps_accum
            self._fps_accum = 0.0
            self._fps_frames = 0
        self.fps = self._fps_display

    def _draw_fps(self, surface: pygame.Surface) -> None:
        """نمایش FPS در گوشه‌ی بالا-راست صفحه."""
        if self._fps_font is None:
            self._fps_font = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)
        text = f"FPS {self.fps:5.1f}"
        img = self._fps_font.render(text, True, S.Palette.HUD_ACCENT)
        rect = img.get_rect()
        rect.topright = (S.Window.WIDTH - 12, 10)
        # پس‌زمینه‌ی نیمه‌شفاف برای خوانایی بیشتر
        bg = pygame.Surface((rect.width + 10, rect.height + 6), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 110))
        surface.blit(bg, (rect.x - 5, rect.y - 3))
        surface.blit(img, rect)

    # ─────────────────────────────────────────────────────────────────────
    #  خروج تمیز
    # ─────────────────────────────────────────────────────────────────────

    def _shutdown(self) -> None:
        """
        خروج تمیز از بازی.
        پشته‌ی صحنه‌ها را خالی می‌کند، pygame را می‌بندد و از فرآیند
        خارج می‌شود. تمام منابع به شکل صحیح آزاد می‌شوند.
        """
        print("[Game] Shutting down…")
        try:
            self.scenes.clear()
            self.scenes.apply_pending()
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass
        print("[Game] Bye 👋")
        # در حالت اجرای معمولی (نه داخل IPython/Jupyter) از فرآیند خارج شو
        if not _is_interactive():
            sys.exit(0)


# ═══════════════════════════════════════════════════════════════════════════
#  کمکی
# ═══════════════════════════════════════════════════════════════════════════

def _is_interactive() -> bool:
    """آیا کد در محیط تعاملی (IPython، Jupyter، IDLE) اجرا می‌شود؟"""
    try:
        import __main__  # noqa: F401
        return hasattr(sys, "ps1") or hasattr(sys, "ipcompleter")
    except Exception:
        return False


__all__ = ["Game"]