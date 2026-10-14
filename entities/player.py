"""
entities/player.py
==================

سفینه‌ی بازیکن (Player Ship) در SPACE BLASTER.

این کلاس مسئول تجربه‌ی مستقیم کاربر است، پس باید دقیق، پاسخ‌گو و
لذت‌بخش باشد. ویژگی‌ها:

    • حرکت با شتاب و میرایی نرم (acceleration + drag) — کنترل حرفه‌ای
    • شلیک با cooldown، muzzle flash و recoil
    • شعله‌ی موتور پویا (اندازه/رنگ با سرعت عمودی تغییر می‌کند)
    • ذرات پس‌زمینه‌ی موتور (thruster particles) با spawn خودکار
    • Invulnerability پس از ضربه با چشمک‌زن و هاله‌ی نئون
    • Power-Up «شلیک سه‌گانه» با تایمر و نوار بصری
    • ظاهر چندلایه: بدنه، بال‌ها، کابین، هاله، شعله
    • HUD-ready: hp، powerup_time، cooldown برای نمایش

این کلاس با scene خودش حرف می‌زند تا گلوله/ذره spawn کند. اگر scene
نداشته باشد، باز هم امن کار می‌کند (فقط گلوله spawn نمی‌شود).
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
#  کلاس Player
# ═══════════════════════════════════════════════════════════════════════════

class Player(Entity):
    """
    سفینه‌ی بازیکن.

    وضعیت‌های داخلی مهم:
        powerup_time   — ثانیه‌ی باقی‌مانده از شلیک سه‌گانه
        invuln_time    — ثانیه‌ی باقی‌مانده از نامیرایی
        shoot_cd       — ثانیه تا شلیک بعدی
        target_vx, vy  — سرعت هدف برای حرکت نرم
    """

    # ─────────────────────────────────────────────────────────────────────
    #  سازنده
    # ─────────────────────────────────────────────────────────────────────

    def __init__(
        self,
        scene: Optional["GameplayScene"] = None,
    ) -> None:
        # موقعیت اولیه: پایین-وسط صفحه
        start_x = S.Window.WIDTH / 2
        start_y = S.Window.HEIGHT - S.PlayerCfg.RESPAWN_Y

        super().__init__(
            start_x, start_y,
            radius=S.PlayerCfg.RADIUS,
            hp=S.PlayerCfg.MAX_HP,
            scene=scene,
        )

        # ---- حرکت ----
        self.target_vx: float = 0.0
        self.target_vy: float = 0.0
        self._accel: float = 9.0       # ضریب شتاب (پیکسل/ثانیه²)
        self._drag: float = 7.5        # ضریب میرایی
        self._speed: float = S.PlayerCfg.SPEED

        # ---- شلیک ----
        self.shoot_cd: float = 0.0
        self.muzzle_flash: float = 0.0  # 0..1 — پس از شلیک به 1 می‌رسد
        self.recoil: float = 0.0        # 0..1 — پس از شلیک

        # ---- نامیرایی ----
        self.invuln_time: float = S.PlayerCfg.INVULN_TIME  # شروع با کمی زمان ایمنی

        # ---- Power-Up ----
        self.powerup_time: float = 0.0

        # ---- Thruster ----
        self._thruster_timer: float = 0.0
        self._thruster_rate: float = 0.025   # ثانیه بین دو ذره

        # ---- انیمیشن ورود ----
        self._enter_anim: float = 0.0        # 0..1 — 1 ثانیه

        # ---- زمان برای انیمیشن‌های چرخه‌ای ----
        self._t: float = 0.0

    # ─────────────────────────────────────────────────────────────────────
    #  هوک‌ها
    # ─────────────────────────────────────────────────────────────────────

    def on_spawn(self) -> None:
        self.angle = -90.0  # سفینه به سمت بالا نگاه می‌کند

    def on_death(self) -> None:
        """وقتی از بین می‌رود، انفجار بزرگ سفینه‌ای spawn کن."""
        if self.scene is not None:
            try:
                self.scene.spawn_player_explosion(self.x, self.y)
            except Exception:
                pass

    def on_hit(self, damage: int) -> None:
        """پس از ضربه، نامیرایی فعال می‌شود."""
        self.invuln_time = S.PlayerCfg.INVULN_TIME
        if self.scene is not None:
            try:
                self.scene.camera.shake(S.FxCfg.SHAKE_ON_HIT)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update_entity(self, dt: float) -> None:
        # ---- زمان ----
        self._t += dt

        # ---- انیمیشن ورود ----
        if self._enter_anim < 1.0:
            self._enter_anim = min(1.0, self._enter_anim + dt * 1.5)

        # ---- timers ----
        if self.shoot_cd > 0:
            self.shoot_cd -= dt
        if self.invuln_time > 0:
            self.invuln_time -= dt
        if self.powerup_time > 0:
            self.powerup_time -= dt
        if self.muzzle_flash > 0:
            self.muzzle_flash = max(0.0, self.muzzle_flash - dt * 6.0)
        if self.recoil > 0:
            self.recoil = max(0.0, self.recoil - dt * 8.0)

        # ---- ورودی → شتاب هدف ----
        self._handle_movement(dt)

        # ---- Thruster particles ----
        if self.scene is not None and self._enter_anim > 0.4:
            self._emit_thruster(dt)

    # ── حرکت نرم با شتاب و میرایی ──
    def _handle_movement(self, dt: float) -> None:
        if self.scene is None:
            return

        # محاسبه‌ی محورهای ورودی
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

        # سرعت هدف
        self.target_vx = axis_x * self._speed
        self.target_vy = axis_y * self._speed

        # شتاب: سرعت فعلی را به سرعت هدف میل می‌دهیم
        blend = min(1.0, dt * self._accel)
        self.vx += (self.target_vx - self.vx) * blend
        self.vy += (self.target_vy - self.vy) * blend

        # میرایی اضافی وقتی ورودی نیست
        if mag < 0.001:
            damp = max(0.0, 1.0 - dt * self._drag)
            self.vx *= damp
            self.vy *= damp

        # ---- اعمال موقعیت ----
        self.x += self.vx * dt
        self.y += self.vy * dt

        # ---- کلیمپ به صفحه ----
        margin = self.radius + 6
        self.x = max(margin, min(S.Window.WIDTH - margin, self.x))
        self.y = max(margin, min(S.Window.HEIGHT - margin, self.y))

        # ---- زاویه‌ی ظاهری (کمی به سمت حرکت کج می‌شود) ----
        target_tilt = -self.vx * 0.06
        self.angle = -90.0 + target_tilt

    # ── ذرات موتور ──
    def _emit_thruster(self, dt: float) -> None:
        # نرخ ذره بر اساس سرعت عمودی
        speed_factor = 1.0 + max(0.0, -self.vy) / 300.0
        self._thruster_timer -= dt * speed_factor
        if self._thruster_timer > 0:
            return
        self._thruster_timer = self._thruster_rate * random.uniform(0.7, 1.3)

        # موقعیت زیر سفینه + کمی پراکندگی
        ox = random.uniform(-4, 4)
        oy = self.radius + 4
        try:
            self.scene.spawn_thruster_particle(
                self.x + ox, self.y + oy,
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
        در صورت آماده بودن، گلوله(ها) را برمی‌گرداند و cooldown را ست می‌کند.
        اگر آماده نباشد، لیست خالی برمی‌گرداند.
        """
        if self.shoot_cd > 0 or not self.alive:
            return []

        self.shoot_cd = S.PlayerCfg.SHOOT_CD
        self.muzzle_flash = 1.0
        self.recoil = 0.6

        bullet_speed = S.PlayerCfg.BULLET_SPEED
        bullets: list[Bullet] = []

        # ---- Power-Up: شلیک سه‌گانه ----
        if self.powerup_time > 0.0:
            # سه گلوله با زوایای کمی متفاوت
            spread = 12.0  # درجه
            base = -90.0
            for offset in (-spread, 0.0, spread):
                a = math.radians(base + offset)
                vx = math.cos(a) * bullet_speed
                vy = math.sin(a) * bullet_speed
                bullets.append(Bullet(
                    self.x + math.cos(a) * (self.radius + 4),
                    self.y + math.sin(a) * (self.radius + 4),
                    vx, vy,
                    friendly=True,
                    kind=BulletKind.PLAYER,
                    scene=self.scene,
                ))
        else:
            bullets.append(Bullet(
                self.x,
                self.y - (self.radius + 4),
                0.0, -bullet_speed,
                friendly=True,
                kind=BulletKind.PLAYER,
                scene=self.scene,
            ))

        # ---- صدا (اگر scene صدا داشته باشد) ----
        if self.scene is not None:
            try:
                self.scene.audio.play("player_shoot")
            except Exception:
                pass

        return bullets

    # ─────────────────────────────────────────────────────────────────────
    #  قدرت‌دهی
    # ─────────────────────────────────────────────────────────────────────

    def grant_powerup(self, duration: float | None = None) -> None:
        """فعال‌سازی شلیک سه‌گانه برای مدت مشخص."""
        d = S.PowerupCfg.DURATION if duration is None else duration
        self.powerup_time = d

    def take_damage(self, damage: int) -> bool:  # type: ignore[override]
        """بازنویسی برای احترام به نامیرایی."""
        if self.invuln_time > 0 or not self.alive:
            return False
        return super().take_damage(damage)

    # ─────────────────────────────────────────────────────────────────────
    #  رسم
    # ─────────────────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────────────────
    #  رسم — سفینه‌ی جنگنده‌ی فضایی چندلایه
    # ─────────────────────────────────────────────────────────────────────

    def draw_entity(self, surface: pygame.Surface) -> None:
        # ---- چشمک نامیرایی ----
        if self.invuln_time > 0:
            if int(self.invuln_time * 12) % 2 == 0:
                self._draw_invuln_aura(surface)
                return

        # محاسبه‌ی موقعیت (با recoil)
        offset_y = self.recoil * 3.0
        cx = int(self.x)
        cy = int(self.y + offset_y)
        r = self.radius

        # ترتیب رسم از عقب به جلو:
