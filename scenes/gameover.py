"""
scenes/gameover.py
==================

صفحه‌ی پایان بازی (Game Over) برای SPACE BLASTER.

ویژگی‌ها:
    • ورود سینمایی: عنوان از دور می‌آید و fade می‌شود
    • نمایش آمار نهایی: امتیاز، موج، High Score
    • تشخیص خودکار رکورد جدید + جشن (ذرات طلایی، متن تپنده)
    • پس‌زمینه‌ی ستاره‌ای آرام (کمتر از Gameplay)
    • رنگ‌بندی قرمز (شکست) + طلایی (رکورد جدید)
    • دکمه‌ها: Play Again, Main Menu, Quit

ذخیره‌سازی:
    فایل saves/highscore.json با ساختار:
        {
          "scores": [
            {"score": 12540, "wave": 7, "ship": "phantom", "date": "..."}
          ],
          "total_games": 23
        }
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

import pygame

from core import settings as S
from scenes.base import Scene
from systems.audio import AudioSystem
from systems.scores import HighScoreStore


# ساختار داده‌ی ذرات جشن؛ موقعیت، سرعت، طول عمر و ویژگی‌های ظاهری هر ذره را نگهداری می‌کند.
# Celebration particle data structure; stores each particle's position, velocity, lifetime, and visual properties.
@dataclass
class _CelebrationParticle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple[int, int, int]
    size: float
    angle: float
    angle_speed: float


class GameOverScene(Scene):
    """صفحه‌ی پایان بازی."""

    # زمان‌بندی انیمیشن ورود عنوان، نمایش آمار و ظاهر شدن دکمه‌ها.
    # Timing configuration for the title entrance, statistics reveal, and button appearance.
    TITLE_IN_TIME: float = 0.9
    STATS_REVEAL_DELAY: float = 0.5
    STATS_REVEAL_TIME: float = 0.6
    BUTTONS_DELAY: float = 1.6
    BUTTONS_FADE_TIME: float = 0.4

    # آماده‌سازی منابع بصری، دریافت نتایج بازی و مقداردهی اجزای صفحه‌ی پایان بازی.
    # Initializes visual resources, retrieves game results, and prepares the Game Over scene components.
    def on_enter(self) -> None:
        # ---- فونت‌ها ----
        self.font_title  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.HUGE, bold=True)
        self.font_sub    = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.LARGE, bold=True)
        self.font_label  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.NORMAL)
        self.font_value  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.BIG, bold=True)
        self.font_btn    = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.NORMAL, bold=True)
        self.font_small  = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL)

        # ---- آمار ----
        # دریافت امتیاز نهایی، موج طی‌شده و سفینه‌ی انتخاب‌شده از وضعیت بازی.
        # Retrieves the final score, reached wave, and selected ship from the game state.
        self.score = int(getattr(self.game, "last_score", 0))
        self.wave = int(getattr(self.game, "last_wave", 0))
        ship_key = getattr(self.game, "selected_ship", "phantom")

        # ---- ثبت در جدول امتیازات (فقط یک بار!) ----
        # ثبت نتیجه در جدول امتیازات و دریافت وضعیت رکورد جدید و رتبه‌ی بازیکن.
        # Submits the result to the leaderboard and retrieves the new-record status and player rank.
        self.store = self.game.scores
        self.is_new_high, self.rank = self.store.submit(
            self.score, self.wave, ship_key,
        )

        self.high_score = self.store.high_score
        self.best_wave = self.store.best_wave
        self.total_games = self.store.total_games

        # ---- زمان‌بندی ----
        # زمان‌سنج‌های مستقل برای کنترل پیشرفت انیمیشن‌های مختلف صفحه.
        # Independent timers control the progress of the scene's different animations.
        self._t: float = 0.0
        self._t_title: float = 0.0
        self._t_stats: float = 0.0
        self._t_buttons: float = 0.0

        # ---- ستاره‌ها ----
        # ایجاد ستاره‌ها با موقعیت، سرعت حرکت و اندازه‌ی تصادفی برای پس‌زمینه‌ی متحرک.
        # Creates stars with randomized positions, movement speeds, and sizes for the animated background.
        self.stars: list[list[float]] = []
        for _ in range(80):
            self.stars.append([
                random.uniform(0, S.Window.WIDTH),
                random.uniform(0, S.Window.HEIGHT),
                random.uniform(4.0, 22.0),
                random.uniform(0.6, 2.0),
            ])

        # ---- ذرات جشن ----
        # در صورت ثبت رکورد جدید، انفجار اولیه‌ی ذرات جشن ایجاد می‌شود.
        # An initial celebration particle burst is created when a new high score is achieved.
        self.celebration: list[_CelebrationParticle] = []
        if self.is_new_high:
            self._spawn_celebration_burst()

        # ---- دکمه‌ها ----
        # ساخت دکمه‌های شروع مجدد، بازگشت به منوی اصلی و خروج از بازی.
        # Creates the Play Again, Main Menu, and Quit buttons.
        from ui.button import Button

        y0 = S.Window.HEIGHT - 190
        self.buttons = [
            Button("PLAY AGAIN", self._play_again, y=y0),
            Button("MAIN MENU",  self._main_menu,  y=y0 + 60),
            Button("QUIT",       self._quit,       y=y0 + 120,
                   accent=S.Palette.HUD_HP),
        ]
        self.selected_idx = 0
        self.buttons[self.selected_idx].selected = True

        # ---- Audio ----
        # دریافت سیستم صوتی بازی و پخش موسیقی منو با محوشدن تدریجی.
        # Retrieves the game's audio system and plays the menu music with a fade transition.
        self.audio: Optional[AudioSystem] = getattr(self.game, "audio", None)
        if self.audio:
            self.audio.play_music("music_menu", loop=True, fade_ms=800)

    # آزادسازی فهرست دکمه‌ها، ستاره‌ها و ذرات هنگام خروج از صحنه.
    # Clears the button, star, and particle collections when leaving the scene.
    def on_exit(self) -> None:
        self.buttons.clear()
        self.stars.clear()
        self.celebration.clear()


    # پردازش ورودی‌های صفحه‌کلید و ماوس برای کنترل دکمه‌های صفحه.
    # Processes keyboard and mouse input to control the scene's buttons.
    def handle_event(self, event: pygame.event.Event) -> None:
        if self._t_buttons < 0.5:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self._move_selection(+1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._move_selection(-1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.buttons[self.selected_idx].trigger_click()
            elif event.key == pygame.K_ESCAPE:
                self._main_menu()

        for b in self.buttons:
            if b.handle_event(event):
                break

    # جابه‌جایی انتخاب فعال بین دکمه‌ها با پیمایش چرخشی و پخش صدای رابط کاربری.
    # Moves the active selection between buttons with wraparound navigation and plays a UI sound.
    def _move_selection(self, delta: int) -> None:
        self.buttons[self.selected_idx].selected = False
        self.selected_idx = (self.selected_idx + delta) % len(self.buttons)
        self.buttons[self.selected_idx].selected = True
        self._play_ui("ui_move")


    # به‌روزرسانی زمان‌بندی انیمیشن‌ها، پس‌زمینه، ذرات و وضعیت دکمه‌ها.
    # Updates animation timers, the background, particles, and button states.
    def update(self, dt: float) -> None:
        self._t += dt

        # پیشرفت تدریجی انیمیشن ورود عنوان تا رسیدن به مقدار نهایی.
        # Progresses the title entrance animation until it reaches its final value.
        if self._t_title < 1.0:
            self._t_title = min(1.0, self._t_title + dt / self.TITLE_IN_TIME)

        # نمایش تدریجی آمار پس از سپری‌شدن زمان تأخیر تعیین‌شده.
        # Gradually reveals the statistics after the configured delay.
        if self._t > self.STATS_REVEAL_DELAY and self._t_stats < 1.0:
            self._t_stats = min(1.0, self._t_stats + dt / self.STATS_REVEAL_TIME)

        # ظاهرشدن تدریجی دکمه‌ها پس از پایان زمان انتظار.
        # Gradually fades in the buttons after the configured delay.
        if self._t > self.BUTTONS_DELAY and self._t_buttons < 1.0:
            self._t_buttons = min(1.0, self._t_buttons + dt / self.BUTTONS_FADE_TIME)

        # حرکت ستاره‌ها به سمت پایین و انتقال مجدد آن‌ها به بالای صفحه پس از خروج.
        # Moves stars downward and wraps them back to the top after they leave the screen.
        for st in self.stars:
            st[1] += st[2] * dt
            if st[1] > S.Window.HEIGHT + 4:
                st[1] = -4
                st[0] = random.uniform(0, S.Window.WIDTH)

        # به‌روزرسانی حرکت، چرخش و طول عمر ذرات جشن و حذف ذرات منقضی‌شده.
        # Updates celebration particle movement, rotation, and lifetime while removing expired particles.
        if self.celebration:
            alive: list[_CelebrationParticle] = []
            for p in self.celebration:
                p.life -= dt
                if p.life <= 0.0:
                    continue
                p.vy += 140.0 * dt
                p.vx *= (1.0 - dt * 1.4)
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.angle += p.angle_speed * dt
                alive.append(p)
            self.celebration = alive

            # تولید انفجارهای کوچک و تصادفی در طول نمایش رکورد جدید.
            # Generates small random bursts while the new high score celebration is active.
            if self.is_new_high and random.random() < dt * 5.0:
                self._spawn_celebration_burst(count=8, small=True)

        # به‌روزرسانی دکمه‌ها و هماهنگ‌سازی انتخاب فعال با موقعیت نشانگر ماوس.
        # Updates buttons and synchronizes the active selection with the mouse cursor position.
        if self._t_buttons > 0.5:
            mouse_pos = pygame.mouse.get_pos()
            for i, b in enumerate(self.buttons):
                b.update(dt, mouse_pos)
                if b.hovered and i != self.selected_idx:
                    self.buttons[self.selected_idx].selected = False
                    self.selected_idx = i
                    b.selected = True


    # ترتیب رسم اجزای صحنه؛ از پس‌زمینه تا عنوان، آمار، دکمه‌ها و اطلاعات پایین صفحه.
    # Draws scene components in order, from the background to the title, statistics, buttons, and footer.
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(S.Palette.BG_DEEP)
        self._draw_backdrop(surface)
        self._draw_stars(surface)
        self._draw_vignette(surface)
        self._draw_celebration(surface)
        self._draw_title(surface)
        self._draw_stats(surface)
        if self._t_buttons > 0.01:
            self._draw_buttons(surface)
        self._draw_footer(surface)

    # ایجاد پس‌زمینه‌ی گرادیانی با ترکیب تدریجی رنگ از بالای صفحه به پایین.
    # Creates a gradient background by gradually blending colors from the top to the bottom of the screen.
    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        top = (12, 5, 15)
        bot = (5, 8, 20)
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(top[0] * (1 - t) + bot[0] * t)
            g = int(top[1] * (1 - t) + bot[1] * t)
            b = int(top[2] * (1 - t) + bot[2] * t)
            pygame.draw.line(overlay, (r, g, b, 255), (0, y), (w, y))
        surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # رسم ستاره‌های پس‌زمینه با اندازه‌ی متناسب با مقدار شعاع آن‌ها.
    # Draws background stars with sizes determined by their radius values.
    def _draw_stars(self, surface: pygame.Surface) -> None:
        for x, y, _, r in self.stars:
            pygame.draw.circle(
                surface, S.Palette.STAR_FAR,
                (int(x), int(y)), max(1, int(r * 0.7)),
            )

    # ایجاد تیرگی تدریجی در لبه‌های صفحه برای تمرکز بصری روی بخش مرکزی.
    # Creates gradual darkening around the screen edges to draw visual attention toward the center.
    def _draw_vignette(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        thickness = 120
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(thickness):
            alpha = int(70 * (1 - i / thickness) ** 1.6)
            if alpha <= 0:
                continue
            color = (60, 0, 20, alpha)
            pygame.draw.line(overlay, color, (i, 0), (i, h))
            pygame.draw.line(overlay, color, (w - 1 - i, 0), (w - 1 - i, h))
        for i in range(thickness // 2):
            alpha = int(50 * (1 - i / (thickness // 2)) ** 1.6)
            if alpha <= 0:
                continue
            color = (60, 0, 20, alpha)
            pygame.draw.line(overlay, color, (0, i), (w, i))
            pygame.draw.line(overlay, color, (0, h - 1 - i), (w, h - 1 - i))
        surface.blit(overlay, (0, 0))

    # رسم عنوان پایان بازی با بزرگ‌شدن تدریجی، محوشدن و جلوه‌ی درخشش.
    # Renders the Game Over title with gradual scaling, fading, and a glow effect.
    def _draw_title(self, surface: pygame.Surface) -> None:
        t = self._t_title
        e = 1.0 - (1.0 - t) ** 3
        scale = 0.6 + 0.4 * e
        alpha = e

        cx = S.Window.WIDTH // 2
        cy = 130

        text = "GAME OVER"
        img = self.font_title.render(text, True, S.Palette.HUD_HP)
        w = max(1, int(img.get_width() * scale))
        h = max(1, int(img.get_height() * scale))
        img_scaled = pygame.transform.smoothscale(img, (w, h))
        if alpha < 1.0:
            img_scaled.set_alpha(int(255 * alpha))

        rect = img_scaled.get_rect(center=(cx, cy))

        # ایجاد چند لایه‌ی درخشش پیرامون عنوان با ترکیب افزایشی رنگ‌ها.
        # Creates multiple glow layers around the title using additive color blending.
        if alpha > 0.15:
            for layer in range(4, 0, -1):
                glow = pygame.transform.smoothscale(
                    img, (w + layer * 14, h + layer * 14)
                )
                gs = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
                gs.blit(glow, (0, 0))
                gs.set_alpha(int(28 * alpha))
                surface.blit(
                    gs, gs.get_rect(center=(cx, cy)),
                    special_flags=pygame.BLEND_RGBA_ADD,
                )

        surface.blit(img_scaled, rect)

        # نمایش پیام رکورد جدید با تغییر اندازه‌ی ضربانی و جلوه‌ی درخشش طلایی.
        # Displays the new high score message with a pulsing scale and golden glow effect.
        if self.is_new_high and alpha > 0.5:
            pulse = 1.0 + 0.08 * math.sin(self._t * 5.0)
            sub_img = self.font_sub.render("<< NEW HIGH SCORE >>", True, S.Palette.YELLOW)
            w2 = int(sub_img.get_width() * pulse)
            h2 = int(sub_img.get_height() * pulse)
            sub_scaled = pygame.transform.smoothscale(sub_img, (w2, h2))
            sub_rect = sub_scaled.get_rect(center=(cx, cy + 70))
            for layer in range(3, 0, -1):
                glow = pygame.transform.smoothscale(
                    sub_img, (w2 + layer * 10, h2 + layer * 10)
                )
                gs = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
                gs.blit(glow, (0, 0))
                gs.set_alpha(40)
                surface.blit(
                    gs, gs.get_rect(center=sub_rect.center),
                    special_flags=pygame.BLEND_RGBA_ADD,
                )
            surface.blit(sub_scaled, sub_rect)

        # نمایش رتبه‌ی بازیکن در جدول امتیازات، در صورت قرارگرفتن میان ده رتبه‌ی برتر.
        # Displays the player's leaderboard rank when it falls within the top ten positions.
        if alpha > 0.5 and 1 <= self.rank <= 10:
            rank_y = cy + 105
            rank_color = (255, 210, 60) if self.rank == 1 else S.Palette.HUD_ACCENT
            rank_text = f"RANK #{self.rank}  on the leaderboard"
            rank_img = self.font_small.render(rank_text, True, rank_color)
            if alpha < 1.0:
                rank_img.set_alpha(int(255 * alpha))
            surface.blit(rank_img, rank_img.get_rect(center=(cx, rank_y)))

    # رسم پنل آمار نهایی همراه با نمایش تدریجی امتیاز، موج و بهترین رکورد.
    # Renders the final statistics panel with a gradual reveal of the score, wave, and best score.
    def _draw_stats(self, surface: pygame.Surface) -> None:
        if self._t_stats < 0.01:
            return

        alpha = self._t_stats
        cx = S.Window.WIDTH // 2
        y0 = 260

        # تعیین مقادیر و رنگ اختصاصی هر ردیف از آمار.
        # Defines the values and individual colors for each statistics row.
        rows = [
            ("FINAL SCORE", f"{self.score:,}",
             S.Palette.YELLOW if self.is_new_high else S.Palette.WHITE),
            ("WAVE REACHED", f"{self.wave}", S.Palette.WHITE),
            ("BEST SCORE", f"{self.high_score:,}", S.Palette.HUD_ACCENT),
        ]

        # ساخت پنل نیمه‌شفاف و قاب دور آن متناسب با میزان پیشرفت انیمیشن.
        # Creates a translucent panel and its border according to the animation progress.
        row_h = 58
        panel_w = 480
        panel_h = row_h * len(rows) + 40
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, int(120 * alpha)))
        panel_rect = panel.get_rect(center=(cx, y0 + panel_h // 2))
        pygame.draw.rect(
            panel, (*S.Palette.HUD_ACCENT, int(90 * alpha)),
            panel.get_rect(), 1, border_radius=10,
        )
        surface.blit(panel, panel_rect.topleft)

        # رسم برچسب و مقدار هر ردیف با تنظیم شفافیت و تراز عمودی.
        # Draws each row's label and value while adjusting transparency and vertical alignment.
        for i, (label, value, color) in enumerate(rows):
            ry = y0 + 30 + i * row_h

            lbl_img = self.font_label.render(label, True, S.Palette.GREY)
            val_img = self.font_value.render(value, True, color)

            if alpha < 1.0:
                lbl_img.set_alpha(int(255 * alpha))
                val_img.set_alpha(int(255 * alpha))

            surface.blit(lbl_img, (panel_rect.x + 30, ry))
            vrect = val_img.get_rect()
            vrect.right = panel_rect.right - 30
            vrect.centery = ry + lbl_img.get_height() // 2
            surface.blit(val_img, vrect)

    # رسم دکمه‌ها روی سطح موقت برای اعمال محوشدن تدریجی گروهی.
    # Draws buttons onto a temporary surface to apply a group fade-in effect.
    def _draw_buttons(self, surface: pygame.Surface) -> None:
        alpha = self._t_buttons

        if alpha < 1.0:
            temp = pygame.Surface((S.Window.WIDTH, S.Window.HEIGHT), pygame.SRCALPHA)
            for b in self.buttons:
                b.draw(temp, self.font_btn)
            temp.set_alpha(int(255 * alpha))
            surface.blit(temp, (0, 0))
        else:
            for b in self.buttons:
                b.draw(surface, self.font_btn)

    # نمایش راهنمای کنترل صفحه و تعداد کل بازی‌های انجام‌شده.
    # Displays the scene control hints and the total number of games played.
    def _draw_footer(self, surface: pygame.Surface) -> None:
        hint = "UP/DOWN  select    |    ENTER  confirm    |    ESC  menu"
        img = self.font_small.render(hint, True, S.Palette.GREY)
        rect = img.get_rect(center=(S.Window.WIDTH // 2, S.Window.HEIGHT - 26))
        surface.blit(img, rect)

        if self.total_games > 1:
            games_img = self.font_small.render(
                f"GAMES PLAYED: {self.total_games}", True, S.Palette.GREY,
            )
            grect = games_img.get_rect()
            grect.bottomright = (S.Window.WIDTH - 12, S.Window.HEIGHT - 10)
            surface.blit(games_img, grect)

    # رسم ذرات جشن با محاسبه‌ی محوشدن، کوچک‌شدن و چرخش تدریجی هر ذره.
    # Renders celebration particles by calculating their fading, shrinking, and gradual rotation.
    def _draw_celebration(self, surface: pygame.Surface) -> None:
        for p in self.celebration:
            t = 1.0 - (p.life / p.max_life)
            alpha = int(255 * (1.0 - t * t))
            if alpha <= 0:
                continue
            size = max(1, int(p.size * (1.0 - t * 0.5)))
            ang = math.radians(p.angle)
            cs, sn = math.cos(ang), math.sin(ang)

            # محاسبه‌ی مختصات چهار رأس ذره با استفاده از تبدیل چرخشی.
            # Calculates the four particle vertices using a rotational transformation.
            pts = [
                (p.x + cs * -size - sn * -size, p.y + sn * -size + cs * -size),
                (p.x + cs * size - sn * -size,  p.y + sn * size + cs * -size),
                (p.x + cs * size - sn * size,   p.y + sn * size + cs * size),
                (p.x + cs * -size - sn * size,  p.y + sn * -size + cs * size),
            ]
            tmp = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
            local = [(x - p.x + size * 1.5, y - p.y + size * 1.5) for x, y in pts]
            pygame.draw.polygon(tmp, (*p.color, alpha), local)
            surface.blit(
                tmp, (p.x - size * 1.5, p.y - size * 1.5),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    # ایجاد مجموعه‌ای از ذرات با جهت، سرعت، طول عمر، رنگ و چرخش تصادفی.
    # Spawns a group of particles with randomized direction, speed, lifetime, color, and rotation.
    def _spawn_celebration_burst(
        self,
        count: int = 26,
        *,
        small: bool = False,
    ) -> None:
        cx = S.Window.WIDTH // 2
        cy = 180

        for _ in range(count):
            side = random.choice((-1, 1))
            origin_x = cx + side * random.uniform(40, 240)
            origin_y = cy + random.uniform(-30, 30)

            # تعیین جهت حرکت با زاویه‌ی تصادفی و تبدیل آن به مؤلفه‌های سرعت.
            # Determines a random movement direction and converts it into velocity components.
            angle = random.uniform(0, math.tau)
            speed = random.uniform(80, 240) * (0.6 if small else 1.0)
            life = random.uniform(0.9, 1.8)
            color = random.choice([
                S.Palette.YELLOW,
                S.Palette.POWERUP_CORE,
                S.Palette.WHITE,
                S.Palette.HUD_ACCENT,
            ])
            self.celebration.append(_CelebrationParticle(
                x=origin_x,
                y=origin_y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 60,
                life=life,
                max_life=life,
                color=color,
                size=random.uniform(2.5, 5.5),
                angle=random.uniform(0, 360),
                angle_speed=random.uniform(-360, 360),
            ))


    # اجرای عملیات مربوط به دکمه‌های اصلی و پخش صداهای رابط کاربری.
    # Executes the main button actions and plays the corresponding user interface sounds.
    def _play_again(self) -> None:
        self._play_ui("ui_confirm")
        self.go_to(S.SceneName.GAMEPLAY.value)

    def _main_menu(self) -> None:
        self._play_ui("ui_cancel")
        self.go_to(S.SceneName.MENU.value)

    def _quit(self) -> None:
        self._play_ui("ui_cancel")
        self.quit_game()

    # پخش صدای رابط کاربری در صورت در دسترس بودن سیستم صوتی.
    # Plays a user interface sound when the audio system is available.
    def _play_ui(self, sound: str) -> None:
        if self.audio:
            try:
                self.audio.play(sound)
            except Exception:
                pass


__all__ = ["GameOverScene", "HighScoreStore"]