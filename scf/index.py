# -*- coding: utf-8 -*-
"""
腾讯云函数 SCF · 飞书 Webhook 中继
浏览器只需传消息内容，SCF 负责计算签名并转发
"""
import json, urllib.request, hmac, hashlib, base64, time

FEISHU_URL = 'https://open.feishu.cn/open-apis/bot/v2/hook/16381057-3595-48f4-89bc-8504d2901ab3'
SECRET = 'RbVRjrUpzmvOI63SL1RQSc'

def main_handler(event, context):
    # 处理 OPTIONS 预检
    method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method', 'POST')
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': '',
        }

    # 获取浏览器发来的消息
    body = event.get('body', '{}')
    if isinstance(body, dict):
        body = json.dumps(body)
    try:
        payload = json.loads(body)
        text = payload.get('text', '')
    except:
        text = body

    # SCF 生成时间戳和签名（避免浏览器端签名差异）
    ts = int(time.time())
    sign_str = f'{ts}\n{SECRET}'
    sign = base64.b64encode(hmac.new(sign_str.encode(), b'', hashlib.sha256).digest()).decode()

    # 转发到飞书
    feishu_body = json.dumps({
        'timestamp': str(ts),
        'sign': sign,
        'msg_type': 'text',
        'content': {'text': text},
    }).encode('utf-8')

    try:
        req = urllib.request.Request(FEISHU_URL, data=feishu_body,
                                     headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read().decode('utf-8'))
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(data, ensure_ascii=False),
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}, ensure_ascii=False),
        }
