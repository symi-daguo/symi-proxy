#!/usr/bin/env python3

import os
import json
import time
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# 全局变量
proxy_manager = None

class WebInterfaceHandler(BaseHTTPRequestHandler):
    """Web界面处理器"""
    
    def _set_headers(self, content_type="text/html", status_code=200):
        """设置HTTP头"""
        self.send_response(status_code)
        self.send_header("Content-type", content_type)
        self.end_headers()
    
    def _load_template(self, template_name):
        """加载HTML模板"""
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", template_name)
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""
    
    def _render_template(self, template_name, **kwargs):
        """渲染HTML模板"""
        template = self._load_template(template_name)
        for key, value in kwargs.items():
            template = template.replace("{{" + key + "}}", str(value))
        return template
    
    def _get_dashboard_html(self):
        """获取仪表盘HTML"""
        if not proxy_manager:
            return "<h1>代理服务器未启动</h1>"
        
        # 获取节点信息
        nodes = proxy_manager.get_all_nodes()
        current_node = proxy_manager.get_current_node()
        stats = proxy_manager.get_stats()
        
        # 构建节点表格
        nodes_html = ""
        for i, node in enumerate(nodes):
            status_class = "success" if node.status == "online" else "danger" if node.status == "offline" else "warning"
            current_mark = "✓" if current_node and node.name == current_node.name else ""
            latency = f"{node.latency} ms" if node.latency is not None else "未知"
            last_check = node.last_check.strftime("%Y-%m-%d %H:%M:%S") if node.last_check else "未检查"
            
            nodes_html += f"""
            <tr>
                <td>{i+1}</td>
                <td>{node.name}</td>
                <td>{node.address}</td>
                <td>{node.port}</td>
                <td><span class="badge bg-{status_class}">{node.status}</span></td>
                <td>{latency}</td>
                <td>{last_check}</td>
                <td>{current_mark}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="selectNode('{node.name}')">选择</button>
                </td>
            </tr>
            """
        
        # 获取订阅信息
        subscription_url = proxy_manager.options.get("subscription_url", "")
        update_interval = proxy_manager.options.get("subscription_update_interval", 24)
        last_update = proxy_manager.last_update.strftime("%Y-%m-%d %H:%M:%S") if proxy_manager.last_update else "未更新"
        
        # 获取统计信息
        total_connections = stats["total_connections"]
        active_connections = stats["active_connections"]
        total_traffic_mb = stats["total_traffic"] / (1024 * 1024)
        
        # 渲染模板
        return self._render_template(
            "dashboard.html",
            nodes_table=nodes_html,
            subscription_url=subscription_url,
            update_interval=update_interval,
            last_update=last_update,
            total_connections=total_connections,
            active_connections=active_connections,
            total_traffic=f"{total_traffic_mb:.2f} MB"
        )
    
    def do_GET(self):
        """处理GET请求"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # 处理API请求
        if path.startswith("/api/"):
            return self._handle_api_get(path, parsed_url)
        
        # 处理静态文件
        if path.startswith("/static/"):
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path[1:])
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    content_type = "text/css" if path.endswith(".css") else "application/javascript" if path.endswith(".js") else "text/plain"
                    self._set_headers(content_type)
                    self.wfile.write(f.read())
                return
        
        # 处理主页
        if path == "/" or path == "/dashboard":
            self._set_headers()
            self.wfile.write(self._get_dashboard_html().encode())
            return
        
        # 404页面
        self._set_headers(status_code=404)
        self.wfile.write(b"404 Not Found")
    
    def _handle_api_get(self, path, parsed_url):
        """处理API GET请求"""
        if not proxy_manager:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": "代理服务器未启动"}).encode())
            return
        
        # 获取节点列表
        if path == "/api/nodes":
            nodes = [node.to_dict() for node in proxy_manager.get_all_nodes()]
            self._set_headers("application/json")
            self.wfile.write(json.dumps({"nodes": nodes}).encode())
            return
        
        # 获取当前节点
        if path == "/api/current_node":
            current_node = proxy_manager.get_current_node()
            if current_node:
                self._set_headers("application/json")
                self.wfile.write(json.dumps(current_node.to_dict()).encode())
            else:
                self._set_headers("application/json", 404)
                self.wfile.write(json.dumps({"error": "没有当前节点"}).encode())
            return
        
        # 获取统计信息
        if path == "/api/stats":
            self._set_headers("application/json")
            self.wfile.write(json.dumps(proxy_manager.get_stats()).encode())
            return
        
        # 404 API
        self._set_headers("application/json", 404)
        self.wfile.write(json.dumps({"error": "API不存在"}).encode())
    
    def do_POST(self):
        """处理POST请求"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data)
        except:
            # 如果不是JSON，尝试解析表单数据
            data = {}
            form_data = parse_qs(post_data)
            for key, values in form_data.items():
                data[key] = values[0] if len(values) == 1 else values
        
        # 处理API请求
        if self.path.startswith("/api/"):
            return self._handle_api_post(self.path, data)
        
        # 404页面
        self._set_headers(status_code=404)
        self.wfile.write(b"404 Not Found")
    
    def _handle_api_post(self, path, data):
        """处理API POST请求"""
        if not proxy_manager:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": "代理服务器未启动"}).encode())
            return
        
        # 选择节点
        if path == "/api/select_node":
            node_name = data.get("node_name")
            if not node_name:
                self._set_headers("application/json", 400)
                self.wfile.write(json.dumps({"error": "缺少node_name参数"}).encode())
                return
            
            success = proxy_manager.select_node(node_name)
            if success:
                self._set_headers("application/json")
                self.wfile.write(json.dumps({"success": True, "message": f"已选择节点: {node_name}"}).encode())
            else:
                self._set_headers("application/json", 400)
                self.wfile.write(json.dumps({"error": f"选择节点失败: {node_name}"}).encode())
            return
        
        # 更新订阅
        if path == "/api/update_subscription":
            success = proxy_manager.update_subscription()
            if success:
                self._set_headers("application/json")
                self.wfile.write(json.dumps({"success": True, "message": "订阅更新成功"}).encode())
            else:
                self._set_headers("application/json", 400)
                self.wfile.write(json.dumps({"error": "订阅更新失败"}).encode())
            return
        
        # 检查节点
        if path == "/api/check_nodes":
            available_nodes = proxy_manager.check_all_nodes()
            self._set_headers("application/json")
            self.wfile.write(json.dumps({
                "success": True,
                "message": f"节点检查完成，共有 {len(available_nodes)}/{len(proxy_manager.get_all_nodes())} 个节点可用"
            }).encode())
            return
        
        # 404 API
        self._set_headers("application/json", 404)
        self.wfile.write(json.dumps({"error": "API不存在"}).encode())

