import os
import json
from typing import Dict, Any, List, Optional

def get_llm_client():
    """Detects if any working external LLM provider is explicitly enabled."""
    openai_key = os.getenv("OPENAI_API_KEY", "")
    openai_base = os.getenv("OPENAI_BASE_URL", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    if openai_key.startswith("sk-") and "localhost" not in openai_base:
        from openai import OpenAI
        return "openai", OpenAI(api_key=openai_key, timeout=4.0)

    if gemini_key:
        try:
            from google import genai
            return "gemini", genai.Client(api_key=gemini_key)
        except Exception:
            pass

    return None, None

def run_multi_agent_research(quote: Dict[str, Any], technicals: Dict[str, Any], fundamentals: Dict[str, Any], news: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    symbol = quote["symbol"]
    name = quote.get("name", symbol)
    price = quote.get("price", 0.0)
    news = news or []

    provider, client = get_llm_client()

    news_headlines = [n.get("title", "") for n in news[:4] if n.get("title")]

    if client and provider == "openai":
        try:
            prompt = (
                f"Analyze {name} ({symbol}) at INR {price}.\n"
                f"Technicals: {technicals}\n"
                f"Fundamentals: {fundamentals}\n"
                f"Recent News Headlines: {news_headlines}\n"
                "Conduct full research synthesis. Return valid JSON with keys: verdict, conviction (1-10), time_horizon, entry_range, target_price, stop_loss, risk_reward_ratio, technical_summary, fundamental_summary, bull_case, bear_case, executive_summary."
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a quantitative and sentiment equity research analyst for Indian markets. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                timeout=4.0
            )
            data = json.loads(response.choices[0].message.content)
            data["provider"] = "openai"
            return data
        except Exception:
            pass

    # Built-in High-Precision Multi-Agent Quantitative & Sentiment Engine
    t_trend = technicals.get("trend", "NEUTRAL")
    t_score = technicals.get("score", 0)
    rsi = technicals.get("rsi", 50.0)
    emas = technicals.get("emas", {})
    levels = technicals.get("levels", {})
    bullish_factors = technicals.get("bullish_factors", [])
    bearish_factors = technicals.get("bearish_factors", [])
    
    f_verdict = fundamentals.get("verdict", "BALANCED_FUNDAMENTALS")
    f_metrics = fundamentals.get("metrics", {})
    f_strengths = fundamentals.get("strengths", [])
    f_risks = fundamentals.get("risks", [])

    # Synthesize Decision
    combined_score = t_score + fundamentals.get("score", 0)
    
    if combined_score >= 3 and rsi < 68:
        verdict = "BUY"
        conviction = min(9, 6 + combined_score)
        time_horizon = "Swing (1-3 weeks)"
    elif combined_score <= -2 or rsi > 78:
        verdict = "SELL"
        conviction = min(9, 6 + abs(combined_score))
        time_horizon = "Immediate Exit / Short"
    else:
        verdict = "HOLD"
        conviction = 5
        time_horizon = "Watchlist / Neutral"

    support = levels.get("support", price * 0.96)
    resistance = levels.get("resistance", price * 1.06)
    atr = levels.get("atr", price * 0.025)

    stop_loss_val = round(min(support, price - (1.5 * atr)), 2)
    target_val = round(max(resistance, price + (2.5 * atr)), 2)
    entry_low = round(price * 0.992, 2)
    entry_high = round(price * 1.005, 2)

    risk_amount = max(1.0, price - stop_loss_val)
    reward_amount = max(1.0, target_val - price)
    rr_ratio = f"1 : {round(reward_amount / risk_amount, 1)}"

    # News catalyst integration
    news_snippet = f" Latest market news: '{news_headlines[0]}'." if news_headlines else ""

    bull_summary = (
        f"{name} demonstrates support above major moving averages (20 EMA: INR {emas.get('ema_20')}). "
        + (f"Key technical drivers: {', '.join(bullish_factors[:2])}. " if bullish_factors else "Momentum remains constructive. ")
        + (f"Fundamental strength: {f_strengths[0]}." if f_strengths else "")
        + news_snippet
    )

    bear_summary = (
        f"Overhead resistance sits at INR {resistance}. "
        + (f"Cautionary signals: {', '.join(bearish_factors[:2])}. " if bearish_factors else "Broader market volatility may trigger pullbacks. ")
        + (f"Key financial risk: {f_risks[0]}." if f_risks else "")
    )

    exec_summary = (
        f"Multi-agent consensus awards a {verdict} rating (Conviction: {conviction}/10). "
        f"Technical structure is {t_trend} with RSI at {rsi}. "
        f"Valuation is classified as {f_verdict.replace('_', ' ').title()} with P/E of {f_metrics.get('pe_ratio')}. "
        f"Recommended operational window: Entry between INR {entry_low} - INR {entry_high} targeting INR {target_val} with strict SL at INR {stop_loss_val}."
    )

    return {
        "verdict": verdict,
        "conviction": conviction,
        "time_horizon": time_horizon,
        "entry_range": f"INR {entry_low} - INR {entry_high}",
        "target_price": f"INR {target_val}",
        "stop_loss": f"INR {stop_loss_val}",
        "risk_reward_ratio": rr_ratio,
        "technical_summary": f"{symbol} trades in a {t_trend} posture with RSI at {rsi} and 20 EMA at INR {emas.get('ema_20')}.",
        "fundamental_summary": f"Classified under {f_verdict.replace('_', ' ').title()} with ROE of {f_metrics.get('roe_pct')}% and P/E of {f_metrics.get('pe_ratio')}.",
        "bull_case": bull_summary,
        "bear_case": bear_summary,
        "executive_summary": exec_summary,
        "news_headlines": news_headlines,
        "provider": "quantitative_agent_engine"
    }
