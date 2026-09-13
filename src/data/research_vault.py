import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

class ResearchVault:
    """
    Persistent Stock Research Vault (Hyperresearch Architecture).
    Maintains historical deep research dossiers, adversarial critique logs,
    and operational trade setups as both structured JSON and human-readable Markdown.
    """

    def __init__(self, vault_dir: Optional[str] = None):
        if vault_dir:
            self.vault_path = Path(vault_dir)
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.vault_path = base_dir / "data" / "vault"
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def _normalize_symbol(self, symbol: str) -> str:
        return symbol.upper().replace(".NS", "").replace(".BO", "").strip()

    def save_dossier(
        self,
        symbol: str,
        research: Dict[str, Any],
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        norm_sym = self._normalize_symbol(symbol)
        now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

        audit = research.get("adversarial_council_audit", {})
        math_m = audit.get("math_metrics", {})
        maker = research.get("maker_checker_audit", {})

        dossier_data = {
            "symbol": norm_sym,
            "saved_at": now_ist,
            "verdict": research.get("verdict", "HOLD"),
            "conviction": research.get("conviction", 5),
            "time_horizon": research.get("time_horizon", "Swing"),
            "entry_range": research.get("entry_range", "N/A"),
            "target_price": research.get("target_price", "N/A"),
            "stop_loss": research.get("stop_loss", "N/A"),
            "risk_reward_ratio": research.get("risk_reward_ratio", "N/A"),
            "executive_summary": research.get("executive_summary", ""),
            "technical_summary": research.get("technical_summary", ""),
            "fundamental_summary": research.get("fundamental_summary", ""),
            "bull_case": research.get("bull_case", ""),
            "bear_case": research.get("bear_case", ""),
            "sentiment_velocity": research.get("sentiment_velocity", ""),
            "news_headlines": research.get("news_headlines", []),
            "adversarial_audit": {
                "verdict": audit.get("verdict", "UNAUDITED"),
                "overall_score": audit.get("overall_audit_score", 0.0),
                "component_scores": audit.get("component_scores", {}),
                "objections": audit.get("objections", []),
                "caveats": audit.get("caveats", []),
                "forensic_bear_case": audit.get("forensic_bear_case", ""),
                "math_metrics": math_m,
                "media_analysis": audit.get("media_analysis", {})
            },
            "maker_checker_audit": maker,
            "extra_metadata": extra_metadata or {}
        }

        # 1. Write Machine-Readable JSON
        json_file = self.vault_path / f"{norm_sym}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(dossier_data, f, indent=2, ensure_ascii=False)

        # 2. Write Human-Readable Markdown Wiki Page
        md_file = self.vault_path / f"{norm_sym}.md"
        md_content = self._render_markdown_dossier(dossier_data)
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        logger.info("Saved research vault dossier for %s to %s and %s", norm_sym, json_file.name, md_file.name)
        return {
            "symbol": norm_sym,
            "status": "SAVED",
            "json_path": str(json_file),
            "md_path": str(md_file),
            "verdict": dossier_data["verdict"],
            "audit_score": audit.get("overall_audit_score", 0.0),
            "saved_at": now_ist
        }

    def get_dossier(self, symbol: str) -> Optional[Dict[str, Any]]:
        norm_sym = self._normalize_symbol(symbol)
        json_file = self.vault_path / f"{norm_sym}.json"
        if not json_file.exists():
            return None
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Error reading vault JSON for %s: %s", norm_sym, str(e))
            return None

    def get_dossier_markdown(self, symbol: str) -> Optional[str]:
        norm_sym = self._normalize_symbol(symbol)
        md_file = self.vault_path / f"{norm_sym}.md"
        if not md_file.exists():
            return None
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning("Error reading vault markdown for %s: %s", norm_sym, str(e))
            return None

    def list_dossiers(self) -> List[Dict[str, Any]]:
        results = []
        for file in self.vault_path.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    audit = data.get("adversarial_audit", {})
                    results.append({
                        "symbol": data.get("symbol", file.stem),
                        "verdict": data.get("verdict", "HOLD"),
                        "conviction": data.get("conviction", 5),
                        "overall_audit_score": audit.get("overall_score", 0.0),
                        "audit_verdict": audit.get("verdict", "UNAUDITED"),
                        "target_price": data.get("target_price", ""),
                        "stop_loss": data.get("stop_loss", ""),
                        "risk_reward_ratio": data.get("risk_reward_ratio", ""),
                        "saved_at": data.get("saved_at", ""),
                        "has_markdown": (self.vault_path / f"{file.stem}.md").exists()
                    })
            except Exception as e:
                logger.warning("Failed reading dossier list entry %s: %s", file.name, str(e))
                continue

        results.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
        return results

    def search_vault(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower().strip()
        all_dossiers = self.list_dossiers()
        if not q:
            return all_dossiers

        matched = []
        for summary in all_dossiers:
            sym = summary["symbol"].lower()
            if q in sym or q in summary.get("verdict", "").lower():
                matched.append(summary)
                continue

            full = self.get_dossier(summary["symbol"])
            if full:
                exec_s = full.get("executive_summary", "").lower()
                bull_s = full.get("bull_case", "").lower()
                bear_s = full.get("bear_case", "").lower()
                if q in exec_s or q in bull_s or q in bear_s:
                    matched.append(summary)

        return matched

    def delete_dossier(self, symbol: str) -> bool:
        norm_sym = self._normalize_symbol(symbol)
        deleted = False
        json_file = self.vault_path / f"{norm_sym}.json"
        md_file = self.vault_path / f"{norm_sym}.md"

        if json_file.exists():
            json_file.unlink()
            deleted = True
        if md_file.exists():
            md_file.unlink()
            deleted = True

        return deleted

    def _render_markdown_dossier(self, d: Dict[str, Any]) -> str:
        audit = d.get("adversarial_audit", {})
        comp = audit.get("component_scores", {})
        math_m = audit.get("math_metrics", {})
        objections = audit.get("objections", [])
        caveats = audit.get("caveats", [])
        news = d.get("news_headlines", [])

        obj_md = "\n".join(f"- ❌ **Objection**: {o}" for o in objections) if objections else "- ✅ None: No critical technical or mathematical objections raised."
        cav_md = "\n".join(f"- ⚠️ **Caveat**: {c}" for c in caveats) if caveats else "- ✅ None: Data sources and provenance verified against filings."
        news_md = "\n".join(f"- 📰 {n}" for n in news) if news else "- No fresh news headlines captured."

        return f"""# 🏛️ Research Vault Dossier: {d['symbol']}
**Last Updated**: {d.get('saved_at', 'N/A')}  
**Consensus Rating**: **{d.get('verdict', 'HOLD')}** | **Conviction**: {d.get('conviction', 5)}/10 | **Horizon**: {d.get('time_horizon', 'Swing')}

---

## ⚡ Operational Trade Boundaries
- **Entry Range**: {d.get('entry_range', 'N/A')}
- **Target Price**: {d.get('target_price', 'N/A')}
- **Stop Loss**: {d.get('stop_loss', 'N/A')}
- **Reward / Risk**: {d.get('risk_reward_ratio', 'N/A')}

---

## 🛡️ Adversarial 4-Critic Audit (Hyperresearch Architecture)
- **Audit Verdict**: `{audit.get('verdict', 'UNAUDITED')}`
- **Composite Score**: **{audit.get('overall_score', 0.0)} / 100**
- **Critic Sub-Scores**:
  - Fact & Provenance: {comp.get('fact_score', 'N/A')}/100
  - Forensic Bear Survival: {comp.get('bear_survival_score', 'N/A')}/100
  - Mathematical Rigor: {comp.get('math_score', 'N/A')}/100
  - Media Independence: {comp.get('media_independence_score', 'N/A')}/100

### Mathematical Rigor Metrics
- **Calculated R:R**: {math_m.get('reward_to_risk', 'N/A')}:1
- **Risk Per Share**: ₹{math_m.get('risk_per_share', 'N/A')}
- **Reward Per Share**: ₹{math_m.get('reward_per_share', 'N/A')}
- **Stop Buffer**: {math_m.get('stop_atr_multiple', 'N/A')}x ATR

### Critic Objections & Flags
{obj_md}

### Provenance Caveats
{cav_md}

### Forensic Bear Case
> {audit.get('forensic_bear_case', 'No severe forensic headwinds detected.')}

---

## 📋 Fundamental & Technical Synthesis
### Executive Summary
{d.get('executive_summary', 'N/A')}

### Technical Pillar
{d.get('technical_summary', 'N/A')}

### Fundamental Pillar
{d.get('fundamental_summary', 'N/A')}

### Bull Case Catalyst
{d.get('bull_case', 'N/A')}

### Bear Case Risks
{d.get('bear_case', 'N/A')}

---

## 📰 Media Coverage & Sentiment Velocity
- **Sentiment Shift**: {d.get('sentiment_velocity', 'STABLE')}
{news_md}
"""


research_vault = ResearchVault()
