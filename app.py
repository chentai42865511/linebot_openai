from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, MessageEvent, TextMessage
import openai
import os
import traceback
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv()

# ---------------------------------------------
# 初始化 Flask
# ---------------------------------------------
app = Flask(__name__)

# ---------------------------------------------
# 1) LINE Bot 設定
# ---------------------------------------------
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise ValueError("請設定 CHANNEL_ACCESS_TOKEN 與 CHANNEL_SECRET 環境變數")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ---------------------------------------------
# 2) DeepSeek 設定
# ---------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")  # DeepSeek 服務

if not OPENAI_API_KEY:
    raise ValueError("請設定 OPENAI_API_KEY 環境變數")

openai.api_key = OPENAI_API_KEY
openai.api_base = OPENAI_API_BASE

# ---------------------------------------------
# 3) DeepSeek API 呼叫函式
# ---------------------------------------------
def GPT_response(user_text: str) -> str:
    """呼叫 DeepSeek API 並回傳回答"""
    try:
        print("[DEBUG] Sending to DeepSeek:", user_text)
        
        # 呼叫 DeepSeek API
        response = openai.ChatCompletion.create(
            model="deepseek-chat",  # 使用 DeepSeek Chat 模型
            messages=[{"role": "user", "content": user_text}],
            temperature=0.5,
            max_tokens=500
        )
        
        print("[DEBUG] Raw response:", response)
        answer = response['choices'][0]['message']['content'].strip()
        return answer
    except Exception as e:
        print("[ERROR] GPT_response Exception:\n", traceback.format_exc())
        return "抱歉，目前無法處理您的請求。"

# ---------------------------------------------
# 4) Flask Webhook 入口
# ---------------------------------------------
@app.route("/callback", methods=["POST"])
def callback() -> str:
    """LINE 官方會把訊息 POST 到這裡"""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    app.logger.info("Request body: %s", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid Signature Error")
        abort(400)
    except Exception as e:
        app.logger.error(f"General Error: {str(e)}")
        abort(400)

    return "OK"

# ---------------------------------------------
# 5) LINE 文字訊息事件
# ---------------------------------------------
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event: MessageEvent) -> None:
    user_msg = event.message.text
    print("[LINE] User message:", user_msg)

    answer = GPT_response(user_msg)
    print("[LINE] GPT answer:", answer)

    try:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=answer))
    except Exception:
        print("[ERROR] Reply Exception:\n", traceback.format_exc())

# ---------------------------------------------
# 6) 主程式入口
# ---------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[INFO] Starting app on port {port} ...")
    print("LINE Access Token:", CHANNEL_ACCESS_TOKEN[:10] + "..." if CHANNEL_ACCESS_TOKEN else "None")
    print("OpenAI Base URL:", openai.api_base)
    app.run(host="0.0.0.0", port=port)
    
