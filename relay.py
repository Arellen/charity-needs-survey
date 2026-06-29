"""
本地中继服务：接收问卷提交 → 转发到飞书 Webhook
启动：python3 relay.py
然后浏览器访问 http://localhost:8765/survey.html 填问卷
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import json
import sys

FEISHU_URL = 'https://open.feishu.cn/open-apis/bot/v2/hook/16381057-3595-48f4-89bc-8504d2901ab3'

class RelayHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/relay':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                req = urllib.request.Request(FEISHU_URL, data=body,
                    headers={'Content-Type': 'application/json'})
                resp = urllib.request.urlopen(req, timeout=10)
                data = resp.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
                print(f'[✓] 转发成功 → 飞书')
            except Exception as e:
                print(f'[✗] 转发失败: {e}')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            super().do_POST()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        # 简洁日志
        if '/api/relay' in str(args):
            pass  # relay 请求不打印，上面已经打印了
        else:
            super().log_message(format, *args)

if __name__ == '__main__':
    port = 8765
    print(f'''
╔══════════════════════════════════════════╗
║   🦅 飞书中继服务已启动                    ║
║                                          ║
║   本地问卷：http://localhost:{port}/survey.html ║
║                                          ║
║   按 Ctrl+C 停止                          ║
╚══════════════════════════════════════════╝
''')
    try:
        HTTPServer(('0.0.0.0', port), RelayHandler).serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
