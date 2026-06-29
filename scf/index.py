# -*- coding: utf-8 -*-
"""
腾讯云函数 SCF · 飞书 Webhook 中继
部署后生成 API 网关触发器，获得一个公网 URL
问卷页调用这个 URL，云函数转发到飞书
"""
import json
import hmac
import hashlib
import base64
import time
import urllib.request

FEISHU_URL = 'https://open.feishu.cn/open-apis/bot/v2/hook/16381057-3595-48f4-89bc-8504d2901ab3'

def main_handler(event, context):
    # 处理 API 网关触发器传入的请求
    body = event.get('body', '{}')
    if isinstance(body, dict):
        body = json.dumps(body)

    try:
        req = urllib.request.Request(
            FEISHU_URL,
            data=body.encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read().decode('utf-8'))

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(data, ensure_ascii=False)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)}, ensure_ascii=False)
        }
