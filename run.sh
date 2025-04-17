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

# 确保 templates 目录存在
mkdir -p /app/templates

# 运行主程序
cd /app
exec python3 /app/main.py 