"""
systems/scores.py
=================

ذخیره‌سازی و بارگذاری امتیازات (High Scores / Leaderboard).

این ماژول یک نگهدارنده‌ی کامل امتیاز با پشتیبانی از تاپ N امتیاز
را فراهم می‌کند. داده‌ها در فایل JSON ذخیره می‌شوند تا بین اجراها
حفظ شوند.

فرمت فایل:
    {
      "scores": [
        {"score": 45200, "wave": 12, "ship": "phantom", "date": "..."},
        ...
      ],
      "total_games": 23
    }

ویژگی‌ها:
    • تاپ N امتیاز (پیش‌فرض ۱۰)
    • مهاجرت خودکار از فرمت قدیمی (فقط high_score)
    • ذخیره‌ی مقاوم به خطا — خطا کرش نمی‌کند
    • API ساده برای ثبت، مرور، و رتبه‌بندی
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import settings as S


# ═══════════════════════════════════════════════════════════════════════════
#  داده‌ی یک امتیاز
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(slots=True)
class ScoreEntry:
    """یک رکورد امتیاز در جدول."""
    score: int
    wave: int
    ship: str
    date: str

    @classmethod
    def from_dict(cls, d: dict) -> "ScoreEntry":
        return cls(
            score=int(d.get("score", 0)),
            wave=int(d.get("wave", 0)),
            ship=str(d.get("ship", "phantom")),
            date=str(d.get("date", "")),
        )

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "wave": self.wave,
            "ship": self.ship,
            "date": self.date,
        }

    def date_short(self) -> str:
        """تاریخ به شکل کوتاه YYYY-MM-DD."""
        if "T" in self.date:
            return self.date.split("T")[0]
        return self.date[:10] if self.date else "—"


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس HighScoreStore
# ═══════════════════════════════════════════════════════════════════════════

class HighScoreStore:
    """مدیر جدول امتیازات با ذخیره‌ی دائمی."""

    MAX_ENTRIES: int = 10

    def __init__(self, path: Optional[Path] = None) -> None:
        if path is None:
            path = S.SAVE_DIR / "highscore.json"
        self.path: Path = Path(path)
        self.scores: list[ScoreEntry] = []
        self.total_games: int = 0
        self._load()

    # ─────────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """بارگذاری از فایل با مهاجرت خودکار از فرمت قدیمی."""
        try:
            if not self.path.is_file():
                return
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return

            # ---- فرمت جدید ----
            if "scores" in data and isinstance(data["scores"], list):
                self.scores = [
                    ScoreEntry.from_dict(d)
                    for d in data["scores"] if isinstance(d, dict)
                ]

            # ---- مهاجرت از فرمت قدیمی ----
            elif "high_score" in data:
                old_high = int(data.get("high_score", 0))
                old_wave = int(data.get("best_wave", 0))
                old_date = str(data.get("last_played", ""))
                if old_high > 0:
                    self.scores = [ScoreEntry(
                        score=old_high,
                        wave=old_wave,
                        ship="phantom",
                        date=old_date,
                    )]

            self.total_games = int(data.get("total_games", 0))
            self.scores.sort(key=lambda e: e.score, reverse=True)
            self.scores = self.scores[:self.MAX_ENTRIES]
        except Exception as exc:
            print(f"[HighScore] Failed to load: {exc}")

    def save(self) -> None:
        """ذخیره‌ی جدول در فایل JSON."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "scores": [e.to_dict() for e in self.scores],
                "total_games": self.total_games,
            }
            with self.path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[HighScore] Failed to save: {exc}")

    # ─────────────────────────────────────────────────────────────────────

    def submit(self, score: int, wave: int, ship: str) -> tuple[bool, int]:
        """
        ثبت یک بازی جدید.

        برمی‌گرداند:
            (is_new_record, rank)
            rank از ۱ شروع می‌شه. اگه جزو تاپ نبود، rank=0 برمی‌گرده.
        """
        self.total_games += 1
        entry = ScoreEntry(
            score=int(score),
            wave=int(wave),
            ship=str(ship),
            date=datetime.now().isoformat(timespec="seconds"),
        )
        self.scores.append(entry)
        self.scores.sort(key=lambda e: e.score, reverse=True)
        self.scores = self.scores[:self.MAX_ENTRIES]

        rank = 0
        for i, e in enumerate(self.scores):
            if e is entry:
                rank = i + 1
                break

        is_new_record = (rank == 1)
        self.save()
        return is_new_record, rank

    # ─────────────────────────────────────────────────────────────────────
    #  خواص
    # ─────────────────────────────────────────────────────────────────────

    @property
    def high_score(self) -> int:
        return self.scores[0].score if self.scores else 0

    @property
    def best_wave(self) -> int:
        return max((e.wave for e in self.scores), default=0)

    @property
    def is_empty(self) -> bool:
        return not self.scores

    def clear(self) -> None:
        """پاک کردن کامل جدول (اختیاری، برای تنظیمات)."""
        self.scores.clear()
        self.total_games = 0
        self.save()


__all__ = ["HighScoreStore", "ScoreEntry"]