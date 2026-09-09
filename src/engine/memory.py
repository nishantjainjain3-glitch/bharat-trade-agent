import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

IST = timezone(timedelta(hours=5, minutes=30))

class AgentMemoryJournal:
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.storage_dir = os.path.join(base_dir, "data")
            self.storage_path = os.path.join(self.storage_dir, "journal.json")
        else:
            self.storage_path = storage_path
            self.storage_dir = os.path.dirname(storage_path)

        os.makedirs(self.storage_dir, exist_ok=True)
        self.entries: List[Dict[str, Any]] = []
        self._load()
        if not self.entries:
            self._seed_initial_entries()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
            except Exception:
                self.entries = []

    def _save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.entries[-200:], f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _seed_initial_entries(self):
        now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
        self.entries = [
            {
                "id": 1,
                "timestamp": now_str,
                "category": "GENESIS",
                "title": "Automaton Protocol Initialized",
                "content": "Autonomous trading agent activated with capital preservation laws and dynamic survival tiers.",
                "metadata": {"version": "2.0.0", "capital": 125000.0}
            },
            {
                "id": 2,
                "timestamp": now_str,
                "category": "CONSTITUTION",
                "title": "Trading Laws Ratified",
                "content": "5 articles locked: 1.5% max risk per trade, mandatory hard stop-loss, macro trend alignment, minimum 1:1.5 R:R, and immutable logging.",
                "metadata": {"articles_count": 5}
            }
        ]
        self._save()

    def record_entry(
        self,
        category: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        entry = {
            "id": len(self.entries) + 1,
            "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
            "category": category.upper(),
            "title": title,
            "content": content,
            "metadata": metadata or {}
        }
        self.entries.append(entry)
        self._save()
        return entry

    def record_reflection(
        self,
        symbol: str,
        outcome: str,
        pnl_pct: float,
        rationale: str
    ) -> Dict[str, Any]:
        """Records an autonomous self-critique on trade execution or setup."""
        is_win = pnl_pct > 0
        critique = (
            f"Trade completed on {symbol} with {pnl_pct:+.2f}% return. "
            f"Verdict: {outcome}. Analysis: {rationale}."
        )
        return self.record_entry(
            category="REFLECTION",
            title=f"Self-Critique: {symbol} ({'+' if is_win else ''}{pnl_pct:.2f}%)",
            content=critique,
            metadata={"symbol": symbol, "pnl_pct": pnl_pct, "outcome": outcome}
        )

    def get_recent_entries(self, limit: int = 15) -> List[Dict[str, Any]]:
        return list(reversed(self.entries[-limit:]))

memory_journal = AgentMemoryJournal()
