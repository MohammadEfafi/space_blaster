"""
entities/entity.py
==================

کلاس پایه‌ی تمام موجودیت‌های بازی (Entity Base Class).

هر چیزی که در دنیای SPACE BLASTER وجود دارد و «حضور فیزیکی» دارد — پلیر،
دشمن، گلوله، پاورآپ، ذره، باس، آسترولید — از این کلاس ارث می‌برد.

این کلاس مسئول موارد زیر است:

    • موقعیت (x, y) و سرعت (vx, vy) با پشتیبانی از شتاب
    • شعاع هیت‌باکس (radius) و ماسک دایره‌ای برای برخورد سریع
    • چرخه‌ی حیات: alive، تایمرها، پاک‌سازی خودکار
    • انیمیشن فریم‌محور و ضربان (flash) روی ضربه
    • نرمال‌سازی بردار حرکت و محاسبه‌ی زاویه
    • هیت‌باکس‌های جایگزین (rect یا چند دایره) برای موجودات پیچیده
    • Hook های قابل Override: on_spawn, on_death, on_hit

طراحی به گونه‌ای است که زیرکلاس‌ها فقط باید draw() و update() خودشان
را بنویسند و بقیه‌ی منطق مشترک به‌صورت خودکار مدیریت می‌شود.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from core import settings as S

if TYPE_CHECKING:
    from core.game import Game
    from scenes.gameplay import GameplayScene


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس پایه‌ی Entity
# ═══════════════════════════════════════════════════════════════════════════

class Entity:
    """
    کلاس پایه برای تمام موجودیت‌های قابل رسم و به‌روزرسانی.

    یک زیرکلاس معمولاً این متدها را Override می‌کند:
        on_spawn()          — یک‌بار وقتی ساخته می‌شود
        on_death()          — یک‌بار وقتی می‌میرد (قبل از حذف)
        on_hit(damage)      — وقتی ضربه می‌خورد (قبل از کاهش HP)
        update_entity(dt)   — منطق اختصاصی هر فریم
        draw_entity(surf)   — رسم اختصاصی

    امکانات آماده‌ی والد:
        self.x, self.y          — موقعیت (float)
        self.vx, self.vy        — سرعت پیکسل بر ثانیه
        self.ax, self.ay        — شتاب پیکسل بر ثانیه²
        self.angle              — زاویه‌ی چرخش (درجه، 0 = راست)
        self.radius             — شعاع هیت‌باکس دایره‌ای
        self.hp                 — جان
        self.max_hp             — سقف جان
        self.alive              — وضعیت
        self.age                — ثانیه از تولد
        self.flash              — میزان flash روی ضربه (0..1)
        self.game               — رفرنس به Game
        self.scene              — رفرنس به Scene جاری (اگر داده شده باشد)
    """

    # ─────────────────────────────────────────────────────────────────────
    #  سازنده
    # ─────────────────────────────────────────────────────────────────────

    def __init__(
        self,
        x: float,
        y: float,
        *,
        vx: float = 0.0,
        vy: float = 0.0,
        radius: float = 10.0,
        hp: int = 1,
        scene: "GameplayScene | None" = None,
    ) -> None:
        # ---- موقعیت و حرکت ----
        self.x: float = float(x)
        self.y: float = float(y)
        self.vx: float = float(vx)
        self.vy: float = float(vy)
        self.ax: float = 0.0
        self.ay: float = 0.0
        self.angle: float = 0.0     # درجه
        self.radius: float = float(radius)

        # ---- سلامتی ----
        self.hp: int = int(hp)
        self.max_hp: int = int(hp)

        # ---- وضعیت ----
        self.alive: bool = True
        self.age: float = 0.0
        self.flash: float = 0.0     # 0..1 — پس از ضربه به 1 می‌رسد و نرم صفر می‌شود
        self._pending_kill: bool = False
        self._error_reported: bool = False

        # ---- رفرنس‌ها ----
        self.scene: "GameplayScene | None" = scene
        self.game: "Game | None" = scene.game if scene is not None else None

        # ---- callbacks ----
        self.on_spawn()

    # ─────────────────────────────────────────────────────────────────────
    #  خواص (Properties)
    # ─────────────────────────────────────────────────────────────────────

    @property
    def pos(self) -> tuple[float, float]:
        return (self.x, self.y)

    @property
    def pos_int(self) -> tuple[int, int]:
        return (int(self.x), int(self.y))

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    @property
    def hp_ratio(self) -> float:
        return self.hp / max(1, self.max_hp)

    # ─────────────────────────────────────────────────────────────────────
    #  هوک‌های قابل Override توسط زیرکلاس
    # ─────────────────────────────────────────────────────────────────────

    def on_spawn(self) -> None:
        """یک‌بار وقتی موجودیت ساخته می‌شود."""
        pass

    def on_death(self) -> None:
        """یک‌بار وقتی موجودیت می‌میرد (قبل از حذف از لیست)."""
        pass

    def on_hit(self, damage: int) -> None:
        """هر بار که ضربه می‌خورد (قبل از کاهش HP)."""
        pass

    def update_entity(self, dt: float) -> None:
        """منطق اختصاصی هر فریم — توسط زیرکلاس Override می‌شود."""
        pass

    def draw_entity(self, surface: pygame.Surface) -> None:
        """رسم اختصاصی — توسط زیرکلاس Override می‌شود."""
        pass

    def get_hitcircles(self) -> list[tuple[float, float, float]]:
        """
        لیست دایره‌های هیت‌باکس: [(x, y, radius), …].
        پیش‌فرض یک دایره‌ی مرکزی است؛ زیرکلاس‌های پیچیده (مثل باس)
        می‌توانند چند دایره برگردانند.
        """
        return [(self.x, self.y, self.radius)]

    # ─────────────────────────────────────────────────────────────────────
    #  حلقه‌ی درونی — توسط Scene صدا زده می‌شود
    # ─────────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """یک گام کامل به‌روزرسانی: فیزیک، timers، سپس منطق زیرکلاس."""
        if not self.alive:
            return

        self.age += dt

        # ---- فیزیک پایه ----
        self.vx += self.ax * dt
        self.vy += self.ay * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # ---- کاهش نرم flash ----
        if self.flash > 0.0:
            self.flash = max(0.0, self.flash - dt * 4.0)

        # ---- منطق اختصاصی زیرکلاس ----
        try:
            self.update_entity(dt)
        except Exception:
            self._report("update_entity")

    def draw(self, surface: pygame.Surface) -> None:
        """رسم — با اعمال اثر flash روی رنگ در صورت نیاز."""
        if not self.alive:
            return
        try:
            self.draw_entity(surface)
        except Exception:
            self._report("draw_entity")

    # ─────────────────────────────────────────────────────────────────────
    #  کمک‌کننده‌های حرکت
    # ─────────────────────────────────────────────────────────────────────

    def move_toward(self, tx: float, ty: float, speed: float, dt: float) -> None:
        """حرکت به سمت هدف با سرعت ثابت."""
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d < 0.001:
            return
        self.x += (dx / d) * speed * dt
        self.y += (dy / d) * speed * dt
        self.angle = math.degrees(math.atan2(dy, dx))

    def normalize_velocity(self, target_speed: float | None = None) -> None:
        """بردار سرعت را به اندازه‌ی مشخص نرمال می‌کند."""
        sp = self.speed
        if sp < 0.001:
            return
        new_sp = target_speed if target_speed is not None else sp
        self.vx = (self.vx / sp) * new_sp
        self.vy = (self.vy / sp) * new_sp

    def face_velocity(self) -> None:
        """زاویه‌ی موجودیت را به جهت حرکت تنظیم می‌کند."""
        if self.speed > 0.001:
            self.angle = math.degrees(math.atan2(self.vy, self.vx))

    # ─────────────────────────────────────────────────────────────────────
    #  کمک‌کننده‌های سلامتی
    # ─────────────────────────────────────────────────────────────────────

    def take_damage(self, damage: int) -> bool:
        """
        اعمال ضربه. اگر موجودیت بمیرد، True برمی‌گرداند.
        پس از فراخوانی، flash فعال می‌شود.
        """
        if not self.alive or damage <= 0:
            return False
        self.on_hit(damage)
        self.hp -= damage
        self.flash = 1.0
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def kill(self) -> None:
        """
        علامت‌گذاری برای مرگ. حذف واقعی از لیست صحنه، در پایان فریم
        توسط Scene انجام می‌شود تا iteratorها نشکنند.
        """
        if not self.alive:
            return
        self.alive = False
        self._pending_kill = True
        try:
            self.on_death()
        except Exception:
            self._report("on_death")

    # ─────────────────────────────────────────────────────────────────────
    #  کمک‌کننده‌های برخورد
    # ─────────────────────────────────────────────────────────────────────

    def collide(self, other: "Entity") -> bool:
        """
        تشخیص برخورد دایره‌ای بین این موجودیت و دیگری.
        برای موجودیت‌های پیچیده، از get_hitcircles استفاده می‌کند.
        """
        a_circles = self.get_hitcircles()
        b_circles = other.get_hitcircles()
        for ax, ay, ar in a_circles:
            for bx, by, br in b_circles:
                dx, dy = ax - bx, ay - by
                r = ar + br
                if dx * dx + dy * dy <= r * r:
                    return True
        return False

    def distance_to(self, other: "Entity") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    # ─────────────────────────────────────────────────────────────────────
    #  کمک‌کننده‌های صفحه
    # ─────────────────────────────────────────────────────────────────────

    def offscreen(self, margin: float = 80.0) -> bool:
        """آیا موجودیت کاملاً از صفحه خارج شده است؟"""
        return (
            self.x < -margin
            or self.x > S.Window.WIDTH + margin
            or self.y < -margin
            or self.y > S.Window.HEIGHT + margin
        )

    def clamp_to_screen(self, margin: float = 0.0) -> None:
        """نگه‌داشتن موجودیت در محدوده‌ی صفحه."""
        self.x = max(margin, min(S.Window.WIDTH - margin, self.x))
        self.y = max(margin, min(S.Window.HEIGHT - margin, self.y))

    def wrap_around_screen(self) -> None:
        """عبور از لبه‌ها و ظاهر شدن از طرف مقابل (مثل Asteroids)."""
        if self.x < -self.radius:
            self.x = S.Window.WIDTH + self.radius
        elif self.x > S.Window.WIDTH + self.radius:
            self.x = -self.radius
        if self.y < -self.radius:
            self.y = S.Window.HEIGHT + self.radius
        elif self.y > S.Window.HEIGHT + self.radius:
            self.y = -self.radius

    # ─────────────────────────────────────────────────────────────────────
    #  کمک‌کننده‌ی رنگ با flash
    # ─────────────────────────────────────────────────────────────────────

    def tint(self, color: tuple[int, int, int]) -> tuple[int, int, int]:
        """
        رنگ را با توجه به مقدار flash روشن‌تر می‌کند.
        در زیرکلاس‌ها هنگام رسم استفاده کن: pygame.draw.circle(..., ent.tint(RED))
        """
        if self.flash <= 0.01:
            return color
        f = min(1.0, self.flash)
        r = int(color[0] + (255 - color[0]) * f)
        g = int(color[1] + (255 - color[1]) * f)
        b = int(color[2] + (255 - color[2]) * f)
        return (r, g, b)

    # ─────────────────────────────────────────────────────────────────────
    #  گزارش خطا
    # ─────────────────────────────────────────────────────────────────────

    def _report(self, where: str) -> None:
        if self._error_reported:
            return
        self._error_reported = True
        from core.log import report_error
        report_error(f"{self.__class__.__name__}.{where}")

    # ─────────────────────────────────────────────────────────────────────
    #  نمایش رشته‌ای (برای دیباگ)
    # ─────────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"pos=({self.x:.1f},{self.y:.1f}) "
            f"hp={self.hp}/{self.max_hp} "
            f"alive={self.alive}>"
        )


__all__ = ["Entity"]