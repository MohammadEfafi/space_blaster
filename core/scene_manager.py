"""
core/scene_manager.py
=====================

مدیر صحنه‌ها (Scene Manager) برای SPACE BLASTER.

این ماژول مسئول دو کار است:

  ①  **جابه‌جایی بین صحنه‌ها** — با استفاده از مکانیزم «تعویض تعویقی»
     (Deferred Transition). هیچ صحنه‌ای وسط update خودش عوض نمی‌شود؛
     تعویض در پایان فریم اعمال می‌شود تا iteratorها و رفرنس‌ها نشکنند.

  ②  **پشتیبانی از پشته‌ی صحنه‌ها (Scene Stack)** — برای مواقعی که
     می‌خواهیم صحنه‌ی زیرین زنده بماند. مثال کلاسیک: باز کردن منوی Pause
     روی Gameplay. در این حالت Gameplay از پشته خارج نمی‌شود، فقط
     وارد حالت Pause می‌شود (متوقف می‌شود) و Pause روی آن قرار می‌گیرد.

API اصلی:
    register(name, scene)   — ثبت یک صحنه با نام مشخص
    go_to(name)             — تعویض کامل صحنه‌ی فعلی با یک صحنه‌ی دیگر
    push(name)              — قرار دادن یک صحنه روی صحنه‌ی فعلی (Pause-like)
    pop()                   — برداشتن صحنه‌ی رویی و برگشت به صحنه‌ی زیرین
    replace(name)           — مثل go_to ولی صحنه‌ی فعلی را از حافظه پاک می‌کند

طراحی این ماژول به گونه‌ای است که تمام تغییرات در پایان هر فریم اعمال
می‌شوند تا از رفتارهای غیرقابل‌پیش‌بینی جلوگیری شود.
"""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Optional

import pygame

from scenes.base import Scene
from core import settings as S

if TYPE_CHECKING:
    from core.game import Game


# ═══════════════════════════════════════════════════════════════════════════
#  انواع عملیات تعویض صحنه (برای صف داخلی)
# ═══════════════════════════════════════════════════════════════════════════

class _Op:
    """عملیات تعویض صحنه که در انتهای فریم اعمال می‌شود."""
    __slots__ = ("kind", "name")

    GO_TO  = "go_to"
    PUSH   = "push"
    POP    = "pop"
    REPLACE = "replace"
    CLEAR  = "clear"

    def __init__(self, kind: str, name: Optional[str] = None) -> None:
        self.kind = kind
        self.name = name


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس SceneManager
# ═══════════════════════════════════════════════════════════════════════════

