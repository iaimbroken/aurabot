import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
CLIENT_ID = os.getenv("TRADOVATE_CLIENT_ID")
CLIENT_SECRET = os.getenv("TRADOVATE_CLIENT_SECRET")
USERNAME = os.getenv("TRADOVATE_USERNAME")
PASSWORD = os.getenv("TRADOVATE_PASSWORD")
ENV = os.getenv("TRADOVATE_ENV", "demo")  # change to "live" for production

AUTH_URL = f"https://{ENV}.tradovateapi.com/auth/accesstokenrequest"
ORDER_URL = f"https://{ENV}.tradovateapi.com/v1/order/placeorder"
POSITION_URL = f"https://{ENV}.tradovateapi.com/v1/position/find"

# === Flask app setup ===
app = Flask(__name__)
access_token = None
account_id = 1427850  # Your live Tradovate account ID

# === Authenticate to Tradovate ===
def authenticate():
    global access_token
    payload = {
        "name": USERNAME,
        "password": PASSWORD,
        "appId": "AuraBot",
        "appVersion": "1.0",
        "cid": int(CLIENT_ID),
        "sec": CLIENT_SECRET
    }
    res = requests.post(AUTH_URL, json=payload)
    res.raise_for_status()
    access_token = res.json()["accessToken"]
    print("✅ Authenticated with Tradovate")

# === Place a market order ===
def place_order(direction):
    headers = {"Authorization": f"Bearer {access_token}"}
    max_spend = 200  # USD
    margin_per_contract = 50
    qty = max(1, int(max_spend / margin_per_contract))

    order = {
        "accountId": account_id,
        "action": "Buy" if direction == "BUY" else "Sell",
        "symbol": "MESM5",
        "orderQty": qty,
        "orderType": "Market",
        "isAutomated": True
    }

    try:
        res = requests.post(ORDER_URL, headers=headers, json=order)
        res.raise_for_status()
        print(f"✅ {direction} order placed | Qty: {qty}")
    except Exception as e:
        print(f"❌ Error placing {direction} order: {e}")

# === Close open MES position ===
def close_open_position():
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        res = requests.get(f"{POSITION_URL}/{account_id}", headers=headers)
        res.raise_for_status()
        positions = res.json()

        for pos in positions:
            if pos["symbol"] == "MESM5" and pos["netPos"] != 0:
                direction = "Sell" if pos["netPos"] > 0 else "Buy"
                qty = abs(pos["netPos"])
                order = {
                    "accountId": account_id,
                    "action": direction,
                    "symbol": "MESM5",
                    "orderQty": qty,
                    "orderType": "Market",
                    "isAutomated": True
                }
                r = requests.post(ORDER_URL, headers=headers, json=order)
                r.raise_for_status()
                print(f"✅ EXIT: Closed {qty} contracts with {direction}")
                return
        print("ℹ️ No open MESM5 position to close.")
    except Exception as e:
        print(f"❌ Error checking or closing position: {e}")

# === Webhook route ===
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        signal = request.data.decode('utf-8').strip().upper()
        print(f"📨 Signal received: {signal}")

        if "BUY" in signal:
            place_order("BUY")
        elif "SELL" in signal:
            place_order("SELL")
        elif "EXIT" in signal:
            close_open_position()
        else:
            return jsonify({"error": "Unknown signal"}), 400

        return jsonify({"status": "OK"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Start server ===
if __name__ == '__main__':
    authenticate()
    app.run(port=5000)
