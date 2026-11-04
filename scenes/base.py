"""
scenes/base.py
==============

کلاس پایه‌ی تمام صحنه‌های بازی (Scene Base Class).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from core import settings as S

if TYPE_CHECKING:
    from core.game import Game


class Scene:
    """کلاس پایه برای تمام صحنه‌های بازی."""

    def __init__(self, game: "Game") -> None:
        self.game: "Game" = game
        self.screen: pygame.Surface = game.screen

        # ---- وضعیت داخلی ----
        self.active: bool = False
        self.paused: bool = False
        self.time: float = 0.0
        self.frame: int = 0

        # ---- ورودی ----
        self.keys: pygame.key.ScancodeWrapper | dict[int, bool] = {}
        self.just_pressed: set[int] = set()
        self.just_released: set[int] = set()
        self.mouse_pos: tuple[int, int] = (0, 0)
        self.mouse_buttons: tuple[bool, bool, bool] = (False, False, False)

    # ─────────────────────────────────────────────────────────────────────
    #  چرخه‌ی حیات
    # ─────────────────────────────────────────────────────────────────────

    def _enter(self) -> None:
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
    #  متدهای قابل Override
    # ─────────────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def on_pause(self) -> None:
        pass

    def on_resume(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass

    # ─────────────────────────────────────────────────────────────────────
    #  حلقه‌ی درونی
    # ─────────────────────────────────────────────────────────────────────

    def _process_event(self, event: pygame.event.Event) -> None:
        """اضافه کردن به just_pressed/just_released (بدون پاک کردن)."""
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

        try:
            self.handle_event(event)
        except Exception:
            self._crash_report("handle_event")

    def _tick(self, dt: float) -> None:
        """
        یک گام از به‌روزرسانی.
        در انتها just_pressed/just_released پاک می‌شن — این‌طوری
        was_pressed() فقط یک فریم True برمی‌گردونه.
        """
        self.time += dt
        self.frame += 1

        self.keys = pygame.key.get_pressed()
        self.mouse_pos = pygame.mouse.get_pos()
        self.mouse_buttons = pygame.mouse.get_pressed(3)

        if not self.paused:
            try:
                self.update(dt)
            except Exception:
                self._crash_report("update")

        # ⚠️ پاک‌سازی در انتها (نه ابتدا) — تا update بتونه استفاده کنه
        self.just_pressed.clear()
        self.just_released.clear()

    def _render(self, surface: pygame.Surface) -> None:
        try:
            self.draw(surface)
        except Exception:
            self._crash_report("draw")

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌های ورودی
    # ─────────────────────────────────────────────────────────────────────

    def is_held(self, key: int) -> bool:
        if not self.keys:
            return False
        try:
            return bool(self.keys[key])
        except (KeyError, IndexError):
            return False

    def any_held(self, keys: tuple[int, ...] | list[int]) -> bool:
        return any(self.is_held(k) for k in keys)

    def was_pressed(self, key: int) -> bool:
        return key in self.just_pressed

    def was_released(self, key: int) -> bool:
        return key in self.just_released

    def any_pressed(self, keys: tuple[int, ...] | list[int]) -> bool:
        return any(k in self.just_pressed for k in keys)

    def axis(self, negative: tuple[int, ...], positive: tuple[int, ...]) -> float:
        neg = 1.0 if self.any_held(negative) else 0.0
        pos = 1.0 if self.any_held(positive) else 0.0
        return pos - neg

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌های رندر
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
        return self.draw_text(
            surface, text, font, color,
            (S.Window.WIDTH // 2, y), center=True,
        )

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی: تعویض صحنه
    # ─────────────────────────────────────────────────────────────────────

    def go_to(self, name: str) -> None:
        self.game.scenes.go_to(name)

    def quit_game(self) -> None:
        self.game.running = False

    # ─────────────────────────────────────────────────────────────────────
    #  گزارش خطا
    # ─────────────────────────────────────────────────────────────────────

    def _crash_report(self, where: str) -> None:
        from core.log import report_error
        report_error(f"{self.__class__.__name__}.{where}")


__all__ = ["Scene"]