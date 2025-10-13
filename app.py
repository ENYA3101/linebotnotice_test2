from flask import Flask, request, jsonify
import os, requests
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

app = Flask(__name__)

# LINE Bot 設定
LINE_TOKEN = os.getenv("LINE_TOKEN")
USER_ID = os.getenv("USER_ID")
GROUP_ID = os.getenv("GROUP_ID")
LINE_API = "https://api.line.me/v2/bot/message/push"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LINE_TOKEN}"
}

def send_line(text: str, to_group=False):
    target = GROUP_ID if to_group else USER_ID
    if not LINE_TOKEN or not target:
        return {"ok": False, "error": "Missing LINE_TOKEN or target ID"}
    
    payload = {
        "to": target,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        r = requests.post(LINE_API, json=payload, headers=HEADERS)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.route("/")
def home():
    return "LINE Bot is running"

@app.route("/notify")
def notify():
    msg = f"📢 群組通知：{datetime.now(ZoneInfo('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')}"
    return jsonify(send_line(msg, to_group=True))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
