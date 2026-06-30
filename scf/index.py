# -*- coding: utf-8 -*-
"""
腾讯云函数 SCF · 飞书 Webhook 中继 + 多维表格存档
配置从多维表格「项目目录」和「问卷版本」读取，新增项目/版本无需改代码
"""
import json, urllib.request, hmac, hashlib, base64, time, os

APP_ID = os.environ.get('APP_ID', 'cli_aac89563e1e59bdf')
APP_SECRET = os.environ.get('APP_SECRET', '')
BITABLE_APP_TOKEN = os.environ.get('BITABLE_APP_TOKEN', 'K3jLbFejyaeZzPsDTzmcEco5ndl')
# 三张工作表的 table_id
DIR_TABLE_ID = 'tblpjL2mkUZVuNVL'    # 项目目录
VER_TABLE_ID = os.environ.get('VER_TABLE_ID', '')  # 问卷版本（建好后填环境变量）
FEISHU_API = 'https://open.feishu.cn/open-apis'

_token_cache = {'token': '', 'expires': 0}

# ===================== 飞书 API 工具 =====================

def get_tenant_token():
    now = time.time()
    if _token_cache['token'] and now < _token_cache['expires']:
        return _token_cache['token']
    url = f'{FEISHU_API}/auth/v3/tenant_access_token/internal'
    body = json.dumps({'app_id': APP_ID, 'app_secret': APP_SECRET}).encode()
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
    token = resp.get('tenant_access_token', '')
    if not token: raise Exception(f'获取token失败: {resp}')
    _token_cache['token'] = token
    _token_cache['expires'] = now + 3600
    return token

def bitable_get(table_id, params=''):
    """读多维表格记录"""
    token = get_tenant_token()
    url = f'{FEISHU_API}/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/records?{params}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())

def bitable_post(table_id, fields):
    """写一行到多维表格"""
    token = get_tenant_token()
    url = f'{FEISHU_API}/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/records'
    body = json.dumps({'fields': fields}).encode()
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())

def feishu_sign(secret):
    ts = int(time.time())
    sign_str = f'{ts}\n{secret}'
    sign = base64.b64encode(hmac.new(sign_str.encode(), b'', hashlib.sha256).digest()).decode()
    return str(ts), sign

def send_webhook(url, secret, text):
    ts, sign = feishu_sign(secret)
    body = json.dumps({'timestamp': ts, 'sign': sign, 'msg_type': 'text',
                       'content': {'text': text}}).encode()
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())

# ===================== 配置查询 =====================

def get_project_config(project_id):
    """从「项目目录」表查项目配置"""
    data = bitable_get(DIR_TABLE_ID)
    for item in data.get('data', {}).get('items', []):
        f = item.get('fields', {})
        if f.get('项目标识') == project_id:
            return f
    return None

def get_version_config(project_name, ver):
    """从「问卷版本」表查版本配置"""
    if not VER_TABLE_ID: return None
    data = bitable_get(VER_TABLE_ID)
    for item in data.get('data', {}).get('items', []):
        f = item.get('fields', {})
        if f.get('所属项目') == project_name and f.get('版本号') == ver:
            return f
    return None

def ensure_version(project_name, ver):
    """确保「问卷版本」表中有该版本，没有则自动创建"""
    if not VER_TABLE_ID: return
    existing = get_version_config(project_name, ver)
    if existing: return existing
    return bitable_post(VER_TABLE_ID, {
        '所属项目': project_name,
        '版本号': ver,
        '问卷名称': f'{project_name} - {ver}',
        '状态': '使用中',
    })

# ===================== 字段映射 =====================

def map_to_fields(project_name, ver, lines):
    raw = {}
    for ln in lines:
        ln = ln.strip()
        if not ln or not ln.startswith('**'): continue
        try:
            end = ln.index('**', 2)
            key = ln[2:end]
            val = ln[end+3:]
            raw[key] = val
        except: continue

    def p(n): return (n < 10 and '0' or '') + str(n)
    now = time.localtime()
    submit_id = f'RQ{now.tm_year}{p(now.tm_mon)}{p(now.tm_mday)}-{p(now.tm_hour)}{p(now.tm_min)}'

    return {
        '提交编号': submit_id,
        '机构名称': raw.get('机构名称', ''),
        '填表人': raw.get('填表人', ''),
        '联系方式': raw.get('联系方式', ''),
        '现有平台': raw.get('现有平台', ''),
        '当前管理方式': raw.get('当前管理方式', ''),
        '捐款功能': raw.get('捐款功能', ''),
        '捐款档位': raw.get('捐款档位', ''),
        '允许匿名': raw.get('允许匿名', ''),
        '场景化入口': raw.get('场景化入口', ''),
        '捐款反馈': raw.get('捐款反馈', ''),
        '受助人功能': raw.get('受助人功能', ''),
        '登记字段': raw.get('登记字段', ''),
        '证明材料': raw.get('证明材料', ''),
        '审核层级': raw.get('审核层级', ''),
        '合作机构录入': raw.get('合作机构录入', ''),
        '项目管理功能': raw.get('项目管理功能', ''),
        '管理费': raw.get('管理费', ''),
        '尊严支付': raw.get('尊严支付', ''),
        '企业配捐': raw.get('企业配捐', ''),
        '月捐': raw.get('月捐', ''),
        '数据大屏': raw.get('数据大屏', ''),
        '期望上线': raw.get('期望上线', ''),
        '预算范围': raw.get('预算范围', ''),
        'IT人员': raw.get('IT人员', ''),
        '补充说明': raw.get('补充说明', ''),
        '参考小程序': raw.get('参考小程序', ''),
        '版本标记': f'{project_name} - {ver}',
    }

# ===================== 主入口 =====================

def main_handler(event, context):
    method = event.get('httpMethod') or \
             event.get('requestContext', {}).get('http', {}).get('method', 'POST')
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'}, 'body': ''}

    body = event.get('body', '{}')
    if isinstance(body, dict): body = json.dumps(body)
    payload = json.loads(body)
    text = payload.get('text', '')
    project_id = payload.get('project', 'charity')
    ver = payload.get('ver', 'v1')

    # 1. 查「项目目录」→ 拿 webhook + table_id
    proj = get_project_config(project_id)
    if not proj:
        return {'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': '{"error":"unknown project: ' + project_id + '"}'}

    webhook_url = proj.get('webhook_url', '')
    webhook_secret = proj.get('webhook_secret', '')
    table_id = proj.get('提交表ID', '')  # 该项目提交数据写到哪个工作表

    # 2. 自动维护「问卷版本」表（不存在则创建）
    ensure_version(proj.get('项目名称', project_id), ver)

    # 3. 发飞书群消息
    try:
        webhook_resp = send_webhook(webhook_url, webhook_secret,
            f'[{proj.get("项目名称", project_id)} · {ver}]\n{text}')
    except Exception as e:
        webhook_resp = {'error': str(e)}

    # 4. 写多维表格提交记录
    bitable_resp = {}
    if table_id:
        try:
            fields = map_to_fields(proj.get('项目名称', project_id), ver, text.split('\n'))
            bitable_resp = bitable_post(table_id, fields)
        except Exception as e:
            bitable_resp = {'error': str(e)}

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'code': webhook_resp.get('code', 0),
                            'bitable': bitable_resp}, ensure_ascii=False),
    }
