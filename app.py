from __future__ import unicode_literals
import errno,os,sys,util,tempfile,datetime,json
from os.path import join, dirname
from argparse import ArgumentParser
from flask import Flask, request, abort, render_template
from dotenv import load_dotenv
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

class CustomFlask(Flask):
  jinja_options = Flask.jinja_options.copy()
  jinja_options.update(dict(
    block_start_string='(%',
    block_end_string='%)',
    variable_start_string='((',
    variable_end_string='))',
    comment_start_string='(#',
    comment_end_string='#)',
  ))

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

# app = Flask(__name__)
app = CustomFlask(__name__)

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

@app.route("/archive/<user_id>", methods=['GET'])
def archive(user_id):
    return render_template('archive.html', dropbox_api_token=dropbox_api_token)

@app.route("/getImages/<user_id>", methods=['GET'])
def getImages(user_id):
    lists = dbx.files_list_folder("/" + user_id)
    images = []
    for entry in lists.entries:
        img = {}
        img_url_tmp = dbx.sharing_list_shared_links(entry.path_display)
        img_url_str = img_url_tmp.links[0].url
        img_url_str2 = img_url_str.replace("www.dropbox.com","dl.dropboxusercontent.com")
        img_url = img_url_str2.replace("?dl=0","")
        img["url"] = img_url
        # 保存日時を一度日付オブジェクトに変換
        saved_datetime = entry.client_modified
        # 日本時間に変換
        saved_datetime_jpn = saved_datetime + datetime.timedelta(hours=9)
        img["saved_datetime"] = saved_datetime_jpn.strftime("%Y-%m-%d %H:%M:%S")
        img["filename"] = entry.name
        images.append(img)
    return json.dumps(images)

@app.route("/deleteImage/<user_id>/<file_name>", methods=['POST'])
def deleteImage(user_id, file_name):
    file_path = "/" + user_id + "/" + file_name
    try:
        tmp = dbx.files_delete_v2(file_path)
    except:
        json_res =  {"status":"500","message":"Delete failed!!"}
    else:
        json_res =  {"status":"200","message":"Delete succeeded!!"}

    return json.dumps(json_res)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
        lists = dbx.files_list_folder("/" + str(event.source.user_id))
        if len(lists.entries) == 0:
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="まだ保存された画像はありません！写真を送って下さい！"),
                ]
            )
            return

        line_bot_api.reply_message(
            event.reply_token,
            [
                # TextSendMessage(text=util.get_message(event.message.text)),
                TextSendMessage(text="式中に撮った写真を送って下さい(*^^*)送っていただいた写真は後ほど新郎新婦やこのアカウントを友達登録してくださった皆様にシェアします！写真をいっぱい送ってくれた方には二次会のときにいいことがあるかも？これまでに保存された写真はこちらのURLから確認出来ます！"),
                TextSendMessage(text=request.host_url + os.path.join("archive",str(event.source.user_id)))
            ]
        )

@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def handle_content_message(event):
    if not os.path.exists(static_tmp_path):
        make_static_tmp_dir()

    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
    else:
        sorry_text='画像以外は送れません、ごめんなさい!'
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=sorry_text))
        return

    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    # send files to dropbox
    print(tempfile_path)
    dist_path = tempfile_path + '.' + ext
    print(dist_path)
    dist_name = os.path.basename(dist_path)
    print(dist_name)

    # create UserId name directory on Dropbox
    user_dir_name = dist_path.replace('app/static/tmp',str(event.source.user_id))

    with open(tempfile_path, 'rb') as f:
        try:
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
            TextSendMessage(text='写真を保存しました！'),
            TextSendMessage(text=request.host_url + os.path.join("archive",str(event.source.user_id)))
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
