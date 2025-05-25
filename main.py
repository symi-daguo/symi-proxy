#!/usr/bin/env python3

import os
import json
import logging
import threading
import socket
from proxy_manager import ProxyManager
from web_interface import start_web_server

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

def load_options():
    """加载配置选项"""
    print("Starting Symi Proxy...")
    print("读取配置...")

    # 优先使用Home Assistant路径，然后是本地路径
    config_files = ["/data/options.json", "data/options.json"]

    for options_file in config_files:
        if os.path.exists(options_file):
            try:
                with open(options_file, "r") as f:
                    options = json.load(f)
                print("配置文件存在")
                print(f"本地端口: {options.get('local_port', 7088)}")
                print(f"订阅更新间隔: {options.get('subscription_update_interval', 12)} 小时")

                # 检查自定义节点配置
                if options.get("use_custom_node", False) and "custom_node" in options:
                    custom_node = options["custom_node"]
                    print(f"检测到自定义节点: {custom_node.get('server')}:{custom_node.get('server_port')}")

                return options
            except Exception as e:
                logger.error(f"加载配置文件失败: {str(e)}")
                continue

    print("配置文件不存在，使用默认配置")
    return {
        "local_port": 7088,
        "web_port": 8123,
        "subscription_url": "",
        "subscription_update_interval": 12,
        "default_node": "auto",
        "use_custom_node": False,
        "custom_nodes": []
    }

def start_proxy_server(manager):
    """启动代理服务器"""
    try:
        # 检查是否有可用节点
        if not manager.nodes or not any(node.status == "online" for node in manager.nodes):
            logger.warning("没有可用节点，跳过启动代理服务器")
            print("警告: 没有可用节点，代理服务器未启动。请检查网络连接或配置文件中的节点信息。")
            print("您仍然可以通过Web界面(端口: " + str(manager.options.get("web_port", 8123)) + ")管理节点。")
            return
        manager.start_proxy_server()
    except Exception as e:
        logger.error(f"启动代理服务器失败: {str(e)}")

def main():
    """主函数"""
    try:
        logger.info("正在启动Symi Proxy...")

        # 加载配置
        options = load_options()

        # 创建代理管理器
        manager = ProxyManager(options)

        # ProxyManager已经处理了节点选择逻辑

        # 启动Web服务器
        web_port = options.get("web_port", 8123)
        web_server = start_web_server(manager, web_port)

        # 启动代理服务器
        start_proxy_server(manager)

    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
        logger.error("程序将保持运行状态，避免重启循环")
        # 保持程序运行，避免重启循环
        import time
        while True:
            time.sleep(60)

if __name__ == "__main__":
    main()
