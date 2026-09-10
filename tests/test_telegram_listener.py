import unittest
import asyncio
from unittest.mock import patch
from src.notifications.telegram_listener import TelegramBotListener

class TestTelegramListener(unittest.TestCase):
    def setUp(self):
        self.listener = TelegramBotListener()
        self.listener.authorized_chat_id = "12345678"

    def test_configuration_check(self):
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat_id"}):
            l = TelegramBotListener()
            self.assertTrue(l.is_configured())

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            l2 = TelegramBotListener()
            self.assertFalse(l2.is_configured())

    @patch("src.notifications.telegram_listener.send_telegram_text")
    def test_handle_help_command(self, mock_send):
        asyncio.run(self.listener.handle_command("12345678", "/help"))
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        self.assertIn("Bharat Trade Agent", args[0])

    @patch("src.notifications.telegram_listener.send_telegram_text")
    def test_handle_funds_command(self, mock_send):
        asyncio.run(self.listener.handle_command("12345678", "/funds"))
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        self.assertIn("Funds & Margin Status", args[0])

    @patch("src.notifications.telegram_listener.send_telegram_text")
    def test_handle_kill_command(self, mock_send):
        asyncio.run(self.listener.handle_command("12345678", "/kill"))
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        self.assertIn("KILL SWITCH", args[0])

    @patch("src.notifications.telegram_listener.send_telegram_text")
    def test_handle_portfolio_command(self, mock_send):
        asyncio.run(self.listener.handle_command("12345678", "/portfolio"))
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        self.assertIn("Portfolio", args[0])

    @patch("src.notifications.telegram_listener.send_telegram_text")
    def test_handle_autotrade_command(self, mock_send):
        asyncio.run(self.listener.handle_command("12345678", "/autotrade on"))
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        self.assertIn("AUTONOMOUS TRADING ENABLED", args[0])

        asyncio.run(self.listener.handle_command("12345678", "/autotrade off"))
        self.assertEqual(mock_send.call_count, 2)

    @patch("src.notifications.telegram_listener.send_telegram_text")
    def test_handle_buy_command_usage(self, mock_send):
        asyncio.run(self.listener.handle_command("12345678", "/buy"))
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        self.assertIn("Usage", args[0])

if __name__ == "__main__":
    unittest.main()
