from fastapi import FastAPI, Request
import uvicorn
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = FastAPI()

# 設定 LINE API
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_SECRET")

if not LINE_ACCESS_TOKEN or not LINE_SECRET:
    raise ValueError("請確認環境變數 LINE_ACCESS_TOKEN 和 LINE_SECRET 是否正確設定！")

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)

@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        return {"message": "Invalid signature"}, 400
    return {"message": "OK"}

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    reply_text = event.message.text  # 取得使用者輸入的文字
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))  # 預設為 8080，確保 Cloud Run 正確運行
    uvicorn.run(app, host="0.0.0.0", port=port)