#!/usr/bin/env python3

import os
import json
import time
import socket
import threading
import requests
import base64
import random
import logging
from datetime import datetime
from selectors import DefaultSelector, EVENT_READ

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("proxy_manager")

class Node:
    """代理节点类"""
    def __init__(self, name, address, port, latency=None, password=None, method=None,
                 obfs=None, obfs_param=None, protocol=None, protocol_param=None):
        self.name = name
        self.address = address
        self.port = port
        self.latency = latency  # 延迟时间，单位毫秒
        self.last_check = None  # 最后一次检查时间
        self.status = "unknown"  # 状态：unknown, online, offline

        # 兼容SS/SSR节点格式
        self.password = password
        self.method = method
        self.obfs = obfs
        self.obfs_param = obfs_param
        self.protocol = protocol
        self.protocol_param = protocol_param

    def to_dict(self):
        """转换为字典"""
        node_dict = {
            "name": self.name,
            "address": self.address,
            "port": self.port,
            "latency": self.latency,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "status": self.status
        }

        # 如果有SS/SSR相关参数，也添加到字典中
        if self.password:
            node_dict["password"] = self.password
        if self.method:
            node_dict["method"] = self.method
        if self.obfs:
            node_dict["obfs"] = self.obfs
        if self.obfs_param:
            node_dict["obfs_param"] = self.obfs_param
        if self.protocol:
            node_dict["protocol"] = self.protocol
        if self.protocol_param:
            node_dict["protocol_param"] = self.protocol_param

        return node_dict

    def check_availability(self, timeout=2):
        """检查节点是否可用"""
        try:
            start_time = time.time()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((self.address, self.port))
            s.close()
            end_time = time.time()
            self.latency = int((end_time - start_time) * 1000)  # 转换为毫秒
            self.status = "online"
            self.last_check = datetime.now()
            return True
        except Exception as e:
            logger.error(f"节点 {self.name} 连接失败: {str(e)}")
            self.status = "offline"
            self.last_check = datetime.now()
            return False

