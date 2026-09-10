import unittest
from unittest.mock import patch, MagicMock

from src.notifications.daily_briefings import (
    build_morning_briefing,
    build_evening_report,
    DailyBriefingScheduler
)


class TestDailyBriefings(unittest.TestCase):
    def test_build_morning_briefing_content(self):
        briefing = build_morning_briefing()
        self.assertIn("MORNING BRIEFING", briefing)
        self.assertIn("Global & Benchmark Cues", briefing)
        self.assertIn("Account Snapshot", briefing)
        self.assertIn("Multi-Asset Tactical Battle Plan", briefing)
        self.assertIn("Risk Mandate", briefing)

    def test_build_evening_report_content(self):
        report = build_evening_report()
        self.assertIn("EVENING REPORT", report)
        self.assertIn("Day Closing Financials", report)
        self.assertIn("Holdings Status", report)
        self.assertIn("System Status & Health", report)

    def test_scheduler_initial_state(self):
        scheduler = DailyBriefingScheduler()
        self.assertFalse(scheduler.is_running)
        self.assertIsNone(scheduler.last_morning_sent_date)
        self.assertIsNone(scheduler.last_evening_sent_date)


if __name__ == "__main__":
    unittest.main()