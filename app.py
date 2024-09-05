from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os
import random
import time
import ast  # テキストファイルから辞書をインポートするために使用

# 環境変数からトークンを取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai.api_key = OPENAI_API_KEY

app = Flask(__name__)
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ユーザーごとのメッセージ履歴を保存するためのメモリ
user_memory = {}

def load_questions_from_file(file_path):
    """テキストファイルから辞書をインポートする関数"""
    with open(file_path, 'r', encoding='utf-8') as file:
        data = file.read()
        questions_dict = ast.literal_eval(data)  # テキストを辞書に変換
    return questions_dict

# 質問辞書のロード
questions_dict = load_questions_from_file('questions.txt')

def get_openai_response(user_id, user_message):
    """OpenAI APIを使用して応答を生成する（メモリを活用）"""
    if user_id not in user_memory:
        user_memory[user_id] = []

    # ユーザーのメッセージをメモリに追加
    user_memory[user_id].append({"role": "user", "content": user_message})

    # OpenAIのAPIリクエストを作成する際にメモリの内容を使用
    response = openai.ChatCompletion.create(
        model="gpt-4",  # 最新モデルを使用
        messages=[
            {"role": "system", "content": "あなたは落ち着いていて、親切な女性です。人を褒めるのが得意で、包容力のある女性です。すべての応答は日本語で行ってください。"},
        ] + user_memory[user_id],  # システムメッセージの後にメモリを追加
        max_tokens=150
    )

    # OpenAIの応答をメモリに追加
    assistant_message = response.choices[0].message['content'].strip()
    user_memory[user_id].append({"role": "assistant", "content": assistant_message})

    return assistant_message

def pick_random_question():
    """q1からq200のランダムな質問を選ぶ"""
    random_key = random.choice(list(questions_dict.keys()))
    return questions_dict[random_key]

@app.route("/callback", methods=['POST'])
def callback():
    # LINE Botからのリクエストを処理
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id

    # 特定のメッセージに応じた処理
    if user_message == "またね":
        # ChatGPTに会話を終了するメッセージを生成させる
        reply_message = get_openai_response(user_id, "会話を終了したいです。")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_message)
        )
        user_memory.pop(user_id, None)  # ユーザーのメモリを削除
        return
    elif user_message == "やっほー":
        # ChatGPTに挨拶のメッセージを生成させる
        greeting_message = get_openai_response(user_id, "挨拶を返してください。")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=greeting_message)
        )

        # 0秒から1800秒（30分）までのランダムな遅延時間を設定
        delay_seconds = random.randint(0, 1800)
        
        # ランダムな時間だけ待機
        time.sleep(delay_seconds)
        
        # ランダムな質問を選んで送信
        random_question = pick_random_question()
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=random_question)
        )
        return

    # OpenAIのAPIを使って応答を生成
    reply_message = get_openai_response(user_id, user_message)
    
    # 0秒から1800秒（30分）までのランダムな遅延時間を設定
    delay_seconds = random.randint(0, 1800)
    
    # ランダムな時間だけ待機
    time.sleep(delay_seconds)
    
    # ユーザーに応答を送信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_message)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
