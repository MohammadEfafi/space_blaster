"""
systems/collision.py
====================

سیستم تشخیص و پردازش برخورد (Collision System) برای SPACE BLASTER.

این ماژول با استفاده از ترکیب دو روش، برخوردها را به‌صورت بهینه
تشخیص می‌دهد:

    ①  Broad-phase: Spatial Hash Grid — به‌جای بررسی همه‌ی جفت‌ها
        (O(n²))، اشیاء در سلول‌های شبکه قرار می‌گیرند و فقط همسایه‌ها
        بررسی می‌شوند. برای صدها موجودیت، سرعت چند برابر می‌شود.

    ②  Narrow-phase: Circle-circle — دقیق و سریع. هر موجودیت
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


# ═══════════════════════════════════════════════════════════════════════════
#  گزارش برخورد (Collision Event)
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
#  Spatial Grid
# ═══════════════════════════════════════════════════════════════════════════

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
        self.cells: dict[tuple[int, int], list[Entity]] = {}
        # بافر reuse برای پیمایش بدون allocate
        self._visited: set[int] = set()

    def clear(self) -> None:
        self.cells.clear()

    def _cell_of(self, x: float, y: float) -> tuple[int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def insert(self, entity: Entity) -> None:
        """موجودیت را در همه‌ی سلول‌هایی که با آن هم‌پوشانی دارد قرار می‌دهد."""
        r = entity.radius
        cx_min = int((entity.x - r) // self.cell_size)
        cx_max = int((entity.x + r) // self.cell_size)
        cy_min = int((entity.y - r) // self.cell_size)
        cy_max = int((entity.y + r) // self.cell_size)

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
        self.clear()
        for e in entities:
            if e.alive:
                self.insert(e)

    def query_pairs(self) -> Iterator[tuple[Entity, Entity]]:
        """
        جفت‌های ممکن (broad-phase) را تولید می‌کند. این جفت‌ها
        الزاماً برخورد ندارند — فقط کاندید هستند.
        """
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
                    key = a_id ^ b_id
                    if key in visited:
                        continue
                    visited.add(key)
                    yield (a, b)

    def query_neighbors(self, entity: Entity) -> Iterator[Entity]:
        """همه‌ی موجودیت‌های نزدیک به entity را برمی‌گرداند."""
        cx, cy = self._cell_of(entity.x, entity.y)
        seen: set[int] = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                bucket = self.cells.get((cx + dx, cy + dy))
                if bucket is None:
                    continue
                for other in bucket:
                    oid = id(other)
                    if oid == id(entity) or oid in seen:
                        continue
                    seen.add(oid)
                    yield other


# ═══════════════════════════════════════════════════════════════════════════
#  توابع هندسی سریع
# ═══════════════════════════════════════════════════════════════════════════

def circles_overlap(
    ax: float, ay: float, ar: float,
    bx: float, by: float, br: float,
) -> bool:
    """برخورد دو دایره — بدون sqrt (سریع‌تر)."""
    dx = ax - bx
    dy = ay - by
    r = ar + br
    return dx * dx + dy * dy <= r * r


def entities_collide(a: Entity, b: Entity) -> bool:
    """
    برخورد دو موجودیت با پشتیبانی از هیت‌باکس چندگانه.
    اگر هر دو ساده (یک دایره) باشند، مسیر سریع استفاده می‌شود.
    """
    a_circles = a.get_hitcircles()
    b_circles = b.get_hitcircles()

    # مسیر سریع: هر دو تک‌دایره
    if len(a_circles) == 1 and len(b_circles) == 1:
        ax, ay, ar = a_circles[0]
        bx, by, br = b_circles[0]
        return circles_overlap(ax, ay, ar, bx, by, br)

    # مسیر کلی
    for ax, ay, ar in a_circles:
        for bx, by, br in b_circles:
            if circles_overlap(ax, ay, ar, bx, by, br):
                return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
#  سیستم برخورد
# ═══════════════════════════════════════════════════════════════════════════

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
        self.grid = SpatialGrid(cell_size=cell_size) if enable_spatial_hash else None

        # ---- آمار (برای دیباگ) ----
        self.stats: dict[str, int] = {
            "bullet_enemy":   0,
            "bullet_player":  0,
            "enemy_player":   0,
            "powerup_player": 0,
            "enemy_enemy":    0,
        }

        # ---- بافر reuse ----
        self._events: list[CollisionEvent] = []

    # ─────────────────────────────────────────────────────────────────────
    #  پرونده‌ی اصلی: bullet ↔ enemy
    # ─────────────────────────────────────────────────────────────────────

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
        if not bullets or not enemies:
            return 0

        hits = 0

        if self.grid is not None and self.enable_spatial_hash:
            # Broad-phase با grid
            self.grid.build(enemies)
            for bullet in bullets:
                if not bullet.alive or not bullet.friendly:
                    continue
                # از سلول خود گلوله شروع می‌کنیم
                neighbors = list(self.grid.query_neighbors(bullet))
                for enemy in neighbors:
                    if not enemy.alive or not bullet.alive:
                        continue
                    if not entities_collide(bullet, enemy):
                        continue
                    self._handle_bullet_enemy(bullet, enemy)
                    hits += 1
                    if not bullet.alive:
                        break
        else:
            # مسیر ساده O(n*m) — برای تعداد کم
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
        self._events.append(CollisionEvent(
            a=bullet, b=enemy,
            kind="bullet_enemy",
            damage=bullet.damage,
            x=bullet.x, y=bullet.y,
        ))

        # آسیب به دشمن
        try:
            died = enemy.take_damage(bullet.damage)
        except Exception:
            died = False

        # اثر برخورد گلوله
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
        try:
            bullet.consume_hit()
        except Exception:
            bullet.alive = False

        self.stats["bullet_enemy"] += 1

    # ─────────────────────────────────────────────────────────────────────
    #  پرونده: bullet ↔ player
    # ─────────────────────────────────────────────────────────────────────

    def process_bullets_vs_player(
        self,
        bullets: list["Bullet"],
        player: "Player",
    ) -> int:
        """گلوله‌های دشمن را با پلیر بررسی می‌کند."""
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
                break

        return hits

    def _handle_bullet_player(self, bullet: "Bullet", player: "Player") -> None:
        self._events.append(CollisionEvent(
            a=bullet, b=player,
            kind="bullet_player",
            damage=bullet.damage,
            x=bullet.x, y=bullet.y,
        ))

        # گلوله نابود
        bullet.alive = False

        # آسیب به پلیر
        try:
            player.take_damage(bullet.damage)
        except Exception:
            pass

        # افکت
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

    # ─────────────────────────────────────────────────────────────────────
    #  پرونده: enemy ↔ player
    # ─────────────────────────────────────────────────────────────────────

    def process_enemies_vs_player(
        self,
        enemies: list["Enemy"],
        player: "Player",
    ) -> int:
        """برخورد فیزیکی دشمن با پلیر (kamikaze)."""
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
                break

        return hits

    def _handle_enemy_player(self, enemy: "Enemy", player: "Player") -> None:
        self._events.append(CollisionEvent(
            a=enemy, b=player,
            kind="enemy_player",
            damage=1,
            x=enemy.x, y=enemy.y,
        ))

        # باس‌ها از برخورد با پلیر نمی‌میرن
        from entities.enemies.boss_base import BossBase
        is_boss = isinstance(enemy, BossBase)

        if not is_boss:
            # دشمن معمولی: kamikaze
            enemy.kill()

        # آسیب به پلیر
        try:
            player.take_damage(1)
        except Exception:
            pass

        # لرزش
        if self.scene is not None:
            try:
                self.scene.camera.shake(S.FxCfg.SHAKE_ON_HIT)
            except Exception:
                pass

        self.stats["enemy_player"] += 1

    # ─────────────────────────────────────────────────────────────────────
    #  پرونده: powerup ↔ player
    # ─────────────────────────────────────────────────────────────────────

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
        if not powerups or player is None or not player.alive:
            return 0

        hits = 0
        for pu in powerups:
            if not pu.alive:
                continue
            # فاصله‌ی مستقیم
            dx = pu.x - player.x
            dy = pu.y - player.y
            d2 = dx * dx + dy * dy
            r = pu.radius + player.radius + 6
            if d2 <= r * r:
                self._handle_powerup_player(pu, player)
                hits += 1

        return hits

    def _handle_powerup_player(self, powerup: "Powerup", player: "Player") -> None:
        self._events.append(CollisionEvent(
            a=powerup, b=player,
            kind="powerup_player",
            x=powerup.x, y=powerup.y,
        ))

        # Powerup خودش متد _on_collect را دارد که افکت را اعمال و خودش را kill می‌کند
        try:
            # type: ignore[attr-defined]
            powerup._on_collect(player)
        except Exception:
            powerup.alive = False

        self.stats["powerup_player"] += 1

    # ─────────────────────────────────────────────────────────────────────
    #  پرونده: enemy ↔ enemy (اختیاری، جدا کردن)
    # ─────────────────────────────────────────────────────────────────────

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
        if not enemies or len(enemies) < 2:
            return 0
        if self.grid is None:
            return 0

        self.grid.build(enemies)
        pushed = 0
        for a, b in self.grid.query_pairs():
            if not a.alive or not b.alive:
                continue
            dx = a.x - b.x
            dy = a.y - b.y
            d2 = dx * dx + dy * dy
            r = a.radius + b.radius
            if d2 >= r * r or d2 < 0.001:
                continue
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

    # ─────────────────────────────────────────────────────────────────────
    #  دسترسی به رویدادها
    # ─────────────────────────────────────────────────────────────────────

    def drain_events(self) -> list[CollisionEvent]:
        """رویدادهای انباشته‌شده از این فریم را برمی‌گرداند و بافر را خالی می‌کند."""
        events = self._events
        self._events = []
        return events

    def reset_stats(self) -> None:
        for k in self.stats:
            self.stats[k] = 0

    # ─────────────────────────────────────────────────────────────────────
    #  دیباگ
    # ─────────────────────────────────────────────────────────────────────

    def draw_debug(self, surface: pygame.Surface, entities: Iterable[Entity]) -> None:
        """نمایش هیت‌باکس‌ها برای دیباگ."""
        for e in entities:
            if not e.alive:
                continue
            for x, y, r in e.get_hitcircles():
                pygame.draw.circle(surface, (0, 255, 0), (int(x), int(y)), int(r), 1)

    def draw_grid_debug(self, surface: pygame.Surface) -> None:
        """نمایش خطوط Spatial Grid."""
        if self.grid is None:
            return
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