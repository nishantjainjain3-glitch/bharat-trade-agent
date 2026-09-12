import os
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class IPGuard:
    """
    Monitors the system's outbound public IP address.
    Indian home broadband connections (Airtel, Jio, etc.) rotate dynamic IPs.
    Angel One SmartAPI requires the exact whitelisted IP.
    This guard auto-detects changes, updates runtime configs, and dispatches alerts.
    """
    def __init__(self):
        self.last_detected_ip: Optional[str] = None
        self._env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

    def get_current_public_ip(self, timeout: int = 5) -> str:
        """Fetches current external public IP from reliable lookup services."""
        endpoints = [
            "https://api.ipify.org?format=json",
            "https://ifconfig.me/all.json"
        ]
        for url in endpoints:
            try:
                r = requests.get(url, timeout=timeout)
                if r.status_code == 200:
                    data = r.json()
                    ip = data.get("ip") or data.get("ip_addr")
                    if ip:
                        self.last_detected_ip = str(ip).strip()
                        return self.last_detected_ip
            except Exception:
                continue

        try:
            r = requests.get("https://checkip.amazonaws.com", timeout=timeout)
            if r.status_code == 200:
                self.last_detected_ip = r.text.strip()
                return self.last_detected_ip
        except Exception:
            pass

        return self.last_detected_ip or "unknown"

    def check_and_sync_ip(self, notify_telegram: bool = True) -> Dict[str, Any]:
        """
        Compares detected outbound IP against ANGEL_CLIENT_PUBLIC_IP in .env.
        If different, updates .env and triggers an alert.
        """
        current_ip = self.get_current_public_ip()
        configured_ip = os.getenv("ANGEL_CLIENT_PUBLIC_IP", "").strip()

        if current_ip == "unknown" or not current_ip:
            return {
                "status": "ERROR",
                "current_ip": current_ip,
                "configured_ip": configured_ip,
                "matches": False,
                "synced": False,
                "message": "Unable to detect public IP from lookup providers."
            }

        matches = (current_ip == configured_ip)

        if not matches:
            logger.warning("IP Guard: Public IP changed! Detected: %s, Configured: %s", current_ip, configured_ip)
            os.environ["ANGEL_CLIENT_PUBLIC_IP"] = current_ip
            synced = self._update_env_file(current_ip)

            try:
                from src.broker.angel_one import angel_client
                angel_client.public_ip = current_ip
            except Exception:
                pass

            if notify_telegram:
                self._send_ip_change_alert(old_ip=configured_ip, new_ip=current_ip)

            return {
                "status": "IP_ROTATED",
                "current_ip": current_ip,
                "old_ip": configured_ip,
                "matches": False,
                "synced": synced,
                "message": f"IP changed to {current_ip}. Updated in .env. Register this IP in SmartAPI portal."
            }

        return {
            "status": "OK",
            "current_ip": current_ip,
            "configured_ip": configured_ip,
            "matches": True,
            "synced": True,
            "message": "Outbound IP matches registered Angel One configuration."
        }

    def _update_env_file(self, new_ip: str) -> bool:
        if not os.path.exists(self._env_file):
            return False
        try:
            with open(self._env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            found = False
            for line in lines:
                if line.startswith("ANGEL_CLIENT_PUBLIC_IP="):
                    new_lines.append(f"ANGEL_CLIENT_PUBLIC_IP={new_ip}\n")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                new_lines.append(f"ANGEL_CLIENT_PUBLIC_IP={new_ip}\n")

            with open(self._env_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            return True
        except Exception as e:
            logger.error("Failed to update .env with new IP: %s", e)
            return False

    def _send_ip_change_alert(self, old_ip: str, new_ip: str):
        try:
            from src.notifications.telegram import send_telegram_text
            msg = (
                f"🌐 *ANGEL ONE IP ROTATION DETECTED*\n\n"
                f"• Previous IP: `{old_ip or 'None'}`\n"
                f"• Current Outbound IP: *`{new_ip}`*\n\n"
                f"⚠️ *Action Required for Live Orders:*\n"
                f"Your ISP rotated your IP. Please log into `smartapi.angelbroking.com`, edit your app, and whitelist IP `{new_ip}` to enable live trading."
            )
            send_telegram_text(msg)
        except Exception as e:
            logger.error("Failed to send IP Telegram alert: %s", e)

ip_guard = IPGuard()
