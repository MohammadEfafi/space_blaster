"""
systems/collision.py
====================

سیستم تشخیص و پردازش برخورد (Collision System) برای SPACE BLASTER.

این ماژول با استفاده از ترکیب دو روش، برخوردها را به‌صورت بهینه
تشخیص می‌دهد:

      Broad-phase: Spatial Hash Grid — به‌جای بررسی همه‌ی جفت‌ها
        (O(n²))، اشیاء در سلول‌های شبکه قرار می‌گیرند و فقط همسایه‌ها
        بررسی می‌شوند. برای صدها موجودیت، سرعت چند برابر می‌شود.

      Narrow-phase: Circle-circle — دقیق و سریع. هر موجودیت
        می‌تواند چند دایره‌ی هیت‌باکس داشته باشد (get_hitcircles).

Handlers اختصاصی:
    • Bullet ↔ Enemy   — آسیب + kill گلوله
    • Bullet ↔ Player  — آسیب + invulnerability
    • Enemy ↔ Player   — آسیب متقابل (kamikaze)
    • Powerup ↔ Player — فعال‌سازی پاورآپ
    • Enemy ↔ Enemy    — جدا کردن (اختیاری، برای آینده)

طراحی:
    CollisionSystem یک نمونه‌ی مستقل است که در هر فریم چند متد
    process_X_Y را فراخوانی می‌کند. هیچ منطق بازی داخلش نیست —
    فقط تشخیص برخورد و فراخوانی callbacks.

استفاده:
    cs = CollisionSystem()
    cs.process_bullets_vs_enemies(bullets, enemies)
    cs.process_enemies_vs_player(enemies, player)
    cs.process_powerups_vs_player(powerups, player)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, Optional

import pygame

from core import settings as S
from entities.entity import Entity

if TYPE_CHECKING:
    from entities.bullet import Bullet
    from entities.enemies import Enemy
    from entities.player import Player
    from entities.powerup import Powerup
    from scenes.gameplay import GameplayScene 



@dataclass(slots=True)
class CollisionEvent:
    """
    یک رکورد برخورد. برای دیباگ، آمار، یا پاس دادن به سیستم‌های دیگر.
    """
    a: Entity
    b: Entity
    kind: str          # "bullet_enemy", "player_hit", …
    damage: int = 0
    x: float = 0.0
    y: float = 0.0



class SpatialGrid:
    """
    شبکه‌ی فضایی ساده برای Broad-phase.

    هر موجودیت در سلول‌هایی که با هیت‌باکسش هم‌پوشانی دارند قرار می‌گیرد.
    سپس برای پیدا کردن برخوردهای ممکن، فقط سلول‌های همسایه بررسی می‌شوند.

    پارامترها:
        cell_size  — اندازه‌ی هر سلول (پیکسل). معمولاً ۲ برابر بزرگ‌ترین
                     شعاع موجودیت‌ها انتخاب می‌شود.
    """

    def __init__(self, cell_size: float = 60.0) -> None:
        self.cell_size: float = float(cell_size)

        # دیکشنری: (cell_x, cell_y) → لیست موجودیت‌ها
        # هر کلید مختصات یک سلول شبکه و مقدار آن فهرست موجودیت‌های قرارگرفته در آن سلول است.
        # Each key represents a grid cell coordinate, and its value contains the entities assigned to that cell.
        self.cells: dict[tuple[int, int], list[Entity]] = {}

        # بافر reuse برای پیمایش بدون allocate
        # این مجموعه برای جلوگیری از بررسی دوباره‌ی جفت‌ها استفاده می‌شود و بین فراخوانی‌ها مجدداً به کار می‌رود.
        # This set prevents duplicate pair checks and is reused between calls.
        self._visited: set[int] = set()

    def clear(self) -> None:
        self.cells.clear()

    def _cell_of(self, x: float, y: float) -> tuple[int, int]:
        # تقسیم صحیح رو به پایین، مختصات منفی را نیز به سلول فضایی صحیح نگاشت می‌کند.
        # Floor division maps negative coordinates to their correct spatial grid cells as well.
        return (int(x // self.cell_size), int(y // self.cell_size))

    def insert(self, entity: Entity) -> None:
        """موجودیت را در همه‌ی سلول‌هایی که با آن هم‌پوشانی دارد قرار می‌دهد."""
        # محدوده‌ی سلول‌ها از جعبه‌ی محاطی دایره‌ی موجودیت به دست می‌آید.
        # The covered cell range is calculated from the entity circle's bounding box.
        r = entity.radius
        cx_min = int((entity.x - r) // self.cell_size)
        cx_max = int((entity.x + r) // self.cell_size)
        cy_min = int((entity.y - r) // self.cell_size)
        cy_max = int((entity.y + r) // self.cell_size)

        # قرار دادن موجودیت در تمام سلول‌هایی که محدوده‌ی شعاعی آن‌ها را قطع می‌کند، مانع از دست رفتن برخوردهای مرزی می‌شود.
        # Inserting the entity into every cell intersected by its radius prevents collisions near cell boundaries from being missed.
        for cx in range(cx_min, cx_max + 1):
            for cy in range(cy_min, cy_max + 1):
                key = (cx, cy)
                bucket = self.cells.get(key)
                if bucket is None:
                    self.cells[key] = [entity]
                else:
                    bucket.append(entity)

    def build(self, entities: Iterable[Entity]) -> None:
        """شبکه را با لیست موجودیت‌ها از نو می‌سازد."""
        # شبکه در هر بار ساخت پاک‌سازی می‌شود تا موقعیت‌های قدیمی موجودیت‌ها باقی نمانند.
        # The grid is cleared on every rebuild so outdated entity positions are not retained.
        self.clear()
        for e in entities:
            if e.alive:
                self.insert(e)

    def query_pairs(self) -> Iterator[tuple[Entity, Entity]]:
        """
        جفت‌های ممکن (broad-phase) را تولید می‌کند. این جفت‌ها
        الزاماً برخورد ندارند — فقط کاندید هستند.
        """
        # مجموعه‌ی بازدیدشده‌ها برای هر پیمایش از ابتدا خالی می‌شود.
        # The visited set is cleared at the beginning of each traversal.
        visited = self._visited
        visited.clear()

        for bucket in self.cells.values():
            n = len(bucket)
            for i in range(n):
                a = bucket[i]
                a_id = id(a)
                for j in range(i + 1, n):
                    b = bucket[j]
                    b_id = id(b)
                    # جلوگیری از پردازش دوباره‌ی یک جفت
                    # چون یک موجودیت ممکن است در چند سلول حضور داشته باشد، یک جفت می‌تواند چند بار دیده شود.
                    # Since an entity may occupy multiple cells, the same pair can otherwise appear more than once.
                    key = a_id ^ b_id
                    if key in visited:
                        continue
                    visited.add(key)
                    yield (a, b)

    def query_neighbors(self, entity: Entity) -> Iterator[Entity]:
        """همه‌ی موجودیت‌های نزدیک به entity را برمی‌گرداند."""
        # فقط سلول مرکزی و هشت سلول اطراف آن برای یافتن همسایه‌ها بررسی می‌شوند.
        # Only the central cell and its eight surrounding cells are checked for nearby entities.
        cx, cy = self._cell_of(entity.x, entity.y)
        seen: set[int] = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                bucket = self.cells.get((cx + dx, cy + dy))
                if bucket is None:
                    continue
                for other in bucket:
                    # خود موجودیت و همسایه‌هایی که قبلاً از سلول دیگری دیده شده‌اند، نادیده گرفته می‌شوند.
                    # The entity itself and neighbors already encountered in another cell are skipped.
                    oid = id(other)
                    if oid == id(entity) or oid in seen:
                        continue
                    seen.add(oid)
                    yield other


def circles_overlap(
    ax: float, ay: float, ar: float,
    bx: float, by: float, br: float,
) -> bool:
    """برخورد دو دایره — بدون sqrt (سریع‌تر)."""
    # مقایسه‌ی مربع فاصله‌ی مراکز با مربع مجموع شعاع‌ها، نیاز به محاسبه‌ی ریشه‌ی دوم را حذف می‌کند.
    # Comparing squared center distance with the squared sum of radii avoids calculating a square root.
    dx = ax - bx
    dy = ay - by
    r = ar + br
    return dx * dx + dy * dy <= r * r


def entities_collide(a: Entity, b: Entity) -> bool:
    """
    برخورد دو موجودیت با پشتیبانی از هیت‌باکس چندگانه.
    اگر هر دو ساده (یک دایره) باشند، مسیر سریع استفاده می‌شود.
    """
    # هیت‌دایره‌های هر دو موجودیت یک‌بار دریافت می‌شوند تا در بررسی جفت‌ها دوباره محاسبه نشوند.
    # Hit circles for both entities are retrieved once to avoid recalculating them during pair checks.
    a_circles = a.get_hitcircles()
    b_circles = b.get_hitcircles()

    # مسیر سریع: هر دو تک‌دایره
    # وقتی هر موجودیت فقط یک دایره دارد، مستقیماً همان دو دایره بررسی می‌شوند.
    # When each entity has only one circle, those two circles are checked directly.
    if len(a_circles) == 1 and len(b_circles) == 1:
        ax, ay, ar = a_circles[0]
        bx, by, br = b_circles[0]
        return circles_overlap(ax, ay, ar, bx, by, br)

    # مسیر کلی
    # در حالت چنددایره‌ای، برخورد هر ترکیب از دایره‌های دو موجودیت برای تشخیص برخورد کافی است.
    # With multiple circles, an overlap between any pair of circles is sufficient to register a collision.
    for ax, ay, ar in a_circles:
        for bx, by, br in b_circles:
            if circles_overlap(ax, ay, ar, bx, by, br):
                return True
    return False



class CollisionSystem:
    """
    مدیر برخوردها. یک نمونه در GameplayScene ساخته می‌شود و در هر
    فریم چند متد process_X_Y صدا زده می‌شود.

    پارامترها:
        scene — رفرنس اختیاری به Scene (برای دسترسی به camera، audio و …)
        enable_spatial_hash — اگر True (پیش‌فرض)، از Spatial Grid استفاده می‌کند
        cell_size — اندازه‌ی سلول برای Spatial Grid
    """

    def __init__(
        self,
        scene: Optional[GameplayScene] = None,
        *,
        enable_spatial_hash: bool = True,
        cell_size: float = 60.0,
    ) -> None:
        self.scene = scene
        self.enable_spatial_hash: bool = enable_spatial_hash

        # در صورت فعال بودن Spatial Hash، شبکه ساخته می‌شود؛ در غیر این صورت مسیر بررسی مستقیم استفاده خواهد شد.
        # When spatial hashing is enabled, a grid is created; otherwise, direct collision checks are used.
        self.grid = SpatialGrid(cell_size=cell_size) if enable_spatial_hash else None

        # ---- آمار (برای دیباگ) ----
        # شمارنده‌ها تعداد برخوردهای پردازش‌شده در هر دسته را نگهداری می‌کنند.
        # These counters track the number of processed collisions in each category.
        self.stats: dict[str, int] = {
            "bullet_enemy":   0,
            "bullet_player":  0,
            "enemy_player":   0,
            "powerup_player": 0,
            "enemy_enemy":    0,
        }

        # ---- بافر reuse ----
        # رویدادهای برخورد تا زمان فراخوانی drain_events در این فهرست جمع‌آوری می‌شوند.
        # Collision events are accumulated in this list until drain_events is called.
        self._events: list[CollisionEvent] = []



    def process_bullets_vs_enemies(
        self,
        bullets: list["Bullet"],
        enemies: list["Enemy"],
    ) -> int:
        """
        گلوله‌های پلیر را با دشمن‌ها بررسی می‌کند.
        هر گلوله می‌تواند چند دشمن را بزند اگر pierce داشته باشد.

        برمی‌گرداند: تعداد کل برخوردها.
        """
        # در صورت خالی بودن هرکدام از ورودی‌ها، بررسی برخورد ضرورتی ندارد.
        # If either input list is empty, collision processing is unnecessary.
        if not bullets or not enemies:
            return 0

        hits = 0

        if self.grid is not None and self.enable_spatial_hash:
            # Broad-phase با grid
            # ابتدا دشمن‌ها در شبکه قرار می‌گیرند تا هر گلوله فقط با همسایه‌های فضایی خود بررسی شود.
            # Enemies are first inserted into the grid so each bullet is checked only against its spatial neighbors.
            self.grid.build(enemies)
            for bullet in bullets:
                if not bullet.alive or not bullet.friendly:
                    continue
                # از سلول خود گلوله شروع می‌کنیم
                # فهرست همسایه‌ها پیش از پیمایش ساخته می‌شود تا تغییرات احتمالی شبکه روی این پیمایش اثر نگذارد.
                # The neighbor list is materialized before iteration so potential grid changes do not affect this traversal.
                neighbors = list(self.grid.query_neighbors(bullet))
                for enemy in neighbors:
                    if not enemy.alive or not bullet.alive:
                        continue
                    if not entities_collide(bullet, enemy):
                        continue
                    self._handle_bullet_enemy(bullet, enemy)
                    hits += 1
                    # گلوله‌ای که پس از برخورد مصرف شده است، دیگر نمی‌تواند به دشمن بعدی آسیب بزند.
                    # A bullet consumed by a collision cannot damage subsequent enemies.
                    if not bullet.alive:
                        break
        else:
            # مسیر ساده O(n*m) — برای تعداد کم
            # در این مسیر، هر گلوله مستقیماً با تمام دشمن‌ها مقایسه می‌شود.
            # In this path, each bullet is checked directly against every enemy.
            for bullet in bullets:
                if not bullet.alive or not bullet.friendly:
                    continue
                for enemy in enemies:
                    if not enemy.alive or not bullet.alive:
                        continue
                    if not entities_collide(bullet, enemy):
                        continue
                    self._handle_bullet_enemy(bullet, enemy)
                    hits += 1
                    if not bullet.alive:
                        break

        return hits

    def _handle_bullet_enemy(self, bullet: "Bullet", enemy: "Enemy") -> None:
        """منطق برخورد یک گلوله با یک دشمن."""
        # ثبت رویداد
        # اطلاعات برخورد در بافر ذخیره می‌شود تا سیستم‌های دیگر بتوانند بعداً آن را دریافت کنند.
        # Collision details are stored in the buffer so other systems can retrieve them later.
        self._events.append(CollisionEvent(
            a=bullet, b=enemy,
            kind="bullet_enemy",
            damage=bullet.damage,
            x=bullet.x, y=bullet.y,
        ))

        # آسیب به دشمن
        # خطای احتمالی در منطق آسیب‌رسانی نباید پردازش سایر برخوردها را متوقف کند.
        # A possible error in damage handling must not interrupt the processing of other collisions.
        try:
            died = enemy.take_damage(bullet.damage)
        except Exception:
            died = False

        # اثر برخورد گلوله
        # تولید افکت به Scene وابسته است؛ بنابراین در نبود Scene یا شکست افکت، برخورد همچنان پردازش می‌شود.
        # Impact effects depend on the scene, so collisions are still processed if the scene is absent or effect creation fails.
        if self.scene is not None:
            try:
                self.scene.spawn_bullet_impact(
                    bullet.x, bullet.y,
                    bullet._color_glow,  # type: ignore[attr-defined]
                    is_friendly=True,
                )
            except Exception:
                pass

        # مدیریت pierce
        # خود گلوله مسئول تعیین تعداد برخوردهای مجاز و زمان نابودی‌اش است.
        # The bullet itself determines how many hits it can pass through before being destroyed.
        try:
            bullet.consume_hit()
        except Exception:
            bullet.alive = False

        self.stats["bullet_enemy"] += 1


    def process_bullets_vs_player(
        self,
        bullets: list["Bullet"],
        player: "Player",
    ) -> int:
        """گلوله‌های دشمن را با پلیر بررسی می‌کند."""
        # اگر پلیر وجود نداشته باشد، زنده نباشد یا در وضعیت مصونیت باشد، برخوردی پردازش نمی‌شود.
        # No collisions are processed if the player is missing, dead, or currently invulnerable.
        if not bullets or player is None or not player.alive:
            return 0
        if player.is_invulnerable:
            return 0

        hits = 0
        for bullet in bullets:
            if not bullet.alive or bullet.friendly:
                continue
            if not entities_collide(bullet, player):
                continue
            self._handle_bullet_player(bullet, player)
            hits += 1
            if player.invuln_time > 0:
                # پلیر نامیرا شد، بقیه‌ی گلوله‌ها بی‌اثر
                # پس از فعال شدن زمان مصونیت، بررسی گلوله‌های بعدی در همین فریم متوقف می‌شود.
                # Once invulnerability is activated, further bullets are skipped for the remainder of this frame.
                break

        return hits

    def _handle_bullet_player(self, bullet: "Bullet", player: "Player") -> None:
        # ثبت جزئیات برخورد برای دسترسی سایر سیستم‌ها.
        # Store collision details for access by other systems.
        self._events.append(CollisionEvent(
            a=bullet, b=player,
            kind="bullet_player",
            damage=bullet.damage,
            x=bullet.x, y=bullet.y,
        ))

        # گلوله نابود
        # گلوله‌ی دشمن پس از برخورد مصرف می‌شود و نمی‌تواند دوباره آسیب وارد کند.
        # The enemy bullet is consumed on impact and cannot deal damage again.
        bullet.alive = False

        # آسیب به پلیر
        try:
            player.take_damage(bullet.damage)
        except Exception:
            pass

        # افکت
        # افکت برخورد برای گلوله‌ی دشمن با مشخصه‌ی is_friendly=False ایجاد می‌شود.
        # The impact effect for an enemy bullet is created with is_friendly=False.
        if self.scene is not None:
            try:
                self.scene.spawn_bullet_impact(
                    bullet.x, bullet.y,
                    bullet._color_glow,  # type: ignore[attr-defined]
                    is_friendly=False,
                )
            except Exception:
                pass

        self.stats["bullet_player"] += 1


    def process_enemies_vs_player(
        self,
        enemies: list["Enemy"],
        player: "Player",
    ) -> int:
        """برخورد فیزیکی دشمن با پلیر (kamikaze)."""
        # برخورد فیزیکی فقط برای پلیر زنده و آسیب‌پذیر بررسی می‌شود.
        # Physical collisions are checked only when the player is alive and vulnerable.
        if not enemies or player is None or not player.alive:
            return 0
        if player.is_invulnerable:
            return 0

        hits = 0
        for enemy in enemies:
            if not enemy.alive:
                continue
            if not entities_collide(enemy, player):
                continue
            self._handle_enemy_player(enemy, player)
            hits += 1
            if player.invuln_time > 0:
                # با فعال شدن مصونیت پلیر، برخوردهای فیزیکی بعدی در همین فریم بررسی نمی‌شوند.
                # Once player invulnerability is activated, further physical collisions are skipped for this frame.
                break

        return hits

    def _handle_enemy_player(self, enemy: "Enemy", player: "Player") -> None:
        # ثبت رویداد برخورد با مقدار آسیب ثابت یک واحد.
        # Record the collision event with a fixed damage value of one.
        self._events.append(CollisionEvent(
            a=enemy, b=player,
            kind="enemy_player",
            damage=1,
            x=enemy.x, y=enemy.y,
        ))

        # باس‌ها از برخورد با پلیر نمی‌میرن
        # تشخیص نوع باس تعیین می‌کند که برخورد باعث نابودی دشمن شود یا فقط به پلیر آسیب بزند.
        # Boss detection determines whether the collision destroys the enemy or only damages the player.
        from entities.enemies.boss_base import BossBase
        is_boss = isinstance(enemy, BossBase)

        if not is_boss:
            # دشمن معمولی: kamikaze
            # دشمن معمولی با برخورد مستقیم، رفتار انتحاری دارد و نابود می‌شود.
            # A regular enemy behaves as a kamikaze on direct contact and is destroyed.
            enemy.kill()

        # آسیب به پلیر
        try:
            player.take_damage(1)
        except Exception:
            pass

        # لرزش
        # در صورت دسترسی به Scene، برخورد فیزیکی افکت لرزش دوربین را فعال می‌کند.
        # When a scene is available, physical contact triggers the camera shake effect.
        if self.scene is not None:
            try:
                self.scene.camera.shake(S.FxCfg.SHAKE_ON_HIT)
            except Exception:
                pass

        self.stats["enemy_player"] += 1


    def process_powerups_vs_player(
        self,
        powerups: list["Powerup"],
        player: "Player",
    ) -> int:
        """
        پاورآپ‌ها با پلیر. توجه: Powerup خودش هم magnet دارد و
        در update_entity بررسی جذب انجام می‌دهد. این متد برای
        برخورد مستقیم (بدون magnet) استفاده می‌شود.
        """
        # در صورت نبود پاورآپ یا پلیر زنده، بررسی برخورد انجام نمی‌شود.
        # Collision checks are skipped when there are no power-ups or no living player.
        if not powerups or player is None or not player.alive:
            return 0

        hits = 0
        for pu in powerups:
            if not pu.alive:
                continue
            # فاصله‌ی مستقیم
            # مربع فاصله با مربع شعاع ترکیبی مقایسه می‌شود تا محاسبه‌ی ریشه‌ی دوم لازم نباشد.
            # Squared distance is compared with the squared combined radius to avoid calculating a square root.
            dx = pu.x - player.x
            dy = pu.y - player.y
            d2 = dx * dx + dy * dy
            r = pu.radius + player.radius + 6
            if d2 <= r * r:
                self._handle_powerup_player(pu, player)
                hits += 1

        return hits

    def _handle_powerup_player(self, powerup: "Powerup", player: "Player") -> None:
        # ثبت محل و نوع برخورد پاورآپ با پلیر.
        # Record the location and type of the power-up collision with the player.
        self._events.append(CollisionEvent(
            a=powerup, b=player,
            kind="powerup_player",
            x=powerup.x, y=powerup.y,
        ))

        # Powerup خودش متد _on_collect را دارد که افکت را اعمال و خودش را kill می‌کند
        # منطق جمع‌آوری به خود Powerup واگذار می‌شود تا اثر و وضعیت آن در همان کلاس مدیریت شود.
        # Collection logic is delegated to the Powerup itself so its effect and state are managed by that class.
        try:
            # type: ignore[attr-defined]
            powerup._on_collect(player)
        except Exception:
            powerup.alive = False

        self.stats["powerup_player"] += 1


    def separate_enemies(
        self,
        enemies: list["Enemy"],
        *,
        strength: float = 0.35,
    ) -> int:
        """
        دشمن‌های هم‌پوشان را کمی از هم جدا می‌کند تا روی هم انبار نشوند.
        این متد ظریف است و می‌تواند غیرفعال باشد؛ اگر performance
        مسئله شد، به‌جای این از «soft push» در update دشمن استفاده کن.
        """
        # جداسازی فقط زمانی ممکن است که دست‌کم دو دشمن و یک Spatial Grid در دسترس باشند.
        # Separation is possible only when at least two enemies and a spatial grid are available.
        if not enemies or len(enemies) < 2:
            return 0
        if self.grid is None:
            return 0

        self.grid.build(enemies)
        pushed = 0
        for a, b in self.grid.query_pairs():
            if not a.alive or not b.alive:
                continue

            # بردار فاصله و مجموع شعاع‌ها برای تشخیص میزان هم‌پوشانی محاسبه می‌شوند.
            # The separation vector and combined radii are calculated to determine the amount of overlap.
            dx = a.x - b.x
            dy = a.y - b.y
            d2 = dx * dx + dy * dy
            r = a.radius + b.radius

            # جفت‌های بدون هم‌پوشانی یا مراکز تقریباً یکسان از این محاسبه کنار گذاشته می‌شوند.
            # Pairs without overlap or with nearly identical centers are excluded from this calculation.
            if d2 >= r * r or d2 < 0.001:
                continue

            # هم‌پوشانی فقط به اندازه‌ی strength تقسیم و در دو جهت مخالف اعمال می‌شود.
            # The overlap is scaled by strength and applied in opposite directions to both entities.
            d = math.sqrt(d2)
            overlap = (r - d) * strength
            ux, uy = dx / d, dy / d
            a.x += ux * overlap
            a.y += uy * overlap
            b.x -= ux * overlap
            b.y -= uy * overlap
            pushed += 1

        self.stats["enemy_enemy"] += pushed
        return pushed


    def drain_events(self) -> list[CollisionEvent]:
        """رویدادهای انباشته‌شده از این فریم را برمی‌گرداند و بافر را خالی می‌کند."""
        # فهرست فعلی به فراخواننده تحویل داده می‌شود و بافر داخلی با یک فهرست تازه جایگزین می‌شود.
        # The current list is returned to the caller, and the internal buffer is replaced with a new list.
        events = self._events
        self._events = []
        return events

    def reset_stats(self) -> None:
        # تمام شمارنده‌های آماری موجود بدون تغییر ساختار دیکشنری صفر می‌شوند.
        # All existing statistics counters are reset to zero without changing the dictionary structure.
        for k in self.stats:
            self.stats[k] = 0


    def draw_debug(self, surface: pygame.Surface, entities: Iterable[Entity]) -> None:
        """نمایش هیت‌باکس‌ها برای دیباگ."""
        # فقط موجودیت‌های زنده و دایره‌های هیت‌باکس آن‌ها روی سطح دیباگ رسم می‌شوند.
        # Only living entities and their hit circles are drawn on the debug surface.
        for e in entities:
            if not e.alive:
                continue
            for x, y, r in e.get_hitcircles():
                pygame.draw.circle(surface, (0, 255, 0), (int(x), int(y)), int(r), 1)

    def draw_grid_debug(self, surface: pygame.Surface) -> None:
        """نمایش خطوط Spatial Grid."""
        # در نبود شبکه، چیزی برای نمایش وجود ندارد.
        # If no spatial grid exists, there is nothing to display.
        if self.grid is None:
            return

        # خطوط عمودی و افقی با فاصله‌ی cell_size رسم می‌شوند تا مرز سلول‌ها مشخص شود.
        # Vertical and horizontal lines are drawn at cell_size intervals to show the grid boundaries.
        cell = self.grid.cell_size
        w, h = S.Window.WIDTH, S.Window.HEIGHT
        color = (40, 60, 90)
        x = 0.0
        while x < w:
            pygame.draw.line(surface, color, (x, 0), (x, h), 1)
            x += cell
        y = 0.0
        while y < h:
            pygame.draw.line(surface, color, (0, y), (w, y), 1)
            y += cell


__all__ = [
    "CollisionSystem",
    "CollisionEvent",
    "SpatialGrid",
    "entities_collide",
    "circles_overlap",
]