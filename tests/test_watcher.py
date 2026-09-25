import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from microscope_watcher import Config, EmailConfig, Mailer, Watcher, human_bytes


class RecordingMailer(Mailer):
    def __init__(self):
        self.messages = []

    def send(self, subject, body):
        self.messages.append((subject, body))


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.folder = self.root / "images"
        self.folder.mkdir()
        self.time = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        self.mailer = RecordingMailer()
        self.config = Config(
            microscope_name="Scope A",
            watch_folder=self.folder,
            recursive=True,
            check_interval_seconds=60,
            daily_report_interval_hours=24,
            state_file=self.root / "state.json",
            log_file=self.root / "watcher.log",
            email=EmailConfig(
                "smtp.test", 587, "starttls", "", "PASSWORD", "", "a@test", ("b@test",), 5
            ),
        )

    def tearDown(self):
        self.temp.cleanup()

    def clock(self):
        return self.time

    def watcher(self):
        return Watcher(self.config, self.mailer, self.clock)

    def test_first_check_establishes_baseline_without_warning(self):
        (self.folder / "first.tif").write_bytes(b"image")
        self.watcher().check_once()
        subjects = [subject for subject, _ in self.mailer.messages]
        self.assertFalse(any("WARNING" in subject for subject in subjects))
        self.assertTrue(any("DAILY REPORT" in subject for subject in subjects))

    def test_stall_repeated_warning_and_recovery(self):
        (self.folder / "first.tif").write_bytes(b"image")
        watcher = self.watcher()
        watcher.check_once()
        self.mailer.messages.clear()

        self.time += timedelta(minutes=1)
        watcher.check_once()
        self.assertIn("[WARNING]", self.mailer.messages[-1][0])

        self.time += timedelta(minutes=1)
        watcher.check_once()
        self.assertEqual(2, sum("WARNING" in subject for subject, _ in self.mailer.messages))

        self.time += timedelta(minutes=1)
        (self.folder / "second.tif").write_bytes(b"image")
        watcher.check_once()
        self.assertIn("[RECOVERED]", self.mailer.messages[-1][0])

    def test_does_not_warn_before_a_full_interval(self):
        watcher = self.watcher()
        watcher.check_once()
        self.mailer.messages.clear()
        self.time += timedelta(seconds=30)
        watcher.check_once()
        self.assertFalse(any("WARNING" in subject for subject, _ in self.mailer.messages))

    def test_daily_report_is_not_repeated_before_24_hours(self):
        watcher = self.watcher()
        watcher.check_once()
        self.mailer.messages.clear()
        self.time += timedelta(hours=23)
        (self.folder / "new.tif").write_bytes(b"x")
        watcher.check_once()
        self.assertFalse(any("DAILY REPORT" in subject for subject, _ in self.mailer.messages))

        self.time += timedelta(hours=1)
        watcher.check_once()
        self.assertTrue(any("DAILY REPORT" in subject for subject, _ in self.mailer.messages))

    def test_state_is_valid_json(self):
        self.watcher().check_once()
        state = json.loads(self.config.state_file.read_text(encoding="utf-8"))
        self.assertIn("last_check_at", state)

    def test_human_bytes(self):
        self.assertEqual("1.0 GiB", human_bytes(1024**3))


if __name__ == "__main__":
    unittest.main()
