from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import json

load_dotenv()

app = Flask(__name__)

# ===== LINE Bot 設定 =====
LINE_TOKEN = os.getenv("LINE_TOKEN")  # Channel Access Token
LINE_API = "https://api.line.me/v2/bot/message/push"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_TOKEN}"
}

# 用來存抓到的群組 ID
GROUP_ID = None

def send_line(text: str, to_id: str):
    payload = {"to": to_id, "messages": [{"type": "text", "text": text}]}
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
    match = re.search(r'時間[=:]\s*([\d\-T\:Z]+)', text)
    if match:
        return match.group(1)
    return None

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "info": "Line push webhook is running"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    global GROUP_ID
    data = request.get_json(silent=True) or {}
    decoded = None

    # 抓訊息內容
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

    # 時間轉台灣
    taiwan_time = None
    if data.get("time"):
        taiwan_time = convert_to_taiwan_time(data.get("time"))
    else:
        t = extract_time_from_message(decoded)
        if t:
            taiwan_time = convert_to_taiwan_time(t)
    if taiwan_time:
        decoded += f"\n🕒 時間（台灣）：{taiwan_time}"
    else:
        now = datetime.now(ZoneInfo("Asia/Taipei"))
        decoded += f"\n🕒 收到時間（台灣）：{now.strftime('%Y-%m-%d %H:%M:%S')}"

    # ✅ 自動抓群組 ID
    if not GROUP_ID and data.get("events"):
        for event in data["events"]:
            source = event.get("source", {})
            if source.get("type") == "group":
                GROUP_ID = source.get("groupId")
                print("抓到 groupId:", GROUP_ID)

    if not GROUP_ID:
        # 如果還沒抓到群組 ID，只回傳訊息，不推送
        return jsonify({"status": "ok", "note": "還沒抓到群組 ID", "message": decoded}), 200

    # 發送到抓到的群組
    result = send_line(decoded, GROUP_ID)
    return jsonify({"status": "ok", "sent": decoded, "line_response": result}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
