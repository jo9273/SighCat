import uvicorn
import os
import time
from collections import defaultdict
from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI  # 最新 OpenAI v1.64.0 的寫法

###############################################################################
#                               基本設定區                                    #
###############################################################################

app = FastAPI()

# 讀取環境變數
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_SECRET = os.getenv("LINE_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = os.getenv("PORT")

# 檢查必備環境變數
if not LINE_ACCESS_TOKEN or not LINE_SECRET or not OPENAI_API_KEY or not PORT:
    raise ValueError("請確認環境變數 LINE_ACCESS_TOKEN, LINE_SECRET, OPENAI_API_KEY, PORT 皆已設定！")

# 初始化 LINE 和 OpenAI
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)
client = OpenAI(api_key=OPENAI_API_KEY)  #最新 OpenAI API 初始化方式

###############################################################################
#                         對話歷史與清理機制 (後端資料)                         #
###############################################################################

# conversation_history：字典，key = user_id，value = list of messages (system/user/assistant)
conversation_history = defaultdict(list)

# conversation_timestamps：紀錄 user_id 最後一次互動時間，用於清理長期未互動的使用者
conversation_timestamps = {}

# 對話歷史設定
MAX_HISTORY_LENGTH = 30   # 包含 system 訊息在內，最多保留 30 則
EXPIRATION_TIME = 7200    # 120 分鐘未互動則刪除對話 (7200秒=2小時)

def cleanup_old_conversations():
    """
    刪除超過 EXPIRATION_TIME（120 分鐘）未互動的使用者對話紀錄
    避免記憶體無限制增長
    """
    current_time = time.time()
    users_to_delete = [
        user for user, last_time in conversation_timestamps.items()
        if current_time - last_time > EXPIRATION_TIME
    ]

    for user in users_to_delete:
        # 刪除對話紀錄與時間戳
        del conversation_history[user]
        del conversation_timestamps[user]

def preserve_system_message_and_trim(user_messages):
    """
    永遠保留最前面的 system 訊息，不論對話多長，
    其餘只保留 MAX_HISTORY_LENGTH - 1 的 user/assistant 訊息。
    """
    if not user_messages:
        return
    if user_messages[0]["role"] != "system":
        user_messages.insert(0, {
            "role": "system",
            "content": 
                "你是一個智慧型職場助手，主要回覆語言為繁體中文，具備以下五個核心功能：\n"
                "1. **語言翻譯**：將用戶輸入的外語翻譯為繁體中文，請明確標示來源語言。\n"
                "2. **圖文摘要**：摘要用戶提供的文章或內容。\n"
                "3. **語音轉文字**（目前以文字方式模擬）。\n"
                "4. **台灣勞基法查詢**：根據台灣最新法規提供準確的建議。\n"
                "5. **職場心靈輔導**：像朋友一樣陪伴使用者，允許抱怨和幽默，最終給予正向回應。\n\n"
                "**請根據使用者輸入，自動判斷適合的回應方式**。\n"
                "**禁止要求個人資料，如姓名、身分證字號、電話等**。\n"
        })

    # 第0筆應該是 system 訊息
    system_msg = user_messages[0]
    others = user_messages[1:]
    
    # 如果超過 (MAX_HISTORY_LENGTH - 1)，就裁切
    if len(others) > (MAX_HISTORY_LENGTH - 1):
        others = others[-(MAX_HISTORY_LENGTH - 1):]
    
    # 重新組合
    user_messages.clear()
    user_messages.append(system_msg)
    user_messages.extend(others)

def split_message(text, max_length=5000):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

###############################################################################
#                           健康檢查 (GET /)                                   #
###############################################################################
@app.get("/")
async def health_check():
    return {"status": "running"}

###############################################################################
#                         LINE Webhook 入口 (POST /webhook)                    #
###############################################################################
@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()  # 取得 request 內容
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        # 簽名驗證失敗，代表並非從 LINE Server 來的請求
        return {"message": "Invalid signature"}, 400
    return {"message": "OK"}

###############################################################################
#                       LINE 訊息事件處理 (MessageEvent, TextMessage)          #
###############################################################################
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    # 取得使用者 ID
    user_id = event.source.user_id

    # 取得使用者輸入內容
    user_text = event.message.text

    # 1. 清理過期對話
    cleanup_old_conversations()

    # 2. 更新使用者最後互動時間
    conversation_timestamps[user_id] = time.time()

    # 3. 若使用者沒有歷史紀錄，初始化 system 訊息
    if not conversation_history[user_id]:
        conversation_history[user_id].append({
            "role": "system",
            "content":
                "你是一個智慧型職場助手，主要回覆語言為繁體中文，具備以下五個核心功能：\n"
                "1. **語言翻譯**：將用戶輸入的外語翻譯為繁體中文，請明確標示來源語言。\n"
                "2. **圖文摘要**：摘要用戶提供的文章或內容。\n"
                "3. **語音轉文字**（目前以文字方式模擬）。\n"
                "4. **台灣勞基法查詢**：根據台灣最新法規提供準確的建議。\n"
                "5. **職場心靈輔導**：像朋友一樣陪伴使用者，允許抱怨和幽默，最終給予正向回應。\n\n"
                "**請根據使用者輸入，自動判斷適合的回應方式**。\n"
                "**禁止要求個人資料，如姓名、身分證字號、電話等**。\n"
        })

    # 4. 加入使用者輸入到對話紀錄
    conversation_history[user_id].append({
        "role": "user",
        "content": user_text
    })

    # 5. 呼叫 OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",          # 選用 GPT-4 or 3.5-turbo ...
            temperature=0.7,         # 創造力參數
            messages=conversation_history[user_id]
        )
        reply_text = response["choices"][0]["message"]["content"] 

        # 把 AI 回應加到對話中
        conversation_history[user_id].append({
            "role": "assistant",
            "content": reply_text
        })

        # 6. 保留 system 訊息，並裁切對話長度
        preserve_system_message_and_trim(conversation_history[user_id])

    except Exception as e:
        if "rate limit" in str(e).lower():
            reply_text = "請求過多，請稍後再試。"
        elif "authentication" in str(e).lower():
            reply_text = "API 金鑰錯誤，請檢查你的 OpenAI API 設定。"
        else:
            reply_text = "很抱歉，我目前無法處理您的需求，請稍後再試。"
        print(f"OpenAI API Error: {e}")

    # 7. 將回應切分成多段，避免超過 LINE 單則訊息限制
    try:
        messages = [TextSendMessage(text=part) for part in split_message(reply_text)]
        line_bot_api.reply_message(event.reply_token, messages)
    except Exception as e:
        print(f"LINE 回應失敗: {e}")

###############################################################################
#                        主程式入口 (port=int(PORT))                           #
###############################################################################
if __name__ == "__main__":
    print(f"伺服器啟動, 監聽 PORT={PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=int(PORT))