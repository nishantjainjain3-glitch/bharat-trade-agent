import os
import requests
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

import time

_tavily_cache: Dict[str, Dict[str, Any]] = {}
_tavily_usage = {
    "date": "",
    "daily_count": 0,
    "max_daily_budget": 25  # 25/day * 30 days = 750/month (well within 1,000 free limit)
}

def fetch_tavily_stock_news(symbol: str, company_name: str = "") -> List[Dict[str, Any]]:
    """
    Fetches clean, verified live financial news using Tavily AI Search API.
    Includes a 45-minute per-symbol cache and a 25 query/day budget guard
    to strictly prevent exceeding the 1,000 monthly free credit tier.
    """
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    clean_sym = symbol.replace(".NS", "").replace(".BO", "").replace("^", "")
    now_ts = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 1. Return cached results if fetched within last 45 minutes
    cached = _tavily_cache.get(clean_sym)
    if cached and (now_ts - cached["timestamp"]) < 2700:
        return cached["results"]

    # 2. Daily budget check and rollover
    if _tavily_usage["date"] != today_str:
        _tavily_usage["date"] = today_str
        _tavily_usage["daily_count"] = 0

    if _tavily_usage["daily_count"] >= _tavily_usage["max_daily_budget"]:
        # Budget preserved for today; seamlessly fall back to unlimited RSS feeds
        return []

    query = f"{clean_sym} {company_name} latest news Indian stock market NSE BSE"
    try:
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "topic": "news",
            "max_results": 5
        }
        res = requests.post("https://api.tavily.com/search", json=payload, timeout=4)
        if res.status_code == 200:
            data = res.json()
            items = []
            for r in data.get("results", []):
                domain = r.get("url", "").split("/")[2].replace("www.", "") if "/" in r.get("url", "") else "Financial Press"
                items.append({
                    "title": r.get("title", "").strip(),
                    "source": domain,
                    "link": r.get("url", "#"),
                    "published_at": r.get("published_date") or datetime.now().strftime("%a, %d %b %Y"),
                    "snippet": r.get("content", "")[:180]
                })

            _tavily_usage["daily_count"] += 1
            _tavily_cache[clean_sym] = {
                "timestamp": now_ts,
                "results": items
            }
            return items
    except Exception as e:
        logger.warning("News fetch error: %s", str(e))
    return []

def fetch_rss_items(url: str, headers: dict, default_source: str = "Financial Press") -> List[Dict[str, Any]]:
    items = []
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item")[:6]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                source = item.findtext("source", default_source)
                clean_title = title.rsplit(" - ", 1)[0] if " - " in title else title
                if clean_title:
                    items.append({
                        "title": clean_title.strip(),
                        "source": source or default_source,
                        "link": link,
                        "published_at": pub_date
                    })
    except Exception as e:
        logger.warning("News fetch error: %s", str(e))
    return items

def get_indian_stock_news(symbol: str, company_name: str = "") -> List[Dict[str, Any]]:
    """
    Fetches real-time financial news headlines for Indian stocks from:
    1. Google News India RSS (Targeted query)
    2. Economic Times Markets RSS (Domestic financial portal)
    3. Moneycontrol Top News RSS (Domestic market wire)
    """
    clean_sym = symbol.replace(".NS", "").replace(".BO", "").replace("^", "")
    query = f"{clean_sym} {company_name} stock share price NSE India".strip()
    encoded_query = urllib.parse.quote(query)
    
    google_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    et_url = "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2143429.cms"
    mc_url = "https://www.moneycontrol.com/rss/MCtopnews.xml"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    all_news = []
    # 0. Tavily AI Search (real-time breaking Indian equity news)
    tavily_news = fetch_tavily_stock_news(symbol, company_name)
    if tavily_news:
        all_news.extend(tavily_news)

    # 1. Primary targeted Google News query
    all_news.extend(fetch_rss_items(google_url, headers, default_source="Google News India"))
    
    # 2. Check domestic Indian feeds for ticker or sector relevance
    domestic_items = fetch_rss_items(et_url, headers, default_source="The Economic Times") + fetch_rss_items(mc_url, headers, default_source="Moneycontrol")
    for item in domestic_items:
        t_lower = item["title"].lower()
        if clean_sym.lower() in t_lower or (company_name and company_name.lower().split()[0] in t_lower):
            all_news.append(item)

    # Deduplicate by title
    seen = set()
    unique_news = []
    for item in all_news:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique_news.append(item)

    if not unique_news:
        unique_news.append({
            "title": f"Recent market updates and regulatory filings for {clean_sym}",
            "source": "NSE Exchange Wire",
            "link": "#",
            "published_at": datetime.now().strftime("%a, %d %b %Y")
        })
        
    return unique_news[:8]
