from __future__ import unicode_literals
import errno,os,sys,util,tempfile
from os.path import join, dirname
from argparse import ArgumentParser
from flask import Flask, request, abort
from dotenv import load_dotenv
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# sys.path.append('/Users/kikuchitakashi/Docker/wedding_bot')
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageTemplateAction,
    ButtonsTemplate, ImageCarouselTemplate, ImageCarouselColumn, URITemplateAction,
    PostbackTemplateAction, DatetimePickerTemplateAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, ImageSendMessage, VideoMessage, VideoSendMessage, AudioMessage, FileMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent
)

app = Flask(__name__)
# 環境変数からchannel_secret・channel_access_tokenを取得
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
dropbox_api_token = os.getenv('DROPBOX_API_TOKEN', None)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
if dropbox_api_token is None:
    print('Specify DROPBOX_API_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)
dbx = dropbox.Dropbox(dropbox_api_token)

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# function for create tmp dir for download content
def make_static_tmp_dir():
    try:
        os.makedirs(static_tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
            pass
        else:
            raise

@app.route("/")
def hello_world():
    return "hello world"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

'''
{
  "events": [
    {
      "replyToken": "nHuyWiB7yP5Zw52FIkcQobQuGDXCTA",
      "type": "message",
      "timestamp": 1462629479859,
      "source": {
        "type": "user",
        "userId": "U4af4980629..."
      },
      "message": {
        "id": "325708",
        "type": "text",
        "text": "Hello, world"
      }
    },
    {
      "replyToken": "nHuyWiB7yP5Zw52FIkcQobQuGDXCTA",
      "type": "follow",
      "timestamp": 1462629479859,
      "source": {
        "type": "user",
        "userId": "U4af4980629..."
      }
    }
  ]
}
'''

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text == "リスト":
        lists = dbx.files_list_folder("/" + str(event.source.user_id))
        img_columns = []
        i = 0
        for entry in lists.entries:
            img_url_tmp = dbx.sharing_list_shared_links(entry.path_display)
            img_url_str = img_url_tmp.links[0].url
            img_url_str2 = img_url_str.replace("www.dropbox.com","dl.dropboxusercontent.com")
            img_url = img_url_str2.replace("?dl=0","")
            column = CarouselColumn(
                thumbnail_image_url=img_url,
                text='保存日時：' + str(entry.client_modified),
                actions=[
                    PostbackTemplateAction(
                        label='この画像を削除',
                        data='action=buy&itemid=1'
                    ),
                ]
            )
            img_columns.append(column)

        carousel_template_message = TemplateSendMessage(
            alt_text='Saved Picture',
            template=CarouselTemplate(columns=img_columns)
        )
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text="これまでに送ってもらった写真を表示します。"),
                # TextSendMessage(text=str(event.source.user_id)),
                carousel_template_message,
            ]
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            # TextSendMessage(text=event.message.text)
            TextSendMessage(text=util.get_message(event.message.text))
        )

@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def handle_content_message(event):
    if not os.path.exists(static_tmp_path):
        make_static_tmp_dir()

    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
    elif isinstance(event.message, VideoMessage):
        ext = 'mp4'
    elif isinstance(event.message, AudioMessage):
        ext = 'm4a'
    else:
        return

    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    # send files to dropbox
    dist_path = tempfile_path + '.' + ext
    dist_name = os.path.basename(dist_path)
    # create UserId name directory on Dropbox
    user_dir_name = dist_path.replace('app/static/tmp',str(event.source.user_id))

    with open(tempfile_path, 'rb') as f:
        try:
            # dbx.files_upload(f.read(), dist_path, mode=WriteMode('overwrite'))
            dbx.files_upload(f.read(), user_dir_name, mode=WriteMode('overwrite'))
            dbx.sharing_create_shared_link_with_settings(user_dir_name)
        except ApiError as err:
            # This checks for the specific error where a user doesn't have
            # enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().reason.is_insufficient_space()):
                sys.exit("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
                sys.exit()
            else:
                print(err)
                sys.exit()

    line_bot_api.reply_message(
        event.reply_token,
        [
            # TextSendMessage(text='Save content.'),
            TextSendMessage(text='写真を保存しました！'),
            TextSendMessage(text=request.host_url + os.path.join('static', 'tmp', dist_name)),
            # ImageSendMessage(
            #     original_content_url=request.host_url + os.path.join('static', 'tmp', dist_name),
            #     preview_image_url=request.host_url + os.path.join('static', 'tmp', dist_name)
            # )
        ]
    )

if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', type=int, default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    # create tmp dir for download content
    make_static_tmp_dir()

    app.run(debug=options.debug, port=options.port)
