@app.route("/webhook", methods=["POST"])
def webhook():
    """
    ✅ 支援 2 種來源：
    1. TradingView Webhook -> 推送訊息到 LINE 群組
    2. LINE Bot 事件 Webhook -> 取得 groupId / userId
    """
    try:
        data = request.get_json(force=True, silent=True)
        print("🔥 收到 Webhook 原始資料：", data)  # Debug 用

        # ✅ 如果是 LINE 官方 Bot webhook 事件（有 events）
        if isinstance(data, dict) and "events" in data:
            events = data.get("events", [])
            for event in events:
                src = event.get("source", {})
                if src.get("type") == "group":
                    group_id = src.get("groupId")
                    print(f"✅ LINE 群組事件，Group ID = {group_id}")
                elif src.get("type") == "user":
                    user_id = src.get("userId")
                    print(f"👤 LINE 私聊事件，User ID = {user_id}")
            return jsonify({"ok": True, "info": "LINE webhook processed"})

        # ✅ 如果是 TradingView Webhook（無 events）
        if isinstance(data, dict):
            message = data.get("message") or data.get("msg") or str(data)
        else:
            message = request.data.decode("utf-8").strip()

        if not message:
            message = "(TradingView 傳來空訊息)"

        result = send_line(message, to_group=True)
        return jsonify({"ok": True, "message_sent": message, "result": result})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
