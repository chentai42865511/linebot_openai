from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

import openai
import os
import traceback

app = Flask(__name__)

# LINE Bot 設定
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# DeepSeek 設定
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_API_BASE")  # 如：https://api.deepseek.com/v1

# 呼叫 DeepSeek Chat 模型
def GPT_response(text):
    try:
        response = openai.ChatCompletion.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": text}],
            temperature=0.5,
            max_tokens=500
        )
        answer = response['choices'][0]['message']['content'].strip()
        return answer
    except Exception as e:
        print(traceback.format_exc())
        return "抱歉，目前無法處理您的請求。"

# LINE Webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 使用者傳送文字訊息時觸發
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    try:
        GPT_answer = GPT_response(msg)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
    except:
        print(traceback.format_exc())
        line_bot_api.reply_message(event.reply_token, TextSendMessage("系統錯誤，請稍後再試"))

# 點擊 postback 時觸發
@handler.add(PostbackEvent)
def handle_postback(event):
    print("Postback data:", event.postback.data)

# 群組新成員加入時觸發
@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name} 歡迎加入本群組！')
    line_bot_api.reply_message(event.reply_token, message)

# 啟動伺服器
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
