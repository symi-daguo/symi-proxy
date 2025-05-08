#!/bin/bash

echo "Starting Symi Proxy..."

# 输出配置信息
echo "读取配置..."
CONFIG_PATH=/data/options.json
LOCAL_PORT=$(jq -r '.local_port // 7088' $CONFIG_PATH)
SUBSCRIPTION_URL=$(jq -r '.subscription_url // ""' $CONFIG_PATH)
SUBSCRIPTION_UPDATE_INTERVAL=$(jq -r '.subscription_update_interval // 24' $CONFIG_PATH)
DEFAULT_NODE=$(jq -r '.default_node // "auto"' $CONFIG_PATH)

echo "本地端口: ${LOCAL_PORT}"
echo "订阅更新间隔: ${SUBSCRIPTION_UPDATE_INTERVAL} 小时"

# 确保iptables可用
if ! command -v iptables >/dev/null 2>&1; then
    echo "iptables not found, installing..."
    apk add --no-cache iptables
fi

# 确保 templates 目录存在并有正确的权限
mkdir -p /app/templates
chmod 755 /app/templates

# 检查Python和依赖
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python3 not found, installing..."
    apk update
    apk add --no-cache python3
fi

if ! python3 -c "import requests" 2>/dev/null; then
    echo "Python requests module not found, installing..."
    if command -v pip3 >/dev/null 2>&1; then
        pip3 install requests
    else
        apk add --no-cache py3-pip
        pip3 install requests
    fi
fi

# 运行主程序
cd /app
echo "启动Symi Proxy主程序..."
exec python3 /app/main.py