class SceneManager:
    """
    مدیر صحنه‌ها با پشتیبانی کامل از Stack و تعویض تعویقی.

    نگاشت نام‌ها به نمونه‌های صحنه در self._scenes است و صف عملیات
    در self._ops نگه داشته می‌شود. تا زمانی که apply_pending() صدا
    زده نشود، هیچ تغییری در پشته اعمال نمی‌شود.
    """

    def __init__(self, game: "Game") -> None:
        self.game: "Game" = game
        self._scenes: dict[str, Scene] = {}
        self._stack: list[tuple[str, Scene]] = []   # (name, scene)
        self._ops: list[_Op] = []

    # ─────────────────────────────────────────────────────────────────────
    #  ثبت صحنه
    # ─────────────────────────────────────────────────────────────────────

    def register(self, name: str, scene: Scene) -> None:
        """یک صحنه را با نام مشخص ثبت می‌کند."""
        if name in self._scenes:
            raise KeyError(f"صحنه با نام '{name}' قبلاً ثبت شده است.")
        self._scenes[name] = scene

    def is_registered(self, name: str) -> bool:
        return name in self._scenes

    # ─────────────────────────────────────────────────────────────────────
    #  دسترسی به صحنه‌ها
    # ─────────────────────────────────────────────────────────────────────

    @property
    def current(self) -> Optional[Scene]:
        """صحنه‌ی رویی پشته (که در حال اجراست)."""
        return self._stack[-1][1] if self._stack else None

    @property
    def current_name(self) -> Optional[str]:
        return self._stack[-1][0] if self._stack else None

    @property
    def stack_depth(self) -> int:
        return len(self._stack)

    # ─────────────────────────────────────────────────────────────────────
    #  درخواست‌های تعویض — بلافاصله اعمال نمی‌شوند، فقط صف می‌شوند
    # ─────────────────────────────────────────────────────────────────────

    def go_to(self, name: str) -> None:
        """
        تعویض کامل صحنه‌ی فعلی با صحنه‌ی داده‌شده.
        پشته خالی می‌شود و فقط صحنه‌ی جدید روی آن قرار می‌گیرد.
        """
        self._validate(name)
        self._ops.append(_Op(_Op.GO_TO, name))

    def push(self, name: str) -> None:
        """
        صحنه‌ی داده‌شده را روی صحنه‌ی فعلی قرار می‌دهد.
        صحنه‌ی زیرین وارد حالت Pause می‌شود ولی از پشته خارج نمی‌شود.
        عالی برای منوی Pause، تنظیمات، دیالوگ تأیید و…
        """
        self._validate(name)
        self._ops.append(_Op(_Op.PUSH, name))

    def pop(self) -> None:
        """
        صحنه‌ی رویی را از پشته برمی‌دارد و صحنه‌ی زیرین را از حالت
        Pause خارج می‌کند. اگر پشته خالی شود، هیچ کاری نمی‌کند.
        """
        self._ops.append(_Op(_Op.POP))

    def replace(self, name: str) -> None:
        """
        صحنه‌ی فعلی را حذف و با صحنه‌ی جدید جایگزین می‌کند.
        تفاوتش با go_to این است که پشته‌ی زیرین دست‌نخورده می‌ماند
        (فقط رویی عوض می‌شود). برای GameOver که می‌خواهیم Gameplay
        پاک شود ولی ساختار پشته حفظ شود.
        """
        self._validate(name)
        self._ops.append(_Op(_Op.REPLACE, name))

    def clear(self) -> None:
        """کل پشته را خالی می‌کند (بدون رفتن به صحنه‌ی جدید)."""
        self._ops.append(_Op(_Op.CLEAR))

    def _validate(self, name: str) -> None:
        if name not in self._scenes:
            raise KeyError(f"صحنه با نام '{name}' ثبت نشده است.")

    # ─────────────────────────────────────────────────────────────────────
    #  اعمال عملیات صف‌شده — در پایان هر فریم از Game صدا زده می‌شود
    # ─────────────────────────────────────────────────────────────────────

    def apply_pending(self) -> None:
        """
        تمام عملیات تعویض صف‌شده را به ترتیب اعمال می‌کند.
        این متد را در پایان هر فریم، بعد از draw، صدا بزن.
        """
        if not self._ops:
            return

        # کپی می‌گیریم چون ممکن است در حین اعمال، عملیات جدیدی صف شود.
        ops, self._ops = self._ops, []

        for op in ops:
            try:
                self._apply_one(op)
            except Exception:
                self._report(f"apply_pending::{op.kind}({op.name})")

    def _apply_one(self, op: _Op) -> None:
        kind = op.kind

        if kind == _Op.GO_TO:
            self._do_clear_stack()
            self._do_push(op.name)

        elif kind == _Op.PUSH:
            self._do_pause_current()
            self._do_push(op.name)

        elif kind == _Op.POP:
            self._do_pop()

        elif kind == _Op.REPLACE:
            self._do_pop()          # حذف صحنه‌ی رویی
            self._do_push(op.name)  # قرار دادن صحنه‌ی جدید

        elif kind == _Op.CLEAR:
            self._do_clear_stack()

    # ── عملیات اتمی روی پشته (بدون صف، فقط از داخل apply_pending) ──

    def _do_push(self, name: str) -> None:
        scene = self._scenes[name]
        self._stack.append((name, scene))
        scene._enter()

    def _do_pop(self) -> None:
        if not self._stack:
            return
        _, scene = self._stack.pop()
        scene._exit()
        self._do_resume_current()

    def _do_pause_current(self) -> None:
        if self._stack:
            self._stack[-1][1]._pause()

    def _do_resume_current(self) -> None:
        if self._stack:
            self._stack[-1][1]._resume()

    def _do_clear_stack(self) -> None:
        while self._stack:
            _, scene = self._stack.pop()
            scene._exit()

    # ─────────────────────────────────────────────────────────────────────
    #  حلقه‌ی اصلی — عبور دادن رویداد/به‌روزرسانی/رندر به صحنه‌ی رویی
    # ─────────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        scene = self.current
        if scene is None:
            return
        scene._process_event(event)

    def update(self, dt: float) -> None:
        """
        به‌روزرسانی. اگر صحنه‌ی رویی در حالت Pause باشد، به‌روزرسانی
        متوقف می‌شود. همچنین اگر پشته بیش از یک صحنه داشته باشد،
        صحنه‌های زیرین هم به‌روزرسانی نمی‌شوند (تا منابع هدر نرود).
        """
        scene = self.current
        if scene is None:
            return
        scene._tick(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """
        رندر. اگر بیش از یک صحنه در پشته باشد (مثلاً Pause روی Gameplay)،
        ابتدا صحنه‌های زیرین رسم می‌شوند تا پس‌زمینه دیده شود، سپس
        صحنه‌ی رویی.
        """
        if not self._stack:
            return

        # فقط صحنه‌ی آخرین سطح زیرین را رسم کن (برای دیده شدن پس‌زمینه)
        if len(self._stack) >= 2:
            try:
                self._stack[-2][1]._render(surface)
            except Exception:
                self._report("draw::background")

        self._stack[-1][1]._render(surface)

    # ─────────────────────────────────────────────────────────────────────
    #  گزارش خطا
    # ─────────────────────────────────────────────────────────────────────

    def _report(self, where: str) -> None:
        header = f"\n[SCENE MANAGER ERROR] {where}"
        print(header)
        print("-" * len(header))
        traceback.print_exc()
        print("-" * len(header))


__all__ = ["SceneManager"]