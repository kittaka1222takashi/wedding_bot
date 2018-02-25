import os,requests,re,sys,json,types

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
