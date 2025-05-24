#!/usr/bin/env python3
"""
诊断脚本 - 帮助分析代理连接问题
"""

import socket
import json
import os
import sys
import requests
from datetime import datetime

def check_config_file():
    """检查配置文件"""
    print("=== 检查配置文件 ===")
    
    config_files = ["data/options.json", "/data/options.json"]
    config_found = False
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ 找到配置文件: {config_file}")
            config_found = True
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                print(f"  - 本地端口: {config.get('local_port', '未设置')}")
                print(f"  - Web端口: {config.get('web_port', '未设置')}")
                print(f"  - 订阅地址: {'已设置' if config.get('subscription_url') else '未设置'}")
                print(f"  - 自定义节点: {len(config.get('custom_nodes', []))} 个")
                
                if config.get('custom_nodes'):
                    for i, node in enumerate(config['custom_nodes']):
                        print(f"    节点{i+1}: {node.get('name', '未命名')} - {node.get('server', 'N/A')}:{node.get('server_port', 'N/A')}")
                
            except Exception as e:
                print(f"❌ 配置文件解析失败: {str(e)}")
        else:
            print(f"❌ 配置文件不存在: {config_file}")
    
    if not config_found:
        print("❌ 未找到任何配置文件")
    
    return config_found

def check_ports():
    """检查端口占用情况"""
    print("\n=== 检查端口占用 ===")
    
    ports_to_check = [7088, 8080, 8123]
    
    for port in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print(f"✅ 端口 {port} 正在监听")
            else:
                print(f"❌ 端口 {port} 未监听")
        except Exception as e:
            print(f"❌ 检查端口 {port} 失败: {str(e)}")

def check_web_interface():
    """检查Web界面"""
    print("\n=== 检查Web界面 ===")
    
    web_ports = [8080, 8123]
    
    for port in web_ports:
        try:
            response = requests.get(f"http://127.0.0.1:{port}", timeout=5)
            if response.status_code == 200:
                print(f"✅ Web界面可访问: http://127.0.0.1:{port}")
                
                # 检查API
                try:
                    api_response = requests.get(f"http://127.0.0.1:{port}/api/nodes", timeout=5)
                    if api_response.status_code == 200:
                        nodes_data = api_response.json()
                        print(f"  - API正常，节点数量: {len(nodes_data.get('nodes', []))}")
                    else:
                        print(f"  - API异常，状态码: {api_response.status_code}")
                except Exception as e:
                    print(f"  - API检查失败: {str(e)}")
                
                break
            else:
                print(f"❌ Web界面异常: http://127.0.0.1:{port} (状态码: {response.status_code})")
        except requests.exceptions.ConnectionError:
            print(f"❌ Web界面无法连接: http://127.0.0.1:{port}")
        except Exception as e:
            print(f"❌ Web界面检查失败: http://127.0.0.1:{port} - {str(e)}")

def check_network_connectivity():
    """检查网络连通性"""
    print("\n=== 检查网络连通性 ===")
    
    test_hosts = [
        ("www.baidu.com", 443, "国内网站"),
        ("www.google.com", 443, "国外网站"),
        ("8.8.8.8", 53, "DNS服务器")
    ]
    
    for host, port, desc in test_hosts:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            start_time = datetime.now()
            sock.connect((host, port))
            end_time = datetime.now()
            sock.close()
            
            latency = (end_time - start_time).total_seconds() * 1000
            print(f"✅ {desc} ({host}:{port}) 可达，延迟: {latency:.0f}ms")
        except Exception as e:
            print(f"❌ {desc} ({host}:{port}) 不可达: {str(e)}")

def check_dependencies():
    """检查依赖"""
    print("\n=== 检查Python依赖 ===")
    
    required_modules = [
        "socket", "json", "threading", "requests", 
        "base64", "hashlib", "hmac", "time"
    ]
    
    optional_modules = [
        ("yaml", "YAML解析"),
        ("Crypto.Cipher", "加密支持")
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} (必需)")
    
    for module, desc in optional_modules:
        try:
            __import__(module)
            print(f"✅ {module} ({desc})")
        except ImportError:
            print(f"⚠️  {module} ({desc}) - 可选")

def main():
    """主函数"""
    print("Symi Proxy 诊断工具")
    print("=" * 50)
    
    check_dependencies()
    check_config_file()
    check_ports()
    check_web_interface()
    check_network_connectivity()
    
    print("\n=== 诊断完成 ===")
    print("如果发现问题，请根据上述信息进行修复。")
    print("如果代理服务器未启动，请运行: python main.py")

if __name__ == "__main__":
    main()
