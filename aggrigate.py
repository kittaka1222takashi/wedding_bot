import errno,os,sys,util,tempfile,json
from os.path import join, dirname
from argparse import ArgumentParser
from flask import Flask, request, abort
from dotenv import load_dotenv
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError
import csv
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

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
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

dropbox_api_token = os.getenv('DROPBOX_API_TOKEN', None)

if dropbox_api_token is None:
    print('Specify DROPBOX_API_TOKEN as environment variable.')
    sys.exit(1)

dbx = dropbox.Dropbox(dropbox_api_token)



lists = dbx.files_list_folder("")
file_num = {}
for entry in lists.entries:
    path = "/" + entry.name
    files = dbx.files_list_folder(path)
    file_num[entry.name] = len(files.entries)
print(file_num)

file_num_sorted = {}
for user_id, num in sorted(file_num.items(), key=lambda x: -x[1]):
    file_num_sorted[user_id] = num

csv_datas = []
f = open("ranking.csv", "w")
writer = csv.writer(f, lineterminator="\n")
rank = 1;
for user_id in file_num_sorted:
    num = file_num_sorted[user_id]
    profile = line_bot_api.get_profile(user_id)
    profile.display_name
    writer.writerow([rank, user_id, file_num_sorted[user_id], profile.display_name])
    csv_datas.append([rank, user_id, file_num_sorted[user_id], profile.display_name])

f.close()
print(csv_datas)

