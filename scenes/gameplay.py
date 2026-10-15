"""
scenes/gameplay.py
==================

صحنه‌ی اصلی بازی (Gameplay Scene) برای SPACE BLASTER.

این فایل قلب تپنده‌ی بازی است: تمام سیستم‌های ساخته‌شده در فازهای
قبلی را مونتاژ می‌کند و به آن‌ها جان می‌بخشد.

مسئولیت‌ها:
    • ساخت و مدیریت Player، Bullets، Enemies، Powerups
    • راه‌اندازی Spawner (مدیریت موج‌ها)
    • راه‌اندازی CollisionSystem، ParticleSystem، Camera، Audio، HUD
    • اجرای حلقه‌ی بازی: ورودی، شلیک، فیزیک، برخورد، موج، دوربین
    • مدیریت Pause (با push به PauseScene)
    • مدیریت Game Over (با replace به GameOverScene)
    • API برای استفاده‌ی سایر سیستم‌ها:
        add_enemy, add_bullet, add_powerup,
        spawn_bullet_impact, spawn_enemy_explosion,
        spawn_player_explosion, spawn_thruster_particle,
        spawn_powerup_burst, spawn_powerup,
        add_score, trigger_screen_bomb

این فایل خودش منطق بازی را «تصمیم» نمی‌گیرد؛ فقط هماهنگ می‌کند.
تمام تصمیم‌ها در entities/ و systems/ گرفته می‌شوند.
"""

from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies import Enemy, EnemyFactory, EnemyKind
from entities.powerup import Powerup, PowerupKind
from scenes.base import Scene
from systems.audio import AudioSystem, Bus
from systems.camera import Camera
from systems.collision import CollisionSystem
from systems.particles import ParticleKind, ParticleSystem
from systems.spawner import Spawner
from ui.hud import HUD
from entities.player import Player, build_ship



# ═══════════════════════════════════════════════════════════════════════════
#  کلاس GameplayScene
# ═══════════════════════════════════════════════════════════════════════════

