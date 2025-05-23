#!/bin/bash

echo "Starting Symi Proxy..."

# 确保基本目录存在
mkdir -p /data
mkdir -p /app/templates
chmod 755 /app/templates

# 创建默认配置（如果不存在）
if [ ! -f "/data/options.json" ]; then
    echo "创建默认配置文件..."
    cat > /data/options.json << EOF
{
    "local_port": 7088,
    "web_port": 8123,
    "subscription_url": "https://example.com/subscribe/demo?format=ssr",
    "subscription_update_interval": 12,
    "default_node": "auto",
    "use_custom_node": true,
    "custom_node": {
        "server": "d3.alibabamysql.com",
        "server_port": 7001,
        "password": "di15PV",
        "method": "chacha20-ietf",
        "protocol": "auth_aes128_md5",
        "protocol_param": "72291:gMe1NM",
        "obfs": "tls1.2_ticket_auth",
        "obfs_param": "90f3b72291.www.gov.hk"
    }
}
EOF
fi

# 输出配置信息
echo "读取配置..."
CONFIG_PATH=/data/options.json
if [ -f "$CONFIG_PATH" ]; then
    echo "配置文件存在"
    if command -v jq >/dev/null 2>&1; then
        LOCAL_PORT=$(jq -r '.local_port // 7088' $CONFIG_PATH 2>/dev/null || echo "7088")
        SUBSCRIPTION_UPDATE_INTERVAL=$(jq -r '.subscription_update_interval // 24' $CONFIG_PATH 2>/dev/null || echo "24")
        echo "本地端口: ${LOCAL_PORT}"
        echo "订阅更新间隔: ${SUBSCRIPTION_UPDATE_INTERVAL} 小时"
    else
        echo "jq命令不可用，使用默认配置"
    fi
else
    echo "配置文件不存在，使用默认配置"
fi

# 运行主程序
cd /app
echo "启动Symi Proxy主程序..."
python3 /app/main.py