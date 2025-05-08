FROM alpine:3.19

# 设置标签
LABEL \
    io.hass.name="Symi Proxy" \
    io.hass.description="Symi Proxy with subscription support for Home Assistant OS" \
    io.hass.version="1.0.8" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386" \
    maintainer="Symi Proxy Team" \
    org.opencontainers.image.title="Symi Proxy" \
    org.opencontainers.image.description="Symi Proxy with subscription support for Home Assistant OS" \
    org.opencontainers.image.licenses="Apache 2.0" \
    org.opencontainers.image.url="https://github.com/symi-daguo/symi-proxy" \
    org.opencontainers.image.source="https://github.com/symi-daguo/symi-proxy" \
    org.opencontainers.image.documentation="https://github.com/symi-daguo/symi-proxy/blob/master/README.md" \
    org.opencontainers.image.version="1.0.8"

# 设置环境变量
ENV LANG="C.UTF-8" \
    PYTHONUNBUFFERED=1

# 安装依赖
RUN apk update && \
    apk add --no-cache python3 py3-pip iptables bash jq curl wget && \
    pip3 install --no-cache-dir requests

# 创建目录
RUN mkdir -p /app/templates

# 复制文件
COPY *.py /app/
COPY run.sh /
# 确保templates目录存在
RUN mkdir -p /app/templates

# 设置权限
RUN chmod a+x /app/*.py \
    && chmod a+x /run.sh

WORKDIR /app

# 健康检查 - 使用环境变量获取web_port，默认为8123
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD PORT=$(jq -r '.web_port // 8123' /data/options.json 2>/dev/null || echo 8123) && \
      wget --quiet --tries=1 --spider http://localhost:${PORT} || exit 1

# 启动命令
CMD ["/run.sh"]

