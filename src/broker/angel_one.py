import os
import pyotp
import requests
from typing import Dict, Any, List, Optional

NSE_SYMBOL_TOKENS = {
    "RELIANCE": "2885",
    "TCS": "11536",
    "INFY": "1594",
    "HDFCBANK": "1333",
    "ICICIBANK": "4963",
    "SBIN": "3045",
    "BHARTIARTL": "10604",
    "ITC": "1660",
    "KOTAKBANK": "1922",
    "LT": "11483",
    "AXISBANK": "5900",
    "HINDUNILVR": "1394",
    "BAJFINANCE": "317",
    "MARUTI": "10999",
    "TATAMOTORS": "3456",
    "TATASTEEL": "3499",
    "SUNPHARMA": "3351",
    "NTPC": "11630",
    "ONGC": "2475",
    "POWERGRID": "14977",
    "TITAN": "3506",
    "ASIANPAINT": "236",
    "WIPRO": "3787",
    "HCLTECH": "7229",
    "ADANIENT": "25",
    "ADANIPORTS": "15083",
    "COALINDIA": "20374",
    "JSWSTEEL": "11723",
    "NIFTYBEES": "10576",
    "BANKBEES": "10577",
    "GOLDBEES": "10578",
    "SILVERBEES": "10579"
}

TOKENS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "angel_tokens.json")
DYNAMIC_TOKENS: Dict[str, str] = {}
if os.path.exists(TOKENS_FILE):
    try:
        import json
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            DYNAMIC_TOKENS = json.load(f)
    except Exception:
        DYNAMIC_TOKENS = {}

def get_symbol_token(symbol: str) -> Optional[str]:
    clean = symbol.replace(".NS", "").replace(".BO", "").replace("-EQ", "").strip().upper()
    return DYNAMIC_TOKENS.get(clean) or NSE_SYMBOL_TOKENS.get(clean)

