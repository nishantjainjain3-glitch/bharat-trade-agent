import os
import pyotp
import requests
from typing import Dict, Any, List, Optional

class AngelOneClient:
    def __init__(self):
        self.api_key = os.getenv("ANGEL_API_KEY", "")
        self.client_code = os.getenv("ANGEL_CLIENT_CODE", "")
        self.pin = os.getenv("ANGEL_PIN", "")
        self.totp_key = os.getenv("ANGEL_TOTP_KEY", "")
        
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
            url = "https://apiconnect.angelbroking.com/rest/auth/partner/v1/loginByPassword"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "127.0.0.1",
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
            url = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/portfolio/v1/getAllHolding"
            headers = {
                "Authorization": f"Bearer {self.jwt_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "MAC_ADDRESS",
                "X-PrivateKey": self.api_key
            }
            res = requests.get(url, headers=headers, timeout=10)
            data = res.json()
            holdings = data.get("data", {}).get("holdings", []) if data.get("status") else []
            return {
                "mode": "LIVE",
                "account_id": self.client_code,
                "holdings": holdings,
                "status": "connected"
            }
        except Exception as e:
            return {"mode": "ERROR", "message": str(e), "holdings": []}

    def place_order(self, symbol: str, quantity: int, transaction_type: str = "BUY", order_type: str = "MARKET", price: float = 0.0) -> Dict[str, Any]:
        if not self.is_configured:
            # Paper execution
            return {
                "status": True,
                "mode": "SIMULATION",
                "order_id": f"SIM-{pyotp.random_base32()[:8]}",
                "symbol": symbol,
                "quantity": quantity,
                "transaction_type": transaction_type,
                "message": f"Paper trade executed: {transaction_type} {quantity} shares of {symbol}."
            }
            
        # Guarded Live Execution
        return {
            "status": False,
            "message": "Live order placement safety gate enabled. Verify credentials and enable LIVE_EXECUTION_ENABLED=true in .env."
        }

angel_client = AngelOneClient()
