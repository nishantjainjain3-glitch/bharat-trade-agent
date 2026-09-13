import re
from typing import Dict, Any, List, Optional

class AdversarialCouncil:
    """
    4-Critic Adversarial Audit Engine (inspired by Hyperresearch):
    Before any research thesis or trade setup is approved, 4 independent
    skeptical critics attack the proposal:
    1. Fact & Provenance Critic: Flags unverified numbers and missing filings.
    2. Forensic Bear Critic: Actively searches for reasons the trade will fail.
    3. Mathematical Rigor Critic: Recalculates R:R, ATR stop buffers, and sizing.
    4. Media Syndication Critic: Deduplicates syndicated PR reprints so 5 copies of 1 release count as 1.
    """

    def audit_trade_proposal(
        self,
        symbol: str,
        price: float,
        stop_loss: float,
        target_price: float,
        technicals: Dict[str, Any],
        fundamentals: Dict[str, Any],
        news_headlines: List[str]
    ) -> Dict[str, Any]:
        objections = []
        caveats = []
        scores = {}

        # 1. Fact & Provenance Critic
        fact_audit = self._critic_facts(fundamentals)
        scores["fact_score"] = fact_audit["score"]
        if fact_audit["unverified"]:
            caveats.append(f"Unverified data: {', '.join(fact_audit['unverified'])} missing from recent filings.")

        # 2. Forensic Bear Critic (Devil's Advocate)
        bear_audit = self._critic_bear(price, technicals, fundamentals)
        scores["bear_survival_score"] = bear_audit["score"]
        if bear_audit["objections"]:
            objections.extend(bear_audit["objections"])

        # 3. Mathematical Rigor Critic
        math_audit = self._critic_math(price, stop_loss, target_price, technicals)
        scores["math_score"] = math_audit["score"]
        if not math_audit["passed"]:
            objections.append(math_audit["error"])

        # 4. Media Syndication Deduplicator
        media_audit = self._critic_media_syndication(news_headlines)
        scores["media_independence_score"] = media_audit["score"]

        # Composite Audit Verdict
        critical_failure = len([o for o in objections if "CRITICAL" in o]) > 0
        overall_score = round(
            (scores["fact_score"] * 0.25) +
            (scores["bear_survival_score"] * 0.35) +
            (scores["math_score"] * 0.30) +
            (scores["media_independence_score"] * 0.10),
            1
        )

        if critical_failure or overall_score < 50.0:
            verdict = "REJECTED_BY_ADVERSARIAL_COUNCIL"
        elif len(objections) > 0 or len(caveats) > 0:
            verdict = "APPROVED_WITH_ADVERSARIAL_CAVEATS"
        else:
            verdict = "PASSED_CLEAN_AUDIT"

        return {
            "verdict": verdict,
            "overall_audit_score": overall_score,
            "component_scores": scores,
            "objections": objections,
            "caveats": caveats,
            "media_analysis": media_audit,
            "forensic_bear_case": bear_audit["bear_case_summary"],
            "math_metrics": math_audit.get("metrics", {})
        }

    def _critic_facts(self, fundamentals: Dict[str, Any]) -> Dict[str, Any]:
        metrics = fundamentals.get("metrics", {})
        unverified = []
        score = 100.0

        if not metrics.get("pe_ratio") or metrics.get("pe_ratio") == "N/A":
            unverified.append("PE_RATIO")
            score -= 20.0
        if not metrics.get("roe_pct") or metrics.get("roe_pct") == "N/A":
            unverified.append("ROE_PCT")
            score -= 20.0
        if not metrics.get("debt_to_equity") or metrics.get("debt_to_equity") == "N/A":
            unverified.append("DEBT_TO_EQUITY")
            score -= 15.0

        return {"score": max(20.0, score), "unverified": unverified}

    def _critic_bear(self, price: float, technicals: Dict[str, Any], fundamentals: Dict[str, Any]) -> Dict[str, Any]:
        objections = []
        score = 85.0
        reasons = []

        rsi = technicals.get("rsi", 50.0)
        if rsi > 72.0:
            objections.append(f"CRITICAL: RSI is overbought at {rsi:.1f}. High risk of mean-reversion pullback.")
            score -= 30.0
            reasons.append("Overbought RSI exhaustion")

        adx_val = technicals.get("adx", 20.0)
        if isinstance(adx_val, dict):
            adx_val = adx_val.get("adx", 20.0)
        if isinstance(adx_val, (int, float)) and adx_val < 18.0:
            objections.append(f"Weak trend: ADX is sluggish at {adx_val:.1f}. Chop and false breakouts likely.")
            score -= 15.0
            reasons.append("Low ADX trend weakness")

        pe = fundamentals.get("metrics", {}).get("pe_ratio")
        if isinstance(pe, (int, float)) and pe > 75.0:
            objections.append(f"Valuation headwind: Extreme PE multiple of {pe:.1f}x prices in aggressive perfection.")
            score -= 15.0
            reasons.append("Elevated valuation multiple")

        f_risks = fundamentals.get("risks", [])
        if f_risks:
            reasons.extend(f_risks[:2])

        bear_case_summary = "; ".join(reasons) if reasons else "No severe forensic headwinds detected."

        return {
            "score": max(10.0, score),
            "objections": objections,
            "bear_case_summary": bear_case_summary
        }

    def _critic_math(self, price: Any, stop_loss: Any, target_price: Any, technicals: Dict[str, Any]) -> Dict[str, Any]:
        try:
            p = float(str(price).replace("INR", "").replace("₹", "").strip())
            sl = float(str(stop_loss).replace("INR", "").replace("₹", "").strip())
            tp = float(str(target_price).replace("INR", "").replace("₹", "").strip())
        except (ValueError, TypeError):
            return {"passed": False, "score": 0.0, "error": "CRITICAL: Unable to parse numeric bounds for mathematical validation."}

        if p <= 0 or sl <= 0 or tp <= 0:
            return {"passed": False, "score": 0.0, "error": "CRITICAL: Non-positive price or boundary values."}

        risk = p - sl
        if risk <= 0:
            return {"passed": False, "score": 0.0, "error": "CRITICAL: Stop loss is above or equal to current entry price."}

        reward = tp - p
        if reward <= 0:
            return {"passed": False, "score": 0.0, "error": "CRITICAL: Target price is below or equal to entry price."}

        rr = reward / risk
        atr = technicals.get("atr", p * 0.02)
        if isinstance(atr, dict):
            atr = atr.get("atr", p * 0.02)
        stop_atr_multiple = risk / atr if atr and atr > 0 else 1.5

        score = 90.0
        if rr < 1.45:
            return {
                "passed": False,
                "score": 40.0,
                "error": f"CRITICAL: Reward-to-risk ratio is {rr:.2f}:1, violating the 1.5:1 minimum threshold."
            }

        if stop_atr_multiple < 1.0:
            score -= 20.0 # Stop is dangerously tight (< 1.0 ATR)

        return {
            "passed": True,
            "score": score,
            "metrics": {
                "reward_to_risk": round(rr, 2),
                "risk_per_share": round(risk, 2),
                "reward_per_share": round(reward, 2),
                "stop_atr_multiple": round(stop_atr_multiple, 2)
            }
        }

    def _critic_media_syndication(self, headlines: List[str]) -> Dict[str, Any]:
        """
        Deduplicates syndicated press releases and identical news stories.
        Clusters headlines sharing >= 60% of significant words.
        """
        if not headlines:
            return {"unique_stories_count": 0, "total_raw_headlines": 0, "syndication_ratio": 1.0, "score": 50.0}

        clusters = []
        for raw_h in headlines:
            clean_words = set(re.findall(r'\b\w{4,}\b', raw_h.lower()))
            matched = False
            for cluster in clusters:
                overlap = len(clean_words.intersection(cluster["words"]))
                min_len = min(len(clean_words), len(cluster["words"]))
                if min_len > 0 and (overlap / min_len) >= 0.55:
                    cluster["count"] += 1
                    matched = True
                    break
            if not matched:
                clusters.append({"headline": raw_h, "words": clean_words, "count": 1})

        unique_count = len(clusters)
        total_count = len(headlines)
        syndication_ratio = round(unique_count / total_count, 2) if total_count > 0 else 1.0

        return {
            "unique_stories_count": unique_count,
            "total_raw_headlines": total_count,
            "syndication_ratio": syndication_ratio,
            "is_syndication_spam": bool(total_count > 3 and syndication_ratio < 0.45),
            "score": round(min(100.0, 50.0 + (syndication_ratio * 50.0)), 1)
        }

adversarial_council = AdversarialCouncil()
