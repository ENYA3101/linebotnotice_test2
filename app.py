from flask import Flask, request, jsonify
import os, requests
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


@app.route("/")
def home():
    return "✅ LINE Bot is running"


@app.route("/notify")
def notify():
    """手動測試通知"""
    msg = f"📢 群組通知：{datetime.now(ZoneInfo('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')}"
    return jsonify(send_line(msg, to_group=True))


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    接收 TradingView 的 Webhook 訊號
    支援 JSON 或純文字，原樣轉送
    """
    try:
        # 嘗試解析 JSON
        data = request.get_json(force=True, silent=True)
        if isinstance(data, dict) and data:
            message = data.get("message") or data.get("msg") or str(data)
        else:
            # 若不是 JSON，改讀純文字內容
            message = request.data.decode("utf-8").strip()

        # 安全保護：確保訊息非空
        if not message:
            message = "(TradingView 傳來空訊息)"

        # 原樣發送到 LINE 群組
        result = send_line(message, to_group=True)
        return jsonify({"ok": True, "message_sent": message, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
