"""
entities/powerup.py
===================

سیستم پاورآپ‌ها (Power-Ups) برای SPACE BLASTER — بازطراحی کامل.

طراحی هر نوع:
    • TRIPLE_SHOT : سفینه‌ی کوچیک با سه پرتوی شلیک
    • HEAL        : صلیب پزشکی با ضربان
    • SHIELD      : شش‌ضلعی زره‌ای با خطوط شبکه
    • BOMB        : مین دندانه‌دار با جرقه‌های چشمک‌زن
    • RAPID_FIRE  : صاعقه با خطوط سرعت کناری
"""

from __future__ import annotations

import math
import random
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable, Optional

import pygame

from core import settings as S
from entities.entity import Entity

if TYPE_CHECKING:
    from entities.player import Player
    from scenes.gameplay import GameplayScene



# انواع پاورآپ‌ها که اثر هرکدام در منطق جمع‌آوری به‌صورت جداگانه تعیین می‌شود.
# Power-up types whose individual effects are handled separately during collection.
class PowerupKind(Enum):
    TRIPLE_SHOT = auto()
    HEAL        = auto()
    SHIELD      = auto()
    BOMB        = auto()
    RAPID_FIRE  = auto()



class _Style:
    """رنگ‌ها و پارامترهای ظاهری هر نوع پاورآپ."""
    __slots__ = (
        "primary", "secondary", "accent",
        "glow", "weight",
    )

    def __init__(
        self,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
        glow: tuple[int, int, int],
        weight: float = 1.0,
    ) -> None:
        # رنگ‌های اصلی، ثانویه، تأکیدی و درخشش برای طراحی ظاهری هر نوع نگهداری می‌شوند.
        # Primary, secondary, accent, and glow colors are stored for each power-up's visual design.
        self.primary = primary
        self.secondary = secondary
        self.accent = accent
        self.glow = glow
        # وزن، احتمال انتخاب تصادفی این نوع پاورآپ را تعیین می‌کند.
        # Weight determines the probability of this power-up type being selected randomly.
        self.weight = weight


# تنظیمات ظاهری و وزن انتخاب تصادفی هر نوع پاورآپ.
# Visual settings and random-selection weights for each power-up type.
_STYLES: dict[PowerupKind, _Style] = {
    PowerupKind.TRIPLE_SHOT: _Style(
        primary=(255, 220, 90),
        secondary=(200, 130, 30),
        accent=(255, 255, 220),
        glow=(255, 180, 60),
        weight=3.0,
    ),
    PowerupKind.HEAL: _Style(
        primary=(120, 255, 150),
        secondary=(40, 140, 70),
        accent=(255, 255, 255),
        glow=(80, 220, 120),
        weight=2.0,
    ),
    PowerupKind.SHIELD: _Style(
        primary=(90, 220, 255),
        secondary=(30, 110, 180),
        accent=(220, 250, 255),
        glow=(60, 180, 255),
        weight=2.0,
    ),
    PowerupKind.BOMB: _Style(
        primary=(255, 110, 90),
        secondary=(160, 30, 30),
        accent=(255, 240, 180),
        glow=(255, 80, 60),
        weight=0.8,
    ),
    PowerupKind.RAPID_FIRE: _Style(
        primary=(255, 250, 120),
        secondary=(200, 130, 20),
        accent=(255, 255, 255),
        glow=(255, 220, 80),
        weight=1.8,
    ),
}



