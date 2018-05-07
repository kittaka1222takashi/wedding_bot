import os,requests,re,sys,json,types,csv

def get_message(text):
    api_key = os.environ['DOCOMO_DIALOGUE_API_KEY']
    endpoint = 'https://api.apigw.smt.docomo.ne.jp/dialogue/v1/dialogue?APIKEY=REGISTER_KEY'
    url = endpoint.replace('REGISTER_KEY', api_key)

    payload = {'utt' : text, 'context': ''}
    headers = {'Content-type': 'application/json'}

    #送信
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    data = r.json()

    #jsonの解析
    response = data['utt']
    context = data['context']

    return response

def get_ranking_message(dbx, line_bot_api):
    # フォルダのリストを取得
    lists = dbx.files_list_folder("")
    file_num = {}
    # それぞれのユーザー（フォルダ）に何個画像があるか
    for entry in lists.entries:
        path = "/" + entry.name
        files = dbx.files_list_folder(path)
        file_num[entry.name] = len(files.entries)
    print(file_num)
    file_num_sorted = {}
    # 数が多い順にソート
    for user_id, num in sorted(file_num.items(), key=lambda x: -x[1]):
        file_num_sorted[user_id] = num
    ranking = []
    rank = 1;
    message = "送ってくれた画像が多い人ランキングは\n"
    # csvファイルとして出力
    for user_id in file_num_sorted:
        num = file_num_sorted[user_id]
        profile = line_bot_api.get_profile(user_id)
        ranking.append([rank, user_id, file_num_sorted[user_id], profile.display_name])
        message = message + str(rank) + "位 " + profile.display_name + "さん " + str(num) + "枚\n" + user_id + "\n"
    message = message + "です！"
    print(ranking)
    return message

