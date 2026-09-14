"""
Social Sentiment Velocity & X (Twitter) Chatter Tracker.
Monitors real-time retail chatter, mention surges, and sentiment velocity
across Twitter/X, Reddit (r/IndianStreetBets, r/IndiaInvestments), and financial search streams.
"""

import os
import re
import json
import logging
import subprocess
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))

TWITTER_CLI_PATH = r"C:\Users\HP\.agent-reach-venv\Scripts\twitter.exe"

BULLISH_KEYWORDS = [
    "breakout", "target", "rally", "surge", "multibagger", "order", "contract",
    "profit", "growth", "high", "upgrade", "outperform", "dividend", "approval",
    "beat", "upper circuit", "accumulate", "undervalued", "fii buying", "dii buying",
    "support", "reversal", "expansion", "bullish"
]

BEARISH_KEYWORDS = [
    "breakdown", "slump", "crash", "dump", "sell", "loss", "decline", "probe",
    "investigation", "penalty", "downgrade", "debt", "fraud", "scam", "notice",
    "plunge", "miss", "lower circuit", "panic", "fined", "sebi", "overvalued",
    "resistance", "weak", "bearish"
]


def _score_text(text: str) -> int:
    """Computes simple net bullish/bearish keyword score."""
    t = text.lower()
    bull = sum(1 for kw in BULLISH_KEYWORDS if kw in t)
    bear = sum(1 for kw in BEARISH_KEYWORDS if kw in t)
    return bull - bear


def fetch_twitter_cli_posts(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches live tweets using the local Twitter CLI if TWITTER_AUTH_TOKEN is configured.
    """
    auth_token = os.getenv("TWITTER_AUTH_TOKEN", "").strip()
    if not auth_token or not os.path.exists(TWITTER_CLI_PATH):
        return []

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        query = f"{symbol} (lang:en)"
        
        # Try search first
        proc = subprocess.run(
            [TWITTER_CLI_PATH, "-c", "search", query],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=12,
            env=env
        )
        output = proc.stdout.strip() if proc.stdout else ""
        
        # Fallback to feed if search returns error or 404
        if "error:" in output or not output or proc.returncode != 0:
            proc = subprocess.run(
                [TWITTER_CLI_PATH, "-c", "feed"],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=12,
                env=env
            )
            output = proc.stdout.strip() if proc.stdout else ""

        posts = []
        if output.startswith("["):
            try:
                items = json.loads(output)
                clean_sym = symbol.replace(".NS", "").replace(".BO", "").lower()
                for item in items:
                    text = item.get("text", "")
                    if clean_sym in text.lower() or not symbol:
                        posts.append({
                            "title": text[:140],
                            "url": f"https://x.com/i/web/status/{item.get('id', '')}",
                            "source": "x_twitter_cli",
                            "author": item.get("author", "unknown"),
                            "created_at": item.get("time")
                        })
                        if len(posts) >= limit:
                            break
            except Exception as e:
                logger.warning("Failed to parse JSON array from twitter.exe: %s", str(e))
        else:
            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    posts.append({
                        "title": data.get("text", "")[:140],
                        "url": data.get("url", f"https://x.com/i/web/status/{data.get('id', '')}"),
                        "source": "x_twitter_cli",
                        "author": data.get("author", "unknown"),
                        "created_at": data.get("created_at")
                    })
                except Exception:
                    posts.append({
                        "title": line[:140],
                        "url": "",
                        "source": "x_twitter_cli",
                        "author": "unknown",
                        "created_at": None
                    })
                if len(posts) >= limit:
                    break
        return posts
    except Exception as e:
        logger.warning("Twitter CLI search error for %s: %s", symbol, str(e))
        return []


def fetch_tavily_social_posts(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches recent posts and news mentioning the symbol via Tavily API.
    """
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    try:
        query = f"{symbol} share stock target breakout site:x.com OR site:twitter.com"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": limit,
            "include_domains": ["x.com", "twitter.com"]
        }
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            headers={"Content-Type": "application/json", "User-Agent": "BharatTradeAgent/1.0"},
            data=json.dumps(payload).encode("utf-8")
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("content", "")[:200],
                    "url": r.get("url", ""),
                    "source": "tavily_x_search",
                    "published_date": r.get("published_date")
                }
                for r in results
            ]
    except Exception as e:
        logger.warning("Tavily social search error for %s: %s", symbol, str(e))
        return []


