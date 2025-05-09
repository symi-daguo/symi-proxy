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
        "web_port": 8123,
        "subscription_url": "https://example.com/subscribe/demo?format=ssr",
        "subscription_update_interval": 12,
        "default_node": "auto",
        "use_custom_node": True,
        "custom_node": {
            "server": "d3.alibabamysql.com",
            "server_port": 7001,
            "password": "di15PV",
            "method": "chacha20-ietf",
            "protocol": "auth_aes128_md5",
            "protocol_param": "72291:gMe1NM",
            "obfs": "tls1.2_ticket_auth",
            "obfs_param": "90f3b72291.www.gov.hk"
        },
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

            # 处理自定义节点
            if options.get("use_custom_node", False) and "custom_node" in options:
                custom_node = options["custom_node"]
                # 创建自定义节点列表
                custom_nodes = []
                if custom_node and "server" in custom_node and "server_port" in custom_node:
                    # 添加名称前缀，以便在ProxyManager中识别为自定义节点
                    if "name" not in custom_node:
                        custom_node["name"] = "自定义节点-1"
                    elif not custom_node["name"].startswith("自定义节点"):
                        custom_node["name"] = "自定义节点-" + custom_node["name"]

                    # 确保所有必要字段都存在
                    if "password" not in custom_node:
                        logger.warning("自定义节点缺少password字段，使用默认值")
                        custom_node["password"] = "password"

                    if "method" not in custom_node:
                        logger.warning("自定义节点缺少method字段，使用默认值")
                        custom_node["method"] = "chacha20-ietf"

                    if "obfs" not in custom_node:
                        logger.warning("自定义节点缺少obfs字段，使用默认值")
                        custom_node["obfs"] = "tls1.2_ticket_auth"

                    # 打印节点详细信息，用于调试
                    logger.info(f"节点详细配置: server={custom_node.get('server')}, "
                               f"port={custom_node.get('server_port')}, "
                               f"method={custom_node.get('method')}, "
                               f"obfs={custom_node.get('obfs')}, "
                               f"protocol={custom_node.get('protocol')}")

                    custom_nodes.append(custom_node)
                    logger.info(f"已添加自定义节点: {custom_node['name']}")
                options["custom_nodes"] = custom_nodes

            return options
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")

    logger.warning("配置文件不存在，使用默认配置")
    return default_options

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
    logger.info("正在启动Symi Proxy...")

    # 加载配置
    options = load_options()

    # 创建代理管理器
    manager = ProxyManager(options)

    # 启动Web服务器
    web_port = options.get("web_port", 8123)
    web_server = start_web_server(manager, web_port)

    # 启动代理服务器
    start_proxy_server(manager)

if __name__ == "__main__":
    main()
