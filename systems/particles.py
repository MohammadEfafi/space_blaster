"""
systems/particles.py
====================

سیستم ذرات (Particle System) برای SPACE BLASTER.

این ماژول موتور جلوه‌های بصری بازی است. تمام انفجارها، دنباله‌ها،
شعله‌ها، ترکش‌ها و افکت‌های ضربه از اینجا تولید و مدیریت می‌شوند.

ویژگی‌ها:
    • شش نوع ذره با رفتار و ظاهر متفاوت:
        SPARK, SMOKE, GLOW, DEBRIS, TRAIL, RING
    • الگوهای انتشار متنوع:
        BURST, CONE, RING, BEAM, TRAIL
    • Object Pooling برای جلوگیری از allocate مکرر
    • فیزیک هر ذره: گرادیان جاذبه، میرایی، تلاطم (turbulence)
    • فید نرم رنگ و شفافیت بر اساس عمر
    • حالت‌های ترکیبی: BLEND_RGBA_ADD و BLEND_NORMAL
    • پریست‌های آماده برای سناریوهای رایج (انفجار دشمن، ترکش، …)
    • بهینه برای صدها ذره‌ی همزمان روی صفحه

طراحی:
    ParticleSystem یک ظرف است که لیستی از ذرات را نگه می‌دارد.
    هر ذره یک ساختار ساده است (بدون پیچیدگی OOP اضافی) تا کارایی
    حداکثری حفظ شود. سطح API تمیز و صریح است.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Iterable, Optional

import pygame

from core import settings as S



class ParticleKind(Enum):
    """دسته‌بندی ذرات برای رفتار بصری متفاوت."""
    SPARK  = auto()   # جرقه‌ی کوچک و درخشان — خط‌دار، سریع
    SMOKE  = auto()   # دود — بزرگ، نرم، کند، بلند-عمر
    GLOW   = auto()   # هاله‌ی درخشان — بدون حرکت زیاد، کم‌عمر
    DEBRIS = auto()   # ترکش — چندضلعی کوچک، چرخان
    TRAIL  = auto()   # دنباله — بدون حرکت، فقط محو می‌شود
    RING   = auto()   # حلقه‌ی گسترده‌شونده



@dataclass
class Particle:
    """
    یک ذره‌ی منفرد. تا حد امکان سبک و flat نگه داشته می‌شود.

    فیلدها:
        x, y          — موقعیت
        vx, vy        — سرعت
        life, max_life— عمر باقی‌مانده و عمر اولیه (برای نرمال‌سازی)
        size          — شعاع/اندازه‌ی اولیه
        end_size      — اندازه‌ی نهایی (برای تغییر اندازه در طول عمر)
        color_start   — رنگ ابتدایی (RGB)
        color_end     — رنگ پایانی
        alpha_start   — شفافیت ابتدایی
        kind          — نوع ذره
        gravity       — شتاب جاذبه‌ی عمودی
        drag          — ضریب میرایی سرعت (نزدیک به ۱ = بدون میرایی)
        turbulence    — شدت تلاطم (نویز سینوسی)
        angle         — زاویه‌ی چرخش (برای DEBRIS)
        angle_speed   — سرعت چرخش
        additive      — اگر True، با BLEND_RGBA_ADD رسم می‌شود
    """

    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    end_size: float
    color_start: tuple[int, int, int]
    color_end: tuple[int, int, int]
    alpha_start: int = 255
    alpha_end: int = 0
    kind: ParticleKind = ParticleKind.SPARK
    gravity: float = 0.0
    drag: float = 0.94
    turbulence: float = 0.0
    angle: float = 0.0
    angle_speed: float = 0.0
    additive: bool = True
    # فیلد پویا
    _turb_phase: float = field(default_factory=lambda: random.uniform(0, math.tau))


    # سن ذره از اختلاف عمر اولیه و عمر باقی‌مانده به دست می‌آید.
    # Particle age is calculated from its initial and remaining lifetime.
    @property
    def age(self) -> float:
        return self.max_life - self.life

    # این نسبت برای محاسبه‌ی تدریجی رنگ، شفافیت و اندازه در طول عمر استفاده می‌شود.
    # This normalized value drives gradual color, opacity, and size changes over the particle's lifetime.
    @property
    def t(self) -> float:
        """نسبت عمر گذشته به عمر کل: 0 → 1."""
        if self.max_life <= 0:
            return 1.0
        return max(0.0, min(1.0, self.age / self.max_life))

    @property
    def alive(self) -> bool:
        return self.life > 0.0


class ParticleSystem:
    """
    مدیر و به‌روزرسان ذرات.

    استفاده:
        ps = ParticleSystem()
        ps.emit_burst(x, y, count=20, color=(255, 100, 40))
        ps.update(dt)
        ps.draw(surface)
    """

    def __init__(self, max_particles: int = 2000) -> None:
        self.particles: list[Particle] = []
        self.max_particles: int = max_particles

        # برآورد سریع در زمان draw
        self._additive_batch: list[Particle] = []
        self._normal_batch: list[Particle] = []


    def __len__(self) -> int:
        return len(self.particles)

    def clear(self) -> None:
        self.particles.clear()


    # در صورت عبور از سقف ظرفیت، قدیمی‌ترین ذرات از ابتدای لیست حذف می‌شوند.
    # When capacity is exceeded, the oldest particles are removed from the beginning of the list.
    def _prune_if_needed(self) -> None:
        """
        اگر تعداد ذرات از سقف گذشت، قدیمی‌ترین‌ها را حذف می‌کنیم.
        جلوگیری از افت ناگهانی فریم در انفجارهای بزرگ.
        """
        overflow = len(self.particles) - self.max_particles
        if overflow > 0:
            # حذف از ابتدای لیست (قدیمی‌ترها)
            del self.particles[:overflow]


    def add(self, p: Particle) -> None:
        self.particles.append(p)


    # به‌روزرسانی با dt انجام می‌شود تا حرکت و عمر ذرات مستقل از نرخ فریم باشد.
    # Updating with dt keeps particle motion and lifetime independent of the frame rate.
    def update(self, dt: float) -> None:
        """
        به‌روزرسانی همه‌ی ذرات. ذرات مرده حذف می‌شوند.
        از «swap-and-pop» استفاده می‌کنیم برای O(n) و بدون allocate.
        """
        particles = self.particles
        i = 0
        n = len(particles)
        while i < n:
            p = particles[i]
            p.life -= dt
            # عنصر انتهایی جای ذره‌ی مرده را می‌گیرد؛ ترتیب لیست حفظ نمی‌شود، اما حذف در زمان ثابت انجام می‌شود.
            # The last element replaces the dead particle; list order is not preserved, but removal is constant-time.
            if p.life <= 0.0:
                # swap with last و کاهش n
                n -= 1
                particles[i] = particles[n]
                particles.pop()
                continue

            # ---- فیزیک ----
            # جاذبه فقط مؤلفه‌ی عمودی سرعت را در هر گام زمانی تغییر می‌دهد.
            # Gravity updates only the vertical velocity component on each time step.
            p.vy += p.gravity * dt

            # فاز سینوسی به‌صورت پیوسته جلو می‌رود تا تلاطم حرکت نرم و متغیر ایجاد کند.
            # The sinusoidal phase advances continuously to produce smooth, varying turbulence.
            if p.turbulence > 0.0:
                # نویز سینوسی با فرکانس تصادفی
                p._turb_phase += dt * 6.0
                p.vx += math.sin(p._turb_phase) * p.turbulence * dt
                p.vy += math.cos(p._turb_phase * 1.37) * p.turbulence * dt

            # میرایی
            # توان‌دهی ضریب drag اثر میرایی را با طول گام زمانی سازگار می‌کند.
            # Exponentiating the drag coefficient makes damping consistent across time-step lengths.
            drag_factor = p.drag ** (dt * 60.0)
            p.vx *= drag_factor
            p.vy *= drag_factor

            p.x += p.vx * dt
            p.y += p.vy * dt

            if p.angle_speed != 0.0:
                p.angle += p.angle_speed * dt

            i += 1


    def draw(self, surface: pygame.Surface) -> None:
        """
        رسم همه‌ی ذرات. ذرات additive در یک پاس، ذرات عادی در پاس دیگر.
        """
        self._additive_batch.clear()
        self._normal_batch.clear()

        # ذرات بر اساس نوع ترکیب رنگ در دو دسته جدا می‌شوند تا هر دسته با تنظیمات مناسب رسم شود.
        # Particles are separated by blend mode so each batch can be rendered with the appropriate settings.
        for p in self.particles:
            if p.additive:
                self._additive_batch.append(p)
            else:
                self._normal_batch.append(p)

        # پاس additive
        if self._additive_batch:
            self._draw_batch(surface, self._additive_batch, blend_additive=True)
        # پاس normal
        if self._normal_batch:
            self._draw_batch(surface, self._normal_batch, blend_additive=False)

    def _draw_batch(
        self,
        surface: pygame.Surface,
        batch: list[Particle],
        blend_additive: bool,
    ) -> None:
        # پرچم ترکیب رنگ فقط برای دسته‌ی additive فعال است؛ دسته‌ی عادی از ترکیب پیش‌فرض استفاده می‌کند.
        # The additive batch uses the additive blend flag, while the normal batch uses default blending.
        flags = pygame.BLEND_RGBA_ADD if blend_additive else 0

        for p in batch:
            # مقدار نرمال‌شده‌ی عمر، مبنای درون‌یابی ویژگی‌های بصری ذره است.
            # The normalized lifetime value drives interpolation of the particle's visual properties.
            t = p.t
            # رنگ و آلفا با درون‌یابی خطی
            r = int(p.color_start[0] + (p.color_end[0] - p.color_start[0]) * t)
            g = int(p.color_start[1] + (p.color_end[1] - p.color_start[1]) * t)
            b = int(p.color_start[2] + (p.color_end[2] - p.color_start[2]) * t)
            a = int(p.alpha_start + (p.alpha_end - p.alpha_start) * t)
            if a <= 0:
                continue
            size = max(0.5, p.size + (p.end_size - p.size) * t)
            cx, cy = int(p.x), int(p.y)

            if p.kind == ParticleKind.SPARK:
                self._draw_spark(surface, cx, cy, size, (r, g, b, a), flags)
            elif p.kind == ParticleKind.SMOKE:
                self._draw_smoke(surface, cx, cy, size, (r, g, b, a))
            elif p.kind == ParticleKind.GLOW:
                self._draw_glow(surface, cx, cy, size, (r, g, b, a), flags)
            elif p.kind == ParticleKind.DEBRIS:
                self._draw_debris(surface, cx, cy, size, (r, g, b, a), p.angle)
            elif p.kind == ParticleKind.TRAIL:
                self._draw_trail(surface, cx, cy, size, (r, g, b, a), flags)
            elif p.kind == ParticleKind.RING:
                self._draw_ring(surface, cx, cy, size, (r, g, b, a), flags)

    # ---- رسم انواع ----

    @staticmethod
    def _draw_spark(
        surface: pygame.Surface,
        cx: int, cy: int,
        size: float,
        color: tuple[int, int, int, int],
        flags: int,
    ) -> None:
        r = max(1, int(size))
        d = r * 2 + 2
        tmp = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(tmp, color, (r + 1, r + 1), r)
        surface.blit(tmp, (cx - r - 1, cy - r - 1), special_flags=flags)

    @staticmethod
    def _draw_smoke(
        surface: pygame.Surface,
        cx: int, cy: int,
        size: float,
        color: tuple[int, int, int, int],
    ) -> None:
        r = max(1, int(size))
        d = r * 2 + 2
        tmp = pygame.Surface((d, d), pygame.SRCALPHA)
        # حلقه‌ی نرم با آلفای کاهشی
        # رسم دایره‌های تو در تو با آلفای کمتر در مرکز، ظاهر نرم و محوشونده‌ی دود را می‌سازد.
        # Drawing nested circles with varying alpha creates the smoke's soft, fading appearance.
        for rr in range(r, 0, -1):
            a = int(color[3] * (1 - rr / r) ** 0.8)
            pygame.draw.circle(tmp, (color[0], color[1], color[2], a), (r + 1, r + 1), rr)
        surface.blit(tmp, (cx - r - 1, cy - r - 1))

    @staticmethod
    def _draw_glow(
        surface: pygame.Surface,
        cx: int, cy: int,
        size: float,
        color: tuple[int, int, int, int],
        flags: int,
    ) -> None:
        r = max(1, int(size * 2))
        d = r * 2 + 2
        tmp = pygame.Surface((d, d), pygame.SRCALPHA)
        # گام دوپیکسلی تعداد لایه‌های هاله را کاهش می‌دهد و جلوه‌ی محو را حفظ می‌کند.
        # A two-pixel step reduces the number of glow layers while retaining the soft falloff.
        for rr in range(r, 0, -2):
            a = int(color[3] * (1 - rr / r) ** 1.6)
            pygame.draw.circle(tmp, (color[0], color[1], color[2], a), (r + 1, r + 1), rr)
        surface.blit(tmp, (cx - r - 1, cy - r - 1), special_flags=flags)

    @staticmethod
    def _draw_debris(
        surface: pygame.Surface,
        cx: int, cy: int,
        size: float,
        color: tuple[int, int, int, int],
        angle: float,
    ) -> None:
        s = max(1, int(size))
        # مربع چرخان
        # مختصات چهار گوشه با ماتریس چرخش دوبعدی حول مرکز ذره محاسبه می‌شوند.
        # The four corner coordinates are transformed with a 2D rotation around the particle center.
        ang = math.radians(angle)
        cs, sn = math.cos(ang), math.sin(ang)
        pts = [
            (cx + cs * -s - sn * -s, cy + sn * -s + cs * -s),
            (cx + cs * s - sn * -s,  cy + sn * s + cs * -s),
            (cx + cs * s - sn * s,   cy + sn * s + cs * s),
            (cx + cs * -s - sn * s,  cy + sn * -s + cs * s),
        ]
        d = s * 3
        tmp = pygame.Surface((d * 2, d * 2), pygame.SRCALPHA)
        local = [(p[0] - cx + d, p[1] - cy + d) for p in pts]
        pygame.draw.polygon(tmp, color, local)
        surface.blit(tmp, (cx - d, cy - d))

    @staticmethod
    def _draw_trail(
        surface: pygame.Surface,
        cx: int, cy: int,
        size: float,
        color: tuple[int, int, int, int],
        flags: int,
    ) -> None:
        r = max(1, int(size))
        d = r * 2 + 2
        tmp = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(tmp, color, (r + 1, r + 1), r)
        surface.blit(tmp, (cx - r - 1, cy - r - 1), special_flags=flags)

    @staticmethod
    def _draw_ring(
        surface: pygame.Surface,
        cx: int, cy: int,
        size: float,
        color: tuple[int, int, int, int],
        flags: int,
    ) -> None:
        r = max(1, int(size))
        d = r * 2 + 4
        tmp = pygame.Surface((d, d), pygame.SRCALPHA)
        width = max(1, int(r * 0.18))
        pygame.draw.circle(tmp, color, (r + 2, r + 2), r, width)
        surface.blit(tmp, (cx - r - 2, cy - r - 2), special_flags=flags)


    def emit_burst(
        self,
        x: float, y: float,
        *,
        count: int = 20,
        color_start: tuple[int, int, int] = (255, 240, 160),
        color_end: tuple[int, int, int] = (255, 60, 40),
        speed_min: float = S.FxCfg.PARTICLE_MIN_SPEED,
        speed_max: float = S.FxCfg.PARTICLE_MAX_SPEED,
        life_min: float = S.FxCfg.PARTICLE_MIN_LIFE,
        life_max: float = S.FxCfg.PARTICLE_MAX_LIFE,
        size_min: float = 2.0,
        size_max: float = 4.5,
        kind: ParticleKind = ParticleKind.SPARK,
        additive: bool = True,
        gravity: float = 0.0,
        drag: float = S.FxCfg.PARTICLE_FRICTION,
        spread_deg: float = 360.0,
        angle_deg: float = 0.0,
        turbulence: float = 0.0,
    ) -> None:
        """
        انفجار دایره‌ای (یا کمانی) ذرات.
        spread_deg=360 → دایره‌ی کامل، 90 → ربع‌دایره، 30 → مخروط باریک.
        """
        # زاویه‌ها به رادیان تبدیل می‌شوند، چون توابع مثلثاتی پایتون با رادیان کار می‌کنند.
        # Angles are converted to radians because Python's trigonometric functions use radians.
        spread = math.radians(spread_deg)
        base_angle = math.radians(angle_deg)
        half = spread / 2.0

        # زاویه‌ی هر ذره به‌صورت تصادفی در بازه‌ی انتشار انتخاب می‌شود تا انفجار یکنواخت نباشد.
        # Each particle receives a random angle within the spread so the burst is not perfectly uniform.
        for _ in range(count):
            a = base_angle + random.uniform(-half, half)
            sp = random.uniform(speed_min, speed_max)
            vx = math.cos(a) * sp
            vy = math.sin(a) * sp

            life = random.uniform(life_min, life_max)
            size = random.uniform(size_min, size_max)

            self.add(Particle(
                x=x + random.uniform(-2, 2),
                y=y + random.uniform(-2, 2),
                vx=vx, vy=vy,
                life=life, max_life=life,
                size=size,
                end_size=size * random.uniform(0.2, 0.6),
                color_start=color_start,
                color_end=color_end,
                alpha_start=255,
                alpha_end=0,
                kind=kind,
                gravity=gravity,
                drag=drag,
                turbulence=turbulence,
                angle=random.uniform(0, 360),
                angle_speed=random.uniform(-360, 360),
                additive=additive,
            ))

        self._prune_if_needed()

    def emit_cone(
        self,
        x: float, y: float,
        *,
        count: int = 15,
        angle_deg: float = -90.0,   # جهت مخروط
        spread_deg: float = 30.0,
        **kwargs,
    ) -> None:
        """مخروط باریک از ذرات (برای recoil، شلیک، موتور)."""
        self.emit_burst(
            x, y,
            count=count,
            spread_deg=spread_deg,
            angle_deg=angle_deg,
            **kwargs,
        )

    def emit_ring(
        self,
        x: float, y: float,
        *,
        count: int = 30,
        radius: float = 10.0,
        speed: float = 220.0,
        color: tuple[int, int, int] = (255, 200, 100),
        life: float = 0.55,
        size: float = 3.0,
    ) -> None:
        """حلقه‌ی کامل ذرات که به بیرون منفجر می‌شوند."""
        # زاویه‌ها با تقسیم دایره به تعداد ذرات، فاصله‌ی زاویه‌ای یکسانی پیدا می‌کنند.
        # Dividing the full circle by the particle count gives each particle an equal angular interval.
        for i in range(count):
            a = (i / count) * math.tau
            vx = math.cos(a) * speed
            vy = math.sin(a) * speed
            px = x + math.cos(a) * radius
            py = y + math.sin(a) * radius
            self.add(Particle(
                x=px, y=py,
                vx=vx, vy=vy,
                life=life, max_life=life,
                size=size, end_size=size * 0.3,
                color_start=color,
                color_end=(60, 20, 20),
                alpha_start=255, alpha_end=0,
                kind=ParticleKind.SPARK,
                gravity=0.0, drag=0.90,
                angle=0, angle_speed=0,
                additive=True,
            ))
        self._prune_if_needed()

    def emit_beam(
        self,
        x: float, y: float,
        *,
        count: int = 20,
        dx: float = 0.0,
        dy: float = -1.0,
        length: float = 60.0,
        width: float = 6.0,
        color: tuple[int, int, int] = (255, 230, 160),
        life: float = 0.25,
        size: float = 3.0,
    ) -> None:
        """پرتابه‌ی خطی از ذرات در جهت مشخص."""
        # بردار جهت نرمال می‌شود؛ مقدار جایگزین از تقسیم بر صفر برای بردار صفر جلوگیری می‌کند.
        # The direction vector is normalized; the fallback prevents division by zero for a zero vector.
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        # بردار عمود، آفست عرضی ذرات را نسبت به راستای پرتو تعیین می‌کند.
        # The perpendicular vector determines each particle's lateral offset from the beam direction.
        px, py = -uy, ux   # عمود

        for _ in range(count):
            t = random.random()
            off = random.uniform(-width / 2, width / 2)
            bx = x + ux * length * t + px * off
            by = y + uy * length * t + py * off
            vx = ux * random.uniform(20, 60)
            vy = uy * random.uniform(20, 60)
            self.add(Particle(
                x=bx, y=by,
                vx=vx, vy=vy,
                life=life * random.uniform(0.7, 1.2),
                max_life=life,
                size=size * random.uniform(0.7, 1.3),
                end_size=0.5,
                color_start=color,
                color_end=(200, 60, 20),
                alpha_start=255, alpha_end=0,
                kind=ParticleKind.SPARK,
                gravity=0.0, drag=0.92,
                additive=True,
            ))
        self._prune_if_needed()

    def emit_trail(
        self,
        x: float, y: float,
        *,
        count: int = 1,
        color: tuple[int, int, int] = (120, 240, 255),
        life: float = 0.35,
        size: float = 3.0,
        jitter: float = 2.0,
        additive: bool = True,
    ) -> None:
        """دنباله‌ی متحرک (برای گلوله، موتور)."""
        for _ in range(count):
            self.add(Particle(
                x=x + random.uniform(-jitter, jitter),
                y=y + random.uniform(-jitter, jitter),
                vx=random.uniform(-20, 20),
                vy=random.uniform(-20, 20),
                life=life, max_life=life,
                size=size, end_size=size * 0.3,
                color_start=color,
                color_end=(40, 40, 80),
                alpha_start=200, alpha_end=0,
                kind=ParticleKind.TRAIL,
                gravity=0.0, drag=0.85,
                additive=additive,
            ))
        self._prune_if_needed()


    def preset_enemy_explosion(
        self,
        x: float, y: float,
        radius: float,
        color: tuple[int, int, int] = (255, 90, 90),
    ) -> None:
        """انفجار دشمن معمولی — چندلایه، با ترکش و حلقه."""
        # لایه‌ی جرقه‌ها
        self.emit_burst(
            x, y,
            count=int(18 + radius),
            color_start=(255, 255, 220),
            color_end=color,
            speed_min=80, speed_max=380,
            life_min=0.3, life_max=0.85,
            size_min=2.0, size_max=4.5,
            kind=ParticleKind.SPARK,
            turbulence=60.0,
        )
        # دود
        self.emit_burst(
            x, y,
            count=int(6 + radius * 0.3),
            color_start=(120, 40, 60),
            color_end=(20, 10, 30),
            speed_min=20, speed_max=90,
            life_min=0.6, life_max=1.4,
            size_min=5, size_max=11,
            kind=ParticleKind.SMOKE,
            additive=False,
            drag=0.90,
        )
        # ترکش
        self.emit_burst(
            x, y,
            count=int(4 + radius * 0.4),
            color_start=color,
            color_end=(60, 20, 20),
            speed_min=120, speed_max=320,
            life_min=0.5, life_max=1.0,
            size_min=2.0, size_max=3.5,
            kind=ParticleKind.DEBRIS,
            additive=False,
            gravity=180.0,
            drag=0.97,
        )
        # حلقه‌ی نهایی
        self.emit_ring(
            x, y,
            count=18,
            radius=radius * 0.5,
            speed=240,
            color=(255, 230, 200),
            life=0.35,
            size=2.5,
        )
        # هاله
        self.emit_burst(
            x, y,
            count=1,
            color_start=(255, 240, 200),
            color_end=(255, 80, 40),
            speed_min=0, speed_max=0,
            life_min=0.35, life_max=0.35,
            size_min=radius * 1.6, size_max=radius * 1.6,
            kind=ParticleKind.GLOW,
        )

    def preset_player_explosion(self, x: float, y: float) -> None:
        """انفجار بزرگ سفینه‌ی پلیر."""
        self.emit_burst(
            x, y,
            count=48,
            color_start=(200, 240, 255),
            color_end=(60, 120, 255),
            speed_min=120, speed_max=520,
            life_min=0.5, life_max=1.2,
            size_min=3, size_max=6,
            kind=ParticleKind.SPARK,
            turbulence=80.0,
        )
        self.emit_ring(x, y, count=30, radius=8, speed=340, color=(120, 220, 255), life=0.55, size=3)
        self.emit_burst(
            x, y,
            count=12,
            color_start=(150, 200, 255),
            color_end=(20, 20, 60),
            speed_min=40, speed_max=140,
            life_min=0.8, life_max=1.6,
            size_min=8, size_max=14,
            kind=ParticleKind.SMOKE,
            additive=False,
            drag=0.92,
        )
        self.emit_burst(
            x, y,
            count=8,
            color_start=(255, 255, 255),
            color_end=(60, 120, 255),
            speed_min=80, speed_max=260,
            life_min=0.7, life_max=1.1,
            size_min=2, size_max=4,
            kind=ParticleKind.DEBRIS,
            additive=False,
            gravity=200.0,
            drag=0.97,
        )

    def preset_bullet_impact(
        self,
        x: float, y: float,
        color: tuple[int, int, int],
        *,
        is_friendly: bool = True,
    ) -> None:
        """برخورد گلوله — کوچک و سریع."""
        self.emit_burst(
            x, y,
            count=8,
            color_start=(255, 255, 255),
            color_end=color,
            speed_min=40, speed_max=180,
            life_min=0.12, life_max=0.35,
            size_min=1.5, size_max=3.0,
            kind=ParticleKind.SPARK,
            turbulence=30.0,
        )
        # هاله‌ی کوچک
        self.emit_burst(
            x, y,
            count=1,
            color_start=(255, 255, 255),
            color_end=color,
            speed_min=0, speed_max=0,
            life_min=0.15, life_max=0.15,
            size_min=6, size_max=6,
            kind=ParticleKind.GLOW,
        )

    def preset_thruster(self, x: float, y: float, vx: float, vy: float) -> None:
        """ذره‌ی موتور پلیر — کوچک، آبی-سفید."""
        self.add(Particle(
            x=x, y=y,
            vx=vx + random.uniform(-20, 20),
            vy=vy + random.uniform(-10, 20),
            life=0.35, max_life=0.35,
            size=2.5, end_size=0.4,
            color_start=(255, 230, 180),
            color_end=(255, 80, 40),
            alpha_start=220, alpha_end=0,
            kind=ParticleKind.SPARK,
            drag=0.88,
            additive=True,
        ))

    def preset_powerup_burst(
        self,
        x: float, y: float,
        color: tuple[int, int, int],
    ) -> None:
        """انفجار برداشتن پاورآپ — درخشان و شاد."""
        self.emit_ring(x, y, count=22, radius=6, speed=280, color=color, life=0.4, size=3)
        self.emit_burst(
            x, y,
            count=18,
            color_start=(255, 255, 255),
            color_end=color,
            speed_min=60, speed_max=260,
            life_min=0.25, life_max=0.7,
            size_min=2, size_max=4,
            kind=ParticleKind.SPARK,
        )
        self.emit_burst(
            x, y,
            count=1,
            color_start=(255, 255, 255),
            color_end=color,
            speed_min=0, speed_max=0,
            life_min=0.28, life_max=0.28,
            size_min=24, size_max=24,
            kind=ParticleKind.GLOW,
        )

    def preset_boss_explosion(self, x: float, y: float) -> None:
        """انفجار بزرگ باس — سینمایی."""
        # موج‌های متعدد حلقه‌ای
        # چند حلقه با شعاع و سرعت افزایشی، حس گسترش موج‌های انفجار باس را ایجاد می‌کنند.
        # Multiple rings with increasing radius and speed create the expanding shockwave effect of a boss explosion.
        for i, delay in enumerate((0, 0.08, 0.16, 0.24)):
            self.emit_ring(
                x, y,
                count=40,
                radius=10 + i * 12,
                speed=300 + i * 80,
                color=(255, 200 - i * 30, 100 - i * 15),
                life=0.7,
                size=3.5,
            )
        # جرقه‌های فراوان
        self.emit_burst(
            x, y,
            count=90,
            color_start=(255, 255, 220),
            color_end=(255, 60, 60),
            speed_min=100, speed_max=620,
            life_min=0.6, life_max=1.6,
            size_min=2, size_max=6,
            kind=ParticleKind.SPARK,
            turbulence=120.0,
        )
        # ترکش
        self.emit_burst(
            x, y,
            count=24,
            color_start=(255, 100, 60),
            color_end=(40, 10, 10),
            speed_min=140, speed_max=440,
            life_min=0.9, life_max=1.8,
            size_min=3, size_max=6,
            kind=ParticleKind.DEBRIS,
            additive=False,
            gravity=240.0,
            drag=0.97,
        )
        # هاله‌ی سفید اولیه
        self.emit_burst(
            x, y,
            count=1,
            color_start=(255, 255, 255),
            color_end=(255, 100, 40),
            speed_min=0, speed_max=0,
            life_min=0.55, life_max=0.55,
            size_min=70, size_max=70,
            kind=ParticleKind.GLOW,
        )


__all__ = ["Particle", "ParticleKind", "ParticleSystem"]