from flask import Flask, request, jsonify
import os, requests, re, json
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

app = Flask(__name__)

# === LINE Bot 設定 ===
LINE_TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("USER_ID")
GROUP_ID = os.getenv("GROUP_ID")  # TradingView 群組推播用
LINE_API = "https://api.line.me/v2/bot/message/push"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_TOKEN}"
}

GROUP_RECORD_FILE = "groups.json"  # ✅ 用來記錄已通知的群組 ID


def load_group_list():
    """讀取已紀錄的群組 ID"""
    if not os.path.exists(GROUP_RECORD_FILE):
        return []
    try:
        with open(GROUP_RECORD_FILE, "r") as f:
            data = json.load(f)
            return data.get("groups", [])
    except:
        return []


def save_group_list(groups):
    """寫入群組 ID"""
    with open(GROUP_RECORD_FILE, "w") as f:
        json.dump({"groups": groups}, f, ensure_ascii=False, indent=2)


def send_line(text: str, to_group=False, target_override=None):
    """發送 LINE 訊息到群組或個人"""
    target = target_override if target_override else (GROUP_ID if to_group else USER_ID)
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
    return jsonify(send_line(msg, to_group=True))


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        print("🔥 收到 Webhook 原始資料：", data)

        # =============== 🎯 LINE 官方 Webhook (抓群組ID) ===============
        if isinstance(data, dict) and "events" in data:
            events = data.get("events", [])
            for event in events:
                src = event.get("source", {})
                if src.get("type") == "group":
                    group_id = src.get("groupId")
                    print(f"✅ LINE 群組事件：Group ID = {group_id}")

                    # ✅ 讀取已記錄的群組 ID
                    known_groups = load_group_list()
                    if group_id not in known_groups:
                        # ✅ 首次偵測 → 回傳群組 ID 到 USER_ID
                        send_line(f"📢 偵測到新群組\nID = {group_id}", target_override=USER_ID)
                        known_groups.append(group_id)
                        save_group_list(known_groups)  # ✅ 寫入紀錄

            return jsonify({"ok": True, "info": "LINE webhook processed"})

        # =============== 📈 TradingView Webhook ===============
        if isinstance(data, dict):
            message = data.get("message") or data.get("msg") or str(data)
        else:
            message = request.data.decode("utf-8").strip()

        if not message:
            message = "(TradingView 傳來空訊息)"

        # ✅ 時區轉換
        message = convert_utc_to_taipei(message)

        result = send_line(message, to_group=True)
        return jsonify({"ok": True, "message_sent": message, "result": result})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))