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
import re
from datetime import datetime
from selectors import DefaultSelector, EVENT_READ
from urllib.parse import unquote, urlparse

try:
    import yaml
except ImportError:
    yaml = None

try:
    from ssr_client import SSRClient
except ImportError:
    SSRClient = None
    logging.warning("SSR客户端模块导入失败，将使用简单TCP连接")

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
        print("启动Symi Proxy主程序...")

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

        # 加载自定义节点
        print("正在加载节点配置...")
        self.load_custom_nodes()

        # 如果有订阅地址，则更新订阅
        subscription_url = self.options.get("subscription_url", "").strip()
        if subscription_url and subscription_url != "":
            print(f"正在更新订阅: {subscription_url[:50]}...")
            self.update_subscription()
        else:
            print("未配置订阅地址，跳过订阅更新")

        # 显示节点加载结果
        if self.nodes:
            print(f"✅ 节点加载完成，共 {len(self.nodes)} 个节点")
            for i, node in enumerate(self.nodes):
                print(f"  节点 {i+1}: {node.name} ({node.address}:{node.port})")
        else:
            print("❌ 未加载任何节点，请检查配置")

        # 选择默认节点
        self.select_node(self.options.get("default_node", "auto"))

        # 启动定时更新线程
        self.start_update_thread()

    def load_custom_nodes(self):
        """加载自定义节点"""
        loaded_count = 0

        print(f"检查配置选项:")
        print(f"  use_custom_node: {self.options.get('use_custom_node', False)}")
        print(f"  custom_node存在: {'custom_node' in self.options}")

        # 处理单个自定义节点配置 (custom_node)
        if self.options.get("use_custom_node", False) and "custom_node" in self.options:
            node_info = self.options["custom_node"]
            print(f"✅ 检测到单个自定义节点配置:")
            print(f"   server: {node_info.get('server')}")
            print(f"   server_port: {node_info.get('server_port')}")
            print(f"   password: {node_info.get('password')}")
            print(f"   method: {node_info.get('method')}")

            try:
                if "server" in node_info and "server_port" in node_info:
                    name = node_info.get("name", "自定义节点-1")
                    if not name.startswith("自定义节点"):
                        name = "自定义节点-" + name

                    node = Node(
                        name=name,
                        address=node_info.get("server"),
                        port=node_info.get("server_port"),
                        password=node_info.get("password"),
                        method=node_info.get("method"),
                        obfs=node_info.get("obfs"),
                        obfs_param=node_info.get("obfs_param"),
                        protocol=node_info.get("protocol"),
                        protocol_param=node_info.get("protocol_param")
                    )

                    self.nodes.append(node)
                    loaded_count += 1
                    print(f"✅ 成功加载自定义节点: {node.name} ({node.address}:{node.port})")
                else:
                    print("❌ 自定义节点配置缺少必要字段 server 或 server_port")
            except Exception as e:
                print(f"❌ 加载自定义节点失败: {str(e)}")
        else:
            print("❌ 未检测到自定义节点配置")

        # 处理自定义节点列表配置 (custom_nodes)
        custom_nodes = self.options.get("custom_nodes", [])
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
        subscription_url = self.options.get("subscription_url", "").strip()
        if not self.nodes and subscription_url and subscription_url != "":
            logger.info("尝试从订阅加载节点")
            self.update_subscription()
        elif not self.nodes:
            logger.warning("没有配置任何节点（自定义节点或订阅地址）")
            logger.info("请在配置文件中添加自定义节点或订阅地址")

    def update_subscription(self):
        """更新订阅"""
        subscription_url = self.options.get("subscription_url")
        if not subscription_url:
            logger.warning("未配置订阅地址")
            return False

        # 修正订阅URL格式
        if subscription_url.endswith("?mu") and not subscription_url.endswith("?mu=1"):
            subscription_url = subscription_url.replace("?mu", "?mu=1")
            logger.info(f"修正订阅URL格式: {subscription_url}")

        try:
            logger.info(f"正在更新订阅: {subscription_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(subscription_url, headers=headers, timeout=10)
            if response.status_code == 429:
                logger.warning(f"订阅请求过于频繁 (429)，跳过本次更新")
                return False
            elif response.status_code != 200:
                logger.error(f"订阅更新失败，状态码: {response.status_code}")
                return False

            # 获取订阅内容
            content = response.content
            logger.info(f"获取到订阅内容，长度: {len(content)}")

            # 检测订阅类型
            subscription_type = self._detect_subscription_type(content, subscription_url)
            logger.info(f"检测到订阅类型: {subscription_type}")

            # 根据订阅类型解析节点
            if subscription_type == "ssr":
                nodes = self._parse_ssr_subscription(content)
            elif subscription_type == "ss":
                nodes = self._parse_ss_subscription(content)
            elif subscription_type == "clash":
                nodes = self._parse_clash_subscription(content)
            else:
                logger.error(f"不支持的订阅类型: {subscription_type}")
                return False

            # 如果没有解析出节点，返回失败
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

                # 记住当前节点
                current_node_name = self.current_node.name if self.current_node else None

                # 如果当前使用的是自定义节点，或者配置要求使用自定义节点，则继续使用自定义节点
                if (current_node_name and current_node_name.startswith("自定义节点")) or \
                   (self.options.get("use_custom_node", False) and custom_nodes):
                    # 强制使用自定义节点
                    self.current_node = custom_nodes[0]
                    logger.info(f"订阅更新后，强制使用自定义节点: {self.current_node.name}")
                else:
                    # 否则，重新选择节点
                    self.select_node(self.options.get("default_node", "auto"))

            logger.info(f"订阅更新成功，共获取 {len(nodes)} 个节点")
            return True

        except Exception as e:
            logger.error(f"订阅更新失败: {str(e)}")
            return False

    def _detect_subscription_type(self, content, url):
        """检测订阅类型"""
        # 根据URL参数判断
        if "format=ssr" in url.lower():
            return "ssr"
        if "format=ss" in url.lower():
            return "ss"
        if "format=clash" in url.lower():
            return "clash"

        # 尝试解析内容判断
        try:
            # 尝试解码Base64
            try:
                # 移除可能的URL安全字符
                content_str = content.decode('utf-8', errors='ignore')
                decoded_content = base64.b64decode(content_str.replace('-', '+').replace('_', '/'))
                decoded_str = decoded_content.decode('utf-8', errors='ignore')

                # 检查解码后的内容
                if decoded_str.startswith('ssr://'):
                    return "ssr"
                if decoded_str.startswith('ss://'):
                    return "ss"
            except:
                pass

            # 尝试解析为JSON/YAML判断是否为Clash配置
            try:
                # 尝试作为JSON解析
                try:
                    json_content = json.loads(content)
                    if "proxies" in json_content and isinstance(json_content["proxies"], list):
                        return "clash"
                except:
                    pass

                # 尝试作为YAML解析
                try:
                    import yaml
                    yaml_content = yaml.safe_load(content)
                    if "proxies" in yaml_content and isinstance(yaml_content["proxies"], list):
                        return "clash"
                except:
                    pass
            except:
                pass

            # 检查原始内容
            content_str = content.decode('utf-8', errors='ignore')
            if 'proxies:' in content_str and ('type: ss' in content_str or 'type: ssr' in content_str):
                return "clash"
        except:
            pass

        # 默认返回SSR类型
        return "ssr"

    def _parse_ssr_subscription(self, content):
        """解析SSR订阅"""
        nodes = []

        try:
            # 尝试Base64解码
            try:
                # 移除可能的URL安全字符
                content_str = content.decode('utf-8', errors='ignore')
                content_str = content_str.replace('-', '+').replace('_', '/')

                # 添加填充字符以确保长度是4的倍数
                padding_needed = len(content_str) % 4
                if padding_needed:
                    content_str += '=' * (4 - padding_needed)

                # 尝试解码
                decoded_content = base64.b64decode(content_str).decode('utf-8')
                logger.info(f"成功解码Base64订阅内容，解码后长度: {len(decoded_content)}")
            except Exception as e:
                # 如果解码失败，使用原始内容
                logger.warning(f"Base64解码失败，使用原始内容: {str(e)}")
                decoded_content = content.decode('utf-8', errors='ignore')

            # 按行分割
            lines = decoded_content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 解析SSR链接
                node = self._parse_ssr_link(line, len(nodes))
                if node:
                    nodes.append(node)
                    logger.info(f"成功解析SSR链接: {node.name}")

            # 如果没有解析出节点，尝试解析为JSON
            if not nodes:
                try:
                    data = json.loads(decoded_content)
                    nodes.extend(self._parse_json_nodes(data))
                except:
                    pass
        except Exception as e:
            logger.error(f"解析SSR订阅失败: {str(e)}")

        return nodes

    def _parse_ssr_link(self, link, index=0):
        """解析SSR链接"""
        if link.startswith('ssr://'):
            try:
                # 移除前缀
                encoded = link[6:]
                # Base64解码
                encoded = encoded.replace('-', '+').replace('_', '/')
                padding_needed = len(encoded) % 4
                if padding_needed:
                    encoded += '=' * (4 - padding_needed)

                decoded = base64.b64decode(encoded).decode('utf-8')

                # 解析格式：server:port:protocol:method:obfs:base64pass/?obfsparam=base64param&protoparam=base64param&remarks=base64remarks
                parts = decoded.split(':')
                if len(parts) >= 6:
                    server = parts[0]
                    port = int(parts[1])
                    protocol = parts[2]
                    method = parts[3]
                    obfs = parts[4]

                    # 处理密码和参数
                    pass_and_params = parts[5].split('/?')
                    password_b64 = pass_and_params[0]
                    # Base64解码密码
                    password_b64 = password_b64.replace('-', '+').replace('_', '/')
                    padding_needed = len(password_b64) % 4
                    if padding_needed:
                        password_b64 += '=' * (4 - padding_needed)
                    password = base64.b64decode(password_b64).decode('utf-8')

                    # 解析参数
                    obfs_param = ""
                    protocol_param = ""
                    remarks = f"SSR节点-{index+1}"

                    if len(pass_and_params) > 1:
                        params = pass_and_params[1].split('&')
                        for param in params:
                            if param.startswith('obfsparam='):
                                obfs_param_b64 = param[10:]
                                if obfs_param_b64:
                                    obfs_param_b64 = obfs_param_b64.replace('-', '+').replace('_', '/')
                                    padding_needed = len(obfs_param_b64) % 4
                                    if padding_needed:
                                        obfs_param_b64 += '=' * (4 - padding_needed)
                                    obfs_param = base64.b64decode(obfs_param_b64).decode('utf-8')
                            elif param.startswith('protoparam='):
                                protocol_param_b64 = param[11:]
                                if protocol_param_b64:
                                    protocol_param_b64 = protocol_param_b64.replace('-', '+').replace('_', '/')
                                    padding_needed = len(protocol_param_b64) % 4
                                    if padding_needed:
                                        protocol_param_b64 += '=' * (4 - padding_needed)
                                    protocol_param = base64.b64decode(protocol_param_b64).decode('utf-8')
                            elif param.startswith('remarks='):
                                remarks_b64 = param[8:]
                                if remarks_b64:
                                    remarks_b64 = remarks_b64.replace('-', '+').replace('_', '/')
                                    padding_needed = len(remarks_b64) % 4
                                    if padding_needed:
                                        remarks_b64 += '=' * (4 - padding_needed)
                                    remarks = base64.b64decode(remarks_b64).decode('utf-8')

                    return Node(
                        name=remarks,
                        address=server,
                        port=port,
                        password=password,
                        method=method,
                        obfs=obfs,
                        obfs_param=obfs_param,
                        protocol=protocol,
                        protocol_param=protocol_param
                    )
            except Exception as e:
                logger.warning(f"解析SSR链接失败: {str(e)}")
        return None

    def _parse_ss_subscription(self, content):
        """解析Shadowsocks订阅"""
        nodes = []

        try:
            # 尝试Base64解码
            try:
                # 移除可能的URL安全字符
                content_str = content.decode('utf-8', errors='ignore')
                content_str = content_str.replace('-', '+').replace('_', '/')

                # 添加填充字符以确保长度是4的倍数
                padding_needed = len(content_str) % 4
                if padding_needed:
                    content_str += '=' * (4 - padding_needed)

                # 尝试解码
                decoded_content = base64.b64decode(content_str).decode('utf-8')
                logger.info(f"成功解码Base64订阅内容，解码后长度: {len(decoded_content)}")
            except Exception as e:
                # 如果解码失败，使用原始内容
                logger.warning(f"Base64解码失败，使用原始内容: {str(e)}")
                decoded_content = content.decode('utf-8', errors='ignore')

            # 按行分割
            ss_urls = decoded_content.strip().split('\n')

            for i, ss_url in enumerate(ss_urls):
                ss_url = ss_url.strip()
                if not ss_url:
                    continue

                if ss_url.startswith('ss://'):
                    try:
                        # 解析SS URL
                        node = self._parse_ss_url(ss_url, i)
                        if node:
                            nodes.append(node)
                            logger.info(f"成功解析SS链接: {node.name}")
                    except Exception as e:
                        logger.error(f"解析SS URL失败: {ss_url}, 错误: {str(e)}")

            # 如果没有解析出节点，尝试解析为JSON
            if not nodes:
                try:
                    data = json.loads(decoded_content)
                    nodes.extend(self._parse_json_nodes(data))
                except:
                    pass

        except Exception as e:
            logger.error(f"解析SS订阅失败: {str(e)}")

        return nodes

    def _parse_ss_url(self, ss_url, index=0):
        """解析单个SS URL"""
        # SS URL格式: ss://BASE64(method:password)@server:port#name
        try:
            name = f"SS节点-{index+1}"

            if '#' in ss_url:
                ss_url, name_part = ss_url.split('#', 1)
                name = unquote(name_part)

            if '@' in ss_url:
                # 新格式: ss://BASE64(method:password)@server:port
                encoded, server_port = ss_url[5:].split('@', 1)

                # 解码method:password
                try:
                    # 尝试Base64解码
                    encoded = encoded.replace('-', '+').replace('_', '/')
                    padding_needed = len(encoded) % 4
                    if padding_needed:
                        encoded += '=' * (4 - padding_needed)
                    decoded = base64.b64decode(encoded).decode('utf-8')
                    method, password = decoded.split(':', 1)
                except:
                    # 如果解码失败，可能是URL编码
                    method, password = unquote(encoded).split(':', 1)

                # 解析服务器和端口
                if ':' in server_port:
                    server, port = server_port.split(':', 1)
                    port = int(port)
                else:
                    server = server_port
                    port = 443  # 默认端口
            else:
                # 旧格式: ss://BASE64(method:password@server:port)
                encoded = ss_url[5:]

                # 解码
                encoded = encoded.replace('-', '+').replace('_', '/')
                padding_needed = len(encoded) % 4
                if padding_needed:
                    encoded += '=' * (4 - padding_needed)
                decoded = base64.b64decode(encoded).decode('utf-8')

                # 解析
                if '@' in decoded:
                    method_pwd, server_port = decoded.split('@', 1)
                    method, password = method_pwd.split(':', 1)

                    if ':' in server_port:
                        server, port = server_port.split(':', 1)
                        port = int(port)
                    else:
                        server = server_port
                        port = 443  # 默认端口
                else:
                    # 可能是SIP002格式的变种
                    parts = decoded.split(':')
                    if len(parts) >= 3:
                        method = parts[0]
                        password = parts[1]
                        server = parts[2]
                        port = int(parts[3]) if len(parts) > 3 else 443
                    else:
                        raise ValueError("无效的SS URL格式")

            # 创建节点对象
            return Node(
                name=name,
                address=server,
                port=port,
                password=password,
                method=method,
                protocol="origin",  # SS默认使用origin协议
                obfs="plain"  # SS默认使用plain混淆
            )
        except Exception as e:
            logger.error(f"解析SS URL失败: {str(e)}")
            return None

    def _parse_clash_subscription(self, content):
        """解析Clash订阅"""
        nodes = []

        try:
            # 解析YAML内容
            content_str = content.decode('utf-8', errors='ignore')

            # 尝试作为YAML解析
            if yaml:
                try:
                    clash_config = yaml.safe_load(content_str)
                except:
                    # 如果YAML解析失败，尝试作为JSON解析
                    try:
                        clash_config = json.loads(content_str)
                    except:
                        logger.error("无法解析Clash配置，既不是有效的YAML也不是有效的JSON")
                        return nodes
            else:
                # 如果没有yaml模块，尝试作为JSON解析
                try:
                    clash_config = json.loads(content_str)
                except:
                    logger.error("无法解析Clash配置，缺少yaml模块且不是有效的JSON")
                    return nodes

            # 处理proxies字段
            if "proxies" in clash_config and isinstance(clash_config["proxies"], list):
                for i, proxy in enumerate(clash_config["proxies"]):
                    try:
                        # 处理不同类型的代理
                        proxy_type = proxy.get("type", "").lower()

                        if proxy_type in ["ss", "shadowsocks"]:
                            # 处理Shadowsocks代理
                            node = Node(
                                name=proxy.get("name", f"Clash-SS-{i+1}"),
                                address=proxy.get("server", ""),
                                port=int(proxy.get("port", 0)),
                                password=proxy.get("password", ""),
                                method=proxy.get("cipher", ""),
                                protocol="origin",
                                obfs="plain"
                            )

                            # 处理插件信息
                            if "plugin" in proxy:
                                plugin = proxy.get("plugin", "")
                                plugin_opts = proxy.get("plugin-opts", {})

                                if plugin == "obfs":
                                    node.obfs = plugin_opts.get("mode", "plain")
                                    node.obfs_param = plugin_opts.get("host", "")

                            if node.address and node.port > 0 and node.password and node.method:
                                nodes.append(node)
                                logger.info(f"成功解析Clash-SS节点: {node.name}")

                        elif proxy_type in ["ssr", "shadowsocksr"]:
                            # 处理ShadowsocksR代理
                            node = Node(
                                name=proxy.get("name", f"Clash-SSR-{i+1}"),
                                address=proxy.get("server", ""),
                                port=int(proxy.get("port", 0)),
                                password=proxy.get("password", ""),
                                method=proxy.get("cipher", ""),
                                protocol=proxy.get("protocol", "origin"),
                                protocol_param=proxy.get("protocol-param", ""),
                                obfs=proxy.get("obfs", "plain"),
                                obfs_param=proxy.get("obfs-param", "")
                            )

                            if node.address and node.port > 0 and node.password and node.method:
                                nodes.append(node)
                                logger.info(f"成功解析Clash-SSR节点: {node.name}")
                    except Exception as e:
                        logger.error(f"解析Clash代理失败: {str(e)}")
        except Exception as e:
            logger.error(f"解析Clash订阅失败: {str(e)}")

        return nodes

    def _parse_json_nodes(self, data):
        """解析JSON格式的节点数据"""
        nodes = []

        try:
            # 处理单个节点的情况
            if isinstance(data, dict):
                if "server" in data and "server_port" in data:
                    # SS/SSR单节点格式
                    name = data.get("name", f"JSON节点-1")
                    node = Node(
                        name=name,
                        address=data.get("server"),
                        port=data.get("server_port"),
                        password=data.get("password"),
                        method=data.get("method"),
                        obfs=data.get("obfs", "plain"),
                        obfs_param=data.get("obfs_param", ""),
                        protocol=data.get("protocol", "origin"),
                        protocol_param=data.get("protocol_param", "")
                    )
                    nodes.append(node)
                    logger.info(f"成功解析JSON单节点: {name}")

            # 处理节点数组
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        if "server" in item and "server_port" in item:
                            # SS/SSR节点格式
                            name = item.get("name", f"JSON节点-{i+1}")
                            node = Node(
                                name=name,
                                address=item.get("server"),
                                port=item.get("server_port"),
                                password=item.get("password"),
                                method=item.get("method"),
                                obfs=item.get("obfs", "plain"),
                                obfs_param=item.get("obfs_param", ""),
                                protocol=item.get("protocol", "origin"),
                                protocol_param=item.get("protocol_param", "")
                            )
                            nodes.append(node)
                            logger.info(f"成功解析JSON数组节点: {name}")

            # 处理包含nodes字段的格式
            elif isinstance(data, dict) and "nodes" in data and isinstance(data["nodes"], list):
                for i, item in enumerate(data["nodes"]):
                    if isinstance(item, dict):
                        if "server" in item and "server_port" in item:
                            # SS/SSR节点格式
                            name = item.get("name", f"JSON节点-{i+1}")
                            node = Node(
                                name=name,
                                address=item.get("server"),
                                port=item.get("server_port"),
                                password=item.get("password"),
                                method=item.get("method"),
                                obfs=item.get("obfs", "plain"),
                                obfs_param=item.get("obfs_param", ""),
                                protocol=item.get("protocol", "origin"),
                                protocol_param=item.get("protocol_param", "")
                            )
                            nodes.append(node)
                            logger.info(f"成功解析nodes字段节点: {name}")
        except Exception as e:
            logger.error(f"解析JSON节点数据失败: {str(e)}")

        return nodes

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

            # 首先检查是否有自定义节点，如果有，优先使用
            custom_nodes = [node for node in available_nodes if node.name.startswith("自定义节点")]
            if custom_nodes and self.options.get("use_custom_node", False):
                # 使用第一个可用的自定义节点
                self.current_node = custom_nodes[0]
                logger.info(f"强制使用自定义节点: {self.current_node.name}")
                return True

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
                    # 记住当前节点
                    current_node_name = self.current_node.name if self.current_node else None

                    # 更新订阅
                    self.update_subscription()

                    # 如果当前没有使用自定义节点，或者更新订阅导致节点变化，则重新选择节点
                    if not (current_node_name and current_node_name.startswith("自定义节点")):
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
        # 检查sock2是否为SSR客户端
        is_ssr_client = hasattr(sock2, '__class__') and sock2.__class__.__name__ == 'SSRClient'

        if is_ssr_client:
            # 使用SSR客户端进行数据转发
            self._proxy_process_ssr(sock1, sock2)
        else:
            # 使用普通socket进行数据转发
            self._proxy_process_normal(sock1, sock2)

    def _proxy_process_normal(self, sock1, sock2):
        """普通socket之间的数据转发"""
        sel = DefaultSelector()
        sel.register(sock1, EVENT_READ)
        sel.register(sock2, EVENT_READ)

        # 获取连接信息用于日志
        try:
            local_addr = sock1.getpeername()
            remote_addr = sock2.getpeername()
            connection_info = f"本地({local_addr[0]}:{local_addr[1]}) <-> 远程({remote_addr[0]}:{remote_addr[1]})"
            logger.info(f"开始数据转发: {connection_info}")
        except:
            connection_info = "未知连接"

        # 统计变量
        bytes_sent = 0
        bytes_received = 0
        last_log_time = time.time()

        while True:
            try:
                events = sel.select(timeout=1.0)

                # 定期记录流量统计
                current_time = time.time()
                if current_time - last_log_time > 30:  # 每30秒记录一次
                    if bytes_sent > 0 or bytes_received > 0:
                        logger.info(f"连接 {connection_info} 流量统计: 发送={bytes_sent}字节, 接收={bytes_received}字节")
                    last_log_time = current_time

                if not events:  # 超时，继续循环
                    continue

                for (key, _) in events:
                    try:
                        data_in = key.fileobj.recv(8192)
                    except ConnectionResetError as e:
                        logger.error(f"连接重置: {str(e)}")
                        sock1.close()
                        sock2.close()
                        self.update_stats(connection_change=-1)
                        logger.info(f"连接关闭 {connection_info}: 连接重置")
                        return
                    except Exception as e:
                        logger.error(f"数据接收错误: {str(e)}")
                        sock1.close()
                        sock2.close()
                        self.update_stats(connection_change=-1)
                        logger.info(f"连接关闭 {connection_info}: 数据接收错误")
                        return

                    if data_in:
                        # 更新流量统计
                        data_len = len(data_in)
                        self.update_stats(traffic=data_len)

                        try:
                            if key.fileobj == sock1:
                                # 本地 -> 远程
                                bytes_sent += data_len
                                sock2.send(data_in)  # 直接发送数据，不进行XOR编码
                            else:
                                # 远程 -> 本地
                                bytes_received += data_len
                                sock1.send(data_in)  # 直接发送数据，不进行XOR编码
                        except Exception as e:
                            logger.error(f"数据发送错误: {str(e)}")
                            sock1.close()
                            sock2.close()
                            self.update_stats(connection_change=-1)
                            logger.info(f"连接关闭 {connection_info}: 数据发送错误")
                            return
                    else:
                        sock1.close()
                        sock2.close()
                        self.update_stats(connection_change=-1)
                        logger.info(f"连接关闭 {connection_info}: 正常关闭, 总流量: 发送={bytes_sent}字节, 接收={bytes_received}字节")
                        return
            except Exception as e:
                logger.error(f"代理处理错误: {str(e)}")
                try:
                    sock1.close()
                    sock2.close()
                except:
                    pass
                self.update_stats(connection_change=-1)
                logger.info(f"连接关闭 {connection_info}: 代理处理错误")
                return

    def _proxy_process_ssr(self, sock_local, ssr_connection):
        """SSR连接的数据转发"""
        logger.info("开始SSR数据转发")

        # 获取连接信息用于日志
        try:
            local_addr = sock_local.getpeername()
            remote_addr = ssr_connection.getpeername()
            connection_info = f"本地({local_addr[0]}:{local_addr[1]}) <-> SSR远程({remote_addr[0]}:{remote_addr[1]})"
            logger.info(f"开始SSR数据转发: {connection_info}")
        except:
            connection_info = "SSR连接"

        # 统计变量
        bytes_sent = 0
        bytes_received = 0
        last_log_time = time.time()

        # 创建线程来处理双向数据转发
        def local_to_remote():
            nonlocal bytes_sent
            try:
                while True:
                    data = sock_local.recv(8192)
                    if not data:
                        break

                    # 通过SSR连接发送数据
                    ssr_connection.send(data)
                    bytes_sent += len(data)
                    self.update_stats(traffic=len(data))

                    logger.debug(f"本地->SSR远程: {len(data)}字节")

            except Exception as e:
                logger.error(f"本地到SSR远程数据转发错误: {str(e)}")
            finally:
                try:
                    sock_local.close()
                    ssr_connection.close()
                except:
                    pass

        def remote_to_local():
            nonlocal bytes_received
            try:
                while True:
                    # 从SSR连接接收数据
                    data = ssr_connection.recv(8192)
                    if not data:
                        break

                    # 发送到本地连接
                    sock_local.send(data)
                    bytes_received += len(data)
                    self.update_stats(traffic=len(data))

                    logger.debug(f"SSR远程->本地: {len(data)}字节")

            except Exception as e:
                logger.error(f"SSR远程到本地数据转发错误: {str(e)}")
            finally:
                try:
                    sock_local.close()
                    ssr_connection.close()
                except:
                    pass

        # 启动双向转发线程
        thread1 = threading.Thread(target=local_to_remote)
        thread2 = threading.Thread(target=remote_to_local)

        thread1.daemon = True
        thread2.daemon = True

        thread1.start()
        thread2.start()

        # 等待线程结束
        thread1.join()
        thread2.join()

        self.update_stats(connection_change=-1)
        logger.info(f"SSR连接关闭 {connection_info}, 总流量: 发送={bytes_sent}字节, 接收={bytes_received}字节")

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

        logger.info(f"使用节点: {node.name}")

        # 尝试解析HTTP请求，支持HTTP代理
        try:
            sock_in.settimeout(5)
            data = sock_in.recv(4096)

            # 检查是否是HTTP CONNECT请求
            if data.startswith(b'CONNECT'):
                # 解析目标地址
                first_line = data.split(b'\r\n')[0].decode('utf-8')
                target = first_line.split(' ')[1]
                logger.info(f"收到HTTP CONNECT请求: {target}")

                host, port = target.split(':')
                port = int(port)

                # 发送连接成功响应
                sock_in.send(b'HTTP/1.1 200 Connection Established\r\n\r\n')

                try:
                    logger.info(f"通过节点 {node.name} 连接到目标: {host}:{port}")

                    # 建立远程连接
                    remote_connection = self._create_remote_connection(node)
                    if not remote_connection:
                        logger.error(f"无法创建到远程节点的连接")
                        sock_in.close()
                        self.update_stats(connection_change=-1)
                        return

                    # 检查是否为SSR客户端
                    if hasattr(remote_connection, '__class__') and remote_connection.__class__.__name__ == 'SSRClient':
                        # SSR连接：需要先建立到目标的连接
                        ssr_connection = remote_connection.create_connection(host, port)
                        if not ssr_connection:
                            logger.error(f"SSR连接到目标 {host}:{port} 失败")
                            sock_in.close()
                            self.update_stats(connection_change=-1)
                            return

                        logger.info(f"SSR连接已建立到目标: {host}:{port}")
                        # 使用SSR连接进行数据转发
                        self.proxy_process(sock_in, ssr_connection)
                    else:
                        # 普通TCP连接：需要手动发送CONNECT请求
                        connect_request = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
                        remote_connection.send(connect_request.encode())

                        # 接收响应
                        response = remote_connection.recv(1024)
                        if b"200" not in response:
                            logger.error(f"代理服务器拒绝连接到 {host}:{port}")
                            remote_connection.close()
                            sock_in.close()
                            self.update_stats(connection_change=-1)
                            return

                        logger.info(f"普通代理连接已建立到目标: {host}:{port}")
                        # 在本地连接与远程连接间转发数据
                        self.proxy_process(sock_in, remote_connection)

                    return
                except Exception as e:
                    logger.error(f"连接到目标 {host}:{port} 失败: {str(e)}")
                    sock_in.close()
                    self.update_stats(connection_change=-1)
                    return

            # 如果不是HTTP CONNECT请求，回退到普通代理模式
            logger.info("非HTTP CONNECT请求，使用普通代理模式")
        except socket.timeout:
            logger.info("接收数据超时，使用普通代理模式")
        except Exception as e:
            logger.warning(f"解析HTTP请求失败: {str(e)}，使用普通代理模式")

        # 重置socket超时
        sock_in.settimeout(None)

        # 建立远程连接
        sock_remote = self._create_remote_connection(node)
        if not sock_remote:
            # 尝试重新选择节点
            if self.select_node("auto"):
                node = self.get_current_node()
                logger.info(f"尝试使用备用节点: {node.name} ({node.address}:{node.port})")
                sock_remote = self._create_remote_connection(node)
                if sock_remote:
                    logger.info(f"已切换到备用节点 {node.name} 并成功连接")
                else:
                    logger.error(f"连接到备用节点失败")
                    sock_in.close()
                    self.update_stats(connection_change=-1)
                    return
            else:
                logger.error("没有可用的备用节点")
                sock_in.close()
                self.update_stats(connection_change=-1)
                return

        # 在本地连接与远程连接间转发数据
        logger.info(f"开始在本地连接 {addr[0]}:{addr[1]} 和远程节点 {node.address}:{node.port} 之间转发数据")
        self.proxy_process(sock_in, sock_remote)

    def _create_remote_connection(self, node):
        """创建到远程节点的连接"""
        try:
            # 对于SSR节点，我们需要特殊处理
            if hasattr(node, 'password') and node.password:
                logger.info(f"检测到SSR节点: {node.name}")

                # 检查加密库是否可用
                try:
                    from ssr_client import CRYPTO_AVAILABLE
                    if CRYPTO_AVAILABLE and SSRClient:
                        logger.info(f"使用SSR协议连接到节点: {node.name}")

                        # 创建SSR客户端
                        ssr_client = SSRClient(
                            server=node.address,
                            port=node.port,
                            password=node.password,
                            method=getattr(node, 'method', 'rc4-md5'),
                            protocol=getattr(node, 'protocol', 'origin'),
                            obfs=getattr(node, 'obfs', 'plain'),
                            protocol_param=getattr(node, 'protocol_param', ''),
                            obfs_param=getattr(node, 'obfs_param', '')
                        )

                        return ssr_client
                    else:
                        logger.warning("加密库不可用，SSR节点无法使用普通TCP连接")
                        return None
                except ImportError:
                    logger.warning("SSR模块不可用，SSR节点无法使用")
                    return None

            # 普通TCP连接（仅用于非SSR节点）
            logger.info(f"使用普通TCP连接到节点: {node.address}:{node.port}")
            sock_remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_remote.settimeout(15)
            sock_remote.connect((node.address, node.port))
            logger.info(f"成功连接到远程节点: {node.address}:{node.port}")
            return sock_remote

        except Exception as e:
            logger.error(f"连接到远程节点 {node.name} ({node.address}:{node.port}) 失败: {str(e)}")
            return None

    def start_proxy_server(self):
        """启动代理服务器"""
        local_port = self.options.get("local_port", 7088)

        def server_thread():
            try:
                # 创建服务器socket
                server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_sock.bind(("0.0.0.0", local_port))
                server_sock.listen(128)

                logger.info(f"代理服务器已启动，监听端口: {local_port}")

                while True:
                    try:
                        client_sock, addr = server_sock.accept()
                        # 为每个连接创建新线程
                        client_thread = threading.Thread(
                            target=self.handle_connection,
                            args=(client_sock, addr),
                            daemon=True
                        )
                        client_thread.start()
                    except Exception as e:
                        logger.error(f"接受连接失败: {str(e)}")

            except Exception as e:
                logger.error(f"代理服务器启动失败: {str(e)}")
                print(f"代理服务器启动失败: {str(e)}")

        # 启动服务器线程
        server_thread_obj = threading.Thread(target=server_thread, daemon=True)
        server_thread_obj.start()

        return True

    def test_connection(self):
        """测试代理连接是否正常工作"""
        logger.info("开始测试代理连接...")

        # 存储站点测试结果
        self._site_test_results = {}

        # 测试国际网站和Home Assistant相关网站
        test_sites = [
            ("www.google.com", 443, "国际"),
            ("github.com", 443, "Home Assistant"),
            ("raw.githubusercontent.com", 443, "Home Assistant"),
            ("pypi.org", 443, "Home Assistant"),
            ("registry.npmjs.org", 443, "Home Assistant")
        ]

        # 获取当前节点
        node = self.get_current_node()
        if not node:
            logger.error("没有可用节点，无法测试连接")
            return False

        success_count_international = 0

        for site, port, site_type in test_sites:
            try:
                logger.info(f"测试连接到 {site}:{port} ({site_type}网站)...")

                # 使用更简单的方法测试连接
                local_port = self.options.get("local_port", 7088)
                logger.info(f"尝试通过本地代理(127.0.0.1:{local_port})连接到 {site}:{port}...")

                # 创建到代理服务器的连接
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(15)  # 增加超时时间

                try:
                    # 连接到本地代理
                    sock.connect(("127.0.0.1", local_port))

                    # 构造HTTP CONNECT请求
                    connect_request = f"CONNECT {site}:{port} HTTP/1.1\r\nHost: {site}:{port}\r\nUser-Agent: Mozilla/5.0\r\nConnection: keep-alive\r\n\r\n"
                    sock.send(connect_request.encode())

                    # 接收响应
                    response = b""
                    sock.settimeout(5)
                    try:
                        response = sock.recv(4096)
                    except socket.timeout:
                        logger.warning(f"接收代理响应超时")

                    if response and b"200 Connection Established" in response:
                        logger.info(f"✅ 代理连接建立成功，开始测试数据传输...")

                        # 发送简单的HTTP请求
                        http_request = f"GET / HTTP/1.1\r\nHost: {site}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n"
                        sock.send(http_request.encode())

                        # 接收响应
                        sock.settimeout(10)
                        data = b""
                        try:
                            while True:
                                chunk = sock.recv(4096)
                                if not chunk:
                                    break
                                data += chunk
                                if len(data) > 1024:  # 只需要接收一部分数据即可
                                    break
                        except socket.timeout:
                            if len(data) > 0:
                                logger.info(f"接收数据超时，但已收到 {len(data)} 字节")
                            else:
                                logger.warning(f"接收数据超时，未收到任何数据")

                        if data:
                            logger.info(f"✅ 成功从 {site} 接收到 {len(data)} 字节数据")
                            success_count_international += 1
                            self._site_test_results[site] = True
                        else:
                            logger.warning(f"❌ 未能从 {site} 接收到数据")
                            self._site_test_results[site] = False
                    else:
                        logger.warning(f"❌ 代理连接建立失败: {response}")
                        self._site_test_results[site] = False

                    sock.close()
                except Exception as e:
                    logger.warning(f"❌ 连接到代理服务器失败: {str(e)}")
                    self._site_test_results[site] = False
            except Exception as e:
                logger.warning(f"❌ 测试连接到 {site}:{port} 失败: {str(e)}")
                self._site_test_results[site] = False

        # 输出测试结果摘要
        total_sites = len(test_sites)
        ha_sites = [site for site in test_sites if site[2] == "Home Assistant"]
        total_ha_sites = len(ha_sites)
        success_ha_sites = sum(1 for site in test_sites if site[2] == "Home Assistant" and self._site_test_results.get(site[0], False))

        logger.info(f"代理连接测试完成:")
        logger.info(f"- 总计: {success_count_international}/{total_sites} 个连接成功")
        logger.info(f"- Home Assistant相关网站: {success_ha_sites}/{total_ha_sites} 个连接成功")

        # 记录每个站点的测试结果
        logger.info("详细测试结果:")
        for site, port, site_type in test_sites:
            result = "✅ 成功" if self._site_test_results.get(site, False) else "❌ 失败"
            logger.info(f"  - {site} ({site_type}): {result}")

        # 判断代理是否正常工作
        if success_count_international > 0:
            logger.info("✅ 代理连接测试通过: 可以访问国际网站")
            if success_ha_sites > 0:
                logger.info("✅ Home Assistant升级应该可以正常工作")
            else:
                logger.warning("⚠️ 无法连接到Home Assistant相关网站，升级可能会失败")
            return True
        else:
            logger.error("❌ 代理连接测试失败: 无法访问任何测试网站")
            logger.info("请检查节点配置是否正确，特别是服务器地址、端口、加密方式等")
            return False



    def _configure_ha_proxy(self, local_port):
        """尝试自动配置Home Assistant使用代理"""
        try:
            # 检查Home Assistant配置文件是否存在
            ha_config_path = "/config/configuration.yaml"
            if not os.path.exists(ha_config_path):
                logger.warning(f"未找到Home Assistant配置文件: {ha_config_path}")
                return

            # 读取配置文件
            with open(ha_config_path, 'r') as f:
                config_content = f.read()

            # 检查是否已经配置了代理
            if "proxy_host: 127.0.0.1" in config_content and f"proxy_port: {local_port}" in config_content:
                logger.info("Home Assistant已配置使用代理")
                return

            # 添加或更新代理配置
            http_section = re.search(r'http:(\s+.*?)((\r?\n\w+:|$))', config_content, re.DOTALL)
            if http_section:
                # 已存在http部分，检查是否有代理配置
                http_content = http_section.group(1)
                if "proxy_host:" in http_content:
                    # 更新现有代理配置
                    new_http_content = re.sub(
                        r'proxy_host:.*?(\r?\n)',
                        f'proxy_host: 127.0.0.1\n',
                        http_content
                    )
                    new_http_content = re.sub(
                        r'proxy_port:.*?(\r?\n)',
                        f'proxy_port: {local_port}\n',
                        new_http_content
                    )
                    new_config = config_content.replace(http_content, new_http_content)
                else:
                    # 添加代理配置到http部分
                    new_http_content = http_content + f"\n  proxy_host: 127.0.0.1\n  proxy_port: {local_port}"
                    new_config = config_content.replace(http_content, new_http_content)
            else:
                # 不存在http部分，添加新的http部分
                new_config = config_content + f"\nhttp:\n  proxy_host: 127.0.0.1\n  proxy_port: {local_port}\n"

            # 备份原配置文件
            backup_path = f"{ha_config_path}.backup"
            with open(backup_path, 'w') as f:
                f.write(config_content)

            # 写入新配置
            with open(ha_config_path, 'w') as f:
                f.write(new_config)

            logger.info(f"已自动配置Home Assistant使用代理 (127.0.0.1:{local_port})")
            logger.info(f"原配置已备份到 {backup_path}")
            logger.info("请重启Home Assistant以使配置生效")

        except Exception as e:
            logger.warning(f"自动配置Home Assistant代理失败: {str(e)}")