
"""
core/game.py
============

هسته‌ی مرکزی بازی SPACE BLASTER.
Central game engine for SPACE BLASTER.
"""

from __future__ import annotations

import sys
import traceback
from typing import Optional

import pygame

from core import settings as S
from core.scene_manager import SceneManager


class Game:
    """میزبان اصلی بازی."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(S.Window.TITLE)

        # ─── Fit window to desktop ───
        # تنظیم ابعاد پنجره متناسب با فضای قابل استفاده دسکتاپ
        # Adjust the window dimensions to fit within the available desktop area.
        info = pygame.display.Info()
        desktop_w, desktop_h = info.current_w, info.current_h

        base_w = S.Window.WIDTH
        base_h = S.Window.HEIGHT
        scale = min(
            (desktop_w * 0.90) / base_w,
            (desktop_h * 0.90) / base_h,
            1.0,
        )
        if scale < 1.0:
            # حفظ نسبت تصویر 16:9 هنگام کوچک‌سازی پنجره
            # Preserve the 16:9 aspect ratio when scaling down the window.
            S.Window.WIDTH = int(base_w * scale)
            S.Window.HEIGHT = int(S.Window.WIDTH * 9 / 16)
            print(
                f"[Game] Desktop {desktop_w}x{desktop_h} too small — "
                f"using {S.Window.WIDTH}x{S.Window.HEIGHT}"
            )
        else:
            print(f"[Game] Window: {S.Window.WIDTH}x{S.Window.HEIGHT}")

        # فعال‌سازی رندر مقیاس‌پذیر و در صورت نیاز، قابلیت تغییر اندازه پنجره
        # Enable scaled rendering and optionally allow window resizing.
        flags = pygame.SCALED
        if S.Window.RESIZABLE:
            flags |= pygame.RESIZABLE

        try:
            # ایجاد پنجره با پشتیبانی از همگام‌سازی عمودی در صورت امکان
            # Create the display window with vertical synchronization when supported.
            self.screen: pygame.Surface = pygame.display.set_mode(
                (S.Window.WIDTH, S.Window.HEIGHT),
                flags,
                vsync=S.Window.VSYNC,
            )
        except pygame.error:
            # استفاده از حالت جایگزین در صورت پشتیبانی‌نشدن تنظیم VSYNC
            # Fall back to standard display initialization if VSYNC is unavailable.
            self.screen = pygame.display.set_mode(
                (S.Window.WIDTH, S.Window.HEIGHT),
                flags,
            )

        self._is_fullscreen: bool = False

        # ساعت بازی و متغیرهای مربوط به زمان‌بندی و آمار فریم
        # Game clock and frame timing/statistics variables.
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.dt: float = 0.0
        self.fps: float = 0.0
        self.total_time: float = 0.0
        self.frame_count: int = 0

        self.running: bool = True

        self.selected_ship: str = "phantom"

        # ---- سیستم صدا (سراسری) ----
        # ---- Global audio system ----
        # مقداردهی اولیه سیستم صدا به‌صورت اختیاری برای جلوگیری از توقف بازی در صورت بروز خطا
        # Initialize the audio system optionally to prevent audio failures from interrupting the game.
        try:
            from systems.audio import AudioSystem
            self.audio: Optional[AudioSystem] = AudioSystem()
        except Exception:
            self.audio = None

        # ---- جدول امتیازات سراسری ----
        # ---- Global leaderboard ----
        # ایجاد مخزن مرکزی برای ذخیره و بازیابی رکوردهای بازی
        # Initialize the central store for saving and retrieving game records.
        from systems.scores import HighScoreStore
        self.scores: HighScoreStore = HighScoreStore()

        # ---- مدیر صحنه‌ها ----
        # ---- Scene manager ----
        # ایجاد مدیر صحنه و ثبت تمام صحنه‌های قابل استفاده در بازی
        # Initialize the scene manager and register all available game scenes.
        self.scenes: SceneManager = SceneManager(self)
        self._register_scenes()

        # ---- FPS نمایشی ----
        # ---- FPS display ----
        # متغیرهای موردنیاز برای محاسبه و نمایش میانگین نرخ فریم
        # Variables used to calculate and display the average frame rate.
        self._fps_font: Optional[pygame.font.Font] = None
        self._fps_accum: float = 0.0
        self._fps_frames: int = 0
        self._fps_display: float = 0.0

        # ---- ورود به صحنه‌ی اولیه ----
        # ---- Initial scene setup ----
        # انتقال به منوی اصلی و اعمال درخواست تغییر صحنه پیش از شروع حلقه بازی
        # Switch to the main menu and apply the pending transition before the game loop starts.
        self.scenes.go_to(S.SceneName.MENU.value)
        self.scenes.apply_pending()

    def _register_scenes(self) -> None:
        # وارد کردن کلاس‌های صحنه برای ثبت در مدیر صحنه
        # Import scene classes for registration with the scene manager.
        from scenes.menu import MenuScene
        from scenes.ship_select import ShipSelectScene
        from scenes.gameplay import GameplayScene
        from scenes.pause import PauseScene
        from scenes.gameover import GameOverScene
        from scenes.leaderboard import LeaderboardScene

        # ثبت تمام صحنه‌های بازی با شناسه‌های تعریف‌شده در تنظیمات
        # Register all game scenes using their identifiers defined in the settings.
        self.scenes.register(S.SceneName.MENU.value,        MenuScene(self))
        self.scenes.register(S.SceneName.SHIP_SELECT.value, ShipSelectScene(self))
        self.scenes.register(S.SceneName.GAMEPLAY.value,    GameplayScene(self))
        self.scenes.register(S.SceneName.PAUSE.value,       PauseScene(self))
        self.scenes.register(S.SceneName.GAME_OVER.value,   GameOverScene(self))
        self.scenes.register(S.SceneName.LEADERBOARD.value, LeaderboardScene(self))

    def run(self) -> None:
        # حلقه اصلی اجرای بازی؛ مدیریت رویدادها، به‌روزرسانی و رندر فریم‌ها
        # Main game loop: event handling, state updates, and frame rendering.
        try:
            while self.running:
                # محاسبه زمان سپری‌شده از فریم قبل و محدودکردن آن برای پایداری به‌روزرسانی‌ها
                # Calculate elapsed frame time and cap it to keep updates stable.
                raw_ms = self.clock.tick(S.Window.FPS)
                self.dt = min(raw_ms / 1000.0, 0.05)
                self.total_time += self.dt
                self.frame_count += 1
                self._update_fps(raw_ms)

                # دریافت و پردازش رویدادهای ورودی و پنجره
                # Retrieve and process input and window events.
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        break
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                        continue
                    self.scenes.handle_event(event)

                if not self.running:
                    break

                # به‌روزرسانی منطق صحنه فعال
                # Update the active scene.
                self.scenes.update(self.dt)

                # پاک‌سازی سطح نمایش و رسم صحنه فعلی
                # Clear the display surface and render the current scene.
                self.screen.fill(S.Palette.BG_DEEP)
                self.scenes.draw(self.screen)
                self.scenes.apply_pending()

                # نمایش نرخ فریم در صورت فعال‌بودن گزینه مربوطه
                # Display the frame rate when the corresponding setting is enabled.
                if S.Debug.SHOW_FPS:
                    self._draw_fps(self.screen)

                pygame.display.flip()

        except KeyboardInterrupt:
            # مدیریت خروج دستی کاربر از طریق صفحه‌کلید
            # Handle manual interruption by the user.
            print("\n[Game] Interrupted by user.")
        except Exception:
            # ثبت جزئیات خطاهای پیش‌بینی‌نشده در حلقه اصلی بازی
            # Print details of unexpected exceptions in the main game loop.
            print("\n[Game] Unhandled exception in main loop:")
            traceback.print_exc()
        finally:
            # آزادسازی منابع بازی هنگام پایان اجرای حلقه
            # Release game resources when the main loop exits.
            self._shutdown()

    def _update_fps(self, raw_ms: int) -> None:
        # محاسبه میانگین FPS در بازه‌های زمانی ۲۵۰ میلی‌ثانیه‌ای
        # Calculate the average FPS over 250-millisecond intervals.
        self._fps_accum += raw_ms / 1000.0
        self._fps_frames += 1
        if self._fps_accum >= 0.25:
            self._fps_display = self._fps_frames / self._fps_accum
            self._fps_accum = 0.0
            self._fps_frames = 0
        self.fps = self._fps_display

    def _draw_fps(self, surface: pygame.Surface) -> None:
        # ایجاد فونت فقط در اولین فراخوانی برای جلوگیری از ساخت مجدد آن در هر فریم
        # Create the font only once to avoid rebuilding it on every frame.
        if self._fps_font is None:
            self._fps_font = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)

        # رندر متن FPS و تعیین موقعیت نمایش آن در گوشه بالای سمت راست
        # Render the FPS text and position it in the upper-right corner.
        text = f"FPS {self.fps:5.1f}"
        img = self._fps_font.render(text, True, S.Palette.HUD_ACCENT)
        rect = img.get_rect()
        rect.topright = (S.Window.WIDTH - 12, 10)

        # رسم پس‌زمینه نیمه‌شفاف برای خوانایی بهتر مقدار FPS
        # Draw a semi-transparent background to improve FPS text readability.
        bg = pygame.Surface((rect.width + 10, rect.height + 6), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 110))
        surface.blit(bg, (rect.x - 5, rect.y - 3))
        surface.blit(img, rect)

    def _toggle_fullscreen(self) -> None:
        # تغییر وضعیت بین حالت تمام‌صفحه و پنجره‌ای
        # Toggle between fullscreen and windowed display modes.
        self._is_fullscreen = not self._is_fullscreen

        flags = pygame.SCALED
        if self._is_fullscreen:
            flags |= pygame.FULLSCREEN
        else:
            flags |= pygame.RESIZABLE

        try:
            # راه‌اندازی مجدد سیستم نمایش برای اعمال حالت جدید پنجره
            # Reinitialize the display subsystem to apply the new window mode.
            pygame.display.quit()
            pygame.display.init()
            self.screen = pygame.display.set_mode(
                (S.Window.WIDTH, S.Window.HEIGHT),
                flags,
                vsync=S.Window.VSYNC,
            )
        except pygame.error as e:
            # گزارش خطا در صورت ناموفق‌بودن تغییر حالت نمایش
            # Report errors if switching display modes fails.
            print(f"[Game] Fullscreen toggle failed: {e}")

    def _shutdown(self) -> None:
        # پایان اجرای بازی و آزادسازی منابع وابسته
        # Stop the game and release associated resources.
        print("[Game] Shutting down…")
        try:
            # پاک‌سازی صحنه‌ها و اعمال درخواست‌های باقی‌مانده مدیر صحنه
            # Clear registered scenes and apply any pending scene operations.
            self.scenes.clear()
            self.scenes.apply_pending()
        except Exception:
            pass
        try:
            # بستن و آزادسازی منابع Pygame
            # Shut down Pygame and release its resources.
            pygame.quit()
        except Exception:
            pass
        print("[Game] Bye 👋")
        if not _is_interactive():
            sys.exit(0)


def _is_interactive() -> bool:
    # تشخیص اجرای برنامه در محیط تعاملی پایتون
    # Detect whether the application is running in an interactive Python environment.
    try:
        import __main__  # noqa: F401
        return hasattr(sys, "ps1") or hasattr(sys, "ipcompleter")
    except Exception:
        return False


__all__ = ["Game"]