#        self._draw_aura(surface, cx, cy)            # ۱. هاله
        self._draw_engine_flames(surface)            # ۲. شعله‌های موتور (سه‌گانه)
        self._draw_wings(surface, cx, cy)            # ۳. بال‌ها
        self._draw_wing_details(surface, cx, cy)     # ۴. جزئیات بال‌ها
        self._draw_hull(surface, cx, cy)             # ۵. بدنه
        self._draw_panel_lines(surface, cx, cy)      # ۶. خطوط پنل
        self._draw_weapon_pods(surface, cx, cy)      # ۷. پادهای سلاح
        self._draw_cockpit(surface, cx, cy)          # ۸. کابین
        self._draw_energy_core(surface, cx, cy)      # ۹. هسته‌ی انرژی
        self._draw_edge_glow(surface, cx, cy)        # ۱۰. خطوط نئونی

        # ---- افکت‌های شرطی ----
        if self.muzzle_flash > 0.05:
            self._draw_muzzle_flash(surface, cx, cy)

        if self.powerup_time > 0.0:
            self._draw_powerup_ring(surface, cx, cy)

    # ═════════════════════════════════════════════════════════════════════
    #  لایه ۱: هاله‌ی زیر
    # ═════════════════════════════════════════════════════════════════════

    def _draw_aura(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = int(self.radius * 1.8)
        if r <= 0:
            return
        aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for rr in range(r, 0, -2):
            a = int(45 * (1 - rr / r) ** 1.5)
            if a <= 0:
                continue
            pygame.draw.circle(aura, (60, 220, 255, a), (r, r), rr)
        surface.blit(aura, (cx - r, cy - r),
                     special_flags=pygame.BLEND_RGBA_ADD)

    # ═════════════════════════════════════════════════════════════════════
    #  لایه ۲: شعله‌های سه‌گانه‌ی موتور
    # ═════════════════════════════════════════════════════════════════════

    def _draw_engine_flames(self, surface: pygame.Surface) -> None:
        r = self.radius
        # طول شعله با سرعت عمودی تغییر می‌کند
        thrust = max(0.0, -self.vy) * 0.05
        base_len = r * 1.6 + thrust

        # سه شعله: چپ، وسط، راست
        positions = [
            (int(self.x - r * 0.55), int(self.y + r * 0.9), 0.7),   # چپ
            (int(self.x),             int(self.y + r * 1.0), 1.0),   # وسط
            (int(self.x + r * 0.55), int(self.y + r * 0.9), 0.7),   # راست
        ]

        for px, py, scale in positions:
            self._draw_single_flame(surface, px, py, base_len * scale, r * 0.28 * scale)

    def _draw_single_flame(
        self, surface: pygame.Surface, x: int, y: int, length: float, width: float,
    ) -> None:
        # flicker انیمیشن
        flicker = 1.0 + 0.25 * math.sin(self._t * 34.0 + x * 0.1)
        length = length * flicker
        w = int(width)

        # شعله‌ی بیرونی (نارنجی)
        pygame.draw.polygon(surface, (255, 130, 20), [
            (x - w, y), (x + w, y), (x, y + int(length)),
        ])
        # میانی (نارنجی روشن)
        pygame.draw.polygon(surface, (255, 180, 60), [
            (x - int(w * 0.65), y), (x + int(w * 0.65), y),
            (x, y + int(length * 0.75)),
        ])
        # داخلی (زرد)
        pygame.draw.polygon(surface, (255, 230, 100), [
            (x - int(w * 0.4), y), (x + int(w * 0.4), y),
            (x, y + int(length * 0.5)),
        ])
        # هسته (سفید)
        pygame.draw.polygon(surface, (255, 255, 220), [
            (x - int(w * 0.2), y), (x + int(w * 0.2), y),
            (x, y + int(length * 0.28)),
        ])

    # ═════════════════════════════════════════════════════════════════════
    #  لایه ۳: بال‌ها
    # ═════════════════════════════════════════════════════════════════════

    def _draw_wings(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = self.radius

        # بال چپ — ذوزنقه‌ای با نوک تیز
        left = [
            (cx - int(r * 0.45), cy - int(r * 0.35)),      # بالا-داخلی
            (cx - int(r * 1.6),  cy + int(r * 0.4)),       # نوک بالا
            (cx - int(r * 1.45), cy + int(r * 0.75)),      # نوک پایین
            (cx - int(r * 0.85), cy + int(r * 0.9)),       # پایین-داخلی
            (cx - int(r * 0.4),  cy + int(r * 0.5)),       # لبه‌ی داخلی
        ]
        # بال راست — آینه
        right = [(cx + (cx - x), y) for (x, y) in left]

        # --- بال چپ ---
        pygame.draw.polygon(surface, (30, 130, 180), left)             # سایه
        pygame.draw.polygon(surface, (60, 220, 255), left, 2)          # خط نئون
        # نوار تیره‌ی داخلی
        inner_left = [
            (cx - int(r * 0.6), cy - int(r * 0.2)),
            (cx - int(r * 1.3), cy + int(r * 0.45)),
            (cx - int(r * 0.9), cy + int(r * 0.65)),
        ]
        pygame.draw.polygon(surface, (40, 100, 160), inner_left)

        # --- بال راست ---
        pygame.draw.polygon(surface, (30, 130, 180), right)
        pygame.draw.polygon(surface, (60, 220, 255), right, 2)
        inner_right = [(cx + (cx - x), y) for (x, y) in inner_left]
        pygame.draw.polygon(surface, (40, 100, 160), inner_right)

    # ═════════════════════════════════════════════════════════════════════
    #  لایه ۴: جزئیات بال‌ها (چراغ‌های ناوبری + خطوط)
    # ═════════════════════════════════════════════════════════════════════

    def _draw_wing_details(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = self.radius
        # چراغ ناوبری چپ (قرمز)
        blink_c = 0.6 + 0.4 * math.sin(self._t * 4.0)
        a_left = int(200 * blink_c)
        left_dot = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(left_dot, (255, 80, 80, a_left), (8, 8), 4)
        pygame.draw.circle(left_dot, (255, 200, 200, a_left), (8, 8), 2)
        surface.blit(left_dot, (cx - int(r * 1.35) - 8, cy + int(r * 0.3) - 8),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # چراغ ناوبری راست (سبز)
        a_right = int(200 * (1.0 - blink_c * 0.5))
        right_dot = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(right_dot, (80, 255, 120, a_right), (8, 8), 4)
        pygame.draw.circle(right_dot, (200, 255, 200, a_right), (8, 8), 2)
        surface.blit(right_dot, (cx + int(r * 1.35) - 8, cy + int(r * 0.3) - 8),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # خط تزئینی افقی روی هر بال
        for sign in (-1, 1):
            x1 = cx + sign * int(r * 0.7)
            x2 = cx + sign * int(r * 1.25)
            y_line = cy + int(r * 0.15)
            pygame.draw.line(surface, (150, 240, 255, 180),
                             (x1, y_line), (x2, y_line), 1)

    # ═════════════════════════════════════════════════════════════════════
    #  لایه ۵: بدنه‌ی مرکزی
    # ═════════════════════════════════════════════════════════════════════

    def _draw_hull(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = self.radius

        # بدنه‌ی اصلی — شش‌ضلعی کشیده به سمت بالا
        hull = [
            (cx,                      cy - int(r * 1.4)),   # نوک بالا
            (cx - int(r * 0.4),       cy - int(r * 0.3)),
            (cx - int(r * 0.5),       cy + int(r * 0.7)),
            (cx,                      cy + int(r * 1.0)),   # پایین وسط
            (cx + int(r * 0.5),       cy + int(r * 0.7)),
            (cx + int(r * 0.4),       cy - int(r * 0.3)),
        ]

        # لایه‌ی تیره‌ی زیرین (سایه)
        hull_shadow = [(x, y + 2) for (x, y) in hull]
        pygame.draw.polygon(surface, (10, 40, 70), hull_shadow)

        # پرکردن با گرادیان شبیه‌سازی‌شده (سه لایه رنگ)
        pygame.draw.polygon(surface, (20, 80, 140), hull)             # بدنه‌ی تیره
        # لایه‌ی میانی روشن‌تر (نصف بالایی)
        hull_mid = [
            (cx, cy - int(r * 1.3)),
            (cx - int(r * 0.3), cy - int(r * 0.2)),
            (cx + int(r * 0.3), cy - int(r * 0.2)),
        ]
        pygame.draw.polygon(surface, (60, 140, 210), hull_mid)
        # خط نئون دور
        pygame.draw.polygon(surface, (100, 240, 255), hull, 2)

        # ---- پنل بالایی روشن (مثلث کوچک در نوک) ----
        tip_panel = [
            (cx, cy - int(r * 1.25)),
            (cx - int(r * 0.2), cy - int(r * 0.7)),
            (cx + int(r * 0.2), cy - int(r * 0.7)),
        ]
        pygame.draw.polygon(surface, (220, 250, 255), tip_panel)

    # ═════════════════════════════════════════════════════════════════════
    #  لایه ۶: خطوط پنل و رگه‌های تزئینی
    # ═════════════════════════════════════════════════════════════════════

    def _draw_panel_lines(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = self.radius

        # خط مرکزی عمودی (با انیمیشن pulse)
        pulse_a = int(180 + 60 * math.sin(self._t * 5.0))
        for i in range(3):
            y1 = cy - int(r * 1.1) + i * 6
            y2 = y1 + 4
            pygame.draw.line(
                surface, (100, 240, 255),
                (cx, y1), (cx, y2), 1,
            )

        # رگه‌های انرژی — خطوط موازی کوچک
        for sign in (-1, 1):
            for i in range(2):
                x = cx + sign * int(r * 0.15 + i * r * 0.12)
                y1 = cy - int(r * 0.6 + i * 3)
                y2 = cy + int(r * 0.3)
                pygame.draw.line(surface, (60, 180, 240), (x, y1), (x, y2), 1)

        # هشدار: خط افقی کوتاه نزدیک نوک
        pygame.draw.line(
            surface, (255, 220, 80),
            (cx - int(r * 0.2), cy - int(r * 0.9)),
            (cx + int(r * 0.2), cy - int(r * 0.9)),
            1,
        )

    # ═════════════════════════════════════════════════════════════════════
    #  لایه ۷: پادهای سلاح (نقاط نارنجی روی بال‌ها)
    # ═════════════════════════════════════════════════════════════════════

    def _draw_weapon_pods(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = self.radius

        # مبدأ شلیک — هماهنگ با try_shoot
        pod_y = cy - int(r * 0.3)
        for sign in (-1, 1):
            pod_x = cx + sign * int(r * 1.05)

            # پاد — مربع کوچک
            pod_w = max(3, int(r * 0.18))
            pod_h = max(4, int(r * 0.25))
            pod_rect = pygame.Rect(
                pod_x - pod_w, pod_y - pod_h // 2,
                pod_w * 2, pod_h,
            )
            pygame.draw.rect(surface, (80, 100, 130), pod_rect)
            pygame.draw.rect(surface, (200, 220, 255), pod_rect, 1)

            # نور نارنجی روی پاد
            glow_size = max(3, int(r * 0.15))
            glow = pygame.Surface((glow_size * 4, glow_size * 4), pygame.SRCALPHA)
            pygame.draw.circle(
                glow, (255, 150, 40, 180),
                (glow_size * 2, glow_size * 2), glow_size * 2,
            )
            pygame.draw.circle(
                glow, (255, 240, 180, 220),
                (glow_size * 2, glow_size * 2), glow_size,
            )
            surface.blit(
                glow,
                (pod_x - glow_size * 2, pod_y - glow_size * 2),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    # ═════════════════════════════════════════════════════════════════════
    #  لایه ۸: کابین
    # ═════════════════════════════════════════════════════════════════════

    def _draw_cockpit(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = self.radius
        cab_y = cy - int(r * 0.35)

        # بیضی کابین
        cab_w = max(4, int(r * 0.35))
        cab_h = max(5, int(r * 0.55))

        cab_rect = pygame.Rect(cab_x := cx - cab_w, cab_y - cab_h, cab_w * 2, cab_h * 2)

        # --- لایه‌ی بیرونی (تیره) ---
        pygame.draw.ellipse(surface, (20, 60, 100), cab_rect)

        # --- کابین داخلی (روشن) ---
        inner = cab_rect.inflate(-2, -2)
        pygame.draw.ellipse(surface, (80, 180, 230), inner)

        # --- درخشش داخلی ---
        glow_size = max(2, int(r * 0.15))
        glow = pygame.Surface((glow_size * 4, glow_size * 4), pygame.SRCALPHA)
        for rr in range(glow_size * 2, 0, -1):
            a = int(120 * (1 - rr / (glow_size * 2)))
            if a <= 0:
                continue
            pygame.draw.circle(glow, (200, 240, 255, a),
                               (glow_size * 2, glow_size * 2), rr)
        surface.blit(
            glow,
            (cx - glow_size * 2, cab_y - glow_size * 2),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        # --- بازتاب روی کابین ---
        refl = pygame.Rect(cab_rect.x + 2, cab_rect.y + 2,
                           max(2, cab_rect.w // 3), max(2, cab_rect.h // 4))
        pygame.draw.ellipse(surface, (220, 250, 255), refl)

    # ═════════════════════════════════════════════════════════════════════
    #  لایه ۹: هسته‌ی انرژی (پالسی)
    # ═════════════════════════════════════════════════════════════════════

    def _draw_energy_core(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = self.radius
        core_y = cy + int(r * 0.3)

        # پالس
        pulse = 0.7 + 0.3 * math.sin(self._t * 6.0)
        size = max(2, int(r * 0.2 * pulse))

        core = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
        center = size * 3
        # هاله
        for rr in range(size * 3, 0, -1):
            a = int(120 * (1 - rr / (size * 3)) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(core, (255, 220, 80, a), (center, center), rr)
        # هسته
        pygame.draw.circle(core, (255, 250, 200), (center, center), size)
        surface.blit(core, (cx - center, core_y - center),
                     special_flags=pygame.BLEND_RGBA_ADD)

    # ═════════════════════════════════════════════════════════════════════
    #  لایه ۱۰: خطوط نئونی نهایی (Edge Glow)
    # ═════════════════════════════════════════════════════════════════════

    def _draw_edge_glow(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = self.radius

        # خط ضخیم نئونی دور بدنه — با پالس شفافیت
        a = int(180 + 60 * math.sin(self._t * 3.0))

        # نقاط درخشان روی نوک بال‌ها
        for sign in (-1, 1):
            tip_x = cx + sign * int(r * 1.6)
            tip_y = cy + int(r * 0.4)
            tip_glow = pygame.Surface((12, 12), pygame.SRCALPHA)
            for rr in range(6, 0, -1):
                ga = int(80 * (1 - rr / 6))
                pygame.draw.circle(tip_glow, (100, 240, 255, ga), (6, 6), rr)
            surface.blit(
                tip_glow, (tip_x - 6, tip_y - 6),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    # ═════════════════════════════════════════════════════════════════════
    #  افکت: فلاش شلیک
    # ═════════════════════════════════════════════════════════════════════

    def _draw_muzzle_flash(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        a = self.muzzle_flash
        r = int(self.radius * 0.7 * (1.0 + a * 0.6))
        if r <= 0:
            return

        flash = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for rr in range(r, 0, -1):
            alpha = int(180 * a * (1 - rr / r))
            if alpha <= 0:
                continue
            pygame.draw.circle(flash, (150, 240, 255, alpha), (r, r), rr)
        # هسته‌ی سفید
        pygame.draw.circle(flash, (255, 255, 255, int(255 * a)), (r, r), max(1, r // 3))

        flash_y = cy - int(self.radius * 1.3)
        surface.blit(
            flash, (cx - r, flash_y - r),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

    # ═════════════════════════════════════════════════════════════════════
    #  افکت: حلقه‌ی Power-Up
    # ═════════════════════════════════════════════════════════════════════

    def _draw_powerup_ring(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = int(self.radius * 2.1)
        num_dots = 14
        dot_size = max(2, int(self.radius * 0.14))

        for i in range(num_dots):
            angle = (i / num_dots) * math.tau + self._t * 2.8
            dx = int(math.cos(angle) * r)
            dy = int(math.sin(angle) * r)
            a = 0.5 + 0.5 * math.sin(self._t * 6.0 + i * 0.5)
            alpha = int(140 + 100 * a)

            dot = pygame.Surface((dot_size * 4, dot_size * 4), pygame.SRCALPHA)
            pygame.draw.circle(dot, (255, 220, 60, alpha),
                               (dot_size * 2, dot_size * 2), dot_size * 2)
            pygame.draw.circle(dot, (255, 255, 200, alpha),
                               (dot_size * 2, dot_size * 2), dot_size)
            surface.blit(
                dot,
                (cx + dx - dot_size * 2, cy + dy - dot_size * 2),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    # ═════════════════════════════════════════════════════════════════════
    #  افکت: هاله‌ی نامیرایی
    # ═════════════════════════════════════════════════════════════════════

    def _draw_invuln_aura(self, surface: pygame.Surface) -> None:
        r = int(self.radius * 2.4)
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
        # حلقه‌ی نازک دور
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
        self.hp = S.PlayerCfg.MAX_HP
        self.invuln_time = S.PlayerCfg.INVULN_TIME
        self.powerup_time = 0.0
        self.shoot_cd = 0.0
        self.alive = True


__all__ = ["Player"]