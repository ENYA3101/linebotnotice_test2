from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+ 支援
import re
import json

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
    if not LINE_TOKEN or not USER_ID:
        return {"ok": False, "error": "LINE_TOKEN or USER_ID not set in environment"}

    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        r = requests.post(LINE_API, json=payload, headers=HEADERS, timeout=10)
        try:
            return {"status_code": r.status_code, "response": r.json()}
        except Exception:
            return {"status_code": r.status_code, "response_text": r.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def convert_to_taiwan_time(utc_time_str: str) -> str:
    try:
        utc_time = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))
        taiwan_time = utc_time.astimezone(ZoneInfo("Asia/Taipei"))
        return taiwan_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return utc_time_str

def extract_time_from_message(text: str) -> str | None:
    """
    從字串中抓時間，支援 TradingView style: '時間=2025-10-13T05:00:00Z'
    """
    match = re.search(r'時間[=:]\s*([\d\-T\:Z]+)', text)
    if match:
        return match.group(1)
    return None

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "info": "Line push webhook is running"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = {}
    decoded = None

    # 1) 嘗試解析 JSON
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}

    # 2) 若是表單資料
    if not data and request.form:
        data = request.form.to_dict()

    # 3) 若以上都空，嘗試取 raw text
    if not data:
        raw = request.get_data(as_text=True)
        if raw:
            data = {"message": raw.strip()}

    # 組合要發送的文字
    if isinstance(data, dict):
        if data.get("message"):
            decoded = data.get("message")
        elif data.get("text"):
            decoded = data.get("text")
        elif data.get("symbol") and data.get("signal"):
            decoded = f"📈 TradingView 訊號通知\n商品：{data.get('symbol')}\n訊號：{data.get('signal')}"
        elif data.get("ticker") and data.get("close"):
            decoded = f"📈 {data.get('ticker')} 現價 {data.get('close')}\n原始訊息：{json.dumps(data, ensure_ascii=False)}"
        else:
            decoded = "Webhook JSON: " + json.dumps(data, ensure_ascii=False)

        # ✅ 1) 優先檢查 time 欄位
        taiwan_time = None
        if data.get("time"):
            taiwan_time = convert_to_taiwan_time(data.get("time"))
        else:
            # 2) 嘗試從訊息字串抓時間
            time_str = extract_time_from_message(decoded)
            if time_str:
                taiwan_time = convert_to_taiwan_time(time_str)

        if taiwan_time:
            decoded += f"\n🕒 時間（台灣）：{taiwan_time}"
        else:
            # 3) 若都沒有，就用接收時間
            now = datetime.now(ZoneInfo("Asia/Taipei"))
            decoded += f"\n🕒 收到時間（台灣）：{now.strftime('%Y-%m-%d %H:%M:%S')}"

    if not decoded:
        return jsonify({"status": "error", "reason": "no message detected", "received": data}), 400

    # 發送到 LINE
    result = send_line(decoded)
    return jsonify({"status": "ok", "sent": decoded, "line_response": result}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
