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
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_TOKEN}"
}

# === API Endpoint 分開，避免混淆 ===
LINE_PUSH_API = "https://api.line.me/v2/bot/message/push"
LINE_REPLY_API = "https://api.line.me/v2/bot/message/reply"


# === Push: 扣推播額，用於 TradingView or Fallback ===
def send_line(text: str):
    """主動推播到群組（會扣推播額度）"""
    payload = {
        "to": GROUP_ID,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        r = requests.post(LINE_PUSH_API, json=payload, headers=HEADERS)
        return {"ok": True, "status": r.status_code, "response": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# === Reply: 不扣推播額，限 webhook 訊息使用 ===
def reply_line(reply_token: str, text: str):
    """replyMessage（不扣推播額度）"""
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        r = requests.post(LINE_REPLY_API, json=payload, headers=HEADERS)
        if r.status_code != 200:  # replyToken 過期 → fallback push
            print("⚠ replyToken 失效 → fallback 推播")
            return send_line(text)
        return {"ok": True, "status": r.status_code, "response": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# === UTC → 台北時間轉換 ===
def convert_utc_to_taipei(msg: str) -> str:
    match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', msg)
    if match:
        utc_str = match.group(1)
        try:
            dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
            dt_taipei = dt_utc.astimezone(ZoneInfo("Asia/Taipei"))
            taipei_str = dt_taipei.strftime("%Y-%m-%d %H:%M:%S")
            msg = msg.replace(utc_str, f"{taipei_str}")
        except Exception as e:
            print("❌ 時間轉換錯誤:", e)
    return msg


@app.route("/")
def home():
    return "✅ LINE Bot is running with reply optimization"


@app.route("/notify")
def notify():
    msg = f"📢 群組通知：{datetime.now(ZoneInfo('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')}"
    return jsonify(send_line(msg))  # /notify 手動測試仍使用推播


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    1️⃣ LINE Webhook（群組有人講話） → reply（不扣額）
    2️⃣ TradingView Webhook → push 推播
    """
    try:
        data = request.get_json(force=True, silent=True)

        # ✅ 如果是 LINE webhook event（群組聊天觸發）
        if isinstance(data, dict) and "events" in data:
            for event in data.get("events", []):
                if event.get("type") == "message":
                    reply_token = event.get("replyToken")
                    user_message = event["message"]["text"]

                    # ✅ 用 reply（免費）
                    reply_line(reply_token, f"✅ 已收到：{user_message}")
            return jsonify({"ok": True, "info": "LINE webhook reply done (不扣推播)"})

        # ✅ 如果是 TradingView webhook → 仍用 push
        if isinstance(data, dict):
            message = data.get("message") or data.get("msg") or str(data)
        else:
            message = request.data.decode("utf-8").strip()

        if not message:
            message = "(TradingView 傳來空訊息)"

        message = convert_utc_to_taipei(message)

        result = send_line(message)  # ✅ TradingView → 仍推播
        return jsonify({"ok": True, "message_sent": message, "result": result})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))