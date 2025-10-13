from flask import Flask, request, jsonify
import os, requests, re
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

app = Flask(__name__)

# === LINE Bot 設定 ===
LINE_TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("USER_ID")
GROUP_ID = os.getenv("GROUP_ID")
LINE_API = "https://api.line.me/v2/bot/message/push"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_TOKEN}"
}


# ===== LINE 推送函數 =====
def send_line(text: str, to_group=False):
    """發送 LINE 訊息給群組或個人"""
    target = GROUP_ID if to_group else USER_ID
    if not LINE_TOKEN or not target:
        return {"ok": False, "error": "Missing LINE_TOKEN or target ID"}

    payload = {
        "to": target,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        r = requests.post(LINE_API, json=payload, headers=HEADERS)
        return {"ok": True, "status": r.status_code, "response": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ===== UTC → 台灣時間轉換函數 =====
def convert_utc_to_taipei(msg: str) -> str:
    """
    偵測 ISO8601 UTC 時間 (例：2025-10-13T07:31:00Z)
    轉換成台北時間 (例：2025-10-13 15:31:00)
    """
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


# ===== 首頁測試 =====
@app.route("/")
def home():
    return "✅ LINE Bot is running"


# ===== 手動通知測試 =====
@app.route("/notify")
def notify():
    msg = f"📢 群組通知：{datetime.now(ZoneInfo('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')}"
    return jsonify(send_line(msg, to_group=True))


# ===== 通用 Webhook (TradingView + LINE事件) =====
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    ✅ 支援 2 種來源：
    1. TradingView Webhook → 自動轉台灣時間 + 推送到 LINE 群組
    2. LINE Bot 事件 Webhook → 印出 groupId / userId
    """
    try:
        data = request.get_json(force=True, silent=True)
        print("🔥 收到 Webhook 原始資料：", data)  # Debug 用

        # ====== LINE 官方事件 ======
        if isinstance(data, dict) and "events" in data:
            events = data.get("events", [])
            for event in events:
                src = event.get("source", {})
                if src.get("type") == "group":
                    group_id = src.get("groupId")
                    print(f"✅ LINE 群組事件：Group ID = {group_id}")
                elif src.get("type") == "user":
                    user_id = src.get("userId")
                    print(f"👤 LINE 私聊事件：User ID = {user_id}")
            return jsonify({"ok": True, "info": "LINE webhook processed"})

        # ====== TradingView Webhook ======
        if isinstance(data, dict):
            message = data.get("message") or data.get("msg") or str(data)
        else:
            message = request.data.decode("utf-8").strip()

        if not message:
            message = "(TradingView 傳來空訊息)"

        # 自動轉換時間
        message = convert_utc_to_taipei(message)

        result = send_line(message, to_group=True)
        return jsonify({"ok": True, "message_sent": message, "result": result})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ===== 主程式 =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))