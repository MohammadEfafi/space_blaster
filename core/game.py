"""
core/game.py
============

هسته‌ی مرکزی بازی SPACE BLASTER.
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

        self._is_fullscreen: bool = False

        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.dt: float = 0.0
        self.fps: float = 0.0
        self.total_time: float = 0.0
        self.frame_count: int = 0

        self.running: bool = True

        self.selected_ship: str = "phantom"

        # ---- سیستم صدا (سراسری) ----
        try:
            from systems.audio import AudioSystem
            self.audio: Optional[AudioSystem] = AudioSystem()
        except Exception:
            self.audio = None

        # ---- جدول امتیازات سراسری ----
        from systems.scores import HighScoreStore
        self.scores: HighScoreStore = HighScoreStore()

        # ---- مدیر صحنه‌ها ----
        self.scenes: SceneManager = SceneManager(self)
        self._register_scenes()

        # ---- FPS نمایشی ----
        self._fps_font: Optional[pygame.font.Font] = None
        self._fps_accum: float = 0.0
        self._fps_frames: int = 0
        self._fps_display: float = 0.0

        # ---- ورود به صحنه‌ی اولیه ----
        self.scenes.go_to(S.SceneName.MENU.value)
        self.scenes.apply_pending()

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

    def run(self) -> None:
        try:
            while self.running:
                raw_ms = self.clock.tick(S.Window.FPS)
                self.dt = min(raw_ms / 1000.0, 0.05)
                self.total_time += self.dt
                self.frame_count += 1
                self._update_fps(raw_ms)

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

                self.scenes.update(self.dt)

                self.screen.fill(S.Palette.BG_DEEP)
                self.scenes.draw(self.screen)
                self.scenes.apply_pending()

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

    def _update_fps(self, raw_ms: int) -> None:
        self._fps_accum += raw_ms / 1000.0
        self._fps_frames += 1
        if self._fps_accum >= 0.25:
            self._fps_display = self._fps_frames / self._fps_accum
            self._fps_accum = 0.0
            self._fps_frames = 0
        self.fps = self._fps_display

    def _draw_fps(self, surface: pygame.Surface) -> None:
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

    def _toggle_fullscreen(self) -> None:
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

    def _shutdown(self) -> None:
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


def _is_interactive() -> bool:
    try:
        import __main__  # noqa: F401
        return hasattr(sys, "ps1") or hasattr(sys, "ipcompleter")
    except Exception:
        return False


__all__ = ["Game"]