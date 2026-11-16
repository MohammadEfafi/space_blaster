"""
scenes/leaderboard.py
=====================

صفحه‌ی جدول امتیازات (Hall of Fame) برای SPACE BLASTER.
"""

from __future__ import annotations

import math
import random
from typing import Callable

import pygame

from core import settings as S
from scenes.base import Scene


# ابعاد صفحه و موقعیت اجزای رابط کاربری بر اساس اندازه پنجره محاسبه می‌شوند.
# Screen dimensions and UI element positions are calculated relative to the window size.
W = S.Window.WIDTH
H = S.Window.HEIGHT

# مختصات عمودی عنوان، زیرعنوان و خط جداکننده برای حفظ چیدمان متناسب با صفحه.
# Vertical coordinates for the title, subtitle, and divider maintain a proportional layout.
TITLE_Y      = int(H * 0.08)
SUBTITLE_Y   = int(H * 0.155)
DIVIDER_Y    = int(H * 0.185)

# ابعاد و موقعیت سکوهای سه رتبه برتر.
# Dimensions and positioning of the podiums for the top three ranks.
PODIUM_CY    = int(H * 0.46)
PODIUM_W     = int(W * 0.18)
PODIUM_H_1   = int(H * 0.22)
PODIUM_H_2   = int(H * 0.17)
PODIUM_H_3   = int(H * 0.14)
PODIUM_GAP   = 20

# محدوده جدول رتبه‌های بعدی و ارتفاع هر ردیف.
# Layout boundaries and row height for the remaining leaderboard entries.
TABLE_X      = int(W * 0.18)
TABLE_TOP    = int(H * 0.72)
ROW_H        = int(H * 0.055)
TABLE_W      = int(W * 0.64)

# موقعیت دکمه بازگشت و راهنمای پایین صفحه.
# Positions of the back button and the bottom-screen hint.
BTN_Y        = int(H * 0.94)
HINT_Y       = H - 12


# رنگ و عنوان اختصاصی هر یک از سه رتبه نخست.
# Dedicated colors and labels for each of the top three ranks.
RANK_COLORS: dict[int, tuple[int, int, int]] = {
    1: (255, 220, 80),
    2: (230, 240, 255),
    3: (240, 160, 90),
}
RANK_LABELS: dict[int, str] = {
    1: "GOLD",
    2: "SILVER",
    3: "BRONZE",
}
DEFAULT_COLOR = (140, 165, 200)


class _BackButton:
    def __init__(self, on_click: Callable[[], None], cx: int, cy: int) -> None:
        self.on_click = on_click
        self.rect = pygame.Rect(0, 0, 240, 46)
        self.rect.center = (cx, cy)
        self.hovered = False
        self._t = 0.0
        self._hover = 0.0

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        self._t += dt
        self.hovered = self.rect.collidepoint(mouse_pos)

        # مقدار انیمیشن به‌صورت تدریجی به وضعیت هاور نزدیک می‌شود تا تغییر ناگهانی نباشد.
        # The animation value gradually approaches the hover state to avoid abrupt transitions.
        target = 1.0 if self.hovered else 0.0
        self._hover += (target - self._hover) * min(1.0, dt * 12.0)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()
                return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        # با افزایش هاور، محدوده دکمه کمی بزرگ‌تر می‌شود.
        # The button's bounds expand slightly as the hover intensity increases.
        pad = int(6 * self._hover)
        rect = self.rect.inflate(pad * 2, pad)
        accent = (120, 200, 255)

        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (*accent, int(50 + 100 * self._hover)),
                         bg.get_rect(), border_radius=8)
        surface.blit(bg, rect.topleft)
        pygame.draw.rect(surface, accent, rect, 2, border_radius=8)

        # لایه درخشش فقط هنگام نزدیک شدن نشانگر به دکمه نمایش داده می‌شود.
        # The glow layer appears only when the pointer is hovering over the button.
        if self._hover > 0.05:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (*accent, int(80 * self._hover)),
                             glow.get_rect(), 0, border_radius=8)
            surface.blit(glow, rect.topleft)

        text_color = S.Palette.WHITE if self.hovered else S.Palette.HUD_TEXT
        img = font.render("BACK TO MENU", True, text_color)
        tr = img.get_rect(center=rect.center)
        shadow = font.render("BACK TO MENU", True, (0, 0, 0))
        surface.blit(shadow, (tr.x + 2, tr.y + 2))
        surface.blit(img, tr)


