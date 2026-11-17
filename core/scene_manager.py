
"""
core/scene_manager.py
=====================

مدیر صحنه‌ها (Scene Manager) برای SPACE BLASTER.

این ماژول مسئول دو کار است:

    **جابه‌جایی بین صحنه‌ها** — با استفاده از مکانیزم «تعویض تعویقی»
     (Deferred Transition). هیچ صحنه‌ای وسط update خودش عوض نمی‌شود؛
     تعویض در پایان فریم اعمال می‌شود تا iteratorها و رفرنس‌ها نشکنند.

    **پشتیبانی از پشته‌ی صحنه‌ها (Scene Stack)** — برای مواقعی که
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




class _Op:
    """عملیات تعویض صحنه که در انتهای فریم اعمال می‌شود."""
    # نگهداری نوع عملیات و نام صحنه بدون ایجاد دیکشنری برای هر درخواست
    # Store the operation type and scene name without allocating a dictionary.
    __slots__ = ("kind", "name")

    # شناسه‌های داخلی عملیات قابل صف‌بندی مدیر صحنه
    # Internal identifiers for the scene manager's queued operations.
    GO_TO  = "go_to"
    PUSH   = "push"
    POP    = "pop"
    REPLACE = "replace"
    CLEAR  = "clear"

    def __init__(self, kind: str, name: Optional[str] = None) -> None:
        self.kind = kind
        self.name = name



class SceneManager:
    """
    مدیر صحنه‌ها با پشتیبانی کامل از Stack و تعویض تعویقی.

    نگاشت نام‌ها به نمونه‌های صحنه در self._scenes است و صف عملیات
    در self._ops نگه داشته می‌شود. تا زمانی که apply_pending() صدا
    زده نشود، هیچ تغییری در پشته اعمال نمی‌شود.
    """

    def __init__(self, game: "Game") -> None:
        self.game: "Game" = game

        # نگاشت شناسه هر صحنه به نمونه ثبت‌شده آن
        # Map each scene identifier to its registered instance.
        self._scenes: dict[str, Scene] = {}

        # پشته اجرای صحنه‌ها؛ هر عضو شامل نام و نمونه صحنه است
        # Scene execution stack; each entry contains a scene name and instance.
        self._stack: list[tuple[str, Scene]] = []   # (name, scene)

        # صف عملیات انتقال که تا زمان apply_pending اجرا نمی‌شوند
        # Queue of scene operations deferred until apply_pending is called.
        self._ops: list[_Op] = []



    def register(self, name: str, scene: Scene) -> None:
        """یک صحنه را با نام مشخص ثبت می‌کند."""
        if name in self._scenes:
            raise KeyError(f"صحنه با نام '{name}' قبلاً ثبت شده است.")
        self._scenes[name] = scene

    def is_registered(self, name: str) -> bool:
        # بررسی وجود شناسه صحنه در مجموعه صحنه‌های ثبت‌شده
        # Check whether the scene identifier exists in the registry.
        return name in self._scenes


    @property
    def current(self) -> Optional[Scene]:
        """صحنه‌ی رویی پشته (که در حال اجراست)."""
        # بازگرداندن صحنه فعال یا None در صورت خالی‌بودن پشته
        # Return the active scene, or None if the stack is empty.
        return self._stack[-1][1] if self._stack else None

    @property
    def current_name(self) -> Optional[str]:
        # دریافت نام صحنه فعال بدون دسترسی مستقیم به ساختار پشته
        # Retrieve the active scene's name without exposing the stack structure.
        return self._stack[-1][0] if self._stack else None

    @property
    def stack_depth(self) -> int:
        # تعداد صحنه‌های موجود در پشته
        # Return the current number of scenes in the stack.
        return len(self._stack)



    def go_to(self, name: str) -> None:
        """
        تعویض کامل صحنه‌ی فعلی با صحنه‌ی داده‌شده.
        پشته خالی می‌شود و فقط صحنه‌ی جدید روی آن قرار می‌گیرد.
        """
        # اعتبارسنجی نام و افزودن درخواست تعویض کامل به صف عملیات
        # Validate the scene name and queue a full scene transition.
        self._validate(name)
        self._ops.append(_Op(_Op.GO_TO, name))

    def push(self, name: str) -> None:
        """
        صحنه‌ی داده‌شده را روی صحنه‌ی فعلی قرار می‌دهد.
        صحنه‌ی زیرین وارد حالت Pause می‌شود ولی از پشته خارج نمی‌شود.
        عالی برای منوی Pause، تنظیمات، دیالوگ تأیید و…
        """
        # اعتبارسنجی نام و صف‌بندی درخواست افزودن صحنه جدید به بالای پشته
        # Validate the name and queue the new scene for the top of the stack.
        self._validate(name)
        self._ops.append(_Op(_Op.PUSH, name))

    def pop(self) -> None:
        """
        صحنه‌ی رویی را از پشته برمی‌دارد و صحنه‌ی زیرین را از حالت
        Pause خارج می‌کند. اگر پشته خالی شود، هیچ کاری نمی‌کند.
        """
        # صف‌بندی حذف صحنه فعال و بازگشت به صحنه زیرین
        # Queue the removal of the active scene and return to the underlying scene.
        self._ops.append(_Op(_Op.POP))

    def replace(self, name: str) -> None:
        """
        صحنه‌ی فعلی را حذف و با صحنه‌ی جدید جایگزین می‌کند.
        تفاوتش با go_to این است که پشته‌ی زیرین دست‌نخورده می‌ماند
        (فقط رویی عوض می‌شود). برای GameOver که می‌خواهیم Gameplay
        پاک شود ولی ساختار پشته حفظ شود.
        """
        # اعتبارسنجی نام و صف‌بندی جایگزینی صحنه رویی بدون تغییر صحنه‌های زیرین
        # Validate the name and queue a replacement without modifying underlying scenes.
        self._validate(name)
        self._ops.append(_Op(_Op.REPLACE, name))

    def clear(self) -> None:
        """کل پشته را خالی می‌کند (بدون رفتن به صحنه‌ی جدید)."""
        # صف‌بندی پاک‌سازی کامل پشته بدون ثبت صحنه جایگزین
        # Queue a complete stack clear without registering a replacement scene.
        self._ops.append(_Op(_Op.CLEAR))

    def _validate(self, name: str) -> None:
        # جلوگیری از صف‌بندی انتقال به صحنه‌ای که قبلاً ثبت نشده است
        # Prevent transitions to scenes that have not been registered.
        if name not in self._scenes:
            raise KeyError(f"صحنه با نام '{name}' ثبت نشده است.")



    def apply_pending(self) -> None:
        """
        تمام عملیات تعویض صف‌شده را به ترتیب اعمال می‌کند.
        این متد را در پایان هر فریم، بعد از draw، صدا بزن.
        """
        # در صورت خالی‌بودن صف، نیازی به پردازش عملیات نیست
        # Skip processing when there are no pending operations.
        if not self._ops:
            return

        # جداسازی عملیات فعلی از صف برای حفظ درخواست‌های جدید هنگام پردازش
        # Detach the current batch to preserve operations queued during processing.
        ops, self._ops = self._ops, []

        # اجرای ترتیبی عملیات و مدیریت مستقل خطاهای هر درخواست
        # Execute operations in order and handle each operation's errors independently.
        for op in ops:
            try:
                self._apply_one(op)
            except Exception:
                self._report(f"apply_pending::{op.kind}({op.name})")

    def _apply_one(self, op: _Op) -> None:
        # تعیین نوع عملیات برای انتخاب مسیر اجرای مناسب
        # Determine the operation type to select the appropriate execution path.
        kind = op.kind

        if kind == _Op.GO_TO:
            # پاک‌سازی کامل پشته پیش از ورود به صحنه جدید
            # Clear the entire stack before entering the new scene.
            self._do_clear_stack()
            self._do_push(op.name)

        elif kind == _Op.PUSH:
            # متوقف‌کردن صحنه فعلی و قرار دادن صحنه جدید روی آن
            # Pause the current scene and push the new scene above it.
            self._do_pause_current()
            self._do_push(op.name)

        elif kind == _Op.POP:
            # حذف صحنه رویی و ازسرگیری صحنه زیرین
            # Remove the top scene and resume the underlying scene.
            self._do_pop()

        elif kind == _Op.REPLACE:
            # جایگزینی صحنه رویی بدون ازسرگیری صحنه زیرین
            # Replace the top scene without resuming the underlying scene.
            self._do_pop_silent()   # ← بدون resume
            self._do_push(op.name)
            
        elif kind == _Op.CLEAR:
            # حذف تمام صحنه‌های موجود در پشته
            # Remove all scenes currently held in the stack.
            self._do_clear_stack()

    # ── عملیات اتمی روی پشته (بدون صف، فقط از داخل apply_pending) ──
    # ── Atomic stack operations (unqueued, called only from apply_pending) ──

    def _do_push(self, name: str) -> None:
        # افزودن نمونه صحنه به پشته و اجرای چرخه ورود آن
        # Push the scene instance onto the stack and invoke its entry lifecycle.
        scene = self._scenes[name]
        self._stack.append((name, scene))
        scene._enter()

    def _do_pop(self) -> None:
        # در صورت خالی‌بودن پشته، عملیات حذف بدون اثر پایان می‌یابد
        # Return without effect when the stack is empty.
        if not self._stack:
            return

        # حذف صحنه رویی، اجرای چرخه خروج و ازسرگیری صحنه زیرین
        # Remove the top scene, invoke its exit lifecycle, and resume the underlying scene.
        _, scene = self._stack.pop()
        scene._exit()
        self._do_resume_current()
        
    def _do_pop_silent(self) -> None:
        """حذف صحنه‌ی رویی بدون resume کردن صحنه‌ی زیرین."""
        # حذف صحنه فعال بدون فراخوانی چرخه ازسرگیری برای صحنه زیرین
        # Remove the active scene without invoking the underlying scene's resume lifecycle.
        if not self._stack:
            return
        _, scene = self._stack.pop()
        scene._exit()

    def _do_pause_current(self) -> None:
        # توقف صحنه رویی در صورت وجود صحنه فعال
        # Pause the top scene if an active scene exists.
        if self._stack:
            self._stack[-1][1]._pause()

    def _do_resume_current(self) -> None:
        # ازسرگیری صحنه رویی پس از حذف صحنه بالاتر از آن
        # Resume the top scene after the scene above it has been removed.
        if self._stack:
            self._stack[-1][1]._resume()

    def _do_clear_stack(self) -> None:
        # خروج ترتیبی از تمام صحنه‌ها تا خالی‌شدن کامل پشته
        # Exit every scene in order until the stack is completely empty.
        while self._stack:
            _, scene = self._stack.pop()
            scene._exit()



    def handle_event(self, event: pygame.event.Event) -> None:
        # دریافت ارجاع صحنه فعال برای ارسال رویداد ورودی
        # Retrieve the active scene to forward the input event.
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
        # به‌روزرسانی فقط صحنه رویی؛ صحنه‌های زیرین در این مرحله پردازش نمی‌شوند
        # Update only the top scene; underlying scenes are not processed here.
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
        # در نبود صحنه، عملیات رندر انجام نمی‌شود
        # Skip rendering when the stack contains no scenes.
        if not self._stack:
            return

        # فقط صحنه‌ی آخرین سطح زیرین را رسم کن (برای دیده شدن پس‌زمینه)
        # Render only the immediately underlying scene to preserve the background.
        if len(self._stack) >= 2:
            try:
                self._stack[-2][1]._render(surface)
            except Exception:
                # ثبت خطای رندر صحنه زیرین بدون متوقف‌کردن ادامه رندر
                # Report underlying scene rendering errors without interrupting rendering.
                self._report("draw::background")

        # رندر صحنه رویی پس از رسم پس‌زمینه
        # Render the top scene after drawing the background.
        self._stack[-1][1]._render(surface)

    def _report(self, where: str) -> None:
        # استفاده از گزارشگر خطای مرکزی برای یکپارچگی لاگ‌های پروژه
        # Delegate to the centralized error reporter for consistent project logging.
        from core.log import report_error
        report_error(f"SceneManager.{where}")


__all__ = ["SceneManager"]
