"""
entities/player/vanguard.py
===========================

سفینه‌ی VANGUARD — پیشتاز سنگین و مقاوم.

سبک بازی:
    • بیشترین HP (۵)
    • کندترین سفینه
    • شلیک دوگانه‌ی همزمان (دو گلوله‌ی موازی)
    • مناسب بازیکن‌هایی که می‌خوان با قدرت پیش برن

ظاهر:
    بدنه‌ی پهن و ضخیم با زره چندلایه،
    دو توپ شلیک در دو طرف،
    کابین شیشه‌ای پهن،
    رنگ سبز-طلایی نظامی.
"""

from __future__ import annotations

import math

import pygame

from core import settings as S
from entities.bullet import BulletKind
from entities.player.base import Player


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس Vanguard
# ═══════════════════════════════════════════════════════════════════════════

class Vanguard(Player):
    """پیشتاز سنگین — کند، مقاوم، پر قدرت."""

    # ---- شناسه ----
    NAME        = "VANGUARD"
    DESCRIPTION = "Heavy armor, slow pace. Stand your ground."
    KIND_KEY    = "vanguard"

    # ---- آمار (سنگین و مقاوم) ----
    MAX_HP:        int   = 6           # بیشترین جان
    SPEED:         float = 260.0       # کند
    RADIUS:        float = 24.0        # بزرگ‌تر
    INVULN_TIME:   float = 1.4         # کمی کمتر (چون جان زیاد داره)
    SHOOT_CD:      float = 0.15        # کندتر شلیک
    BULLET_SPEED:  float = 680.0
    BULLET_DAMAGE: int   = 1
    BULLET_KIND:   BulletKind = BulletKind.PLAYER

    # فیزیک سنگین (شتاب کم، میرایی زیاد — حس وزن)
    ACCEL: float = 6.0
    DRAG:  float = 6.5

    # ---- رنگ‌ها ----
    PRIMARY_COLOR:   tuple[int, int, int] = (80, 200, 120)     # سبز نظامی
    SECONDARY_COLOR: tuple[int, int, int] = (30, 90, 60)
    ACCENT_COLOR:    tuple[int, int, int] = (255, 200, 60)     # طلایی
    HIGHLIGHT_COLOR: tuple[int, int, int] = (220, 255, 230)
    FLAME_COLOR:     tuple[int, int, int] = (255, 180, 60)

    # ─────────────────────────────────────────────────────────────────────
    #  الگوی شلیک: دو گلوله‌ی موازی
    # ─────────────────────────────────────────────────────────────────────

    def _get_shot_angles(self) -> list[float]:
        """
        دو گلوله‌ی موازی از دو پاد کناری.
        زاویه‌ها نسبت به محور افقی محاسبه می‌شن ولی ما موقعیت افقی
        رو جدا مدیریت می‌کنیم (به همین خاطر هم‌زاویه‌ان).
        """
        if self.powerup_time > 0.0:
            # شلیک پنج‌گانه (Power-Up)
            return [-108.0, -99.0, -90.0, -81.0, -72.0]
        return [-90.0, -90.0]  # دو گلوله‌ی موازی

    def try_shoot(self):
        """
        Override برای اضافه کردن offset افقی به دو گلوله.
        گلوله‌ی اول از پاد چپ، گلوله‌ی دوم از پاد راست.
        """
        from entities.bullet import Bullet
        import math

        if self.shoot_cd > 0.0 or not self.alive:
            return []

        self.shoot_cd = self.SHOOT_CD
        self.muzzle_flash = 1.0
        self.recoil = 0.7

        bullets = []
        r = self.radius

        # ---- Power-Up: پنج‌گانه ----
        if self.powerup_time > 0.0:
            angles = [-108.0, -99.0, -90.0, -81.0, -72.0]
            for angle_deg in angles:
                a = math.radians(angle_deg)
                vx = math.cos(a) * self.BULLET_SPEED
                vy = math.sin(a) * self.BULLET_SPEED
                ox = math.cos(a) * (r + 6)
                oy = math.sin(a) * (r + 6)
                bullets.append(Bullet(
                    self.x + ox, self.y + oy,
                    vx, vy,
                    friendly=True,
                    kind=self.BULLET_KIND,
                    damage=self.BULLET_DAMAGE,
                    scene=self.scene,
                ))
        else:
            # ---- دو گلوله از پادهای کناری ----
            pod_offsets = [-r * 0.65, r * 0.65]
            for pod_x_offset in pod_offsets:
                bullets.append(Bullet(
                    self.x + pod_x_offset,
                    self.y - (r + 4),
                    0.0, -self.BULLET_SPEED,
                    friendly=True,
                    kind=self.BULLET_KIND,
                    damage=self.BULLET_DAMAGE,
                    scene=self.scene,
                ))

        if self.scene is not None:
            try:
                self.scene.audio.play("player_shoot")
            except Exception:
                pass

        return bullets

    # ─────────────────────────────────────────────────────────────────────
    #  موتورها: سه‌گانه پهن (حس سنگینی)
    # ─────────────────────────────────────────────────────────────────────

    def get_engine_offsets(self) -> list[tuple[float, float, float]]:
        return [
            (-0.55, 0.95, 0.75),
            ( 0.00, 1.05, 1.00),
            ( 0.55, 0.95, 0.75),
        ]

    # ─────────────────────────────────────────────────────────────────────
    #  رسم بدنه — پیشتاز سنگین
    # ─────────────────────────────────────────────────────────────────────

    def draw_ship(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = int(self.radius)
        primary = self.PRIMARY_COLOR
        secondary = self.SECONDARY_COLOR
        highlight = self.HIGHLIGHT_COLOR
        accent = self.ACCENT_COLOR

        # ---- ۱. سایه‌ی زیر (عمق) ----
        shadow_pts = [
            (cx - int(r * 0.85), cy - int(r * 0.80) + 2),
            (cx - int(r * 1.05), cy + int(r * 0.75) + 2),
            (cx + int(r * 1.05), cy + int(r * 0.75) + 2),
            (cx + int(r * 0.85), cy - int(r * 0.80) + 2),
        ]
        pygame.draw.polygon(surface, (10, 40, 20), shadow_pts)

        # ---- ۲. بال‌های پهن و ضخیم ----
        # بال چپ — با یک پله برای حس زره
        left_wing = [
            (cx - int(r * 0.50), cy - int(r * 0.70)),   # بالا-داخلی
            (cx - int(r * 1.05), cy - int(r * 0.50)),   # پله‌ی بالا
            (cx - int(r * 1.15), cy + int(r * 0.30)),   # نوک چپ
            (cx - int(r * 0.95), cy + int(r * 0.70)),   # پایین-چپ
            (cx - int(r * 0.40), cy + int(r * 0.55)),   # پایین-داخلی
        ]
        right_wing = [(cx + (cx - x), y) for (x, y) in left_wing]

        pygame.draw.polygon(surface, secondary, left_wing)
        pygame.draw.polygon(surface, secondary, right_wing)
        pygame.draw.polygon(surface, primary, left_wing, 2)
        pygame.draw.polygon(surface, primary, right_wing, 2)

        # ---- ۳. نوارهای زره روی بال‌ها ----
        for sign in (-1, 1):
            # خط طولی روی بال
            pygame.draw.line(
                surface, highlight,
                (cx + sign * int(r * 0.70), cy - int(r * 0.40)),
                (cx + sign * int(r * 0.90), cy + int(r * 0.55)),
                2,
            )
            # خط عرضی کوتاه
            pygame.draw.line(
                surface, accent,
                (cx + sign * int(r * 0.65), cy - int(r * 0.25)),
                (cx + sign * int(r * 0.95), cy - int(r * 0.25)),
                1,
            )

        # ---- ۴. پادهای سلاح (توپ‌ها) ----
        for sign in (-1, 1):
            pod_x = cx + sign * int(r * 0.65)
            pod_y = cy - int(r * 0.30)
            pod_w = max(4, int(r * 0.22))
            pod_h = max(6, int(r * 0.40))

            rect = pygame.Rect(
                pod_x - pod_w, pod_y - pod_h // 2,
                pod_w * 2, pod_h,
            )
            pygame.draw.rect(surface, secondary, rect)
            pygame.draw.rect(surface, highlight, rect, 2)

            # نوک درخشان (لوله)
            tip_y = pod_y - pod_h // 2 - 3
            pygame.draw.circle(surface, accent, (pod_x, tip_y), max(2, int(r * 0.10)))
            pygame.draw.circle(surface, (255, 255, 220), (pod_x, tip_y), max(1, int(r * 0.05)))

        # ---- ۵. بدنه‌ی اصلی — ذوزنقه‌ی پهن ----
        hull = [
            (cx,                  cy - int(r * 0.90)),   # بالا
            (cx - int(r * 0.55),  cy - int(r * 0.70)),   # چپ بالا
            (cx - int(r * 0.60),  cy + int(r * 0.65)),   # چپ پایین
            (cx,                  cy + int(r * 0.90)),   # دنباله‌ی وسط
            (cx + int(r * 0.60),  cy + int(r * 0.65)),
            (cx + int(r * 0.55),  cy - int(r * 0.70)),
        ]
        pygame.draw.polygon(surface, primary, hull)
        pygame.draw.polygon(surface, highlight, hull, 2)

        # ---- ۶. پنل زره میانی (روشن‌تر) ----
        armor_panel = [
            (cx,                  cy - int(r * 0.80)),
            (cx - int(r * 0.35),  cy - int(r * 0.50)),
            (cx - int(r * 0.40),  cy + int(r * 0.30)),
            (cx,                  cy + int(r * 0.55)),
            (cx + int(r * 0.40),  cy + int(r * 0.30)),
            (cx + int(r * 0.35),  cy - int(r * 0.50)),
        ]
        pygame.draw.polygon(surface, (120, 230, 150), armor_panel)
        pygame.draw.polygon(surface, highlight, armor_panel, 1)

        # ---- ۷. خط عمودی میانی ----
        pygame.draw.line(
            surface, secondary,
            (cx, cy - int(r * 0.75)),
            (cx, cy + int(r * 0.85)),
            2,
        )

        # ---- ۸. کابین پهن (شیشه‌ای) ----
        cab_w = max(4, int(r * 0.32))
        cab_h = max(3, int(r * 0.18))
        cab_y = cy - int(r * 0.35)
        cab_rect = pygame.Rect(
            cx - cab_w, cab_y - cab_h,
            cab_w * 2, cab_h * 2,
        )
        pygame.draw.ellipse(surface, secondary, cab_rect)
        pygame.draw.ellipse(surface, accent, cab_rect, 2)

        inner_rect = cab_rect.inflate(-2, -2)
        pygame.draw.ellipse(surface, (200, 250, 210), inner_rect)

        # ---- ۹. خطوط زره افقی ----
        for i, y_off in enumerate([-0.20, 0.15, 0.45]):
            y = cy + int(r * y_off)
            w = int(r * (0.50 - i * 0.08))
            pygame.draw.line(
                surface, highlight,
                (cx - w, y), (cx + w, y), 1,
            )

        # ---- ۱۰. نشان نظامی (ستاره‌ی کوچک) ----
        star_y = cy + int(r * 0.15)
        size = max(3, int(r * 0.15))
        pts = []
        for i in range(5):
            a_out = -math.pi / 2 + i * 2 * math.pi / 5
            a_in = a_out + math.pi / 5
            pts.append((cx + math.cos(a_out) * size, star_y + math.sin(a_out) * size))
            pts.append((cx + math.cos(a_in) * size * 0.45, star_y + math.sin(a_in) * size * 0.45))
        pygame.draw.polygon(surface, accent, pts)

        # ---- ۱۱. چراغ‌های ناوبری (کمی متفاوت با Interceptor) ----
        blink = 0.5 + 0.5 * math.sin(self._t * 4.0)
        for sign, color in [(-1, (255, 80, 80)), (1, (80, 255, 120))]:
            tip_x = cx + sign * int(r * 1.05)
            tip_y = cy - int(r * 0.15)
            alpha = int(180 * (blink if sign < 0 else (1 - blink)))
            glow = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, alpha), (6, 6), 4)
            pygame.draw.circle(glow, (255, 255, 255, alpha), (6, 6), 2)
            surface.blit(glow, (tip_x - 6, tip_y - 6),
                         special_flags=pygame.BLEND_RGBA_ADD)


__all__ = ["Vanguard"]