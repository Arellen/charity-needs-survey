# -*- coding: utf-8 -*-
"""
腾讯云函数 SCF · 飞书 Webhook 中继 + 多维表格存档
"""
import json, urllib.request, hmac, hashlib, base64, time

# ===================== 配置 =====================

# 飞书应用凭据（敏感信息放在 SCF 环境变量中）
import os
APP_ID = os.environ.get('APP_ID', 'cli_aac89563e1e59bdf')
APP_SECRET = os.environ.get('APP_SECRET', '')
BITABLE_APP_TOKEN = os.environ.get('BITABLE_APP_TOKEN', 'K3jLbFejyaeZzPsDTzmcEco5ndl')

# 项目配置（每新增一个项目在下面加一条）
# webhook_secret 从环境变量读取，不在代码中明文存储
PROJECTS = {
    'charity': {
        'name': '公益小程序',
        'webhook_url': os.environ.get('CHARITY_WEBHOOK_URL', ''),
        'webhook_secret': os.environ.get('CHARITY_WEBHOOK_SECRET', ''),
        'table_id': os.environ.get('CHARITY_TABLE_ID', 'tblvS2hZ3s41OvUX'),
    },
}

# 飞书表格 API 基础地址
FEISHU_API = 'https://open.feishu.cn/open-apis'

# ===================== 缓存 =====================
_token_cache = {'token': '', 'expires': 0}

def get_tenant_token():
    """获取 tenant_access_token（2小时有效，带缓存）"""
    now = time.time()
    if _token_cache['token'] and now < _token_cache['expires']:
        return _token_cache['token']

    url = f'{FEISHU_API}/auth/v3/tenant_access_token/internal'
    body = json.dumps({'app_id': APP_ID, 'app_secret': APP_SECRET}).encode()
    req = urllib.request.Request(url, data=body,
        headers={'Content-Type': 'application/json'})
    resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
    token = resp.get('tenant_access_token', '')
    _token_cache['token'] = token
    _token_cache['expires'] = now + 3600  # 提前一点过期
    return token

def feishu_sign(secret):
    """生成飞书 Webhook 签名"""
    ts = int(time.time())
    sign_str = f'{ts}\n{secret}'
    sign = base64.b64encode(hmac.new(sign_str.encode(), b'', hashlib.sha256).digest()).decode()
    return str(ts), sign

def send_webhook(url, secret, text):
    """发飞书群消息"""
    ts, sign = feishu_sign(secret)
    body = json.dumps({
        'timestamp': ts, 'sign': sign,
        'msg_type': 'text', 'content': {'text': text}
    }).encode()
    req = urllib.request.Request(url, data=body,
        headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())

def write_bitable(table_id, fields):
    """写一行到多维表格"""
    token = get_tenant_token()
    url = f'{FEISHU_API}/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/records'
    body = json.dumps({'fields': fields}).encode()
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    })
    return json.loads(urllib.request.urlopen(req, timeout=5).read())

def map_to_fields(project_name, ver, lines):
    """把问卷文本行映射为多维表格字段"""
    # 文本行格式：**字段名**：值
    raw = {}
    for ln in lines:
        ln = ln.strip()
        if not ln or not ln.startswith('**'):
            continue
        try:
            # **机构名称**：XX基金会
            key_end = ln.index('**', 2)
            key = ln[2:key_end]
            val = ln[key_end+3:]  # ** + ： = 3 字符
            raw[key] = val
        except:
            continue

    def p(n): return (n < 10 and '0' or '') + str(n)
    now = time.localtime()
    submit_id = f'RQ{now.tm_year}{p(now.tm_mon)}{p(now.tm_mday)}-{p(now.tm_hour)}{p(now.tm_min)}'

    # 映射到表格字段（多选字段存为文本避免API选项匹配问题）
    fields = {
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
    return fields

# ===================== 主入口 =====================

def main_handler(event, context):
    # OPTIONS 预检
    method = event.get('httpMethod') or \
             event.get('requestContext', {}).get('http', {}).get('method', 'POST')
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'},
            'body': '',
        }

    # 解析请求
    body = event.get('body', '{}')
    if isinstance(body, dict):
        body = json.dumps(body)
    payload = json.loads(body)
    text = payload.get('text', '')
    project_id = payload.get('project', 'charity')
    ver = payload.get('ver', 'v1')

    # 查项目配置
    proj = PROJECTS.get(project_id)
    if not proj:
        return {'statusCode': 400, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': '{"error":"unknown project"}'}

    lines = text.split('\n')

    # 1. 发飞书群消息
    try:
        webhook_resp = send_webhook(proj['webhook_url'], proj['webhook_secret'], text)
    except Exception as e:
        webhook_resp = {'error': str(e)}

    # 2. 写多维表格
    bitable_resp = {}
    try:
        fields = map_to_fields(proj['name'], ver, lines)
        bitable_resp = write_bitable(proj['table_id'], fields)
    except Exception as e:
        bitable_resp = {'error': str(e)}

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'code': webhook_resp.get('code', 0),
                            'webhook': webhook_resp,
                            'bitable': bitable_resp}, ensure_ascii=False),
    }
