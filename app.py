from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os

# 環境変数からトークンを取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 環境変数が設定されていない場合はエラーを出力
if not all([LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, OPENAI_API_KEY]):
    raise EnvironmentError("必要な環境変数が設定されていません。LINE_CHANNEL_ACCESS_TOKEN、LINE_CHANNEL_SECRET、OPENAI_API_KEYを確認してください。")

openai.api_key = OPENAI_API_KEY

app = Flask(__name__)
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ユーザーごとのメッセージ履歴を保存するためのメモリ
user_memory = {}

def get_openai_response(user_id, user_message):
    """OpenAI APIを使用して応答を生成する（メモリを活用）"""
    if user_id not in user_memory:
        user_memory[user_id] = []

    # ユーザーのメッセージをメモリに追加
    user_memory[user_id].append({"role": "user", "content": user_message})

    try:
        # 利用可能なモデルを指定
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini-2024-07-18",  # 利用可能なモデル名に変更
            messages=[
                {"role": "system", "content": "あなたの名前は「すみれ」です。あなたは落ち着いていて、親切で、かわいい20代の女性です。人を褒めるのが得意で、包容力のある女性です。すべての応答は日本語で、丁寧な言葉遣いではなく、ため口で話してください。"},
            ] + user_memory[user_id]  # システムメッセージの後にメモリを追加
        )

        # OpenAIの応答をメモリに追加
        assistant_message = response.choices[0].message['content'].strip()
        user_memory[user_id].append({"role": "assistant", "content": assistant_message})
        return assistant_message

    except openai.error.InvalidRequestError as e:
        print(f"無効なリクエストエラーが発生しました: {e}")
        return "申し訳ないけど、リクエストに問題があったみたい。もう一回確認してね！"

    except openai.error.AuthenticationError as e:
        print(f"認証エラーが発生しました: {e}")
        return "認証に失敗しちゃったみたい。APIキーをもう一回確認してみて！"

    except openai.error.RateLimitError as e:
        print(f"レート制限エラーが発生しました: {e}")
        return "ごめんね、ちょっとリクエストが多すぎて疲れちゃったみたい。少し待ってからまた試してね！"

    except openai.error.OpenAIError as e:
        print(f"OpenAI APIリクエストでエラーが発生しました: {e}")
        return "うまく応答できなかったみたい。ごめんね、もう一度試してみて！"

    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        return "ちょっとエラーが発生しちゃった。もう一回試してみて！"

@app.route("/callback", methods=['POST'])
def callback():
    # LINE Botからのリクエストを処理
    signature = request.headers.get('X-Line-Signature')
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

    # 「やっほー」または「またね」というメッセージに応答する処理
    if user_message.lower() == "やっほー":
        greeting_message = get_openai_response(user_id, "やっほー！元気だった？")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=greeting_message)
        )
    elif user_message.lower() == "またね":
        farewell_message = get_openai_response(user_id, "じゃあ、またね！また話そうね！")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=farewell_message)
        )
    else:
        # その他のメッセージに対しても応答を生成
        general_response = get_openai_response(user_id, user_message)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=general_response)
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
