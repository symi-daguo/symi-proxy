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
    options_file = "/data/options.json"
    
    # 默认选项
    default_options = {
        "local_port": 7088,
        "subscription_url": "",
        "subscription_update_interval": 24,
        "default_node": "auto",
        "custom_nodes": []
    }
    
    # 如果配置文件存在，则加载配置
    if os.path.exists(options_file):
        try:
            with open(options_file, "r") as f:
                options = json.load(f)
            logger.info("已加载配置文件")
            
            # 合并默认选项和用户配置
            for key, value in default_options.items():
                if key not in options:
                    options[key] = value
            
            return options
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
    
    logger.warning("配置文件不存在，使用默认配置")
    return default_options

def start_proxy_server(manager):
    """启动代理服务器"""
    try:
        manager.start_proxy_server()
    except Exception as e:
        logger.error(f"启动代理服务器失败: {str(e)}")

def main():
    """主函数"""
    logger.info("正在启动Symi Proxy...")
    
    # 加载配置
    options = load_options()
    
    # 创建代理管理器
    manager = ProxyManager(options)
    
    # 启动Web服务器
    web_port = 8088
    web_server = start_web_server(manager, web_port)
    
    # 启动代理服务器
    start_proxy_server(manager)

if __name__ == "__main__":
    main()
