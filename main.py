import uvicorn
import os
import json
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 建立 FastAPI 應用
app = FastAPI()

# 讀取環境變數
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_SECRET")

# 環境變數檢查
if not LINE_ACCESS_TOKEN or not LINE_SECRET:
    raise ValueError("x 環境變數 LINE_ACCESS_TOKEN 和 LINE_SECRET 未設定，請確認 Cloud Run 變數設定！")

# 初始化 LINE Bot API
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# v 健康檢查 API（Cloud Run 需要 `GET /`）
@app.get("/")
async def health_check():
    return {"status": "running"}

# v LINE Webhook API（接收 `POST /webhook`）
@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        return {"message": "Invalid signature"}, 400
    return {"message": "OK"}

# v LINE 訊息事件處理
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    reply_text = event.message.text  # 取得使用者輸入的文字
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是: {reply_text}"))

# v 確保程式監聽 Cloud Run 提供的 `PORT`
if __name__ == "__main__":
    print(f"🚀 伺服器啟動中，監聽 PORT={PORT}")  # 除錯訊息
    uvicorn.run(app, host="0.0.0.0", port=int(PORT))