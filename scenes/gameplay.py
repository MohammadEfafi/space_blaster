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




class GameplayScene(Scene):
    """
    صحنه‌ی اصلی بازی.

    چرخه‌ی حیات:
        on_enter()  — ساخت همه‌ی موجودیت‌ها و سیستم‌ها
        update(dt)  — گام منطق بازی
        draw(surf)  — رندر لایه‌به‌لایه
        on_exit()   — پاک‌سازی
    """



    # راه‌اندازی منابع بصری، سیستم‌های بازی، موجودیت‌ها و وضعیت اولیه‌ی مرحله.
    # Initializes visual resources, game systems, entities, and the initial scene state.
    def on_enter(self) -> None:
        # ---- فونت‌ها ----
        self.font_hud_big   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.HUGE, bold=True)
        self.font_hud_mid   = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.BIG, bold=True)
        self.font_hud_small = pygame.font.SysFont(S.FontCfg.FAMILY, S.FontCfg.SMALL, bold=True)

        # ---- سیستم‌ها ----
        # ساخت و اتصال سیستم‌های دوربین، صدا، ذرات، برخورد و رابط کاربری.
        # Creates and connects the camera, audio, particle, collision, and user interface systems.
        self.camera     = Camera()
        self.audio      = self._get_audio()
        self.particles  = ParticleSystem(max_particles=2200)
        self.collision  = CollisionSystem(self, enable_spatial_hash=True)
        self.hud        = HUD()
        self.hud.set_show_fps(S.Debug.SHOW_FPS)

        # ---- موجودیت‌ها ----
        # ساخت سفینه‌ی انتخاب‌شده و آماده‌سازی فهرست موجودیت‌های فعال بازی.
        # Builds the selected ship and initializes the collections of active game entities.
        ship_key = getattr(self.game, "selected_ship", "phantom")
        self.player: Player = build_ship(ship_key, self)
        self.enemies: list[Enemy] = []
        self.bullets: list[Bullet] = []
        self.powerups: list[Powerup] = []

        # ---- Spawner ----
        # راه‌اندازی سیستم ایجاد دشمن‌ها و مدیریت روند موج‌های بازی.
        # Initializes the enemy spawning system and manages the game's wave progression.
        self.spawner = Spawner(
            self,
            spawn_enemy=self.add_enemy,
            boss_every=S.WaveCfg.BOSS_EVERY,
        )
        self.spawner.start()

        # ---- وضعیت ----
        # مقداردهی امتیاز، وضعیت مکث و زمان‌سنج‌های رویدادهای پایانی مرحله.
        # Initializes the score, pause state, and timers for end-of-game events.
        self.score: int = 0
        self.score_snapshot: int = 0   # برای محاسبه‌ی delta (اختیاری)
        self.paused_internal: bool = False
        self.game_over_pending: bool = False
        self.game_over_timer: float = 0.0    # مکث کوتاه قبل از رفتن به GameOver
        self.boss_defeated_timer: float = 0.0

        # ---- HUD init ----
        # تنظیم مقادیر اولیه‌ی نوار وضعیت بر اساس مشخصات سفینه و وضعیت شروع مرحله.
        # Sets the initial HUD values according to the ship's attributes and the starting game state.
        self.hud.set_hp(self.player.hp, self.player.MAX_HP)
        self.hud.set_score(0)
        self.hud.set_wave(0)

        # ---- پس‌زمینه‌ی ستاره‌ای (ساده، در همین صحنه) ----
        # ایجاد ستاره‌های پس‌زمینه برای نمایش حرکت فضایی در صحنه‌ی بازی.
        # Initializes background stars to create a sense of movement in the game scene.
        self._init_stars()

        # ---- موسیقی ----
        # پخش موسیقی مبارزه به‌صورت تکرارشونده با محوشدن تدریجی موسیقی قبلی.
        # Plays the battle music in a loop with a gradual transition from the previous track.
        if self.audio:
            self.audio.play_music("music_battle", loop=True, fade_ms=700)

    # توقف صدای شلیک هنگام خروج از صحنه و آزادسازی منابع مرتبط.
    # Stops the shooting audio bus when leaving the scene and releases related resources.
    def on_exit(self) -> None:
        # آزادسازی منابع
        if self.audio:
            self.audio.stop_bus(Bus.SHOOT, fade_ms=150)


    # دریافت سیستم صوتی مشترک بازی یا ساخت نمونه‌ی جدید در صورت نبود آن.
    # Retrieves the shared game audio system or creates a new instance if none exists.
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


    # ایجاد ستاره‌ها با موقعیت، سرعت و اندازه‌ی تصادفی.
    # Initializes stars with randomized positions, speeds, and sizes.
    def _init_stars(self) -> None:
        self.stars: list[list[float]] = []
        for _ in range(S.FxCfg.STAR_COUNT):
            self.stars.append([
                random.uniform(0, S.Window.WIDTH),
                random.uniform(0, S.Window.HEIGHT),
                random.uniform(S.FxCfg.STAR_SPEED_MIN, S.FxCfg.STAR_SPEED_MAX),
                random.uniform(0.7, 2.4),
            ])

    # به‌روزرسانی موقعیت ستاره‌ها و انتقال ستاره‌های خارج‌شده به بالای صفحه.
    # Updates star positions and wraps stars that leave the screen back to the top.
    def _update_stars(self, dt: float) -> None:
        for st in self.stars:
            st[1] += st[2] * dt
            if st[1] > S.Window.HEIGHT + 2:
                st[1] = -2
                st[0] = random.uniform(0, S.Window.WIDTH)

    # رسم ستاره‌های پس‌زمینه با اندازه و موقعیت فعلی آن‌ها.
    # Draws background stars using their current positions and sizes.
    def _draw_stars(self, surface: pygame.Surface) -> None:
        for x, y, _, r in self.stars:
            pygame.draw.circle(
                surface, S.Palette.STAR_FAR,
                (int(x), int(y)), max(1, int(r)),
            )



    # دریافت ورودی‌های صفحه‌کلید برای مکث، بازگشت به منو و شلیک.
    # Handles keyboard input for pausing, returning to the menu, and shooting.
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

    # اجرای شلیک با بررسی وضعیت بازی و افزودن گلوله‌های تولیدشده به فهرست.
    # Executes shooting after checking the game state and adds the generated bullets to the collection.
    def _handle_shoot(self) -> None:
        if self.game_over_pending or self.paused_internal:
            return
        bullets = self.player.try_shoot()
        for b in bullets:
            self.bullets.append(b)
        # بازخورد دوربینی خیلی ملایم
        if bullets:
            self.camera.shake(2.0)


    # حلقه‌ی اصلی به‌روزرسانی منطق بازی در هر فریم.
    # Main per-frame update loop for the game's logic.
    def update(self, dt: float) -> None:
        # ---- زمان‌بندی و مکث‌ها ----
        # مدیریت مکث پیش از پایان بازی و به‌روزرسانی اجزای بصری در این بازه.
        # Handles the delay before the game ends and updates visual systems during this interval.
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
        # بررسی ورودی پیوسته برای امکان شلیک تا زمانی که کلید مربوطه نگه داشته شده است.
        # Checks continuous input to allow shooting while the corresponding key remains held.
        if self.any_held(S.Keys.SHOOT):
            self._handle_shoot()

        # ---- به‌روزرسانی موجودیت‌ها ----
        # به‌روزرسانی وضعیت و حرکت سفینه، گلوله‌ها، دشمن‌ها و پاورآپ‌ها.
        # Updates the state and movement of the player, bullets, enemies, and power-ups.
        self.player.update(dt)

        for b in self.bullets:
            b.update(dt)
        for e in self.enemies:
            e.update(dt)
        for p in self.powerups:
            p.update(dt)

        # ---- برخوردها ----
        # بررسی برخورد میان گلوله‌ها، دشمن‌ها، بازیکن و پاورآپ‌ها.
        # Checks collisions between bullets, enemies, the player, and power-ups.
        self.collision.process_bullets_vs_enemies(self.bullets, self.enemies)
        self.collision.process_bullets_vs_player(self.bullets, self.player)
        self.collision.process_enemies_vs_player(self.enemies, self.player)
        self.collision.process_powerups_vs_player(self.powerups, self.player)

        # ---- پردازش رویدادهای برخورد ----
        # دریافت رویدادهای ثبت‌شده‌ی برخورد و نمایش بازخورد مربوط به نابودی دشمن.
        # Processes recorded collision events and displays feedback for defeated enemies.
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
        # حذف موجودیت‌هایی که دیگر زنده نیستند از فهرست‌های فعال بازی.
        # Removes entities that are no longer alive from the active game collections.
        self.bullets  = [b for b in self.bullets  if b.alive]
        self.enemies  = [e for e in self.enemies  if e.alive]
        self.powerups = [p for p in self.powerups if p.alive]

        # ---- Spawner ----
        # مدیریت تولید دشمن‌ها و موج‌ها بر اساس تعداد دشمن‌های زنده‌ی فعلی.
        # Manages enemy spawning and wave progression based on the current number of living enemies.
        self.spawner.update(dt, alive_enemies=len(self.enemies))

        # ---- ستاره‌ها، ذرات، دوربین ----
        # به‌روزرسانی جلوه‌های پس‌زمینه، سیستم ذرات و حرکت دوربین.
        # Updates background effects, the particle system, and camera movement.
        self._update_stars(dt)
        self.particles.update(dt)
        self.camera.update(dt)

        # ---- HUD ----
        # همگام‌سازی اطلاعات نمایشگر وضعیت با مقادیر فعلی بازی و بازیکن.
        # Synchronizes the HUD with the current game and player state.
        self.hud.set_score(self.score)
        self.hud.set_wave(self.spawner.current_wave)
        self.hud.set_hp(self.player.hp, self.player.MAX_HP)

        # محاسبه‌ی مدت‌زمان مؤثر پاورآپ‌ها با درنظرگرفتن ضریب اختصاصی سفینه.
        # Calculates the effective power-up duration while accounting for the ship's specific multiplier.
        p_dur = S.PowerupCfg.DURATION
        if hasattr(self.player, "POWERUP_MULTIPLIER"):
            p_dur *= self.player.POWERUP_MULTIPLIER
        rf_dur = p_dur  # rapid_fire و powerup هر دو از همون multiplier استفاده می‌کنن

        # نمایش نوار وضعیت بر اساس پاورآپ فعال و زمان باقی‌مانده‌ی آن.
        # Displays the power-up bar according to the active effect and its remaining duration.
        if self.player.powerup_time > 0:
            ratio = min(1.0, self.player.powerup_time / p_dur)
            bar_color = S.Palette.POWERUP_CORE
            self.hud.set_powerup(ratio, bar_color)
        elif self.player.shield_time > 0:
            ratio = min(1.0, self.player.shield_time / S.PowerupCfg.DURATION)
            bar_color = (90, 220, 255)
            self.hud.set_powerup(ratio, bar_color)
        elif self.player.rapid_fire_time > 0:
            ratio = min(1.0, self.player.rapid_fire_time / rf_dur)
            bar_color = (255, 250, 120)
            self.hud.set_powerup(ratio, bar_color)
        else:
            self.hud.set_powerup(0.0)

        self.hud.set_fps(self.game.fps if hasattr(self.game, "fps") else 0.0)
        self.hud.update(dt)

        # ---- بررسی Game Over ----
        # تشخیص پایان بازی بر اساس صفرشدن جان بازیکن و غیرفعال‌شدن سفینه.
        # Detects game over when the player's health reaches zero and the ship is no longer alive.
        if self.player.hp <= 0 and self.player.alive is False:
            if not self.game_over_pending:
                self._begin_game_over()


    # رسم لایه‌های مختلف صحنه‌ی بازی و ترکیب آن‌ها با خروجی دوربین و HUD.
    # Draws the different game scene layers and composites them with the camera output and HUD.
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
        # انتقال سطح دنیا بر اساس جابه‌جایی دوربین، بدون تغییر مختصات HUD.
        # Applies the camera offset to the world surface without shifting the HUD coordinates.
        ox, oy = self.camera.offset
        surface.fill(S.Palette.BG_DEEP)
        surface.blit(world, (int(ox), int(oy)))

        # ---- HUD (روی همه چیز، بدون offset دوربین) ----
        self.hud.draw(surface)

        # ---- پیام موج ----
        self.spawner.draw_announcement(surface, self.font_hud_mid)

        # ---- پاورآپ‌های آماده‌ی صفحه‌ی بازی ----
        # (نشانگر «Press P to Pause» فقط برای چند ثانیه‌ی اول)
        # نمایش راهنمای کنترل‌ها در ابتدای بازی.
        # Displays the control hints during the initial moments of gameplay.
        if self.time < 20.0:
            img = self.font_hud_small.render(
                "WASD/Arrows - move    |    SPACE - shoot    |    P - pause    |    F11 - fullscreen    |    ALT+TAB - minimize    |  ESC - quit    " ,
                True, (200, 220, 255),
            )
            rect = img.get_rect(center=(S.Window.WIDTH // 2, S.Window.HEIGHT - 40))
            surface.blit(img, rect)

        # ---- نوار HP باس ----
        # رسم نوار سلامت باس‌های فعال در بالای صفحه.
        # Draws the health bars of active bosses near the top of the screen.
        self._draw_boss_health_bar(surface)

        # ---- دیباگ هیت‌باکس ----
        # نمایش محدوده‌ی برخورد موجودیت‌ها در صورت فعال‌بودن تنظیم دیباگ.
        # Displays entity collision boundaries when hitbox debugging is enabled.
        if S.Debug.SHOW_HITBOX:
            self.collision.draw_debug(surface, [self.player] + self.enemies + self.bullets)


    # ---- افزودن موجودیت‌ها ----
    # متدهای عمومی برای اضافه‌کردن موجودیت‌ها به فهرست‌های صحنه.
    # Public methods for adding entities to the scene collections.

    def add_enemy(self, enemy: Enemy) -> None:
        """یک دشمن به لیست اضافه می‌کند."""
        self.enemies.append(enemy)

    def add_bullet(self, bullet: Bullet) -> None:
        self.bullets.append(bullet)

    def add_powerup(self, powerup: Powerup) -> None:
        self.powerups.append(powerup)

    # ---- Spawn اختصاصی (با امضاهای Player/Enemy/Bullet) ----
    # متدهای تولید و ثبت گلوله‌ها و جلوه‌های بصری مورد استفاده‌ی موجودیت‌ها.
    # Methods for spawning and registering bullets and visual effects used by game entities.

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

    # ساخت پاورآپ با امکان تعیین نوع و جلوگیری از تولید BOMB هنگام مبارزه با باس.
    # Spawns a power-up with an optional type and prevents BOMB drops during boss fights.
    def spawn_powerup(
        self, x: float, y: float, kind: Optional[PowerupKind] = None,
    ) -> None:
        """ساخت پاورآپ. در باس‌فایت BOMB نمی‌ندازه."""
        try:
            # در باس‌فایت، BOMB نمیاد
            if kind is None and self._get_bosses():
                import random as _r
                non_bomb = [k for k in PowerupKind if k != PowerupKind.BOMB]
                if non_bomb:
                    kind = _r.choice(non_bomb)

            pu = Powerup(x, y, kind=kind, scene=self)
            self.powerups.append(pu)
            if self.audio:
                self.audio.play("powerup_spawn")
        except Exception:
            pass

    # ---- Score ----
    # افزایش امتیاز بازی با جلوگیری از اضافه‌شدن مقادیر منفی.
    # Updates the game score while preventing negative amounts from being added.

    def add_score(self, amount: int) -> None:
        """افزودن امتیاز (توسط Enemy.on_death صدا زده می‌شود)."""
        self.score += max(0, int(amount))

    # ---- رویدادهای خاص ----
    # مدیریت رویدادهای ویژه‌ی بازی و جلوه‌های مرتبط با آن‌ها.
    # Handles special gameplay events and their associated effects.

    def trigger_screen_bomb(self, x: float, y: float) -> None:
        """
        پاک‌سازی همه‌ی دشمن‌های روی صفحه (پاورآپ BOMB).
        همه‌ی دشمن‌ها نابود می‌شوند و امتیاز می‌دهند.
        """
        # انفجار مرکزی
        self.particles.preset_boss_explosion(x, y)  # افکت بزرگ
        self.camera.shake(S.FxCfg.SHAKE_ON_BOSS_KILL, aftershock=2)

        # نابود کردن دشمن‌ها (باس‌ها در امان)
        # حذف دشمن‌های عادی، ثبت امتیاز و ایجاد انفجار؛ باس‌ها از این اثر مستثنا هستند.
        # Removes regular enemies, awards score, and creates explosions while excluding bosses.
        from entities.enemies.boss_base import BossBase
        for enemy in list(self.enemies):
            if not enemy.alive:
                continue
            # باس‌ها رو نکش
            if isinstance(enemy, BossBase):
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
        # غیرفعال‌کردن گلوله‌های متعلق به دشمن‌ها پس از فعال‌شدن بمب.
        # Deactivates enemy-owned bullets after the bomb is triggered.
        for b in self.bullets:
            if not b.friendly:
                b.alive = False

        if self.audio:
            self.audio.play("player_explode")  # صدای بم


    # مدیریت مکث بازی با قراردادن صحنه‌ی Pause روی Gameplay.
    # Pauses gameplay by pushing the Pause scene onto the scene stack.
    def _push_pause(self) -> None:
        """باز کردن منوی Pause روی همین صحنه."""
        if self.game_over_pending:
            return
        self.paused_internal = True
        if self.audio:
            self.audio.pause_music()
        # push روی Gameplay — بعد از pop، خودکار resume می‌شه
        self.game.scenes.push(S.SceneName.PAUSE.value)

    # ازسرگیری وضعیت Gameplay و موسیقی پس از بازگشت از صحنه‌ی Pause.
    # Resumes gameplay and its music after returning from the Pause scene.
    def on_resume(self) -> None:
        """وقتی از Pause برگشتیم."""
        self.paused_internal = False
        if self.audio:
            self.audio.resume_music()

    # آغاز فرایند پایان بازی و تعیین مدت مکث برای نمایش انفجار سفینه.
    # Starts the game-over sequence and sets the delay for displaying the player explosion.
    def _begin_game_over(self) -> None:
        """شروع مکث کوتاه قبل از رفتن به صفحه‌ی Game Over."""
        self.game_over_pending = True
        self.game_over_timer = 1.6  # ثانیه نمایش انفجار پلیر

    # انتقال به صحنه‌ی Game Over همراه با ذخیره‌ی امتیاز و شماره‌ی موج نهایی.
    # Transitions to the Game Over scene while storing the final score and wave number.
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


    # بازگشت فوری به منوی اصلی و توقف تدریجی موسیقی مبارزه.
    # Immediately returns to the main menu and gradually fades out the battle music.
    def _go_to_menu(self) -> None:
        """بازگشت فوری به منوی اصلی."""
        if self.audio:
            self.audio.stop_music(fade_ms=300)
        self.go_to(S.SceneName.MENU.value)



    # دریافت فهرست باس‌هایی که هنوز زنده هستند.
    # Retrieves the collection of bosses that are still alive.
    def _get_bosses(self) -> list:
        """همه‌ی باس‌های زنده."""
        from entities.enemies.boss_base import BossBase
        return [e for e in self.enemies if isinstance(e, BossBase) and e.alive]

    # ثبت رویداد شکست باس و نمایش پیام پیروزی در مرکز صفحه.
    # Handles a boss defeat event and displays a victory message at the center of the screen.
    def on_boss_defeated(self) -> None:
        """وقتی باس کشته شد."""
        self.boss_defeated_timer = 2.5  # پیام پیروزی
        try:
            self.hud.notify_text(
                "BOSS DEFEATED!",
                S.Window.WIDTH // 2, S.Window.HEIGHT // 2,
                color=(255, 240, 80),
                font_size=48,
                life=2.0,
            )
        except Exception:
            pass

    # رسم نوار سلامت باس‌های زنده با رنگ‌بندی متناسب با میزان HP باقی‌مانده.
    # Draws health bars for living bosses with colors based on their remaining HP.
    def _draw_boss_health_bar(self, surface: pygame.Surface) -> None:
        """نوار HP همه‌ی باس‌ها."""
        bosses = self._get_bosses()
        if not bosses:
            return

        n = len(bosses)
        bar_w = S.Window.WIDTH - 200
        x = 100

        # تنظیم ارتفاع، فاصله و موقعیت نوارها بر اساس تعداد باس‌های فعال.
        # Adjusts bar height, spacing, and vertical position according to the number of active bosses.
        if n == 1:
            bar_h, gap, top = 22, 0, 70
        else:
            bar_h, gap, top = 16, 6, 68

        font_size = 20 if n == 1 else 15
        font = pygame.font.SysFont(S.FontCfg.FAMILY, font_size, bold=True)

        for i, boss in enumerate(bosses):
            y = top + i * (bar_h + gap)
            ratio = max(0.0, boss.hp / boss.max_hp)

            # انتخاب رنگ نوار بر اساس نسبت HP باقی‌مانده.
            # Selects the health bar color based on the remaining HP ratio.
            # رنگ
            if ratio > 0.5:
                color = (255, 60, 60)
                dark_c = (150, 20, 20)
            elif ratio > 0.25:
                color = (255, 140, 40)
                dark_c = (150, 60, 10)
            else:
                color = (255, 80, 255)
                dark_c = (150, 30, 150)

            # ---- پس‌زمینه ----
            # رسم پس‌زمینه‌ی نیمه‌شفاف زیر نوار سلامت.
            # Draws a translucent background beneath the health bar.
            bg = pygame.Surface((bar_w + 4, bar_h + 4), pygame.SRCALPHA)
            bg.fill((5, 5, 15, 220))
            surface.blit(bg, (x - 2, y - 2))

            # ---- پر شده ----
            # محاسبه‌ی طول بخش پرشده و ایجاد گرادیان رنگی در امتداد نوار.
            # Calculates the filled bar width and creates a color gradient across it.
            filled = int(bar_w * ratio)
            if filled > 0:
                bsurf = pygame.Surface((filled, bar_h), pygame.SRCALPHA)
                for j in range(filled):
                    t = j / max(1, filled - 1)
                    r = int(dark_c[0] * (1 - t) + color[0] * t)
                    g = int(dark_c[1] * (1 - t) + color[1] * t)
                    b = int(dark_c[2] * (1 - t) + color[2] * t)
                    pygame.draw.line(bsurf, (r, g, b, 255), (j, 0), (j, bar_h))
                surface.blit(bsurf, (x, y))

            # ---- حاشیه ----
            # رسم حاشیه‌ی نوار سلامت با رنگ وضعیت فعلی باس.
            # Draws the health bar border using the boss's current status color.
            pygame.draw.rect(surface, color, (x, y, bar_w, bar_h), 2)

            # ---- متن ----
            # نمایش نام باس و مقدار HP فعلی در مرکز نوار.
            # Displays the boss name and current HP value at the center of the bar.
            name = getattr(boss, "boss_name", "BOSS")
            label = f"{name}   {boss.hp} / {boss.max_hp}"
            text = font.render(label, True, (255, 240, 255))
            t_rect = text.get_rect(center=(x + bar_w // 2, y + bar_h // 2))
            shadow = font.render(label, True, (0, 0, 0))
            surface.blit(shadow, (t_rect.x + 1, t_rect.y + 1))
            surface.blit(text, t_rect)

__all__ = ["GameplayScene"]