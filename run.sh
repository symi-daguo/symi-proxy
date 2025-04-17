#!/usr/bin/with-contenv bashio

# 获取配置信息
CONFIG_PATH=/data/options.json
LOCAL_PORT=$(bashio::config 'local_port')
SUBSCRIPTION_URL=$(bashio::config 'subscription_url')
SUBSCRIPTION_UPDATE_INTERVAL=$(bashio::config 'subscription_update_interval')
DEFAULT_NODE=$(bashio::config 'default_node')

# 输出配置信息
bashio::log.info "Starting Symi Proxy..."
bashio::log.info "Local port: ${LOCAL_PORT}"
bashio::log.info "Subscription update interval: ${SUBSCRIPTION_UPDATE_INTERVAL} hours"

# 确保iptables可用
if ! command -v iptables >/dev/null 2>&1; then
    bashio::log.warning "iptables not found, installing..."
    apk add --no-cache iptables
fi

# 确保 templates 目录存在
mkdir -p /app/templates

# 运行主程序
cd /app
exec python3 /app/main.py 