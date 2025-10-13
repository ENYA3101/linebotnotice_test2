from flask import Flask, request, jsonify
import os, requests, re
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

app = Flask(__name__)

# === LINE Bot 設定 ===
LINE_TOKEN = os.getenv("LINE_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")  # TradingView 群組推播用
LINE_API = "https://api.line.me/v2/bot/message/push"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_TOKEN}"
}


def send_line(text: str):
    """發送 LINE 訊息到群組"""
    if not LINE_TOKEN or not GROUP_ID:
        return {"ok": False, "error": "Missing LINE_TOKEN or GROUP_ID"}

    payload = {
        "to": GROUP_ID,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        r = requests.post(LINE_API, json=payload, headers=HEADERS)
        return {"ok": True, "status": r.status_code, "response": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def convert_utc_to_taipei(msg: str) -> str:
    """自動轉 UTC → 台北時間"""
    match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', msg)
    if match:
        utc_str = match.group(1)
        try:
            dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
            dt_taipei = dt_utc.astimezone(ZoneInfo("Asia/Taipei"))
            taipei_str = dt_taipei.strftime("%Y-%m-%d %H:%M:%S")
            msg = msg.replace(utc_str, f"{taipei_str} (台北時間)")
        except Exception as e:
            print("❌ 時間轉換錯誤:", e)
    return msg


@app.route("/")
def home():
    return "✅ LINE Bot is running"


@app.route("/notify")
def notify():
    msg = f"📢 群組通知：{datetime.now(ZoneInfo('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')}"
    return jsonify(send_line(msg))


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    1️⃣ TradingView Webhook → 發訊息到 LINE 群組
    2️⃣ LINE 官方 Webhook → 僅處理 message 類型事件
    """
    try:
        data = request.get_json(force=True, silent=True)

        # 先檢查是否是 LINE webhook event
        if isinstance(data, dict) and "events" in data:
            events = data.get("events", [])
            for event in events:
                # 只處理 message 類型
                if event.get("type") != "message":
                    continue
                # 如果是 message，可以在此擴充處理，例如回覆、分析等等
            return jsonify({"ok": True, "info": "LINE webhook processed (message only)"})

        # 如果是 TradingView webhook
        if isinstance(data, dict):
            message = data.get("message") or data.get("msg") or str(data)
        else:
            message = request.data.decode("utf-8").strip()

        if not message:
            message = "(TradingView 傳來空訊息)"

        # 時區轉換
        message = convert_utc_to_taipei(message)

        result = send_line(message)
        return jsonify({"ok": True, "message_sent": message, "result": result})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))