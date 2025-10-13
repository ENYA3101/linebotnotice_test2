from flask import Flask, request, jsonify
import os, requests, json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# === LINE Bot 設定 ===
LINE_TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("USER_ID")  # 只回傳到你的個人 LINE
LINE_API = "https://api.line.me/v2/bot/message/push"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_TOKEN}"
}

GROUP_RECORD_FILE = "groups.json"  # ✅ 記錄已通知的群組 ID


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
    """寫入已通知過的群組 ID"""
    with open(GROUP_RECORD_FILE, "w") as f:
        json.dump({"groups": groups}, f, ensure_ascii=False, indent=2)


def send_line(text: str):
    """發送 LINE 訊息到你的個人帳號"""
    if not LINE_TOKEN or not USER_ID:
        return {"ok": False, "error": "Missing LINE_TOKEN or USER_ID"}

    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        r = requests.post(LINE_API, json=payload, headers=HEADERS)
        return {"ok": True, "status": r.status_code, "response": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.route("/")
def home():
    return "✅ LINE Bot is running (Group ID Scanner Mode)"


@app.route("/webhook", methods=["POST"])
def webhook():
    """只抓群組 ID，一次性通知"""
    try:
        data = request.get_json(force=True, silent=True)

        if isinstance(data, dict) and "events" in data:
            events = data.get("events", [])
            for event in events:
                src = event.get("source", {})
                if src.get("type") == "group":
                    group_id = src.get("groupId")

                    # ✅ 讀取已記錄的群組
                    known_groups = load_group_list()

                    if group_id not in known_groups:
                        # ✅ 新群組 → 發給你
                        send_line(f"📢 發現新群組\nID = {group_id}")
                        known_groups.append(group_id)
                        save_group_list(known_groups)  # ✅ 寫入紀錄

            return jsonify({"ok": True, "info": "Group ID scanner complete"})

        return jsonify({"ok": False, "error": "No LINE events"})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))