class Powerup(Entity):

    # ---- جذب مغناطیسی ----
    # محدوده‌ی فعال‌شدن جذب، قدرت کشش و فاصله‌ی جمع‌آوری پاورآپ را مشخص می‌کنند.
    # These values define the magnet activation range, pull strength, and collection distance.
    MAGNET_RANGE:  float = 130.0
    MAGNET_FORCE:  float = 620.0
    COLLECT_RANGE: float = 24.0


    def __init__(
        self,
        x: float,
        y: float,
        *,
        kind: Optional[PowerupKind] = None,
        scene: Optional["GameplayScene"] = None,
        lifetime: float = 12.0,
        fall_speed: Optional[float] = None,
    ) -> None:
        # در صورت مشخص‌نشدن نوع، یک پاورآپ با توجه به وزن‌های تعریف‌شده انتخاب می‌شود.
        # If no type is specified, a power-up is selected using the configured weights.
        if kind is None:
            kind = self._random_kind()

        # پالت رنگی متناسب با نوع انتخاب‌شده دریافت می‌شود.
        # The color palette corresponding to the selected type is retrieved.
        style = _STYLES[kind]

        # موقعیت، سرعت سقوط، شعاع برخورد و رفرنس صحنه در کلاس پایه مقداردهی می‌شوند.
        # Position, falling speed, collision radius, and scene reference are initialized in the base class.
        super().__init__(
            x, y,
            vx=0.0,
            vy=S.PowerupCfg.FALL_SPEED,
            radius=S.PowerupCfg.RADIUS,
            hp=1,
            scene=scene,
        )

        # نوع، سبک ظاهری و زمان حیات پاورآپ ثبت می‌شوند.
        # The power-up type, visual style, and lifetime are stored.
        self.kind: PowerupKind = kind
        self.style: _Style = style
        self.lifetime: float = float(lifetime)
        self.max_lifetime: float = float(lifetime)
        # سرعت سقوط اختصاصی، در صورت تعیین‌شدن، جایگزین مقدار پیش‌فرض تنظیمات می‌شود.
        # A custom falling speed, when provided, overrides the default configured speed.
        self.fall_speed: float = (
            S.PowerupCfg.FALL_SPEED if fall_speed is None else float(fall_speed)
        )

        # ---- مغناطیس ----
        # این پرچم مشخص می‌کند که پاورآپ در محدوده‌ی جذب مغناطیسی قرار دارد یا خیر.
        # This flag indicates whether the power-up is currently within magnetic attraction range.
        self._magnet_active: bool = False

        # ---- انیمیشن ----
        # مقادیر اولیه‌ی زمان و چرخش تصادفی‌اند تا پاورآپ‌ها حرکت بصری یکسانی نداشته باشند.
        # Initial time and rotation values are randomized to give power-ups varied visual motion.
        self._t: float = random.uniform(0, math.tau)
        self._rotation: float = random.uniform(0, 360)
        self._rotation_speed: float = random.uniform(30.0, 55.0) * random.choice((-1, 1))
        # مقیاس اولیه‌ی صفر، امکان اجرای انیمیشن بزرگ‌شدن هنگام ورود را فراهم می‌کند.
        # An initial scale of zero allows the power-up to grow into view during its spawn animation.
        self._spawn_scale: float = 0.0
        self._spawn_time: float = 0.42

        # ---- ذرات چرخان دور ----
        # برای هر ذره، زاویه، سرعت چرخش، فاصله از مرکز، اندازه و فاز چشمک‌زدن تعیین می‌شود.
        # Each orbiting particle receives an angle, rotation speed, distance from center, size, and twinkle phase.
        self._orbit_dots: list[dict] = [
            {
                "angle": random.uniform(0, math.tau),
                "speed": random.uniform(1.8, 2.8),
                "radius": random.uniform(1.3, 1.55),   # نسبت به radius
                "size": random.uniform(1.2, 2.0),
                "phase": random.uniform(0, math.tau),
            }
            for _ in range(4)
        ]


    @staticmethod
    def _random_kind() -> PowerupKind:
        # انواع پاورآپ و وزن متناظرشان برای انتخاب تصادفی استخراج می‌شوند.
        # Power-up types and their corresponding weights are collected for weighted random selection.
        kinds = list(_STYLES.keys())
        weights = [_STYLES[k].weight for k in kinds]
        return random.choices(kinds, weights=weights, k=1)[0]


    def update_entity(self, dt: float) -> None:
        # زمان انیمیشن و زاویه‌ی چرخش با زمان سپری‌شده از فریم به‌روزرسانی می‌شوند.
        # Animation time and rotation angle are updated using the elapsed frame time.
        self._t += dt
        self._rotation = (self._rotation + self._rotation_speed * dt) % 360

        # ---- انیمیشن ورود ----
        # مقیاس پاورآپ طی مدت مشخص‌شده به‌تدریج تا مقدار کامل افزایش می‌یابد.
        # The power-up scale gradually increases to its full value over the configured duration.
        if self._spawn_scale < 1.0:
            self._spawn_scale = min(1.0, self._spawn_scale + dt / self._spawn_time)

        # ---- ذرات چرخان ----
        # زاویه‌ی هر ذره مستقل از سایر ذرات و متناسب با سرعت خودش افزایش می‌یابد.
        # Each particle's angle advances independently according to its own rotation speed.
        for d in self._orbit_dots:
            d["angle"] += d["speed"] * dt

        # ---- عمر ----
        # با پایان زمان حیات، پاورآپ حذف می‌شود و ادامه‌ی به‌روزرسانی متوقف می‌گردد.
        # When the lifetime expires, the power-up is killed and further updating is stopped.
        self.lifetime -= dt
        if self.lifetime <= 0.0:
            self.kill()
            return

        # ---- مغناطیس / سقوط ----
        # در صورت وجود پلیر زنده، منطق جذب اجرا می‌شود؛ در غیر این صورت پاورآپ سقوط می‌کند.
        # If a living player exists, magnetic attraction is processed; otherwise, the power-up falls.
        player = self._get_player()
        if player is not None and player.alive:
            self._handle_magnet(player, dt)
        else:
            self.y += self.fall_speed * dt

        # ---- خروج از پایین ----
        # خروج کامل از پایین صفحه با علامت‌گذاری مرگ ثبت می‌شود.
        # Leaving the bottom of the screen completely marks the power-up for removal.
        if self.y > S.Window.HEIGHT + self.radius + 20:
            self.alive = False
            self._pending_kill = True

    def _get_player(self) -> Optional["Player"]:
        # اگر صحنه در دسترس نباشد، پلیر قابل بازیابی نیست.
        # If the scene is unavailable, the player cannot be retrieved.
        if self.scene is None:
            return None
        return getattr(self.scene, "player", None)

    def _handle_magnet(self, player: "Player", dt: float) -> None:
        # بردار و فاصله‌ی میان پاورآپ و پلیر برای محاسبه‌ی نیروی جذب به دست می‌آیند.
        # The vector and distance between the power-up and player are calculated for magnetic attraction.
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        if dist < self.MAGNET_RANGE:
            self._magnet_active = True
            # هرچه پاورآپ به پلیر نزدیک‌تر باشد، شدت جذب بیشتر می‌شود.
            # Attraction strength increases as the power-up gets closer to the player.
            strength = 1.0 - (dist / self.MAGNET_RANGE)
            strength = max(0.15, strength)
            if dist > 0.001:
                # بردار جهت نرمال می‌شود تا کشش در راستای پلیر و مستقل از فاصله اعمال شود.
                # The direction vector is normalized so the pull follows the player independently of distance.
                ux, uy = dx / dist, dy / dist
                pull = self.MAGNET_FORCE * strength * dt
                self.x += ux * pull
                self.y += uy * pull
            # رسیدن به محدوده‌ی جمع‌آوری، اثر پاورآپ را فعال می‌کند.
            # Entering the collection range activates the power-up's effect.
            if dist < self.COLLECT_RANGE:
                self._on_collect(player)
                return
        else:
            self._magnet_active = False
            # خارج از محدوده‌ی مغناطیس، حرکت عادی سقوط ادامه پیدا می‌کند.
            # Outside the magnetic range, normal falling movement continues.
            self.y += self.fall_speed * dt


    def _on_collect(self, player: "Player") -> None:
        # خطای احتمالی در اعمال اثر پاورآپ مانع ادامه‌ی فرایند جمع‌آوری نمی‌شود.
        # An exception while applying the power-up effect does not interrupt the collection process.
        try:
            self._apply_effect(player)
        except Exception:
            pass

        # افکت بصری، صدای دریافت و لرزش دوربین در صورت در دسترس بودن صحنه اجرا می‌شوند.
        # The visual burst, pickup sound, and camera shake are triggered when the scene is available.
        if self.scene is not None:
            try:
                self.scene.spawn_powerup_burst(self.x, self.y, self.style.glow)
                self.scene.audio.play("powerup_pickup")
                self.scene.camera.shake(3.0)
            except Exception:
                pass

        # پس از جمع‌آوری، پاورآپ از چرخه‌ی حیات خارج می‌شود.
        # After collection, the power-up is removed from its lifecycle.
        self.kill()

    def _apply_effect(self, player: "Player") -> None:
        # نوع پاورآپ مبنای انتخاب اثر قابل اعمال روی پلیر است.
        # The power-up type determines which effect is applied to the player.
        kind = self.kind

        if kind == PowerupKind.TRIPLE_SHOT:
            # قابلیت شلیک سه‌گانه برای مدت تعیین‌شده فعال می‌شود.
            # Triple-shot capability is activated for the configured duration.
            player.grant_powerup(S.PowerupCfg.DURATION)

        elif kind == PowerupKind.HEAL:
            # یک واحد سلامتی به پلیر اضافه می‌شود.
            # One health point is restored to the player.
            player.heal(1)

        elif kind == PowerupKind.SHIELD:
            # قابلیت سپر فقط در صورت وجود و قابل‌فراخوانی بودن متد مربوطه فعال می‌شود.
            # The shield is activated only if the corresponding method exists and is callable.
            fn: Optional[Callable] = getattr(player, "grant_shield", None)
            if callable(fn):
                fn(S.PowerupCfg.DURATION)

        elif kind == PowerupKind.BOMB:
            # بمب صفحه‌ای از طریق صحنه فعال می‌شود، زیرا اثر آن به کل محیط بازی وابسته است.
            # The screen bomb is triggered through the scene because its effect involves the entire game environment.
            if self.scene is not None:
                try:
                    self.scene.trigger_screen_bomb(self.x, self.y)
                except Exception:
                    pass

        elif kind == PowerupKind.RAPID_FIRE:
            # شلیک سریع در صورت پشتیبانی پلیر و برای مدت مشخص فعال می‌شود.
            # Rapid fire is activated for the configured duration if the player supports it.
            fn = getattr(player, "grant_rapid_fire", None)
            if callable(fn):
                fn(S.PowerupCfg.DURATION)


    def draw_entity(self, surface: pygame.Surface) -> None:
        # ---- محو شدن در ۲ ثانیه‌ی آخر ----
        # در دو ثانیه‌ی پایانی، شفافیت کاهش می‌یابد و با کم‌وزیادشدن دوره‌ای، حالت چشمک‌زن ایجاد می‌شود.
        # During the final two seconds, opacity decreases and periodic modulation creates a blinking effect.
        fade_alpha = 255
        if self.lifetime < 2.0:
            fade_alpha = int(255 * (self.lifetime / 2.0))
            if int(self.lifetime * 8) % 2 == 0:
                fade_alpha = int(fade_alpha * 0.5)

        # ---- scale ورود (ease-out-back) ----
        # تابع easing مقیاس انیمیشن ورود را با اندکی فراتررفتن از مقدار نهایی محاسبه می‌کند.
        # The easing function calculates the spawn scale with a slight overshoot beyond its final value.
        scale = self._ease_out_back(self._spawn_scale)

        # ---- پالس breathing ----
        # نوسان سینوسی، اندازه‌ی پایه‌ی آیکون را به‌آرامی تغییر می‌دهد.
        # A sinusoidal oscillation gently varies the icon's base size.
        pulse = 1.0 + 0.08 * math.sin(self._t * 4.5)
        base_r = self.radius * scale * pulse

        cx = int(self.x)
        cy = int(self.y)

        # ---- لایه‌ها (به ترتیب) ----
        # اجزای بصری از پس‌زمینه به پیش‌زمینه رسم می‌شوند تا عمق و تفکیک مناسبی داشته باشند.
        # Visual elements are drawn from background to foreground to create proper depth and separation.
        # ۱. درخشش نرم (خیلی کم، پشت همه)
        self._draw_soft_glow(surface, cx, cy, base_r, fade_alpha)

        # ۲. ذرات چرخان دور
        self._draw_orbit_dots(surface, cx, cy, base_r, fade_alpha)

        # ۳. سایه‌ی زیر (عمق)
        self._draw_ground_shadow(surface, cx, cy, base_r, fade_alpha)

        # ۴. آیکون اختصاصی
        self._draw_icon(surface, cx, cy, int(base_r), fade_alpha)


    def _draw_soft_glow(
        self,
        surface: pygame.Surface,
        cx: int, cy: int,
        r: float,
        alpha: int,
    ) -> None:
        """درخشش نرم خیلی کم — نه هاله‌ی دایره‌ای."""
        glow_r = int(r * 2.0)
        if glow_r < 4:
            return
        # سطح شفاف جداگانه برای ساخت گرادیان درخشش استفاده می‌شود.
        # A separate transparent surface is used to construct the glow gradient.
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        base_a = int(35 * (alpha / 255.0))
        # دایره‌های هم‌مرکز با آلفای متغیر، درخشش را به‌صورت تدریجی محو می‌کنند.
        # Concentric circles with varying alpha create a gradually fading glow.
        for rr in range(glow_r, 0, -3):
            a = int(base_a * (1 - rr / glow_r) ** 2.2)
            if a <= 0:
                continue
            pygame.draw.circle(glow, (*self.style.glow, a), (glow_r, glow_r), rr)
        surface.blit(
            glow, (cx - glow_r, cy - glow_r),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

    def _draw_orbit_dots(
        self,
        surface: pygame.Surface,
        cx: int, cy: int,
        r: float,
        alpha: int,
    ) -> None:
        """ذرات ریز چرخان دور آیکون (نقطه‌ای، نه دایره‌ای)."""
        # موقعیت هر ذره با زاویه‌ی فعلی و فاصله‌ی نسبی آن از مرکز محاسبه می‌شود.
        # Each particle's position is calculated from its current angle and relative distance from the center.
        for d in self._orbit_dots:
            a = d["angle"]
            rr = r * d["radius"]
            px = cx + math.cos(a) * rr
            py = cy + math.sin(a) * rr

            # تغییر سینوسی فاز ذره، شدت نور آن را به‌صورت متناوب تغییر می‌دهد.
            # Sinusoidal phase variation periodically changes the particle's light intensity.
            twinkle = 0.5 + 0.5 * math.sin(self._t * 6.0 + d["phase"])
            dot_a = int((100 + 120 * twinkle) * (alpha / 255.0))
            if dot_a <= 0:
                continue

            # دو دایره‌ی نورانی با اندازه‌های متفاوت، ظاهر درخشان ذره را ایجاد می‌کنند.
            # Two glowing circles of different sizes create the particle's luminous appearance.
            size = int(d["size"]) + 1
            dot_surf = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
            pygame.draw.circle(dot_surf, (*self.style.accent, dot_a),
                               (size * 3, size * 3), size * 2)
            pygame.draw.circle(dot_surf, (*self.style.glow, dot_a),
                               (size * 3, size * 3), size)
            surface.blit(
                dot_surf, (int(px - size * 3), int(py - size * 3)),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    def _draw_ground_shadow(
        self,
        surface: pygame.Surface,
        cx: int, cy: int,
        r: float,
        alpha: int,
    ) -> None:
        """سایه‌ی بیضوی نرم زیر آیکون."""
        # ابعاد سطح سایه متناسب با اندازه‌ی آیکون تعیین می‌شوند.
        # The shadow surface dimensions are determined proportionally to the icon size.
        sw = int(r * 1.2)
        sh = int(r * 0.35)
        if sw < 3:
            return
        shadow = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        # بیضی‌های تو‌در‌تو با آلفای تدریجی، سایه‌ای نرم و متمرکز ایجاد می‌کنند.
        # Nested ellipses with gradually changing alpha create a soft, concentrated shadow.
        for rr in range(sh, 0, -1):
            a = int(70 * (1 - rr / sh) ** 1.6 * (alpha / 255.0))
            if a <= 0:
                continue
            pygame.draw.ellipse(
                shadow, (0, 0, 0, a),
                (sw - rr, sh - rr, rr * 2, rr * 2),
            )
        surface.blit(shadow, (cx - sw, cy - sh))


    def _draw_icon(
        self,
        surface: pygame.Surface,
        cx: int, cy: int,
        r: int,
        alpha: int,
    ) -> None:
        # بر اساس نوع پاورآپ، تابع رسم آیکون اختصاصی همان نوع انتخاب می‌شود.
        # The drawing function for the corresponding power-up icon is selected based on its type.
        kind = self.kind
        if kind == PowerupKind.TRIPLE_SHOT:
            self._icon_triple_shot(surface, cx, cy, r, alpha)
        elif kind == PowerupKind.HEAL:
            self._icon_heal(surface, cx, cy, r, alpha)
        elif kind == PowerupKind.SHIELD:
            self._icon_shield(surface, cx, cy, r, alpha)
        elif kind == PowerupKind.BOMB:
            self._icon_bomb(surface, cx, cy, r, alpha)
        elif kind == PowerupKind.RAPID_FIRE:
            self._icon_rapid_fire(surface, cx, cy, r, alpha)

    # ── TRIPLE_SHOT: سفینه‌ی کوچیک با سه پرتو ──
    def _icon_triple_shot(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
        s = self.style
        # چرخش آیکون با ضریب کمتر از چرخش اصلی انجام می‌شود تا حرکت ملایم‌تری داشته باشد.
        # The icon rotates at a reduced rate to produce gentler motion than the main rotation.
        rot = math.radians(self._rotation * 0.4)

        # هاله‌ی طلایی (خط‌های شلیک)
        # سه پرتو با اختلاف زاویه‌ی مشخص، الگوی شلیک سه‌گانه را نمایش می‌دهند.
        # Three beams with fixed angular offsets represent the triple-shot firing pattern.
        for offset_deg in (-18, 0, 18):
            a = -math.pi / 2 + math.radians(offset_deg) + rot
            # خط از مرکز به بیرون
            x1 = cx + math.cos(a) * (r * 0.45)
            y1 = cy + math.sin(a) * (r * 0.45)
            x2 = cx + math.cos(a) * (r * 1.15)
            y2 = cy + math.sin(a) * (r * 1.15)

            # خط درخشان
            # سطح شفاف پیرامون هر پرتو ساخته می‌شود تا خطوط با رنگ و ضخامت متفاوت روی هم رسم شوند.
            # A transparent surface is created around each beam so layered lines can be drawn with different colors and widths.
            line_surf = pygame.Surface((int(abs(x2 - x1)) + 8, int(abs(y2 - y1)) + 8),
                                       pygame.SRCALPHA)
            ox = min(x1, x2) - 4
            oy = min(y1, y2) - 4
            pygame.draw.line(
                line_surf, (*s.primary, alpha),
                (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), 3,
            )
            pygame.draw.line(
                line_surf, (*s.accent, alpha),
                (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), 1,
            )
            surface.blit(line_surf, (ox, oy))

            # نقطه‌ی نور در نوک
            # نقطه‌ی انتهایی هر پرتو با دو لایه‌ی نوری رسم می‌شود.
            # The endpoint of each beam is rendered using two luminous layers.
            tx = cx + math.cos(a) * (r * 1.1)
            ty = cy + math.sin(a) * (r * 1.1)
            dot = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(dot, (*s.accent, alpha), (4, 4), 3)
            pygame.draw.circle(dot, (*s.primary, alpha), (4, 4), 2)
            surface.blit(dot, (int(tx - 4), int(ty - 4)))

        # ---- بدنه‌ی سفینه (مثلث کوچک) ----
        # سه رأس مثلث، فرم اصلی بدنه‌ی سفینه را تشکیل می‌دهند.
        # Three vertices define the main triangular body of the ship.
        tip = (cx, cy - int(r * 0.55))
        bl = (cx - int(r * 0.55), cy + int(r * 0.55))
        br = (cx + int(r * 0.55), cy + int(r * 0.55))

        # سایه‌ی بدنه
        # جابه‌جایی جزئی سایه به پایین، به بدنه عمق بصری می‌دهد.
        # A slight downward offset of the shadow gives the body visual depth.
        pygame.draw.polygon(surface, s.secondary, [
            (tip[0], tip[1] + 2),
            (bl[0], bl[1] + 2),
            (br[0], br[1] + 2),
        ])
        # بدنه
        pygame.draw.polygon(surface, s.primary, [tip, bl, br])
        # خط دور
        pygame.draw.polygon(surface, s.accent, [tip, bl, br], 2)

        # کابین درخشان وسط
        # کابین با دو دایره‌ی هم‌مرکز و روشنایی متفاوت مشخص می‌شود.
        # The cockpit is highlighted using two concentric circles with different brightness levels.
        cab_r = max(2, r // 5)
        pygame.draw.circle(surface, s.accent, (cx, cy - int(r * 0.05)), cab_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy - int(r * 0.05)), max(1, cab_r - 1))

    # ── HEAL: صلیب پزشکی ──
    def _icon_heal(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
        s = self.style
        # ضربان قلب (پالس قوی‌تر)
        # نوسان سینوسی اندازه‌ی صلیب را تغییر می‌دهد تا حس ضربان ایجاد شود.
        # A sinusoidal oscillation changes the cross size to create a heartbeat effect.
        beat = 1.0 + 0.12 * math.sin(self._t * 7.0)
        size = r * beat

        # ابعاد صلیب
        # طول بازوها و ضخامت آن‌ها از اندازه‌ی متغیر صلیب محاسبه می‌شوند.
        # The arm length and thickness are calculated from the cross's animated size.
        arm = int(size * 0.9)
        thick = int(size * 0.32)

        # سایه
        self._draw_cross(surface, cx + 2, cy + 2, arm, thick, s.secondary, alpha)
        # صلیب اصلی
        self._draw_cross(surface, cx, cy, arm, thick, s.primary, alpha)
        # خط روشن داخلی
        self._draw_cross_outline(surface, cx, cy, arm, thick, s.accent, alpha)

        # خط افقی روشن وسط
        # خطوط روشن مرکزی، جزئیات داخلی صلیب را برجسته می‌کنند.
        # Bright central lines emphasize the inner details of the cross.
        pygame.draw.line(
            surface, s.accent,
            (cx - arm + 3, cy), (cx + arm - 3, cy), 1,
        )
        pygame.draw.line(
            surface, s.accent,
            (cx, cy - arm + 3), (cx, cy + arm - 3), 1,
        )

    def _draw_cross(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, arm: int, thick: int,
        color: tuple[int, int, int], alpha: int,
    ) -> None:
        # بازوی عمودی صلیب با یک مستطیل رسم می‌شود.
        # The vertical arm of the cross is drawn as a rectangle.
        # عمودی
        pygame.draw.rect(
            surface, color,
            (cx - thick // 2, cy - arm, thick, arm * 2),
        )
        # بازوی افقی، مستطیل عمودی را در مرکز قطع می‌کند.
        # The horizontal arm intersects the vertical rectangle at the center.
        # افقی
        pygame.draw.rect(
            surface, color,
            (cx - arm, cy - thick // 2, arm * 2, thick),
        )

    def _draw_cross_outline(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, arm: int, thick: int,
        color: tuple[int, int, int], alpha: int,
    ) -> None:
        # فقط لبه‌های داخلی برای حس شیشه‌ای
        # مستطیل‌های متناظر با دو بازوی صلیب ساخته و با خط دور یک‌پیکسلی رسم می‌شوند.
        # Rectangles corresponding to both cross arms are created and drawn with a one-pixel outline.
        rect_v = pygame.Rect(cx - thick // 2, cy - arm, thick, arm * 2)
        rect_h = pygame.Rect(cx - arm, cy - thick // 2, arm * 2, thick)
        pygame.draw.rect(surface, color, rect_v, 1)
        pygame.draw.rect(surface, color, rect_h, 1)

    # ── SHIELD: شش‌ضلعی زره‌ای ──
    def _icon_shield(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
        s = self.style
        # زاویه‌ی چرخش و شدت پالس برای تغییرات ظاهری سپر محاسبه می‌شوند.
        # Rotation angle and pulse intensity are calculated for the shield's visual animation.
        rot = math.radians(self._rotation * 0.3)
        pulse = 0.5 + 0.5 * math.sin(self._t * 3.0)

        # ---- شش‌ضلعی بیرونی ----
        # مختصات شش رأس با استفاده از زاویه‌های مساوی روی محیط دایره محاسبه می‌شوند.
        # The six vertex coordinates are calculated using equally spaced angles around a circle.
        outer = []
        for i in range(6):
            a = rot + i * math.tau / 6 - math.pi / 2
            outer.append((
                cx + math.cos(a) * r,
                cy + math.sin(a) * r,
            ))

        # سایه‌ی شش‌ضلعی
        # انتقال رأس‌ها به پایین، سایه‌ی جابه‌جاشده‌ی سپر را ایجاد می‌کند.
        # Shifting the vertices downward creates an offset shadow of the shield.
        shadow = [(p[0], p[1] + 2) for p in outer]
        pygame.draw.polygon(surface, s.secondary, shadow)

        # بدنه‌ی شش‌ضلعی
        pygame.draw.polygon(surface, s.primary, outer)
        pygame.draw.polygon(surface, s.accent, outer, 2)

        # ---- شش‌ضلعی داخلی ----
        # شش‌ضلعی کوچک‌تر با همان زاویه‌ها ساخته می‌شود تا لایه‌ی داخلی زره شکل بگیرد.
        # A smaller hexagon is generated using the same angles to form the inner armor layer.
        inner = []
        for i in range(6):
            a = rot + i * math.tau / 6 - math.pi / 2
            inner.append((
                cx + math.cos(a) * r * 0.62,
                cy + math.sin(a) * r * 0.62,
            ))
        pygame.draw.polygon(surface, s.secondary, inner)
        pygame.draw.polygon(surface, s.accent, inner, 1)

        # ---- خطوط شبکه (به رأس‌ها) ----
        # هر رأس داخلی به رأس متناظر بیرونی متصل می‌شود تا ساختار شبکه‌ای ایجاد شود.
        # Each inner vertex is connected to its corresponding outer vertex to create a mesh structure.
        for i in range(6):
            a = rot + i * math.tau / 6 - math.pi / 2
            x1 = cx + math.cos(a) * r * 0.62
            y1 = cy + math.sin(a) * r * 0.62
            x2 = cx + math.cos(a) * r
            y2 = cy + math.sin(a) * r
            pygame.draw.line(surface, s.accent,
                             (int(x1), int(y1)), (int(x2), int(y2)), 1)

        # ---- هسته‌ی درخشان وسط ----
        # اندازه‌ی هسته با شدت پالس تغییر می‌کند تا مرکز سپر حالت زنده داشته باشد.
        # The core size varies with pulse intensity to give the shield's center a dynamic appearance.
        core_r = max(2, int(r * 0.22 * (0.85 + 0.15 * pulse)))
        pygame.draw.circle(surface, s.accent, (cx, cy), core_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(1, core_r - 1))

    # ── BOMB: مین دندانه‌دار ──
    def _icon_bomb(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
        s = self.style
        # پالس سینوسی برای تغییر شدت هسته‌ی مرکزی مین استفاده می‌شود.
        # A sinusoidal pulse is used to vary the intensity of the mine's central core.
        pulse = 0.5 + 0.5 * math.sin(self._t * 8.0)

        # ---- خارهای بیرونی (۸ تا) ----
        # هشت خار با فاصله‌ی زاویه‌ای مساوی پیرامون بدنه قرار می‌گیرند.
        # Eight spikes are positioned around the body at equal angular intervals.
        num_spikes = 8
        spike_len = r * 0.35
        spike_base = r * 0.85
        for i in range(num_spikes):
            a = (i / num_spikes) * math.tau + math.radians(self._rotation * 0.5)
            x1 = cx + math.cos(a) * spike_base
            y1 = cy + math.sin(a) * spike_base
            x2 = cx + math.cos(a) * (spike_base + spike_len)
            y2 = cy + math.sin(a) * (spike_base + spike_len)
            pygame.draw.line(
                surface, s.primary,
                (int(x1), int(y1)), (int(x2), int(y2)), 3,
            )
            # نوک درخشان
            pygame.draw.circle(surface, s.accent, (int(x2), int(y2)), 2)

        # ---- بدنه‌ی دایره‌ای ----
        # شعاع بدنه با شعاع پایه‌ی خارها هماهنگ است.
        # The body radius is aligned with the base radius of the spikes.
        body_r = int(spike_base)
        # سایه
        pygame.draw.circle(surface, s.secondary, (cx, cy + 2), body_r)
        # بدنه
        pygame.draw.circle(surface, s.primary, (cx, cy), body_r)
        # حلقه‌ی روشن
        # دو حلقه با رنگ‌های متفاوت، لایه‌های بدنه‌ی مین را از هم تفکیک می‌کنند.
        # Two rings with different colors visually separate the mine's body layers.
        pygame.draw.circle(surface, s.accent, (cx, cy), body_r, 2)
        pygame.draw.circle(surface, s.secondary, (cx, cy), int(body_r * 0.7), 2)

        # ---- هسته‌ی چشمک‌زن (چشم مین) ----
        # اندازه و شدت نور هسته با مقدار پالس تغییر می‌کند.
        # The core size and light intensity vary according to the pulse value.
        core_r = max(2, int(r * 0.28 * (0.7 + 0.3 * pulse)))
        # درخشش مرکزی
        # دایره‌های هم‌مرکز با آلفای متغیر، گرادیان نور هسته را می‌سازند.
        # Concentric circles with varying alpha create the core's glow gradient.
        for rr in range(core_r + 4, 0, -1):
            a = int(120 * (1 - rr / (core_r + 4)) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(surface, (*s.accent, a), (cx, cy), rr)
        pygame.draw.circle(surface, s.accent, (cx, cy), core_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(1, core_r - 1))

    # ── RAPID_FIRE: صاعقه ──
    def _icon_rapid_fire(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
        s = self.style
        # پالس برای تغییر جزئیات درخشش صاعقه در طول زمان استفاده می‌شود.
        # The pulse is used to animate subtle changes in the lightning bolt's glow.
        pulse = 0.5 + 0.5 * math.sin(self._t * 9.0)

        # ---- خطوط سرعت کناری ----
        # خطوط در دو طرف صاعقه و در سه موقعیت عمودی رسم می‌شوند.
        # Speed lines are drawn on both sides of the bolt at three vertical positions.
        for sign in (-1, 1):
            for i in range(3):
                ly = cy - int(r * 0.4) + i * int(r * 0.4)
                lx1 = cx + sign * int(r * 0.7)
                lx2 = cx + sign * int(r * 1.0)
                # شفافیت خطوط با موقعیت آن‌ها تغییر می‌کند.
                # Line opacity varies according to each line's position.
                line_a = int(alpha * (0.4 + 0.6 * (1 - i / 3)))
                pygame.draw.line(
                    surface, (*s.primary, line_a),
                    (lx1, ly), (lx2, ly), 2,
                )

        # ---- بدنه‌ی صاعقه (zigzag) ----
        # نقاط چندضلعی، مسیر شکسته و زاویه‌دار صاعقه را تعریف می‌کنند.
        # Polygon vertices define the lightning bolt's angular zigzag shape.
        bolt = [
            (cx + int(r * 0.15), cy - int(r * 0.95)),
            (cx - int(r * 0.45), cy - int(r * 0.10)),
            (cx + int(r * 0.05), cy - int(r * 0.10)),
            (cx - int(r * 0.15), cy + int(r * 0.95)),
            (cx + int(r * 0.50), cy - int(r * 0.05)),
            (cx + int(r * 0.00), cy - int(r * 0.05)),
        ]

        # سایه‌ی صاعقه
        # انتقال نقاط به پایین، سایه‌ای با شکل مشابه بدنه ایجاد می‌کند.
        # Shifting the vertices downward creates a shadow matching the bolt's shape.
        shadow = [(p[0], p[1] + 2) for p in bolt]
        pygame.draw.polygon(surface, s.secondary, shadow)

        # بدنه
        pygame.draw.polygon(surface, s.primary, bolt)
        pygame.draw.polygon(surface, s.accent, bolt, 2)

        # ---- درخشش روی بدنه (وسط) ----
        # در نیمه‌ی روشن‌تر چرخه‌ی پالس، یک سطح سفید داخلی روی صاعقه رسم می‌شود.
        # During the brighter half of the pulse cycle, a white inner highlight is drawn on the bolt.
        if pulse > 0.5:
            inner_bolt = [
                (cx + int(r * 0.08), cy - int(r * 0.55)),
                (cx - int(r * 0.15), cy - int(r * 0.05)),
                (cx + int(r * 0.08), cy - int(r * 0.05)),
                (cx + int(r * 0.00), cy + int(r * 0.35)),
            ]
            pygame.draw.polygon(surface, (255, 255, 255), inner_bolt)

        # ---- جرقه‌های اطراف ----
        # جرقه‌ها با زاویه و فاصله‌ی تصادفی در اطراف صاعقه ظاهر می‌شوند.
        # Sparks appear around the bolt at randomized angles and distances.
        for _ in range(3):
            spark_a = (self._t * 5.0 + random.uniform(0, 6.28)) % math.tau
            spark_r = r * (0.9 + random.uniform(0, 0.15))
            sx = cx + math.cos(spark_a) * spark_r
            sy = cy + math.sin(spark_a) * spark_r
            spark_size = random.randint(1, 2)
            pygame.draw.circle(
                surface, s.accent,
                (int(sx), int(sy)), spark_size,
            )


    @staticmethod
    def _ease_out_back(t: float) -> float:
        """easing با overshoot — پاورآپ با «پاپ» ظاهر می‌شود."""
        # پس از تکمیل انیمیشن، مقدار نهایی دقیقاً یک برگردانده می‌شود.
        # Once the animation completes, the exact final value of one is returned.
        if t >= 1.0:
            return 1.0
        # ضرایب منحنی، میزان و شکل فراتررفتن موقت از مقدار نهایی را کنترل می‌کنند.
        # The curve coefficients control the amount and shape of the temporary overshoot.
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2

    @property
    def magnet_active(self) -> bool:
        # وضعیت فعال‌بودن جذب مغناطیسی برای دسترسی سایر بخش‌های بازی ارائه می‌شود.
        # Exposes the magnetic attraction state for access by other parts of the game.
        return self._magnet_active


__all__ = ["Powerup", "PowerupKind"]