class ProxyManager:
    """代理管理器"""
    def __init__(self, options):
        self.options = options
        self.nodes = []  # 节点列表
        self.current_node = None  # 当前使用的节点
        self.last_update = None  # 最后一次更新时间
        self.stats = {  # 统计信息
            "total_connections": 0,
            "active_connections": 0,
            "total_traffic": 0,  # 单位：字节
        }
        self.lock = threading.Lock()  # 线程锁
        self.load_custom_nodes()  # 加载自定义节点

        # 如果有订阅地址，则更新订阅
        if self.options.get("subscription_url"):
            self.update_subscription()

        # 选择默认节点
        self.select_node(self.options.get("default_node", "auto"))

        # 启动定时更新线程
        self.start_update_thread()

    def load_custom_nodes(self):
        """加载自定义节点"""
        custom_nodes = self.options.get("custom_nodes", [])
        loaded_count = 0
        for node_info in custom_nodes:
            try:
                # 支持两种格式：简单格式(name,address,port)和完整格式(包括SS/SSR参数)
                if "server" in node_info:
                    # SS/SSR完整格式
                    name = node_info.get("name", f"自定义节点-{len(self.nodes)+1}")
                    server = node_info.get("server")
                    server_port = node_info.get("server_port")

                    # 确保必要字段存在
                    if not server or not server_port:
                        logger.warning(f"节点 {name} 缺少必要字段 server 或 server_port，跳过")
                        continue

                    node = Node(
                        name=name,
                        address=server,
                        port=server_port,
                        password=node_info.get("password"),
                        method=node_info.get("method"),
                        obfs=node_info.get("obfs"),
                        obfs_param=node_info.get("obfs_param"),
                        protocol=node_info.get("protocol"),
                        protocol_param=node_info.get("protocol_param")
                    )
                elif "address" in node_info and "port" in node_info:
                    # 简单格式
                    node = Node(
                        name=node_info.get("name", f"自定义节点-{len(self.nodes)+1}"),
                        address=node_info.get("address"),
                        port=node_info.get("port")
                    )
                else:
                    logger.warning(f"节点格式不正确，缺少必要字段，跳过")
                    continue

                self.nodes.append(node)
                loaded_count += 1
            except Exception as e:
                logger.error(f"加载自定义节点失败: {str(e)}")

        if loaded_count > 0:
            logger.info(f"已加载 {loaded_count} 个自定义节点")
        else:
            logger.warning("没有加载任何自定义节点")

        # 如果没有节点，尝试从订阅加载
        if not self.nodes and self.options.get("subscription_url"):
            logger.info("尝试从订阅加载节点")
            self.update_subscription()

    def update_subscription(self):
        """更新订阅"""
        subscription_url = self.options.get("subscription_url")
        if not subscription_url:
            logger.warning("未配置订阅地址")
            return False

        try:
            logger.info(f"正在更新订阅: {subscription_url}")
            response = requests.get(subscription_url, timeout=10)
            if response.status_code != 200:
                logger.error(f"订阅更新失败，状态码: {response.status_code}")
                return False

            # 解析订阅内容
            content = response.text.strip()
            try:
                # 尝试Base64解码
                # 添加填充字符以确保长度是4的倍数
                padding_needed = len(content) % 4
                if padding_needed:
                    content += '=' * (4 - padding_needed)

                # 尝试解码
                decoded_content = base64.b64decode(content).decode('utf-8')
                content = decoded_content
                logger.info("成功解码Base64订阅内容")
            except Exception as e:
                # 如果解码失败，使用原始内容
                logger.warning(f"Base64解码失败，使用原始内容: {str(e)}")
                pass

            # 解析节点信息
            nodes = []

            # 尝试解析为JSON
            try:
                data = json.loads(content)

                # 处理单个节点的情况
                if isinstance(data, dict) and "server" in data and "server_port" in data:
                    # SS/SSR单节点格式
                    name = data.get("name", f"节点-1")
                    nodes.append(Node(
                        name=name,
                        address=data.get("server"),
                        port=data.get("server_port"),
                        password=data.get("password"),
                        method=data.get("method"),
                        obfs=data.get("obfs"),
                        obfs_param=data.get("obfs_param"),
                        protocol=data.get("protocol"),
                        protocol_param=data.get("protocol_param")
                    ))

                # 处理节点数组
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        if isinstance(item, dict):
                            if "server" in item and "server_port" in item:
                                # SS/SSR节点格式
                                name = item.get("name", f"节点-{i+1}")
                                nodes.append(Node(
                                    name=name,
                                    address=item.get("server"),
                                    port=item.get("server_port"),
                                    password=item.get("password"),
                                    method=item.get("method"),
                                    obfs=item.get("obfs"),
                                    obfs_param=item.get("obfs_param"),
                                    protocol=item.get("protocol"),
                                    protocol_param=item.get("protocol_param")
                                ))
                            elif "name" in item and "address" in item and "port" in item:
                                # 简单格式
                                nodes.append(Node(
                                    name=item["name"],
                                    address=item["address"],
                                    port=item["port"]
                                ))

                # 处理包含nodes字段的格式
                elif isinstance(data, dict) and "nodes" in data and isinstance(data["nodes"], list):
                    for i, item in enumerate(data["nodes"]):
                        if isinstance(item, dict):
                            if "server" in item and "server_port" in item:
                                # SS/SSR节点格式
                                name = item.get("name", f"节点-{i+1}")
                                nodes.append(Node(
                                    name=name,
                                    address=item.get("server"),
                                    port=item.get("server_port"),
                                    password=item.get("password"),
                                    method=item.get("method"),
                                    obfs=item.get("obfs"),
                                    obfs_param=item.get("obfs_param"),
                                    protocol=item.get("protocol"),
                                    protocol_param=item.get("protocol_param")
                                ))
                            elif "name" in item and "address" in item and "port" in item:
                                # 简单格式
                                nodes.append(Node(
                                    name=item["name"],
                                    address=item["address"],
                                    port=item["port"]
                                ))

            except json.JSONDecodeError:
                # 如果不是JSON，尝试按行解析
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # 尝试解析格式：name|address|port
                    parts = line.split('|')
                    if len(parts) >= 3:
                        try:
                            nodes.append(Node(
                                name=parts[0],
                                address=parts[1],
                                port=int(parts[2])
                            ))
                            continue
                        except:
                            pass

                    # 尝试解析格式：address:port name
                    parts = line.split(' ', 1)
                    if len(parts) >= 1:
                        addr_parts = parts[0].split(':')
                        if len(addr_parts) == 2:
                            try:
                                name = parts[1] if len(parts) > 1 else f"节点-{len(nodes)+1}"
                                nodes.append(Node(
                                    name=name,
                                    address=addr_parts[0],
                                    port=int(addr_parts[1])
                                ))
                                continue
                            except:
                                pass

            if not nodes:
                logger.error("未能从订阅中解析出有效节点")
                return False

            # 更新节点列表
            with self.lock:
                # 保留自定义节点
                custom_nodes = [node for node in self.nodes if node.name.startswith("自定义节点")]
                # 添加订阅节点
                self.nodes = custom_nodes + nodes
                self.last_update = datetime.now()

            logger.info(f"订阅更新成功，共获取 {len(nodes)} 个节点")
            return True

        except Exception as e:
            logger.error(f"订阅更新失败: {str(e)}")
            return False

    def check_all_nodes(self):
        """检查所有节点的可用性"""
        logger.info("开始检查所有节点的可用性")
        threads = []

        for node in self.nodes:
            t = threading.Thread(target=node.check_availability)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        logger.info("节点可用性检查完成")

        # 统计可用节点数量
        available_nodes = [node for node in self.nodes if node.status == "online"]
        logger.info(f"共有 {len(available_nodes)}/{len(self.nodes)} 个节点可用")

        return available_nodes

    def select_node(self, node_selector="auto"):
        """选择节点

        参数:
            node_selector: 节点选择器，可以是节点名称、索引或"auto"（自动选择最快节点）
        """
        with self.lock:
            # 如果没有节点，返回False
            if not self.nodes:
                logger.warning("没有可用节点")
                # 保持current_node不变
                return False

            # 检查所有节点的可用性
            available_nodes = self.check_all_nodes()
            if not available_nodes:
                logger.warning("没有可用节点")
                # 保持current_node不变
                return False

            # 根据选择器选择节点
            if node_selector == "auto":
                # 自动选择延迟最低的节点
                available_nodes.sort(key=lambda x: x.latency if x.latency is not None else float('inf'))
                self.current_node = available_nodes[0]
                logger.info(f"自动选择节点: {self.current_node.name}, 延迟: {self.current_node.latency}ms")
            elif node_selector.isdigit() and 0 <= int(node_selector) < len(self.nodes):
                # 按索引选择节点
                index = int(node_selector)
                if self.nodes[index].status == "online":
                    self.current_node = self.nodes[index]
                    logger.info(f"选择节点 #{index}: {self.current_node.name}")
                else:
                    logger.warning(f"节点 #{index} 不可用，自动选择最快节点")
                    return self.select_node("auto")
            else:
                # 按名称选择节点
                found = False
                for node in self.nodes:
                    if node.name == node_selector and node.status == "online":
                        self.current_node = node
                        logger.info(f"选择节点: {self.current_node.name}")
                        found = True
                        break

                # 如果找不到指定节点或节点不可用，自动选择最快节点
                if not found:
                    logger.warning(f"节点 '{node_selector}' 不存在或不可用，自动选择最快节点")
                    if available_nodes:
                        return self.select_node("auto")
                    else:
                        return False

            return True

    def start_update_thread(self):
        """启动定时更新线程"""
        def update_loop():
            while True:
                # 计算下次更新时间
                interval_hours = self.options.get("subscription_update_interval", 24)
                sleep_seconds = interval_hours * 3600

                # 休眠
                time.sleep(sleep_seconds)

                # 更新订阅
                if self.options.get("subscription_url"):
                    self.update_subscription()
                    # 重新选择节点
                    self.select_node(self.options.get("default_node", "auto"))

        # 启动线程
        t = threading.Thread(target=update_loop, daemon=True)
        t.start()
        logger.info(f"定时更新线程已启动，间隔: {self.options.get('subscription_update_interval', 24)}小时")

    def get_current_node(self):
        """获取当前使用的节点"""
        return self.current_node

    def get_all_nodes(self):
        """获取所有节点"""
        return self.nodes

    def get_stats(self):
        """获取统计信息"""
        return self.stats

    def update_stats(self, connection_change=0, traffic=0):
        """更新统计信息"""
        with self.lock:
            self.stats["total_connections"] += max(0, connection_change)
            self.stats["active_connections"] += connection_change
            self.stats["total_traffic"] += traffic

    def xor_encode(self, bstring):
        """XOR编码"""
        MASK = 0x55
        ret = bytearray(bstring)
        for i in range(len(ret)):
            ret[i] ^= MASK
        return ret

    def proxy_process(self, sock1, sock2):
        """在两个socket之间转发数据"""
        sel = DefaultSelector()
        sel.register(sock1, EVENT_READ)
        sel.register(sock2, EVENT_READ)

        while True:
            events = sel.select()
            for (key, _) in events:
                try:
                    data_in = key.fileobj.recv(8192)
                except ConnectionResetError as e:
                    logger.error(f"连接重置: {str(e)}")
                    sock1.close()
                    sock2.close()
                    self.update_stats(connection_change=-1)
                    return

                if data_in:
                    # 更新流量统计
                    self.update_stats(traffic=len(data_in))

                    if key.fileobj == sock1:
                        sock2.send(self.xor_encode(data_in))
                    else:
                        sock1.send(self.xor_encode(data_in))
                else:
                    sock1.close()
                    sock2.close()
                    self.update_stats(connection_change=-1)
                    return

    def handle_connection(self, sock_in, addr):
        """处理新的连接请求"""
        logger.info(f"新的连接: {addr[0]}:{addr[1]}")
        self.update_stats(connection_change=1)

        # 获取当前节点
        node = self.get_current_node()
        if not node:
            logger.error("没有可用节点，拒绝连接")
            sock_in.close()
            self.update_stats(connection_change=-1)
            return

        # 建立远程连接
        sock_remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_remote.settimeout(15)
        try:
            sock_remote.connect((node.address, node.port))
        except Exception as e:
            logger.error(f"连接到远程节点 {node.name} ({node.address}:{node.port}) 失败: {str(e)}")

            # 尝试重新选择节点
            if self.select_node("auto"):
                node = self.get_current_node()
                try:
                    sock_remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock_remote.settimeout(15)
                    sock_remote.connect((node.address, node.port))
                    logger.info(f"已切换到备用节点 {node.name}")
                except Exception as e:
                    logger.error(f"连接到备用节点失败: {str(e)}")
                    sock_in.close()
                    self.update_stats(connection_change=-1)
                    return
            else:
                logger.error("没有可用的备用节点")
                sock_in.close()
                self.update_stats(connection_change=-1)
                return

        # 在本地连接与远程连接间转发数据
        self.proxy_process(sock_in, sock_remote)

    def start_proxy_server(self):
        """启动代理服务器"""
        local_port = self.options.get("local_port", 7088)

        # 检查当前节点是否存在
        if not self.current_node:
            logger.error("没有可用节点，无法启动代理服务器")
            raise Exception("没有可用节点，请检查配置或订阅地址")

        # 设置iptables规则，防止RST包（仅在Linux环境下）
        if os.name != 'nt':  # 非Windows系统
            try:
                # 检查iptables是否可用
                if os.system("which iptables > /dev/null 2>&1") == 0:
                    # 先清除可能存在的旧规则
                    os.system("iptables -D INPUT -p tcp --tcp-flags RST RST -j DROP 2>/dev/null || true")
                    # 添加新规则
                    os.system(f"iptables -A INPUT -p tcp --tcp-flags RST RST -j DROP")
                    logger.info("已设置iptables规则")
                else:
                    logger.warning("iptables命令不可用，跳过设置规则")
            except Exception as e:
                logger.warning(f"设置iptables规则失败: {str(e)}")

        # 创建socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("0.0.0.0", local_port))
        s.listen()
        logger.info(f"代理服务器已启动，监听端口: {local_port}")

        while True:
            sock, addr = s.accept()
            t = threading.Thread(target=self.handle_connection, args=(sock, addr))
            t.start()