def create_templates_directory():
    """创建模板目录"""
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    os.makedirs(templates_dir, exist_ok=True)
    
    # 创建仪表盘模板
    dashboard_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Symi Proxy 管理界面</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-top: 20px; }
        .container { max-width: 1200px; }
        .card { margin-bottom: 20px; }
        .table-responsive { margin-bottom: 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">Symi Proxy 管理界面</h1>
        
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0">订阅信息</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>订阅地址:</strong> {{subscription_url}}</p>
                        <p><strong>更新间隔:</strong> {{update_interval}} 小时</p>
                        <p><strong>最后更新:</strong> {{last_update}}</p>
                        <button class="btn btn-primary" onclick="updateSubscription()">立即更新订阅</button>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0">统计信息</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>总连接数:</strong> <span id="total-connections">{{total_connections}}</span></p>
                        <p><strong>活动连接数:</strong> <span id="active-connections">{{active_connections}}</span></p>
                        <p><strong>总流量:</strong> <span id="total-traffic">{{total_traffic}}</span></p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">节点列表</h5>
                        <button class="btn btn-sm btn-secondary" onclick="checkNodes()">检查节点</button>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>名称</th>
                                        <th>地址</th>
                                        <th>端口</th>
                                        <th>状态</th>
                                        <th>延迟</th>
                                        <th>最后检查</th>
                                        <th>当前</th>
                                        <th>操作</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {{nodes_table}}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 选择节点
        function selectNode(nodeName) {
            fetch('/api/select_node', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ node_name: nodeName })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert('错误: ' + data.error);
                }
            })
            .catch(error => {
                alert('请求失败: ' + error);
            });
        }
        
        // 更新订阅
        function updateSubscription() {
            fetch('/api/update_subscription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert('错误: ' + data.error);
                }
            })
            .catch(error => {
                alert('请求失败: ' + error);
            });
        }
        
        // 检查节点
        function checkNodes() {
            fetch('/api/check_nodes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert('错误: ' + data.error);
                }
            })
            .catch(error => {
                alert('请求失败: ' + error);
            });
        }
        
        // 定时刷新统计信息
        setInterval(() => {
            fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                document.getElementById('total-connections').textContent = data.total_connections;
                document.getElementById('active-connections').textContent = data.active_connections;
                const totalTrafficMB = (data.total_traffic / (1024 * 1024)).toFixed(2);
                document.getElementById('total-traffic').textContent = totalTrafficMB + ' MB';
            })
            .catch(error => {
                console.error('获取统计信息失败:', error);
            });
        }, 5000);
    </script>
</body>
</html>
"""
    
    try:
        dashboard_path = os.path.join(templates_dir, "dashboard.html")
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(dashboard_template)
        print(f"已创建模板文件: {dashboard_path}")
    except Exception as e:
        print(f"创建模板文件失败: {str(e)}")

def start_web_server(manager, port=8088):
    """启动Web服务器"""
    global proxy_manager
    proxy_manager = manager
    
    # 创建模板目录和模板文件
    create_templates_directory()
    
    # 创建HTTP服务器
    server = HTTPServer(("0.0.0.0", port), WebInterfaceHandler)
    print(f"Web服务器已启动，监听端口: {port}")
    
    # 启动服务器线程
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return server
