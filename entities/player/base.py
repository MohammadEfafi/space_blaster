"""
entities/player/base.py
=======================

کلاس پایه‌ی سفینه‌های بازیکن (Player Base Class) برای SPACE BLASTER.

این ماژول زیرساخت مشترک تمام سفینه‌های قابل‌انتخاب را فراهم می‌کند.
هر سفینه‌ی خاص (Interceptor، Vanguard، …) از این کلاس ارث می‌برد و
فقط آمار و گرافیک اختصاصی خود را Override می‌کند.

منطق مشترک این کلاس:
    • حرکت با شتاب و میرایی نرم (accel/drag)
    • شلیک با cooldown، muzzle flash و recoil
    • Invulnerability با چشمک‌زن
    • Power-Up با تایمر
    • Thruster particles (ذرات موتور)
    • هاله، چشمک نامیرایی، muzzle flash و ring مشترک

هر زیرکلاس مسئول:
    • تعریف آمار (HP, SPEED, SHOOT_CD, …)
    • تعریف رنگ‌ها (PRIMARY, SECONDARY, ACCENT)
    • پیاده‌سازی draw_ship() — بدنه‌ی اختصاصی
    • (اختیاری) Override الگوی شلیک، offset موتورها
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Optional

import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.entity import Entity

if TYPE_CHECKING:
    from scenes.gameplay import GameplayScene


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس پایه‌ی Player
# ═══════════════════════════════════════════════════════════════════════════

class Player(Entity):
    """
    کلاس پایه برای تمام سفینه‌های بازیکن.

    برای ساخت سفینه‌ی جدید:
        ①  این کلاس را ارث‌بری کن
        ②  NAME، DESCRIPTION، KIND_KEY را ست کن
        ③  آمار (MAX_HP، SPEED، …) را Override کن
        ④  رنگ‌ها (PRIMARY_COLOR، …) را ست کن
        ⑤  متد draw_ship() را پیاده کن
        ⑥  اگر الگوی شلیک خاصی می‌خواهی، _get_shot_angles() را Override کن
    """

    # ─────────────────────────────────────────────────────────────────────
    #  شناسه (در زیرکلاس بازنویسی می‌شود)
    # ─────────────────────────────────────────────────────────────────────

    NAME:        str = "SHIP"
    DESCRIPTION: str = "Standard issue vessel."
    KIND_KEY:    str = "ship"

    # ─────────────────────────────────────────────────────────────────────
    #  آمار پایه (در زیرکلاس بازنویسی می‌شود)
    # ─────────────────────────────────────────────────────────────────────

    MAX_HP:       int   = 3
    SPEED:        float = 340.0
    RADIUS:       float = 20.0
    INVULN_TIME:  float = 1.6
    SHOOT_CD:     float = 0.16
    BULLET_SPEED: float = 780.0
    BULLET_DAMAGE: int  = 1
    BULLET_KIND:  BulletKind = BulletKind.PLAYER

    # فیزیک حرکت
    ACCEL: float = 9.0     # ضریب شتاب (هرچه بیشتر، سریع‌تر به سرعت هدف می‌رسد)
    DRAG:  float = 7.5     # ضریب میرایی وقتی ورودی نیست

    # ─────────────────────────────────────────────────────────────────────
    #  رنگ‌ها (در زیرکلاس بازنویسی می‌شود)
    # ─────────────────────────────────────────────────────────────────────

    PRIMARY_COLOR:   tuple[int, int, int] = (60, 220, 255)
    SECONDARY_COLOR: tuple[int, int, int] = (30, 130, 180)
    ACCENT_COLOR:    tuple[int, int, int] = (255, 220, 60)
    HIGHLIGHT_COLOR: tuple[int, int, int] = (235, 245, 255)
    FLAME_COLOR:     tuple[int, int, int] = (255, 150, 40)

    # ─────────────────────────────────────────────────────────────────────
    #  سازنده
    # ─────────────────────────────────────────────────────────────────────

    def __init__(self, scene: Optional["GameplayScene"] = None) -> None:
        start_x = S.Window.WIDTH / 2
        start_y = S.Window.HEIGHT - S.PlayerCfg.RESPAWN_Y

        super().__init__(
            start_x, start_y,
            radius=self.RADIUS,
            hp=self.MAX_HP,
            scene=scene,
        )

        # ---- وضعیت حرکت ----
        self.target_vx: float = 0.0
        self.target_vy: float = 0.0

        # ---- شلیک ----
        self.shoot_cd: float = 0.0
        self.muzzle_flash: float = 0.0
        self.recoil: float = 0.0

        # ---- نامیرایی ----
        self.invuln_time: float = self.INVULN_TIME

        # ---- Power-Up ----
        self.powerup_time: float = 0.0

        # ---- Thruster ----
        self._thruster_timer: float = 0.0
        self._thruster_rate: float = 0.025

        # ---- زمان انیمیشن ----
        self._t: float = 0.0

    # ─────────────────────────────────────────────────────────────────────
    #  هوک‌های قابل Override
    # ─────────────────────────────────────────────────────────────────────

    def draw_ship(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        """
        رسم بدنه‌ی سفینه. باید توسط هر زیرکلاس پیاده‌سازی شود.
        مختصات cx, cy مرکز سفینه است (با در نظر گرفتن recoil).
        """
        # پیش‌فرض: یک مثلث ساده (برای تست)
        r = int(self.radius)
        hull = [
            (cx, cy - int(r * 1.2)),
            (cx - int(r * 0.8), cy + int(r * 0.9)),
            (cx + int(r * 0.8), cy + int(r * 0.9)),
        ]
        pygame.draw.polygon(surface, self.PRIMARY_COLOR, hull)
        pygame.draw.polygon(surface, self.HIGHLIGHT_COLOR, hull, 2)

    def get_engine_offsets(self) -> list[tuple[float, float, float]]:
        """
        موقعیت شعله‌های موتور نسبت به مرکز و radius.
        خروجی: [(offset_x_ratio, offset_y_ratio, scale), ...]
        """
        return [(0.0, 1.0, 1.0)]

    def _get_shot_angles(self) -> list[float]:
        """
        زاویه‌های شلیک (درجه). -90 = مستقیم به بالا.
        زیرکلاس‌ها برای الگوی شلیک خاص، این را Override می‌کنند.
        """
        if self.powerup_time > 0.0:
            return [-102.0, -90.0, -78.0]
        return [-90.0]

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update_entity(self, dt: float) -> None:
        self._t += dt

        # ---- کاهش timers ----
        if self.shoot_cd > 0.0:
            self.shoot_cd -= dt
        if self.invuln_time > 0.0:
            self.invuln_time -= dt
        if self.powerup_time > 0.0:
            self.powerup_time -= dt
        if self.muzzle_flash > 0.0:
            self.muzzle_flash = max(0.0, self.muzzle_flash - dt * 6.0)
        if self.recoil > 0.0:
            self.recoil = max(0.0, self.recoil - dt * 8.0)

        # ---- حرکت ----
        self._handle_movement(dt)

        # ---- Thruster particles ----
        if self.scene is not None:
            self._emit_thruster(dt)

    # ─────────────────────────────────────────────────────────────────────
    #  حرکت
    # ─────────────────────────────────────────────────────────────────────

    def _handle_movement(self, dt: float) -> None:
        if self.scene is None:
            return

        # ---- ورودی ----
        axis_x = 0.0
        axis_y = 0.0
        if self.scene.any_held(S.Keys.LEFT):
            axis_x -= 1.0
        if self.scene.any_held(S.Keys.RIGHT):
            axis_x += 1.0
        if self.scene.any_held(S.Keys.UP):
            axis_y -= 1.0
        if self.scene.any_held(S.Keys.DOWN):
            axis_y += 1.0

        # نرمال‌سازی برای حرکت قطری یکنواخت
        mag = math.hypot(axis_x, axis_y)
        if mag > 0.001:
            axis_x /= mag
            axis_y /= mag

        self.target_vx = axis_x * self.SPEED
        self.target_vy = axis_y * self.SPEED

        # ---- شتاب (lerp به سمت سرعت هدف) ----
        blend = min(1.0, dt * self.ACCEL)
        self.vx += (self.target_vx - self.vx) * blend
        self.vy += (self.target_vy - self.vy) * blend

        # ---- میرایی اضافی وقتی ورودی نیست ----
        if mag < 0.001:
            damp = max(0.0, 1.0 - dt * self.DRAG)
            self.vx *= damp
            self.vy *= damp

        # ---- اعمال موقعیت ----
        self.x += self.vx * dt
        self.y += self.vy * dt

        # ---- کلیمپ به صفحه ----
        margin = self.radius + 6
        self.x = max(margin, min(S.Window.WIDTH - margin, self.x))
        self.y = max(margin, min(S.Window.HEIGHT - margin, self.y))

    # ─────────────────────────────────────────────────────────────────────
    #  Thruster Particles
    # ─────────────────────────────────────────────────────────────────────

    def _emit_thruster(self, dt: float) -> None:
        speed_factor = 1.0 + max(0.0, -self.vy) / 300.0
        self._thruster_timer -= dt * speed_factor
        if self._thruster_timer > 0.0:
            return
        self._thruster_timer = self._thruster_rate * random.uniform(0.7, 1.3)

        for ox, oy, _ in self.get_engine_offsets():
            px = self.x + ox * self.radius
            py = self.y + oy * self.radius
            try:
                self.scene.spawn_thruster_particle(
                    px, py,
                    self.vx * 0.3 + random.uniform(-30, 30),
                    120.0 + random.uniform(0, 80),
                )
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────
    #  شلیک
    # ─────────────────────────────────────────────────────────────────────

    def try_shoot(self) -> list[Bullet]:
        """
        اگر آماده است، گلوله‌ها را برمی‌گرداند و cooldown را ست می‌کند.
        """
        if self.shoot_cd > 0.0 or not self.alive:
            return []

        self.shoot_cd = self.SHOOT_CD
        self.muzzle_flash = 1.0
        self.recoil = 0.6

        bullets: list[Bullet] = []
        for angle_deg in self._get_shot_angles():
            a = math.radians(angle_deg)
            vx = math.cos(a) * self.BULLET_SPEED
            vy = math.sin(a) * self.BULLET_SPEED
            # موقعیت شروع از نوک سفینه
            ox = math.cos(a) * (self.radius + 6)
            oy = math.sin(a) * (self.radius + 6)

            bullets.append(Bullet(
                self.x + ox,
                self.y + oy,
                vx, vy,
                friendly=True,
                kind=self.BULLET_KIND,
                damage=self.BULLET_DAMAGE,
                scene=self.scene,
            ))

        # ---- صدا ----
        if self.scene is not None:
            try:
                self.scene.audio.play("player_shoot")
            except Exception:
                pass

        return bullets

    # ─────────────────────────────────────────────────────────────────────
    #  قدرت‌دهی (Power-Up)
    # ─────────────────────────────────────────────────────────────────────

    def grant_powerup(self, duration: Optional[float] = None) -> None:
        """فعال‌سازی الگوی شلیک قدرتمند برای مدت مشخص."""
        d = S.PowerupCfg.DURATION if duration is None else duration
        self.powerup_time = d

    def grant_shield(self, duration: float) -> None:
        """پیش‌فرض: نامیرایی موقت (زیرکلاس‌ها می‌توانند Override کنند)."""
        self.invuln_time = max(self.invuln_time, duration)

    def grant_rapid_fire(self, duration: float) -> None:
        """پیش‌فرض: کاهش موقت cooldown — زیرکلاس می‌تواند Override کند."""
        # فعلاً فقط half cooldown توسط flag موقت
        if not hasattr(self, "_rapid_fire_time"):
            self._rapid_fire_time = 0.0
        self._rapid_fire_time = duration
        self._rapid_fire_base_cd = self.SHOOT_CD

    # ─────────────────────────────────────────────────────────────────────
    #  آسیب
    # ─────────────────────────────────────────────────────────────────────

    def take_damage(self, damage: int) -> bool:  # type: ignore[override]
        """احترام به نامیرایی."""
        if self.invuln_time > 0.0 or not self.alive:
            return False
        return super().take_damage(damage)

    def on_hit(self, damage: int) -> None:
        self.invuln_time = self.INVULN_TIME
        if self.scene is not None:
            try:
                self.scene.camera.shake(S.FxCfg.SHAKE_ON_HIT)
            except Exception:
                pass

    def on_death(self) -> None:
        if self.scene is not None:
            try:
                self.scene.spawn_player_explosion(self.x, self.y)
            except Exception:
                pass

    def on_spawn(self) -> None:
        self.angle = -90.0

    # ─────────────────────────────────────────────────────────────────────
    #  رسم
    # ─────────────────────────────────────────────────────────────────────

    def draw_entity(self, surface: pygame.Surface) -> None:
        # ---- چشمک نامیرایی ----
        if self.invuln_time > 0.0:
            if int(self.invuln_time * 12) % 2 == 0:
                self._draw_invuln_aura(surface)
                return

        # ---- محاسبه‌ی مرکز (با recoil) ----
        offset_y = self.recoil * 3.0
        cx = int(self.x)
        cy = int(self.y + offset_y)

        # ---- شعله‌ی موتور ----
        self._draw_engine_flames(surface)

        # ---- بدنه‌ی سفینه (زیرکلاس) ----
        self.draw_ship(surface, cx, cy)

        # ---- افکت‌های شرطی ----
        if self.muzzle_flash > 0.05:
            self._draw_muzzle_flash(surface, cx, cy)

        if self.powerup_time > 0.0:
            self._draw_powerup_ring(surface, cx, cy)

    # ─────────────────────────────────────────────────────────────────────
    #  اجزای رسم مشترک
    # ─────────────────────────────────────────────────────────────────────

    def _draw_aura(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = int(self.radius * 1.6)
        if r <= 0:
            return
        aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        c = self.PRIMARY_COLOR
        for rr in range(r, 0, -2):
            a = int(40 * (1 - rr / r) ** 1.4)
            if a <= 0:
                continue
            pygame.draw.circle(aura, (c[0], c[1], c[2], a), (r, r), rr)
        surface.blit(aura, (cx - r, cy - r), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_engine_flames(self, surface: pygame.Surface) -> None:
        r = self.radius
        thrust = max(0.0, -self.vy) * 0.05
        base_len = r * 1.4 + thrust

        for ox, oy, scale in self.get_engine_offsets():
            px = int(self.x + ox * r)
            py = int(self.y + oy * r)
            length = base_len * scale
            width = r * 0.28 * scale
            self._draw_single_flame(surface, px, py, length, width)

    def _draw_single_flame(
        self,
        surface: pygame.Surface,
        x: int, y: int,
        length: float, width: float,
    ) -> None:
        flicker = 1.0 + 0.25 * math.sin(self._t * 34.0 + x * 0.1)
        length = length * flicker
        w = max(1, int(width))

        fc = self.FLAME_COLOR
        # لایه‌ی بیرونی
        pygame.draw.polygon(surface, fc, [
            (x - w, y), (x + w, y), (x, y + int(length)),
        ])
        # میانی
        pygame.draw.polygon(surface, (255, 200, 90), [
            (x - int(w * 0.65), y), (x + int(w * 0.65), y),
            (x, y + int(length * 0.75)),
        ])
        # داخلی
        pygame.draw.polygon(surface, (255, 240, 150), [
            (x - int(w * 0.35), y), (x + int(w * 0.35), y),
            (x, y + int(length * 0.5)),
        ])

    def _draw_cockpit(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = max(2, int(self.radius * 0.18))
        y_off = int(self.radius * 0.35)
        pygame.draw.circle(surface, self.ACCENT_COLOR, (cx, cy - y_off), r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy - y_off - 1), max(1, r - 2))

    def _draw_muzzle_flash(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        a = self.muzzle_flash
        r = int(self.radius * 0.7 * (1.0 + a * 0.6))
        if r <= 0:
            return
        flash = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        c = self.PRIMARY_COLOR
        for rr in range(r, 0, -1):
            alpha = int(180 * a * (1 - rr / r))
            if alpha <= 0:
                continue
            pygame.draw.circle(flash, (c[0], c[1], c[2], alpha), (r, r), rr)
        pygame.draw.circle(flash, (255, 255, 255, int(255 * a)), (r, r), max(1, r // 3))

        flash_y = cy - int(self.radius * 1.2)
        surface.blit(flash, (cx - r, flash_y - r),
                     special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_powerup_ring(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = int(self.radius * 2.0)
        num_dots = 14
        dot_size = max(2, int(self.radius * 0.14))
        c = self.ACCENT_COLOR

        for i in range(num_dots):
            angle = (i / num_dots) * math.tau + self._t * 2.8
            dx = int(math.cos(angle) * r)
            dy = int(math.sin(angle) * r)
            a = 0.5 + 0.5 * math.sin(self._t * 6.0 + i * 0.5)
            alpha = int(140 + 100 * a)

            dot = pygame.Surface((dot_size * 4, dot_size * 4), pygame.SRCALPHA)
            pygame.draw.circle(dot, (c[0], c[1], c[2], alpha),
                               (dot_size * 2, dot_size * 2), dot_size * 2)
            pygame.draw.circle(dot, (255, 255, 255, alpha),
                               (dot_size * 2, dot_size * 2), dot_size)
            surface.blit(
                dot,
                (cx + dx - dot_size * 2, cy + dy - dot_size * 2),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    def _draw_invuln_aura(self, surface: pygame.Surface) -> None:
        r = int(self.radius * 2.2)
        if r <= 0:
            return
        aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for rr in range(r, 0, -2):
            alpha = int(80 * (1 - rr / r))
            if alpha <= 0:
                continue
            pygame.draw.circle(aura, (60, 220, 255, alpha), (r, r), rr)
        cx, cy = int(self.x), int(self.y)
        surface.blit(aura, (cx - r, cy - r),
                     special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, (100, 240, 255), (cx, cy), r - 4, 2)

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌ها
    # ─────────────────────────────────────────────────────────────────────

    def reset_to_start(self) -> None:
        """بازگرداندن پلیر به موقعیت شروع (برای Restart)."""
        self.x = S.Window.WIDTH / 2
        self.y = S.Window.HEIGHT - S.PlayerCfg.RESPAWN_Y
        self.vx = 0.0
        self.vy = 0.0
        self.hp = self.MAX_HP
        self.invuln_time = self.INVULN_TIME
        self.powerup_time = 0.0
        self.shoot_cd = 0.0
        self.alive = True

    @staticmethod
    def darker(c: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
        return (max(0, c[0] - amount), max(0, c[1] - amount), max(0, c[2] - amount))

    @staticmethod
    def lighter(c: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
        return (min(255, c[0] + amount), min(255, c[1] + amount), min(255, c[2] + amount))


__all__ = ["Player"]