def fetch_reddit_trading_posts(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches real-time retail posts from r/IndianStreetBets via public RSS.
    """
    subreddits = ["IndianStreetBets", "IndiaInvestments"]
    posts = []
    
    clean_sym = symbol.replace(".NS", "").replace(".BO", "")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BharatTradeAgent/1.0"}

    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/search.rss?q={urllib.parse.quote(clean_sym)}&sort=new&restrict_sr=1"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                xml_data = resp.read()
                root = ET.fromstring(xml_data)
                entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                for e in entries:
                    title_elem = e.find("{http://www.w3.org/2005/Atom}title")
                    link_elem = e.find("{http://www.w3.org/2005/Atom}link")
                    title = title_elem.text if title_elem is not None else ""
                    href = link_elem.attrib.get("href", "") if link_elem is not None else ""
                    
                    posts.append({
                        "title": title,
                        "url": href,
                        "source": f"reddit_r_{sub.lower()}",
                        "author": "reddit_user"
                    })
                    if len(posts) >= limit:
                        break
        except Exception as e:
            logger.warning("Reddit RSS fetch error for %s on r/%s: %s", clean_sym, sub, str(e))
        if len(posts) >= limit:
            break

    return posts


def calculate_social_velocity(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates net sentiment score (-100 to +100), label, and volume surge status.
    """
    if not posts:
        return {
            "sentiment_score": 0.0,
            "sentiment_label": "NEUTRAL",
            "velocity_status": "STABLE",
            "velocity_spike": False,
            "total_mentions": 0,
            "bullish_count": 0,
            "bearish_count": 0
        }

    bull_count = 0
    bear_count = 0
    net_score_sum = 0

    for p in posts:
        text = f"{p.get('title', '')} {p.get('snippet', '')}"
        score = _score_text(text)
        net_score_sum += score
        if score > 0:
            bull_count += 1
        elif score < 0:
            bear_count += 1

    total_tagged = bull_count + bear_count
    if total_tagged > 0:
        ratio = (bull_count - bear_count) / total_tagged
        sentiment_score = round(ratio * 100.0, 1)
    else:
        sentiment_score = 0.0

    # Surge detection: high volume with strong conviction
    velocity_spike = len(posts) >= 6 and abs(sentiment_score) >= 25.0

    if sentiment_score >= 25.0:
        label = "BULLISH"
        status = "ACCELERATING_BULLISH" if velocity_spike else "MILDLY_BULLISH"
    elif sentiment_score <= -25.0:
        label = "BEARISH"
        status = "ACCELERATING_BEARISH" if velocity_spike else "MILDLY_BEARISH"
    else:
        label = "NEUTRAL"
        status = "STABLE"

    return {
        "sentiment_score": sentiment_score,
        "sentiment_label": label,
        "velocity_status": status,
        "velocity_spike": velocity_spike,
        "total_mentions": len(posts),
        "bullish_count": bull_count,
        "bearish_count": bear_count
    }


def get_stock_social_sentiment(symbol: str) -> Dict[str, Any]:
    """
    Fetches real-time social streams across Twitter, Tavily, and Reddit,
    aggregates results, and computes social sentiment velocity metrics.
    """
    posts = []
    sources_used = []

    # 1. Try Twitter CLI if authenticated
    tw_posts = fetch_twitter_cli_posts(symbol, limit=10)
    if tw_posts:
        posts.extend(tw_posts)
        sources_used.append("twitter_cli")

    # 2. Try Tavily X search
    tavily_posts = fetch_tavily_social_posts(symbol, limit=8)
    if tavily_posts:
        posts.extend(tavily_posts)
        sources_used.append("tavily_x_search")

    # 3. Try Reddit RSS
    reddit_posts = fetch_reddit_trading_posts(symbol, limit=8)
    if reddit_posts:
        posts.extend(reddit_posts)
        sources_used.append("reddit_rss")

    metrics = calculate_social_velocity(posts)
    now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")

    return {
        "symbol": symbol,
        "timestamp_ist": now_ist,
        "sources_used": sources_used,
        "metrics": metrics,
        "sample_posts": posts[:5]
    }


def get_watchlist_social_sentiment(symbols: List[str]) -> Dict[str, Any]:
    """
    Scans social sentiment velocity for a list of watchlist symbols.
    """
    results = {}
    for sym in symbols:
        try:
            results[sym] = get_stock_social_sentiment(sym)
        except Exception as e:
            logger.warning("Error evaluating sentiment for %s: %s", sym, str(e))
            results[sym] = {
                "symbol": sym,
                "metrics": {
                    "sentiment_score": 0.0,
                    "sentiment_label": "NEUTRAL",
                    "velocity_status": "ERROR",
                    "velocity_spike": False,
                    "total_mentions": 0
                },
                "sources_used": [],
                "sample_posts": []
            }
    return {
        "watchlist_sentiment": results,
        "analyzed_count": len(symbols)
    }
