from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

app = Flask(__name__)

# ===== LINE Bot 設定 =====
LINE_TOKEN = os.getenv("LINE_TOKEN")  # Channel Access Token
USER_ID = os.getenv("USER_ID")        # 你的 LINE 使用者 ID
LINE_API = "https://api.line.me/v2/bot/message/push"

# ===== 發送 LINE 訊息函數 =====
def send_line(text):
    if not LINE_TOKEN or not USER_ID:
        return {"ok": False, "error": "Missing LINE_TOKEN or USER_ID"}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }

    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": text}]
    }

    try:
        res = requests.post(LINE_API, headers=headers, json=payload)
        return {"ok": res.status_code == 200, "status_code": res.status_code, "response": res.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ===== Routes =====
@app.route("/", methods=["GET"])
def home():
    return "✅ TradingView → LINE Bot 已啟動 🚀"

@app.route("/test", methods=["GET"])
def test_send():
    """手動測試 LINE 發送功能"""
    result = send_line("✅ 測試成功！LINE Bot 正常運作 🚀")
    return jsonify(result)

@app.route("/tradingview", methods=["POST"])
def tradingview_webhook():
    """TradingView Webhook 入口"""
    data = request.get_json(force=True) or {}
    print("📩 收到 TradingView 訊息：", data)

    # 處理 URL encode 或換行亂碼
    message = data.get("message", "")
    decoded = urllib.parse.unquote(message).replace("\\n", "\n")

    # 如果有 symbol + signal
    symbol = data.get("symbol")
    signal = data.get("signal")
    if symbol and signal:
        decoded = f"📈 TradingView 訊號通知\n商品：{symbol}\n訊號：{signal}"

    result = send_line(decoded)
    return jsonify({"status": "ok", "sent": decoded, "line_response": result}), 200

# ===== Flask 啟動 =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
