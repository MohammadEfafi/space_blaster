from systems.collision import circles_overlap
from systems.scores import HighScoreStore, ScoreEntry


class TestScoreEntry:
    def test_roundtrip(self):
        entry = ScoreEntry(
            score=100, wave=5, ship="phantom",
            date="2024-01-15T12:00:00",
        )
        restored = ScoreEntry.from_dict(entry.to_dict())
        assert restored.score == 100
        assert restored.wave == 5
        assert restored.ship == "phantom"

    def test_date_short(self):
        entry = ScoreEntry(
            score=1, wave=1, ship="x",
            date="2024-01-15T12:00:00",
        )
        assert entry.date_short() == "2024-01-15"

    def test_date_short_empty(self):
        entry = ScoreEntry(score=1, wave=1, ship="x", date="")
        assert entry.date_short() == "—"


class TestHighScoreStore:
    def test_empty_initially(self, tmp_path):
        store = HighScoreStore(path=tmp_path / "test.json")
        assert store.is_empty
        assert store.high_score == 0
        assert store.total_games == 0

    def test_submit_new_record(self, tmp_path):
        store = HighScoreStore(path=tmp_path / "test.json")
        is_record, rank = store.submit(100, wave=1, ship="phantom")
        assert is_record is True
        assert rank == 1
        assert store.high_score == 100
        assert store.total_games == 1

    def test_submit_lower_score(self, tmp_path):
        store = HighScoreStore(path=tmp_path / "test.json")
        store.submit(500, wave=3, ship="phantom")
        is_record, rank = store.submit(100, wave=1, ship="phantom")
        assert is_record is False
        assert rank == 2
        assert store.high_score == 500

    def test_submit_top_10_limit(self, tmp_path):
        store = HighScoreStore(path=tmp_path / "test.json")
        for i in range(15):
            store.submit(i * 100, wave=1, ship="phantom")
        assert len(store.scores) == 10
        assert store.high_score == 1400

    def test_persistence(self, tmp_path):
        path = tmp_path / "test.json"
        store1 = HighScoreStore(path=path)
        store1.submit(200, wave=2, ship="phantom")
        store2 = HighScoreStore(path=path)
        assert store2.high_score == 200
        assert store2.total_games == 1

    def test_best_wave(self, tmp_path):
        store = HighScoreStore(path=tmp_path / "test.json")
        store.submit(100, wave=3, ship="phantom")
        store.submit(200, wave=7, ship="phantom")
        assert store.best_wave == 7


class TestCirclesOverlap:
    def test_overlapping(self):
        assert circles_overlap(0, 0, 10, 5, 0, 10) is True

    def test_touching(self):
        assert circles_overlap(0, 0, 10, 20, 0, 10) is True

    def test_not_overlapping(self):
        assert circles_overlap(0, 0, 5, 100, 0, 5) is False

    def test_same_center(self):
        assert circles_overlap(0, 0, 5, 0, 0, 5) is True

    def test_distant(self):
        assert circles_overlap(0, 0, 2, 100, 100, 2) is False