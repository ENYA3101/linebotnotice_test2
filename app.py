from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ===== LINE Bot 設定（從 .env 讀取） =====
LINE_TOKEN = os.getenv("LINE_TOKEN")  # Channel Access Token
USER_ID = os.getenv("USER_ID")        # 目標接收者的 userId 或 groupId
LINE_API = "https://api.line.me/v2/bot/message/push"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_TOKEN}"
}

def send_line(text: str):
    """
    使用 push message 發送單一文字訊息到 USER_ID。
    回傳 LINE API 的 response (dict) 或錯誤字串。
    """
    if not LINE_TOKEN or not USER_ID:
        return {"ok": False, "error": "LINE_TOKEN or USER_ID not set in environment"}

    payload = {
        "to": USER_ID,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    try:
        r = requests.post(LINE_API, json=payload, headers=HEADERS, timeout=10)
        try:
            return {"status_code": r.status_code, "response": r.json()}
        except Exception:
            return {"status_code": r.status_code, "response_text": r.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "info": "Line push webhook is running"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    接收 TradingView 或其他服務的 webhook。
    支援：
      - JSON body: {"message": "..."} 或 {"symbol": "...", "signal": "..."}
      - application/x-www-form-urlencoded (form) with message field
      - raw text body
    會把解析後的文字透過 LINE push message 傳出。
    """
    data = {}
    decoded = None

    # 1) 嘗試解析 JSON
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}

    # 2) 若是表單資料（或 query string）
    if not data and request.form:
        data = request.form.to_dict()

    # 3) 若以上都空，嘗試取 raw text
    if not data:
        raw = request.get_data(as_text=True)
        if raw:
            # TradingView 有時會直接傳 plain text
            data = {"message": raw.strip()}

    # 組合要發送的文字（優先順序）
    # 支援常見欄位：message / text / symbol+signal / custom
    if isinstance(data, dict):
        # 1) raw message 或 text 欄位
        if data.get("message"):
            decoded = data.get("message")
        elif data.get("text"):
            decoded = data.get("text")
        # 2) symbol + signal (結構化)
        elif data.get("symbol") and data.get("signal"):
            decoded = f"📈 TradingView 訊號通知\n商品：{data.get('symbol')}\n訊號：{data.get('signal')}"
        # 3) 其他成對欄位（舉例：ticker + close）
        elif data.get("ticker") and data.get("close"):
            decoded = f"📈 {data.get('ticker')} 現價 {data.get('close')}\n原始訊息：{data}"
        # 4) 若傳來整個 JSON，直接把它序列化
        else:
            try:
                import json as _json
                decoded = "Webhook JSON: " + _json.dumps(data, ensure_ascii=False)
            except Exception:
                decoded = str(data)

    # 如果真的還沒得到要傳的字串，回傳錯誤
    if not decoded:
        return jsonify({"status": "error", "reason": "no message detected", "received": data}), 400

    # 發送到 LINE
    result = send_line(decoded)
    return jsonify({"status": "ok", "sent": decoded, "line_response": result}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