class LeaderboardScene(Scene):

    # زمان‌بندی ورود تدریجی ردیف‌ها و سکوهای رتبه‌بندی.
    # Timing values for the staggered entrance of leaderboard rows and podiums.
    ROW_STAGGER    = 0.06
    ROW_FADE_TIME  = 0.32
    PODIUM_STAGGER = 0.10

    def on_enter(self) -> None:
        # فونت‌های موردنیاز بخش‌های مختلف جدول امتیازات.
        # Fonts used by the different sections of the leaderboard.
        self.font_title   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.BIG, bold=True)
        self.font_sub     = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.NORMAL, bold=True)
        self.font_rank    = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.HUGE, bold=True)
        self.font_score   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.LARGE, bold=True)
        self.font_label   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)
        self.font_row     = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.LARGE, bold=True)
        self.font_row_sm  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.NORMAL, bold=True)
        self.font_hint    = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)
        self.font_empty   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.LARGE, bold=True)

        # داده‌های جدول از مخزن امتیازات دریافت و به دو گروه تقسیم می‌شوند.
        # Leaderboard data is retrieved from the score store and divided into two groups.
        self.store = self.game.scores
        self.top3 = self.store.scores[:3]
        self.rest = self.store.scores[3:10]
        self.total_games = self.store.total_games

        # ستاره‌ها با موقعیت، سرعت و اندازه تصادفی برای پس‌زمینه متحرک ساخته می‌شوند.
        # Stars are initialized with random positions, speeds, and sizes for the animated background.
        self.stars = [
            [random.uniform(0, W),
             random.uniform(0, H),
             random.uniform(S.FxCfg.STAR_SPEED_MIN, S.FxCfg.STAR_SPEED_MAX),
             random.uniform(0.6, 2.0)]
            for _ in range(150)
        ]

        self._t = 0.0

        self.btn_back = _BackButton(
            self._go_back,
            cx=W // 2,
            cy=BTN_Y,
        )

        self.audio = getattr(self.game, "audio", None)

    def on_exit(self) -> None:
        # آزادسازی فهرست ستاره‌ها هنگام خروج از صحنه.
        # Clear the star list when leaving the scene.
        self.stars.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._go_back()
                return
        self.btn_back.handle_event(event)

    def update(self, dt: float) -> None:
        self._t += dt

        # حرکت عمودی ستاره‌ها با سرعت مستقل و متناسب با زمان فریم.
        # Stars move vertically at individual speeds scaled by the frame delta time.
        for st in self.stars:
            st[1] += st[2] * dt

            # ستاره‌های خارج‌شده از پایین صفحه از بالا و در موقعیتی افقی جدید ظاهر می‌شوند.
            # Stars leaving the bottom of the screen reappear at the top with a new horizontal position.
            if st[1] > H + 4:
                st[1] = -4
                st[0] = random.uniform(0, W)

        mouse_pos = pygame.mouse.get_pos()
        self.btn_back.update(dt, mouse_pos)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(S.Palette.BG_DEEP)

        # رسم پس‌زمینه ستاره‌ای پیش از سایر اجزای رابط کاربری.
        # Draw the starfield background before rendering the other UI elements.
        for x, y, _, r in self.stars:
            pygame.draw.circle(surface, S.Palette.STAR_FAR,
                               (int(x), int(y)), max(1, int(r)))

        self._draw_title(surface)

        # در نبود رکورد، پیام خالی نمایش داده می‌شود؛ در غیر این صورت رتبه‌بندی رسم می‌شود.
        # An empty-state message is shown when no records exist; otherwise, the leaderboard is rendered.
        if self.store.is_empty:
            self._draw_empty(surface)
        else:
            self._draw_podium(surface)
            if self.rest:
                self._draw_table(surface)

        self.btn_back.draw(surface, self.font_row_sm)

    def _draw_background_glow(self, surface: pygame.Surface) -> None:
        cx = W // 2
        cy = int(H * 0.35)
        r = 320
        halo = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)

        # حلقه‌های هم‌مرکز با آلفای متغیر، هاله‌ای نرم در مرکز پس‌زمینه ایجاد می‌کنند.
        # Concentric circles with varying alpha values create a soft central background glow.
        for rr in range(r, 0, -10):
            a = int(5 * (1 - rr / r) ** 1.4)
            if a <= 0:
                continue
            pygame.draw.circle(halo, (60, 90, 180, a), (r, r), rr)
        surface.blit(halo, (cx - r, cy - r),
                     special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_title(self, surface: pygame.Surface) -> None:
        cx = W // 2

        # تغییر سینوسی مقیاس عنوان، جلوه‌ای از تپش آرام ایجاد می‌کند.
        # A sinusoidal scale variation gives the title a subtle pulsing effect.
        pulse = 1.0 + 0.02 * math.sin(self._t * 2.5)

        img = self.font_title.render("HALL OF FAME", True, S.Palette.MENU_TITLE)
        w = int(img.get_width() * pulse)
        h = int(img.get_height() * pulse)
        img_s = pygame.transform.smoothscale(img, (w, h))

        # چند لایه بزرگ‌تر با شفافیت متفاوت، درخشش اطراف عنوان را می‌سازند.
        # Multiple enlarged layers with different alpha values create the title's glow.
        for layer in range(3, 0, -1):
            g = pygame.transform.smoothscale(img, (w + layer * 10, h + layer * 10))
            gs = pygame.Surface(g.get_size(), pygame.SRCALPHA)
            gs.blit(g, (0, 0))
            gs.set_alpha(28 - layer * 6)
            surface.blit(gs, gs.get_rect(center=(cx, TITLE_Y)),
                         special_flags=pygame.BLEND_RGBA_ADD)

        surface.blit(img_s, img_s.get_rect(center=(cx, TITLE_Y)))

        sub = self.font_sub.render(
            f"{self.total_games} MISSIONS  ·  {len(self.store.scores)} RECORDS",
            True, S.Palette.GREY,
        )
        surface.blit(sub, sub.get_rect(center=(cx, SUBTITLE_Y)))

        # شفافیت خط جداکننده در مرکز بیشترین مقدار را دارد و به دو انتها کاهش می‌یابد.
        # The divider's opacity peaks at the center and fades toward both ends.
        line_w = int(W * 0.42)
        for i in range(line_w):
            t = i / line_w
            a = int(140 * math.sin(math.pi * t))
            x = cx - line_w // 2 + i
            pygame.draw.line(surface, (*S.Palette.MENU_TITLE, a),
                             (x, DIVIDER_Y), (x, DIVIDER_Y + 1))

    def _draw_podium(self, surface: pygame.Surface) -> None:
        # ترتیب چیدمان از چپ به راست، رتبه دوم، اول و سوم است.
        # The left-to-right podium order is second place, first place, then third place.
        order = [1, 0, 2]
        n = min(len(self.top3), 3)
        actual_order = [i for i in order if i < n]

        cx = W // 2
        base_y = PODIUM_CY + PODIUM_H_1 // 2

        # عرض کل سکوها برای قرارگیری متقارن در مرکز صفحه محاسبه می‌شود.
        # The total podium width is calculated to center the arrangement on the screen.
        total_w = len(actual_order) * PODIUM_W + (len(actual_order) - 1) * PODIUM_GAP
        start_x = cx - total_w // 2

        for slot_idx, data_idx in enumerate(actual_order):
            entry = self.top3[data_idx]
            rank = data_idx + 1

            px = start_x + slot_idx * (PODIUM_W + PODIUM_GAP)

            if rank == 1:
                ph = PODIUM_H_1
            elif rank == 2:
                ph = PODIUM_H_2
            else:
                ph = PODIUM_H_3

            # هر سکو با تأخیر مختص رتبه خود وارد می‌شود و ارتفاعش به‌صورت easing افزایش می‌یابد.
            # Each podium enters with a rank-based delay, while its height grows using an easing curve.
            delay = rank * self.PODIUM_STAGGER
            local_t = (self._t - delay) / 0.45
            if local_t <= 0:
                continue
            e = 1.0 - (1.0 - min(1.0, local_t)) ** 3
            display_h = int(ph * e)
            alpha = int(255 * min(1.0, local_t * 1.5))

            self._draw_podium_block(
                surface, px, base_y, PODIUM_W, display_h,
                rank, entry, alpha, e,
            )

    def _draw_podium_block(
        self,
        surface: pygame.Surface,
        x: int, base_y: int,
        w: int, h: int,
        rank: int,
        entry,
        alpha: int,
        entry_e: float,
    ) -> None:
        color = RANK_COLORS[rank]

        block_rect = pygame.Rect(x, base_y - h, w, h)
        block = pygame.Surface(block_rect.size, pygame.SRCALPHA)

        # رنگ هر ردیف عمودی با توجه به فاصله از بالای سکو تغییر می‌کند تا گرادیان شکل بگیرد.
        # Each horizontal row changes color according to its vertical position, creating a gradient.
        for i in range(h):
            t = i / max(1, h - 1)
            r = int(color[0] * (0.55 + 0.45 * (1 - t)))
            g = int(color[1] * (0.55 + 0.45 * (1 - t)))
            b = int(color[2] * (0.55 + 0.45 * (1 - t)))
            a = int(180 * (alpha / 255))
            pygame.draw.line(block, (r, g, b, a), (0, i), (w, i))
        surface.blit(block, block_rect.topleft)

        border_col = (*color, alpha)
        pygame.draw.rect(surface, border_col, block_rect, 2)

        # اندازه عدد رتبه در صورت نیاز متناسب با ارتفاع فعلی سکو کوچک می‌شود.
        # The rank number is scaled down when necessary to fit the podium's current height.
        rank_img = self.font_rank.render(str(rank), True, color)
        max_text_h = int(h * 0.55)
        if rank_img.get_height() > max_text_h:
            scale = max_text_h / rank_img.get_height()
            rank_img = pygame.transform.smoothscale(
                rank_img,
                (int(rank_img.get_width() * scale), int(rank_img.get_height() * scale)),
            )
        rank_img.set_alpha(alpha)
        rank_rect = rank_img.get_rect(center=(x + w // 2, base_y - h // 2 + 8))
        surface.blit(rank_img, rank_rect)

        if h > 60:
            label_img = self.font_label.render(RANK_LABELS[rank], True, color)
            label_img.set_alpha(int(alpha * 0.8))
            label_rect = label_img.get_rect(
                center=(x + w // 2, base_y - h + 18)
            )
            surface.blit(label_img, label_rect)

        # جزئیات رکورد پس از کامل‌تر شدن انیمیشن ورود سکو ظاهر می‌شوند.
        # Record details appear once the podium entrance animation has progressed sufficiently.
        if entry_e > 0.7:
            info_alpha = int(255 * (entry_e - 0.7) / 0.3)

            score_img = self.font_score.render(f"{entry.score:,}", True, color)
            score_img.set_alpha(info_alpha)
            score_rect = score_img.get_rect(
                center=(x + w // 2, base_y - h - 90)
            )
            surface.blit(score_img, score_rect)

            wave_img = self.font_row_sm.render(
                f"WAVE {entry.wave}", True, (200, 215, 240),
            )
            wave_img.set_alpha(info_alpha)
            wave_rect = wave_img.get_rect(
                center=(x + w // 2, base_y - h - 55)
            )
            surface.blit(wave_img, wave_rect)

            ship_img = self.font_row_sm.render(
                entry.ship.upper(), True, (200, 215, 240),
            )
            ship_img.set_alpha(info_alpha)
            ship_rect = ship_img.get_rect(
                center=(x + w // 2, base_y - h - 25)
            )
            surface.blit(ship_img, ship_rect)

    def _draw_table(self, surface: pygame.Surface) -> None:
        x = TABLE_X
        y_start = TABLE_TOP

        # ردیف‌ها با تأخیر پلکانی، محوشدن تدریجی و حرکت افقی کوتاه نمایش داده می‌شوند.
        # Rows appear with staggered delays, gradual fading, and a short horizontal slide.
        for i, entry in enumerate(self.rest):
            rank = i + 4
            delay = 0.4 + i * self.ROW_STAGGER
            local_t = (self._t - delay) / self.ROW_FADE_TIME
            if local_t <= 0:
                continue
            t = min(1.0, local_t)
            e = 1.0 - (1.0 - t) ** 3
            alpha = int(255 * e)
            slide_x = int((1.0 - e) * 30)

            y = y_start + i * ROW_H
            self._draw_table_row(surface, x, y, rank, entry, alpha, slide_x)

        bottom_y = y_start + len(self.rest) * ROW_H + 6
        pygame.draw.line(surface, (60, 80, 120),
                         (x - 10, bottom_y), (x + TABLE_W + 10, bottom_y), 1)

    def _draw_table_row(
        self,
        surface: pygame.Surface,
        x: int, y: int,
        rank: int,
        entry,
        alpha: int,
        slide_x: int,
    ) -> None:
        # پس‌زمینه نیمه‌شفاف و حاشیه هر ردیف، ساختار جدول را از پس‌زمینه جدا می‌کنند.
        # A translucent background and border distinguish each row from the surrounding background.
        row_rect = pygame.Rect(x - 10, y - 2, TABLE_W + 20, ROW_H - 2)
        bg = pygame.Surface(row_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            bg, (30, 45, 70, int(alpha * 0.35)),
            bg.get_rect(), border_radius=6,
        )
        surface.blit(bg, row_rect.topleft)

        pygame.draw.rect(
            surface, (70, 90, 130, alpha // 2),
            row_rect, 1, border_radius=6,
        )

        cy = y + (ROW_H - 2) // 2

        # اطلاعات هر رکورد در ستون‌های ثابت و با شفافیت هماهنگ با انیمیشن ردیف رسم می‌شوند.
        # Each record field is rendered in a fixed column with opacity synchronized to the row animation.
        rank_img = self.font_row.render(f"#{rank}", True, (200, 220, 255))
        rank_img.set_alpha(alpha)
        surface.blit(rank_img, rank_img.get_rect(midleft=(x + slide_x, cy)))

        score_img = self.font_row.render(
            f"{entry.score:,}", True, S.Palette.WHITE,
        )
        score_img.set_alpha(alpha)
        surface.blit(score_img, score_img.get_rect(midleft=(x + 110 + slide_x, cy)))

        wave_img = self.font_row_sm.render(
            f"WAVE {entry.wave}", True, S.Palette.CYAN,
        )
        wave_img.set_alpha(alpha)
        surface.blit(wave_img, wave_img.get_rect(midleft=(x + 300 + slide_x, cy)))

        ship_img = self.font_row_sm.render(
            entry.ship.upper(), True, (200, 215, 240),
        )
        ship_img.set_alpha(alpha)
        surface.blit(ship_img, ship_img.get_rect(midleft=(x + 420 + slide_x, cy)))

        date_img = self.font_row_sm.render(
            entry.date_short(), True, (170, 190, 220),
        )
        date_img.set_alpha(alpha)
        surface.blit(date_img, date_img.get_rect(midleft=(x + 590 + slide_x, cy)))

    def _draw_empty(self, surface: pygame.Surface) -> None:
        cx = W // 2
        cy = H // 2 - 20

        # هاله اطراف آیکون با حلقه‌های کاهنده و ضربان سینوسی ساخته می‌شود.
        # The icon's halo is built from shrinking circles and a sinusoidal pulse.
        icon_r = 60
        pulse = 0.9 + 0.1 * math.sin(self._t * 2.0)
        for rr in range(int(icon_r * 1.6), 0, -6):
            a = int(20 * (1 - rr / (icon_r * 1.6)) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(surface, (*S.Palette.HUD_ACCENT, a),
                               (cx, cy - 40), int(rr))

        empty_img = self.font_empty.render("NO MISSIONS YET", True, S.Palette.GREY)
        surface.blit(empty_img, empty_img.get_rect(center=(cx, cy + 60)))

        sub = self.font_row_sm.render(
            "Complete a mission to appear on the leaderboard",
            True, (120, 140, 170),
        )
        surface.blit(sub, sub.get_rect(center=(cx, cy + 110)))

    def _go_back(self) -> None:
        # پخش صدای لغو در صورت در دسترس بودن سیستم صوتی؛ خطای صوتی مانع بازگشت نمی‌شود.
        # Play the cancel sound when audio is available; audio errors do not prevent navigation.
        if self.audio is not None:
            try:
                self.audio.play("ui_cancel")
            except Exception:
                pass
        self.go_to(S.SceneName.MENU.value)


__all__ = ["LeaderboardScene"]