class AngelOneClient:
    def __init__(self):
        self.api_key = os.getenv("ANGEL_API_KEY", "")
        self.client_code = os.getenv("ANGEL_CLIENT_CODE", "")
        self.pin = os.getenv("ANGEL_PIN", "")
        self.totp_key = os.getenv("ANGEL_TOTP_KEY", "")
        self.public_ip = os.getenv("ANGEL_CLIENT_PUBLIC_IP", "152.59.151.52")
        
        self.jwt_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        
        # Check if live credentials are configured
        self.is_configured = bool(self.api_key and self.client_code and self.pin and self.totp_key)
        self.mode = "LIVE" if self.is_configured else "SIMULATION"

    def login(self) -> Dict[str, Any]:
        if not self.is_configured:
            return {
                "status": True,
                "mode": "SIMULATION",
                "message": "Running in Paper Trading mode. Real Angel One credentials not provided in .env."
            }
            
        try:
            totp = pyotp.TOTP(self.totp_key).now()
            url = "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": self.public_ip,
                "X-MACAddress": "MAC_ADDRESS",
                "X-PrivateKey": self.api_key
            }
            payload = {
                "clientcode": self.client_code,
                "password": self.pin,
                "totp": totp
            }
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            data = res.json()
            if data.get("status"):
                self.jwt_token = data["data"]["jwtToken"]
                self.refresh_token = data["data"]["refreshToken"]
                self.feed_token = data["data"]["feedToken"]
                return {"status": True, "mode": "LIVE", "message": "Angel One logged in successfully"}
            else:
                return {"status": False, "mode": "SIMULATION", "message": data.get("message", "Login failed")}
        except Exception as e:
            return {"status": False, "mode": "SIMULATION", "message": f"Connection error: {str(e)}"}

    def get_portfolio_summary(self) -> Dict[str, Any]:
        if not self.is_configured or not self.jwt_token:
            # Attempt login first if credentials exist but token expired
            if self.is_configured and not self.jwt_token:
                login_res = self.login()
                if not login_res.get("status"):
                    pass

        if not self.is_configured or not self.jwt_token:
            # Return realistic simulated portfolio for paper trading
            return {
                "mode": "SIMULATION",
                "account_id": self.client_code or "SIM-ANGEL-DEMO",
                "available_cash": 125000.00,
                "invested_amount": 75000.00,
                "total_portfolio_value": 208450.00,
                "overall_pnl": 8450.00,
                "overall_pnl_pct": 4.22,
                "holdings": [
                    {
                        "tradingsymbol": "RELIANCE-EQ",
                        "symbol": "RELIANCE.NS",
                        "quantity": 15,
                        "averageprice": 2850.00,
                        "ltp": 2960.00,
                        "pnl": 1650.00,
                        "pnl_pct": 3.86
                    },
                    {
                        "tradingsymbol": "TCS-EQ",
                        "symbol": "TCS.NS",
                        "quantity": 8,
                        "averageprice": 4100.00,
                        "ltp": 4250.00,
                        "pnl": 1200.00,
                        "pnl_pct": 3.66
                    }
                ],
                "positions": []
            }
            
        # If live credentials exist and authenticated, fetch via Angel One API
        try:
            headers = {
                "Authorization": f"Bearer {self.jwt_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": self.public_ip,
                "X-MACAddress": "MAC_ADDRESS",
                "X-PrivateKey": self.api_key
            }

            # 1. Fetch live available funds / RMS
            cash_val = 0.0
            try:
                funds_url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getRMS"
                funds_res = requests.get(funds_url, headers=headers, timeout=8)
                funds_data = funds_res.json()
                if funds_data.get("status"):
                    cash_val = float(funds_data.get("data", {}).get("net", 0.0))
            except Exception:
                pass

            # 2. Fetch live holdings
            holdings_url = "https://apiconnect.angelone.in/rest/secure/angelbroking/portfolio/v1/getAllHolding"
            res = requests.get(holdings_url, headers=headers, timeout=10)
            data = res.json()
            holdings = data.get("data", {}).get("holdings", []) if data.get("status") else []
            total_invested = sum(float(h.get("invested", 0.0) or (float(h.get("averageprice", 0.0)) * int(h.get("quantity", 0)))) for h in holdings)
            total_pnl = sum(float(h.get("profitandloss", h.get("pnl", 0.0)) or 0.0) for h in holdings)

            return {
                "mode": "LIVE",
                "account_id": self.client_code,
                "available_cash": round(cash_val, 2),
                "invested_amount": round(total_invested, 2),
                "total_portfolio_value": round(cash_val + total_invested + total_pnl, 2),
                "overall_pnl": round(total_pnl, 2),
                "overall_pnl_pct": round((total_pnl / total_invested * 100.0), 2) if total_invested > 0 else 0.0,
                "holdings": holdings,
                "status": "connected"
            }
        except Exception as e:
            return {"mode": "ERROR", "message": str(e), "holdings": []}

    def place_order(self, symbol: str, quantity: int, transaction_type: str = "BUY", order_type: str = "MARKET", price: float = 0.0) -> Dict[str, Any]:
        live_enabled = os.getenv("LIVE_EXECUTION_ENABLED", "false").lower() in ("true", "1")
        trade_locked = os.getenv("TRADE_EXECUTION_LOCKED", "true").lower() in ("true", "1")
        clean_sym = symbol.replace(".NS", "").replace(".BO", "").replace("-EQ", "").upper()
        trading_sym = f"{clean_sym}-EQ"
        
        if trade_locked or not self.is_configured or not live_enabled:
            # Paper execution (default safe mode)
            sim_id = f"SIM-{pyotp.random_base32()[:8]}"
            return {
                "status": True,
                "mode": "SIMULATION",
                "order_id": sim_id,
                "symbol": clean_sym,
                "quantity": quantity,
                "transaction_type": transaction_type,
                "order_type": order_type,
                "price": price,
                "message": f"Trade execution locked per user safety instructions. Paper simulated {transaction_type} {quantity} shares of {clean_sym} at INR {price:.2f}."
            }

        # Real Live Order Execution on Angel One SmartAPI
        if not self.jwt_token:
            self.login()

        token = get_symbol_token(clean_sym)
        if not token:
            return {
                "status": False,
                "mode": "LIVE_ERROR",
                "message": f"Order rejected: Unknown token for '{clean_sym}'. Symbol not found in Angel One instrument master."
            }

        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/placeOrder"
        headers = {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": self.public_ip,
            "X-MACAddress": "MAC_ADDRESS",
            "X-PrivateKey": self.api_key
        }
        payload = {
            "variety": "NORMAL",
            "tradingsymbol": trading_sym,
            "symboltoken": token,
            "transactiontype": transaction_type.upper(),
            "exchange": "NSE",
            "ordertype": order_type.upper(),
            "producttype": "DELIVERY",
            "duration": "DAY",
            "price": str(round(price, 2)) if order_type.upper() == "LIMIT" else "0.0",
            "squareoff": "0",
            "stoploss": "0",
            "quantity": str(quantity)
        }
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            data = res.json()
            if data.get("status"):
                order_id = data.get("data", {}).get("orderid", "LIVE-ORDER")
                return {
                    "status": True,
                    "mode": "LIVE",
                    "order_id": order_id,
                    "symbol": clean_sym,
                    "quantity": quantity,
                    "transaction_type": transaction_type,
                    "price": price,
                    "message": f"LIVE order executed on Angel One! Order ID: {order_id}"
                }
            else:
                return {
                    "status": False,
                    "mode": "LIVE_ERROR",
                    "message": data.get("message", "Angel One order rejected"),
                    "errorcode": data.get("errorcode")
                }
        except Exception as e:
            return {"status": False, "mode": "LIVE_ERROR", "message": f"Order placement failed: {str(e)}"}

angel_client = AngelOneClient()
