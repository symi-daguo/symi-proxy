#!/usr/bin/env python3
"""
测试代理连接的脚本
"""

import socket
import time
import sys

def test_proxy_connection(proxy_host="127.0.0.1", proxy_port=7088, target_host="www.google.com", target_port=443):
    """测试代理连接"""
    print(f"测试代理连接: {proxy_host}:{proxy_port} -> {target_host}:{target_port}")
    
    try:
        # 连接到代理服务器
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        print(f"正在连接到代理服务器 {proxy_host}:{proxy_port}...")
        sock.connect((proxy_host, proxy_port))
        print("✅ 成功连接到代理服务器")
        
        # 发送CONNECT请求
        connect_request = f"CONNECT {target_host}:{target_port} HTTP/1.1\r\nHost: {target_host}:{target_port}\r\n\r\n"
        print(f"发送CONNECT请求: {connect_request.strip()}")
        sock.send(connect_request.encode())
        
        # 接收响应
        response = sock.recv(1024)
        print(f"收到响应: {response.decode('utf-8', errors='ignore')}")
        
        if b"200 Connection Established" in response:
            print("✅ 代理连接建立成功")
            
            # 发送HTTP请求测试数据传输
            http_request = f"GET / HTTP/1.1\r\nHost: {target_host}\r\nConnection: close\r\n\r\n"
            sock.send(http_request.encode())
            
            # 接收响应数据
            data = sock.recv(1024)
            if data:
                print(f"✅ 成功接收到 {len(data)} 字节数据")
                print("代理连接工作正常！")
                return True
            else:
                print("❌ 未接收到数据")
                return False
        else:
            print("❌ 代理连接失败")
            return False
            
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def check_proxy_server_running(host="127.0.0.1", port=7088):
    """检查代理服务器是否运行"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

if __name__ == "__main__":
    print("=== Symi Proxy 连接测试 ===")
    
    # 检查代理服务器是否运行
    if not check_proxy_server_running():
        print("❌ 代理服务器未运行，请先启动 main.py")
        sys.exit(1)
    
    print("✅ 代理服务器正在运行")
    
    # 测试多个目标
    test_targets = [
        ("www.google.com", 443),
        ("github.com", 443),
        ("www.baidu.com", 443)
    ]
    
    success_count = 0
    for target_host, target_port in test_targets:
        print(f"\n--- 测试 {target_host}:{target_port} ---")
        if test_proxy_connection(target_host=target_host, target_port=target_port):
            success_count += 1
        time.sleep(1)
    
    print(f"\n=== 测试结果 ===")
    print(f"成功: {success_count}/{len(test_targets)}")
    
    if success_count > 0:
        print("✅ 代理服务器工作正常")
    else:
        print("❌ 代理服务器可能存在问题")
