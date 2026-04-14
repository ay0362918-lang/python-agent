from fastapi import FastAPI, Request, HTTPException
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY, SELL
import os
import requests
import py_clob_client.http_helpers.helpers as helpers

PROXY = {
    "http": "http://brd-customer-hl_7fd945c2-zone-residential_proxy1-country-uk:6o7yof0w641d@brd.superproxy.io:33335",
    "https": "http://brd-customer-hl_7fd945c2-zone-residential_proxy1-country-uk:6o7yof0w641d@brd.superproxy.io:33335"
}

class ProxiedSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.proxies.update(PROXY)

helpers.Session = ProxiedSession

app = FastAPI()

# =========================
# ENV VARIABLES
# =========================
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Builder creds (IMPORTANT)
BUILDER_API_KEY = os.getenv("BUILDER_API_KEY")
BUILDER_API_SECRET = os.getenv("BUILDER_API_SECRET")
BUILDER_API_PASSPHRASE = os.getenv("BUILDER_API_PASSPHRASE")

HOST = "https://clob.polymarket.com"
CHAIN_ID = 137

if not PRIVATE_KEY:
    raise Exception("PRIVATE_KEY missing")

# =========================
# INIT CLIENT
# =========================
client = ClobClient(
    HOST,
    key=PRIVATE_KEY,
    chain_id=CHAIN_ID
)

# 👇 THIS IS CRITICAL
# Create API creds using builder signing
api_creds = client.create_or_derive_api_creds()

# Re-init with creds (REQUIRED)
client = ClobClient(
    HOST,
    key=PRIVATE_KEY,
    chain_id=CHAIN_ID,
    creds=api_creds
)

print("✅ Polymarket client initialized")

# =========================
# ROUTES
# =========================

@app.get("/")
def health():
    return {
        "status": "LIVE TRADING READY",
        "chain": "Polygon",
        "mode": "LIVE"
    }


@app.post("/trade")
async def trade(req: Request):
    try:
        body = await req.json()

        token_id = body.get("market_id")
        side_raw = body.get("side")
        price = float(body.get("price"))
        size = float(body.get("size"))

        if not token_id:
            raise HTTPException(status_code=400, detail="Missing market_id")

        if side_raw not in ["BUY", "SELL"]:
            raise HTTPException(status_code=400, detail="Invalid side")

        if not (0.01 <= price <= 0.99):
            raise HTTPException(status_code=400, detail="Invalid price")

        if size <= 0:
            raise HTTPException(status_code=400, detail="Invalid size")

        side = BUY if side_raw == "BUY" else SELL

        print(f"🚀 Executing trade: {token_id} | {side_raw} | {price} | ${size}")

        order = client.create_and_post_order(
            OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=side
            )
        )

        return {
            "status": "SUCCESS",
            "mode": "LIVE",
            "order_id": str(order),
            "details": {
                "market_id": token_id,
                "side": side_raw,
                "price": price,
                "size": size
            }
        }

    except Exception as e:
        print("❌ Trade error:", str(e))
        return {
            "status": "FAILED",
            "mode": "LIVE",
            "error": str(e)
        }
