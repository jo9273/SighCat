import os
import uvicorn
import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv()

# 取得 LINE API Key
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_SECRET")

# 初始化 FastAPI 應用
app = FastAPI()

# LINE Messaging API 的回應 URL
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

# 根目錄路由（測試用）
@app.get("/")
async def root():
    return {"message": "LINE Chatbot Server is running!"}

# 接收 LINE Webhook 事件
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    events = body.get("events", [])

    for event in events:
        if event["type"] == "message" and "text" in event["message"]:
            reply_token = event["replyToken"]
            user_message = event["message"]["text"]

            # 回應相同的訊息（Echo Bot）
            send_text_message(reply_token, user_message)

    return {"status": "ok"}

# 傳送訊息到 LINE 使用者
def send_text_message(reply_token, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(LINE_REPLY_URL, headers=headers, json=payload)

# 啟動 FastAPI 伺服器
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)