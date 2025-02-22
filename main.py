import uvicorn
import os
import json
from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = FastAPI()

# 從環境變數讀取
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_SECRET")
PORT = os.getenv("PORT")  # 必須從環境變數取得，不能預設 8080

# 檢查必備環境變數
if not LINE_ACCESS_TOKEN or not LINE_SECRET:
    raise ValueError("環境變數 LINE_ACCESS_TOKEN 或 LINE_SECRET 未設定!")
if not PORT:
    raise ValueError("環境變數 PORT 未設定，Cloud Run 無法注入 PORT!")

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# 健康檢查 (GET /)
@app.get("/")
async def health_check():
    return {"status": "running"}

# 接收 LINE Webhook (POST /webhook)
@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        return {"message": "Invalid signature"}, 400
    return {"message": "OK"}

# 處理文字訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    reply_text = event.message.text
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"你說的是: {reply_text}")
    )

# 確保監聽 Cloud Run 提供的 PORT
if __name__ == "__main__":
    print(f"伺服器啟動, 監聽 PORT={PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=int(PORT))