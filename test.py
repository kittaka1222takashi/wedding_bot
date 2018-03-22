import errno,os,sys,util,tempfile,json
from os.path import join, dirname
from argparse import ArgumentParser
from flask import Flask, request, abort
from dotenv import load_dotenv
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

dropbox_api_token = os.getenv('DROPBOX_API_TOKEN', None)

if dropbox_api_token is None:
    print('Specify DROPBOX_API_TOKEN as environment variable.')
    sys.exit(1)

dbx = dropbox.Dropbox(dropbox_api_token)
lists = dbx.files_list_folder("/Ue48e02158a9a7624852bb45f636d0966")
# print(lists.entries[0].name)
print(lists.entries[0].client_modified)
# dbx.sharing_create_shared_link_with_settings()
entry = lists.entries[2]
img_url_tmp = dbx.sharing_list_shared_links(entry.path_display)

print(entry)
# if len(img_url.links) == 0:
#     img_url = dbx.sharing_create_shared_link_with_settings(entry.path_display)
img_url = img_url_tmp.links[0].url
img_url_modified = img_url.replace("www.dropbox.com","dl.dropboxusercontent.com")
img_url_modified2 = img_url_modified.replace("?dl=0","")
# print(img_url_modified2)
# print(img_url_tmp.links[0].path_lower)
# tmp = dbx.files_delete_v2(entry.path_display)
# print(tmp)
# print(json.dumps({"schedule":le}))