class GameplayScene(Scene):
    """
    صحنه‌ی اصلی بازی.

    چرخه‌ی حیات:
        on_enter()  — ساخت همه‌ی موجودیت‌ها و سیستم‌ها
        update(dt)  — گام منطق بازی
        draw(surf)  — رندر لایه‌به‌لایه
        on_exit()   — پاک‌سازی
    """

    # ─────────────────────────────────────────────────────────────────────
    #  چرخه‌ی حیات
    # ─────────────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        # ---- فونت‌ها ----
        self.font_hud_big   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.HUGE, bold=True)
        self.font_hud_mid   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.BIG, bold=True)
        self.font_hud_small = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)

        # ---- سیستم‌ها ----
        self.camera     = Camera()
        self.audio      = self._get_audio()
        self.particles  = ParticleSystem(max_particles=2200)
        self.collision  = CollisionSystem(self, enable_spatial_hash=True)
        self.hud        = HUD()
        self.hud.set_show_fps(S.Debug.SHOW_FPS)

        # ---- موجودیت‌ها ----
        ship_key = getattr(self.game, "selected_ship", "phantom")
        self.player: Player = build_ship(ship_key, self)
        self.enemies: list[Enemy] = []
        self.bullets: list[Bullet] = []
        self.powerups: list[Powerup] = []

        # ---- Spawner ----
        self.spawner = Spawner(self, spawn_enemy=self.add_enemy, boss_every=5)
        self.spawner.start()

        # ---- وضعیت ----
        self.score: int = 0
        self.score_snapshot: int = 0   # برای محاسبه‌ی delta (اختیاری)
        self.paused_internal: bool = False
        self.game_over_pending: bool = False
        self.game_over_timer: float = 0.0    # مکث کوتاه قبل از رفتن به GameOver
        self._shoot_was_held: bool = False

        # ---- HUD init ----
        self.hud.set_hp(self.player.hp, self.player.MAX_HP)
        self.hud.set_score(0)
        self.hud.set_wave(0)

        # ---- پس‌زمینه‌ی ستاره‌ای (ساده، در همین صحنه) ----
        self._init_stars()

        # ---- موسیقی ----
        if self.audio:
            self.audio.play_music("music_battle", loop=True, fade_ms=700)

    def on_exit(self) -> None:
        # آزادسازی منابع
        if self.audio:
            self.audio.stop_bus(Bus.SHOOT, fade_ms=150)

    # ─────────────────────────────────────────────────────────────────────
    #  Audio — اگر Game audio داشته باشد از آن استفاده می‌کند
    # ─────────────────────────────────────────────────────────────────────

    def _get_audio(self) -> Optional[AudioSystem]:
        """
        اگر در Game یک AudioSystem سراسری وجود داشته باشد، استفاده می‌کند.
        وگرنه یکی می‌سازد. این باعث می‌شود موسیقی بین صحنه‌ها حفظ شود.
        """
        audio = getattr(self.game, "audio", None)
        if audio is None:
            try:
                audio = AudioSystem()
                setattr(self.game, "audio", audio)
            except Exception:
                audio = None
        return audio

    # ─────────────────────────────────────────────────────────────────────
    #  ستاره‌های پس‌زمینه
    # ─────────────────────────────────────────────────────────────────────

    def _init_stars(self) -> None:
        self.stars: list[list[float]] = []
        for _ in range(S.FxCfg.STAR_COUNT):
            self.stars.append([
                random.uniform(0, S.Window.WIDTH),
                random.uniform(0, S.Window.HEIGHT),
                random.uniform(S.FxCfg.STAR_SPEED_MIN, S.FxCfg.STAR_SPEED_MAX),
                random.uniform(0.7, 2.4),
            ])

    def _update_stars(self, dt: float) -> None:
        for st in self.stars:
            st[1] += st[2] * dt
            if st[1] > S.Window.HEIGHT + 2:
                st[1] = -2
                st[0] = random.uniform(0, S.Window.WIDTH)

    def _draw_stars(self, surface: pygame.Surface) -> None:
        for x, y, _, r in self.stars:
            pygame.draw.circle(
                surface, S.Palette.STAR_FAR,
                (int(x), int(y)), max(1, int(r)),
            )

    # ─────────────────────────────────────────────────────────────────────
    #  ورودی‌ها
    # ─────────────────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            # ---- Pause ----
            if event.key in S.Keys.PAUSE:
                self._push_pause()
                return
            # ---- بازگشت به منو ----
            if event.key in S.Keys.QUIT:  # ESC
                self._go_to_menu()
                return
            # ---- شلیک ----
            if event.key in S.Keys.SHOOT:
                self._handle_shoot()

    def _handle_shoot(self) -> None:
        if self.game_over_pending or self.paused_internal:
            return
        bullets = self.player.try_shoot()
        for b in bullets:
            self.bullets.append(b)
        # بازخورد دوربینی خیلی ملایم
        if bullets:
            self.camera.shake(2.0)

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        # ---- زمان‌بندی و مکث‌ها ----
        if self.game_over_pending:
            self.game_over_timer -= dt
            if self.game_over_timer <= 0.0:
                self._go_to_gameover()
            # در این حالت، فقط ذرات و دوربین به‌روز می‌شوند
            self.particles.update(dt)
            self.camera.update(dt)
            self.hud.update(dt)
            return

        # ---- ورودی پیوسته: شلیک با نگه‌داشتن Space ----
        if self.any_held(S.Keys.SHOOT):
            self._handle_shoot()

        # ---- به‌روزرسانی موجودیت‌ها ----
        self.player.update(dt)

        for b in self.bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for p in self.powerups:
            p.update(dt)

        # ---- برخوردها ----
        self.collision.process_bullets_vs_enemies(self.bullets, self.enemies)
        self.collision.process_bullets_vs_player(self.bullets, self.player)
        self.collision.process_enemies_vs_player(self.enemies, self.player)
        self.collision.process_powerups_vs_player(self.powerups, self.player)

        # ---- پردازش رویدادهای برخورد ----
        for ev in self.collision.drain_events():
            if ev.kind == "bullet_enemy":
                # نمایش امتیاز شناور فقط اگر دشمن مرده باشد
                if not ev.b.alive:
                    self.hud.register_kill()
                    self.hud.notify_score(
                        getattr(ev.b, "score_value", 10),
                        ev.b.x, ev.b.y - 8,
                    )

        # ---- پاک‌سازی موجودیت‌های مرده ----
        self.bullets  = [b for b in self.bullets  if b.alive]
        self.enemies  = [e for e in self.enemies  if e.alive]
        self.powerups = [p for p in self.powerups if p.alive]

        # ---- Spawner ----
        self.spawner.update(dt, alive_enemies=len(self.enemies))

        # ---- ستاره‌ها، ذرات، دوربین ----
        self._update_stars(dt)
        self.particles.update(dt)
        self.camera.update(dt)

        # ---- HUD ----
        self.hud.set_score(self.score)
        self.hud.set_wave(self.spawner.current_wave)
        self.hud.set_hp(self.player.hp, self.player.MAX_HP)

        # نوار Power-Up
        if self.player.powerup_time > 0:
            ratio = self.player.powerup_time / S.PowerupCfg.DURATION
            self.hud.set_powerup(ratio, S.Palette.POWERUP_CORE)
        else:
            self.hud.set_powerup(0.0)

        self.hud.set_fps(self.game.fps if hasattr(self.game, "fps") else 0.0)
        self.hud.update(dt)

        # ---- بررسی Game Over ----
        if self.player.hp <= 0 and self.player.alive is False:
            if not self.game_over_pending:
                self._begin_game_over()

    # ─────────────────────────────────────────────────────────────────────
    #  رسم
    # ─────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        # ---- رسم روی سطح دنیا ----
        # همه‌ی موجودیت‌ها را روی یه سطح می‌کشیم تا دوربین راحت اعمال شود
        world = pygame.Surface((S.Window.WIDTH, S.Window.HEIGHT))
        world.fill(S.Palette.BG_DEEP)

        # ---- ستاره‌های پس‌زمینه ----
        self._draw_stars(world)

        # ---- ذرات (پشت موجودیت‌ها) ----
        self.particles.draw(world)

        # ---- پاورآپ‌ها ----
        for p in self.powerups:
            p.draw(world)

        # ---- دشمن‌ها ----
        for e in self.enemies:
            e.draw(world)

        # ---- گلوله‌ها ----
        for b in self.bullets:
            b.draw(world)

        # ---- پلیر (اگر زنده) ----
        if self.player.alive:
            self.player.draw(world)

        # ---- اعمال دوربین (offset) ----
        ox, oy = self.camera.offset
        surface.fill(S.Palette.BG_DEEP)
        surface.blit(world, (int(ox), int(oy)))

        # ---- HUD (روی همه چیز، بدون offset دوربین) ----
        self.hud.draw(surface)

        # ---- پیام موج ----
        self.spawner.draw_announcement(surface, self.font_hud_mid)

        # ---- پاورآپ‌های آماده‌ی صفحه‌ی بازی ----
        # (نشانگر «Press P to Pause» فقط برای چند ثانیه‌ی اول)
        if self.time < 4.0 and self.spawner.wave <= 1:
            img = self.font_hud_small.render(
                "WASD/Arrows move  •  Space shoot  •  P pause  •  ESC quit",
                True, S.Palette.GREY,
            )
            rect = img.get_rect(center=(S.Window.WIDTH // 2, S.Window.HEIGHT - 40))
            surface.blit(img, rect)

        # ---- دیباگ هیت‌باکس ----
        if S.Debug.SHOW_HITBOX:
            self.collision.draw_debug(surface, [self.player] + self.enemies + self.bullets)

    # ─────────────────────────────────────────────────────────────────────
    #  ═══════════  API عمومی برای موجودیت‌ها و سیستم‌ها  ═══════════
    # ─────────────────────────────────────────────────────────────────────
    #  این متدها توسط Player، Enemy، Bullet، Powerup و Spawner صدا زده
    #  می‌شوند. همه‌ی آن‌ها Safety-First هستند: اگر چیزی نبود، کرش نمی‌کنند.
    # ─────────────────────────────────────────────────────────────────────

    # ---- افزودن موجودیت‌ها ----

    def add_enemy(self, enemy: Enemy) -> None:
        """یک دشمن به لیست اضافه می‌کند."""
        self.enemies.append(enemy)

    def add_bullet(self, bullet: Bullet) -> None:
        self.bullets.append(bullet)

    def add_powerup(self, powerup: Powerup) -> None:
        self.powerups.append(powerup)

    # ---- Spawn اختصاصی (با امضاهای Player/Enemy/Bullet) ----

    def spawn_bullet(self, bullet: Bullet) -> None:
        """Bullet در جای خودش ثبت می‌شود (برای Enemy._do_shoot)."""
        self.bullets.append(bullet)

    def spawn_bullet_impact(
        self,
        x: float, y: float,
        color: tuple[int, int, int] = (255, 200, 100),
        *,
        is_friendly: bool = True,
    ) -> None:
        """افکت کوچک برخورد گلوله."""
        self.particles.preset_bullet_impact(x, y, color, is_friendly=is_friendly)

    def spawn_enemy_explosion(
        self,
        x: float, y: float,
        radius: float,
        color: tuple[int, int, int] = (255, 90, 90),
    ) -> None:
        """انفجار دشمن (چندلایه)."""
        self.particles.preset_enemy_explosion(x, y, radius, color=color)

    def spawn_player_explosion(self, x: float, y: float) -> None:
        """انفجار سفینه‌ی پلیر."""
        self.particles.preset_player_explosion(x, y)

    def spawn_thruster_particle(
        self,
        x: float, y: float,
        vx: float, vy: float,
    ) -> None:
        """ذره‌ی موتور پلیر."""
        self.particles.preset_thruster(x, y, vx, vy)

    def spawn_powerup_burst(
        self,
        x: float, y: float,
        color: tuple[int, int, int] = (255, 220, 60),
    ) -> None:
        """انفجار برداشتن پاورآپ."""
        self.particles.preset_powerup_burst(x, y, color)

    def spawn_powerup(self, x: float, y: float, kind: Optional[PowerupKind] = None) -> None:
        """ساخت یک پاورآپ در موقعیت مشخص (توسط Enemy.on_death صدا زده می‌شود)."""
        try:
            pu = Powerup(x, y, kind=kind, scene=self)
            self.powerups.append(pu)
            if self.audio:
                self.audio.play("powerup_spawn")
        except Exception:
            pass

    # ---- Score ----

    def add_score(self, amount: int) -> None:
        """افزودن امتیاز (توسط Enemy.on_death صدا زده می‌شود)."""
        self.score += max(0, int(amount))

    # ---- رویدادهای خاص ----

    def trigger_screen_bomb(self, x: float, y: float) -> None:
        """
        پاک‌سازی همه‌ی دشمن‌های روی صفحه (پاورآپ BOMB).
        همه‌ی دشمن‌ها نابود می‌شوند و امتیاز می‌دهند.
        """
        # انفجار مرکزی
        self.particles.preset_boss_explosion(x, y)  # افکت بزرگ
        self.camera.shake(S.FxCfg.SHAKE_ON_BOSS_KILL, aftershock=2)

        # نابود کردن دشمن‌ها
        for enemy in list(self.enemies):
            if not enemy.alive:
                continue
            # امتیاز نصفه
            self.score += int(getattr(enemy, "score_value", 10) * 0.5)
            # انفجار
            self.particles.preset_enemy_explosion(
                enemy.x, enemy.y,
                enemy.radius,
                color=getattr(enemy, "BODY_COLOR", (255, 90, 90)),
            )
            enemy.alive = False
            enemy._pending_kill = True

        # پاک‌سازی گلوله‌های دشمن
        for b in self.bullets:
            if not b.friendly:
                b.alive = False

        if self.audio:
            self.audio.play("player_explode")  # صدای بم

    # ─────────────────────────────────────────────────────────────────────
    #  Pause / Game Over
    # ─────────────────────────────────────────────────────────────────────

    def _push_pause(self) -> None:
        """باز کردن منوی Pause روی همین صحنه."""
        if self.game_over_pending:
            return
        self.paused_internal = True
        if self.audio:
            self.audio.pause_music()
        # push روی Gameplay — بعد از pop، خودکار resume می‌شه
        self.game.scenes.push(S.SceneName.PAUSE.value)

    def on_resume(self) -> None:
        """وقتی از Pause برگشتیم."""
        self.paused_internal = False
        if self.audio:
            self.audio.resume_music()

    def _begin_game_over(self) -> None:
        """شروع مکث کوتاه قبل از رفتن به صفحه‌ی Game Over."""
        self.game_over_pending = True
        self.game_over_timer = 1.6  # ثانیه نمایش انفجار پلیر

    def _go_to_gameover(self) -> None:
        """رفتن به صفحه‌ی Game Over با پاس دادن آمار."""
        # ذخیره‌ی آمار در Game تا GameOverScene بخواند
        try:
            setattr(self.game, "last_score", self.score)
            setattr(self.game, "last_wave", self.spawner.current_wave)
        except Exception:
            pass
        if self.audio:
            self.audio.stop_music(fade_ms=400)
        self.go_to(S.SceneName.GAME_OVER.value)


    def _go_to_menu(self) -> None:
        """بازگشت فوری به منوی اصلی."""
        if self.audio:
            self.audio.stop_music(fade_ms=300)
        self.go_to(S.SceneName.MENU.value)

__all__ = ["GameplayScene"]