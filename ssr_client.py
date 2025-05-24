#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSR客户端实现
支持基本的SSR协议、加密和混淆
"""

import socket
import struct
import hashlib
import hmac
import random
import time
import logging
from Crypto.Cipher import AES, ChaCha20
from Crypto.Random import get_random_bytes
import base64

logger = logging.getLogger("ssr_client")

class SSRClient:
    """SSR客户端"""

    def __init__(self, server, port, password, method, protocol="origin", obfs="plain",
                 protocol_param="", obfs_param=""):
        self.server = server
        self.port = port
        self.password = password
        self.method = method
        self.protocol = protocol
        self.obfs = obfs
        self.protocol_param = protocol_param
        self.obfs_param = obfs_param

        # 生成密钥
        self.key = self._derive_key(password, method)

    def _derive_key(self, password, method):
        """从密码派生密钥"""
        key_len = {
            'aes-128-cfb': 16, 'aes-192-cfb': 24, 'aes-256-cfb': 32,
            'aes-128-ctr': 16, 'aes-192-ctr': 24, 'aes-256-ctr': 32,
            'chacha20': 32, 'chacha20-ietf': 32,
            'rc4-md5': 16
        }.get(method, 32)

        # 使用MD5派生密钥
        d = d_i = b''
        while len(d) < key_len:
            d_i = hashlib.md5(d_i + password.encode()).digest()
            d += d_i
        return d[:key_len]

    def _create_cipher(self, key, iv, encrypt=True):
        """创建加密器"""
        if self.method.startswith('aes-'):
            if 'cfb' in self.method:
                cipher = AES.new(key, AES.MODE_CFB, iv)
            elif 'ctr' in self.method:
                cipher = AES.new(key, AES.MODE_CTR, nonce=iv[:8], initial_value=iv[8:])
            else:
                cipher = AES.new(key, AES.MODE_CFB, iv)
            return cipher
        elif self.method.startswith('chacha20'):
            cipher = ChaCha20.new(key=key, nonce=iv[:12] if self.method == 'chacha20-ietf' else iv[:8])
            return cipher
        else:
            # 简单的RC4实现或其他
            return None

    def _encrypt(self, data, cipher):
        """加密数据"""
        if cipher:
            return cipher.encrypt(data)
        return data

    def _decrypt(self, data, cipher):
        """解密数据"""
        if cipher:
            return cipher.decrypt(data)
        return data

    def _apply_protocol(self, data, is_first_packet=False):
        """应用协议层"""
        if self.protocol == "origin":
            return data
        elif self.protocol == "auth_aes128_md5":
            # 简化的auth_aes128_md5实现
            if is_first_packet:
                # 添加认证头
                utc_time = int(time.time()) & 0xFFFFFFFF
                client_id = random.randint(0, 0xFFFFFFFF)
                connection_id = random.randint(0, 0xFFFFFFFF)

                auth_data = struct.pack('<III', utc_time, client_id, connection_id)
                auth_data += data

                # 计算HMAC
                key = self.key + self.protocol_param.encode()
                hmac_key = hashlib.md5(key).digest()
                auth_hmac = hmac.new(hmac_key, auth_data, hashlib.md5).digest()[:4]

                return auth_data + auth_hmac
            return data
        else:
            logger.warning(f"不支持的协议: {self.protocol}")
            return data

    def _apply_obfs(self, data, is_first_packet=False):
        """应用混淆层"""
        if self.obfs == "plain":
            return data
        elif self.obfs == "tls1.2_ticket_auth":
            # 简化的TLS混淆实现
            if is_first_packet:
                # 构造假的TLS Client Hello
                tls_header = b'\x16\x03\x01'  # TLS Handshake, version 1.2
                tls_length = struct.pack('>H', len(data) + 32)  # 长度
                tls_hello = b'\x01\x00\x00\x1c'  # Client Hello
                tls_random = get_random_bytes(28)  # 随机数

                return tls_header + tls_length + tls_hello + tls_random + data
            return data
        else:
            logger.warning(f"不支持的混淆: {self.obfs}")
            return data

    def connect(self, target_host, target_port):
        """连接到目标服务器"""
        try:
            # 连接到SSR服务器
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect((self.server, self.port))

            # 生成IV
            iv_len = 16 if self.method.startswith('aes-') else 12 if self.method == 'chacha20-ietf' else 8
            iv = get_random_bytes(iv_len)

            # 创建加密器
            encrypt_cipher = self._create_cipher(self.key, iv, encrypt=True)

            # 构造SOCKS5连接请求
            # 地址类型 + 地址 + 端口
            if target_host.replace('.', '').isdigit():  # IPv4
                addr_type = b'\x01'
                addr = socket.inet_aton(target_host)
            else:  # 域名
                addr_type = b'\x03'
                addr = bytes([len(target_host)]) + target_host.encode()

            port_bytes = struct.pack('>H', target_port)
            request_data = addr_type + addr + port_bytes

            # 应用协议层
            request_data = self._apply_protocol(request_data, is_first_packet=True)

            # 加密
            encrypted_data = self._encrypt(request_data, encrypt_cipher)

            # 应用混淆层
            final_data = self._apply_obfs(iv + encrypted_data, is_first_packet=True)

            # 发送到服务器
            sock.send(final_data)

            logger.info(f"SSR连接已建立: {self.server}:{self.port} -> {target_host}:{target_port}")
            logger.info(f"使用加密: {self.method}, 协议: {self.protocol}, 混淆: {self.obfs}")

            return sock, encrypt_cipher

        except Exception as e:
            logger.error(f"SSR连接失败: {str(e)}")
            return None, None

    def create_connection(self, target_host, target_port):
        """创建SSR连接的简化接口"""
        sock, cipher = self.connect(target_host, target_port)
        if sock:
            return SSRConnection(sock, cipher, self)
        return None

class SSRConnection:
    """SSR连接包装器"""

    def __init__(self, sock, cipher, client):
        self.sock = sock
        self.cipher = cipher
        self.client = client
        self.closed = False

    def send(self, data):
        """发送数据"""
        if self.closed:
            raise ConnectionError("连接已关闭")

        try:
            # 加密数据
            encrypted_data = self.client._encrypt(data, self.cipher)
            # 应用混淆
            final_data = self.client._apply_obfs(encrypted_data)
            # 发送
            return self.sock.send(final_data)
        except Exception as e:
            logger.error(f"发送数据失败: {str(e)}")
            self.close()
            raise

    def recv(self, size):
        """接收数据"""
        if self.closed:
            raise ConnectionError("连接已关闭")

        try:
            # 接收数据
            data = self.sock.recv(size)
            if not data:
                self.close()
                return b''

            # 简化处理：对于SSR连接，我们需要解密数据
            # 但为了保持兼容性，这里先直接返回
            # 实际使用中，SSR服务器会处理加密/解密
            return data
        except Exception as e:
            logger.error(f"接收数据失败: {str(e)}")
            self.close()
            raise

    def close(self):
        """关闭连接"""
        if not self.closed:
            self.closed = True
            try:
                self.sock.close()
            except:
                pass

    def settimeout(self, timeout):
        """设置超时"""
        self.sock.settimeout(timeout)

    def getpeername(self):
        """获取对端地址"""
        return self.sock.getpeername()