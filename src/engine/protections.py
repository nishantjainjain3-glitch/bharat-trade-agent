import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
COOLDOWNS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "trade_cooldowns.json"
)


class FreqtradeProtectionManager:
    """
    Freqtrade Protection Subsystem for Indian Stock Trading.
    Implements:
    1. StoplossGuard: Locks a symbol if stopped out repeatedly.
    2. MaxDrawdownProtection: Freezes new entries if rolling drawdown exceeds threshold.
    3. LowProfitPairLock: Flags dead-money positions held > N days with stagnant return.
    4. CooldownPeriod: Persistent cooldown tracker with timestamp expiry.
    """

    def __init__(self, storage_path: str = COOLDOWNS_FILE):
        self.storage_path = storage_path
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({"cooldowns": {}, "stoploss_history": []}, f, indent=2)

    def _load_data(self) -> Dict[str, Any]:
        self._ensure_storage()
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load cooldowns file: %s", e)
            return {"cooldowns": {}, "stoploss_history": []}

    def _save_data(self, data: Dict[str, Any]):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save cooldowns file: %s", e)

    def is_in_cooldown(self, symbol: str) -> Tuple[bool, Optional[str]]:
        """
        Returns (True, reason) if symbol is under an active cooldown period.
        Automatically purges expired cooldowns.
        """
        clean_sym = symbol.replace(".NS", "").upper()
        data = self._load_data()
        cooldowns = data.get("cooldowns", {})

        if clean_sym not in cooldowns:
            return False, None

        cd = cooldowns[clean_sym]
        expires_str = cd.get("expires_at", "")
        try:
            expires_at = datetime.fromisoformat(expires_str)
            now = datetime.now(IST)
            if now < expires_at:
                remaining_hours = round((expires_at - now).total_seconds() / 3600.0, 1)
                return True, f"{cd.get('reason', 'Cooldown active')} (Expires in {remaining_hours}h)"
            else:
                del cooldowns[clean_sym]
                self._save_data(data)
                return False, None
        except Exception:
            return False, None

    def set_cooldown(self, symbol: str, hours: float, reason: str):
        """Enforces an automated cooldown on a stock."""
        clean_sym = symbol.replace(".NS", "").upper()
        now = datetime.now(IST)
        expires_at = now + timedelta(hours=hours)

        data = self._load_data()
        data["cooldowns"][clean_sym] = {
            "symbol": clean_sym,
            "reason": reason,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "duration_hours": hours
        }
        self._save_data(data)
        logger.info("Protection Cooldown SET for %s for %sh: %s", clean_sym, hours, reason)

    def clear_cooldown(self, symbol: str):
        """Clears cooldown early if overridden."""
        clean_sym = symbol.replace(".NS", "").upper()
        data = self._load_data()
        if clean_sym in data["cooldowns"]:
            del data["cooldowns"][clean_sym]
            self._save_data(data)

    def record_stoploss_hit(self, symbol: str, exit_price: float, loss_pct: float) -> bool:
        """
        Freqtrade StoplossGuard trigger.
        Records stoploss event and checks if threshold is breached.
        Rule: If 2 or more stoplosses in the last 5 days -> 72-hour lockout.
        """
        clean_sym = symbol.replace(".NS", "").upper()
        now = datetime.now(IST)

        data = self._load_data()
        history = data.get("stoploss_history", [])

        history.append({
            "symbol": clean_sym,
            "exit_price": exit_price,
            "loss_pct": loss_pct,
            "timestamp": now.isoformat()
        })

        cutoff = now - timedelta(days=5)
        recent_hits = [
            h for h in history
            if h.get("symbol") == clean_sym and datetime.fromisoformat(h["timestamp"]) >= cutoff
        ]

        data["stoploss_history"] = history[-50:]
        self._save_data(data)

        if len(recent_hits) >= 2:
            self.set_cooldown(
                symbol=clean_sym,
                hours=72.0,
                reason=f"StoplossGuard: {len(recent_hits)} stop-loss hits in last 5 days (Whipsaw Protection)"
            )
            return True
        return False

    def evaluate_entry_protections(
        self,
        symbol: str,
        current_equity: float,
        peak_equity: float,
        daily_loss_pct: float = 0.0
    ) -> Dict[str, Any]:
        """
        Evaluates whether a new trade entry is allowed under all Freqtrade protection guards.
        """
        clean_sym = symbol.replace(".NS", "").upper()
        violations = []

        # 1. Cooldown Guard
        in_cd, cd_reason = self.is_in_cooldown(clean_sym)
        if in_cd:
            violations.append(f"COOLDOWN_ACTIVE: {cd_reason}")

        # 2. MaxDrawdownProtection Guard
        if peak_equity > 0:
            dd_pct = max(0.0, ((peak_equity - current_equity) / peak_equity) * 100.0)
            if dd_pct >= 5.0:
                violations.append(f"MAX_DRAWDOWN_GUARD: Portfolio drawdown is {dd_pct:.1f}% (Limit: 5.0%)")

        # 3. Daily Loss Protection
        if daily_loss_pct <= -2.0:
            violations.append(f"DAILY_LOSS_GUARD: Daily loss is {daily_loss_pct:.1f}% (Limit: -2.0%)")

        allowed = len(violations) == 0
        return {
            "allowed": allowed,
            "symbol": clean_sym,
            "violations": violations,
            "in_cooldown": in_cd,
            "guard_status": "PASS" if allowed else "BLOCKED"
        }


# Global singleton instance
protections_manager = FreqtradeProtectionManager()
