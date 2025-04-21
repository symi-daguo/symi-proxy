FROM alpine:3.19

# 设置标签
LABEL \
    io.hass.name="Symi Proxy" \
    io.hass.description="Symi Proxy with subscription support for Home Assistant OS" \
    io.hass.version="1.0.2" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386" \
    maintainer="Symi Proxy Team" \
    org.opencontainers.image.title="Symi Proxy" \
    org.opencontainers.image.description="Symi Proxy with subscription support for Home Assistant OS" \
    org.opencontainers.image.licenses="Apache 2.0" \
    org.opencontainers.image.url="https://github.com/symi-daguo/symi-proxy" \
    org.opencontainers.image.source="https://github.com/symi-daguo/symi-proxy" \
    org.opencontainers.image.documentation="https://github.com/symi-daguo/symi-proxy/blob/master/README.md" \
    org.opencontainers.image.version="1.0.2"

# 设置环境变量
ENV LANG="C.UTF-8" \
    PYTHONUNBUFFERED=1

# 安装依赖
RUN echo "http://dl-cdn.alpinelinux.org/alpine/v3.19/main" > /etc/apk/repositories && \
    echo "http://dl-cdn.alpinelinux.org/alpine/v3.19/community" >> /etc/apk/repositories && \
    apk update && \
    apk add --no-cache python3 && \
    apk add --no-cache py3-pip && \
    apk add --no-cache iptables bash jq && \
    pip3 install --no-cache-dir --break-system-packages requests

# 创建目录
RUN mkdir -p /app/templates

# 复制文件
COPY *.py /app/
COPY templates /app/templates
COPY run.sh /

# 设置权限
RUN chmod a+x /app/*.py \
    && chmod a+x /run.sh

WORKDIR /app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD wget --quiet --tries=1 --spider http://localhost:8123 || exit 1

# 启动命令
CMD ["/run.sh"]

