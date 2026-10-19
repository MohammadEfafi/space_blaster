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
        pygame.init()
        pygame.display.set_caption(S.Window.TITLE)

        # ---- پنجره ----
        # pygame.SCALED: رزولوشن منطقی (900x650) رو حفظ می‌کنه ولی تصویر
        # رو خودکار به اندازه‌ی پنجره‌ی واقعی مقیاس می‌ده. این یعنی:
        #   • همه‌ی صحنه‌ها همچنان در مختصات 900x650 کار می‌کنن
        #   • ماوس هم خودکار به همون مختصات تبدیل می‌شه
        #   • در حالت fullscreen، تصویر کل صفحه رو پر می‌کنه (بدون حاشیه)
        flags = pygame.SCALED
        if S.Window.RESIZABLE:
            flags |= pygame.RESIZABLE

        try:
            self.screen: pygame.Surface = pygame.display.set_mode(
                (S.Window.WIDTH, S.Window.HEIGHT),
                flags,
                vsync=S.Window.VSYNC,
            )
        except pygame.error:
            self.screen = pygame.display.set_mode(
                (S.Window.WIDTH, S.Window.HEIGHT),
                flags,
            )

        # ---- وضعیت تمام‌صفحه ----
        self._is_fullscreen: bool = False

        # ---- ساعت و زمان ----
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.dt: float = 0.0
        self.fps: float = 0.0
        self.total_time: float = 0.0
        self.frame_count: int = 0

        # ---- وضعیت اجرا ----
        self.running: bool = True

        # ---- انتخاب سفینه‌ی پیش‌فرض ----
        self.selected_ship: str = "phantom"

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

    def _register_scenes(self) -> None:
        from scenes.menu import MenuScene
        from scenes.ship_select import ShipSelectScene
        from scenes.gameplay import GameplayScene
        from scenes.pause import PauseScene
        from scenes.gameover import GameOverScene
        from scenes.leaderboard import LeaderboardScene

        self.scenes.register(S.SceneName.MENU.value,        MenuScene(self))
        self.scenes.register(S.SceneName.SHIP_SELECT.value, ShipSelectScene(self))
        self.scenes.register(S.SceneName.GAMEPLAY.value,    GameplayScene(self))
        self.scenes.register(S.SceneName.PAUSE.value,       PauseScene(self))
        self.scenes.register(S.SceneName.GAME_OVER.value,   GameOverScene(self))
        self.scenes.register(S.SceneName.LEADERBOARD.value, LeaderboardScene(self))

    # ─────────────────────────────────────────────────────────────────────
    #  حلقه‌ی اصلی
    # ─────────────────────────────────────────────────────────────────────

    def run(self) -> None:
        """اجرای حلقه‌ی اصلی بازی."""
        try:
            while self.running:
                # ① زمان
                raw_ms = self.clock.tick(S.Window.FPS)
                self.dt = min(raw_ms / 1000.0, 0.05)
                self.total_time += self.dt
                self.frame_count += 1
                self._update_fps(raw_ms)

                # ② رویدادها
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        break
                    # ---- F11 = تاگل تمام‌صفحه ----
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                        continue
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
            print("\n[Game] Interrupted by user.")
        except Exception:
            print("\n[Game] Unhandled exception in main loop:")
            traceback.print_exc()
        finally:
            self._shutdown()

    # ─────────────────────────────────────────────────────────────────────
    #  FPS
    # ─────────────────────────────────────────────────────────────────────

    def _update_fps(self, raw_ms: int) -> None:
        """به‌روزرسانی نرم FPS برای نمایش."""
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
        bg = pygame.Surface((rect.width + 10, rect.height + 6), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 110))
        surface.blit(bg, (rect.x - 5, rect.y - 3))
        surface.blit(img, rect)

    # ─────────────────────────────────────────────────────────────────────
    #  تاگل تمام‌صفحه (F11)
    # ─────────────────────────────────────────────────────────────────────

    def _toggle_fullscreen(self) -> None:
        """راه‌حل جایگزین: ری‌استارت display برای تغییر حالت."""
        self._is_fullscreen = not self._is_fullscreen

        flags = pygame.SCALED
        if self._is_fullscreen:
            flags |= pygame.FULLSCREEN
        else:
            flags |= pygame.RESIZABLE

        try:
            pygame.display.quit()
            pygame.display.init()
            self.screen = pygame.display.set_mode(
                (S.Window.WIDTH, S.Window.HEIGHT),
                flags,
                vsync=S.Window.VSYNC,
            )
        except pygame.error as e:
            print(f"[Game] Fullscreen toggle failed: {e}")

    # ─────────────────────────────────────────────────────────────────────
    #  خروج تمیز
    # ─────────────────────────────────────────────────────────────────────

    def _shutdown(self) -> None:
        """خروج تمیز از بازی."""
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