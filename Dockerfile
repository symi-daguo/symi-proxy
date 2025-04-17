ARG BUILD_FROM
FROM $BUILD_FROM

# 设置标签
LABEL \
    io.hass.name="Symi Proxy" \
    io.hass.description="Symi Proxy with subscription support for Home Assistant OS" \
    io.hass.version="1.0.4" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386" \
    maintainer="Symi Proxy Team" \
    org.opencontainers.image.title="Symi Proxy" \
    org.opencontainers.image.description="Symi Proxy with subscription support for Home Assistant OS" \
    org.opencontainers.image.licenses="Apache 2.0" \
    org.opencontainers.image.url="https://github.com/symi-daguo/symi-proxy" \
    org.opencontainers.image.source="https://github.com/symi-daguo/symi-proxy" \
    org.opencontainers.image.documentation="https://github.com/symi-daguo/symi-proxy/blob/master/README.md" \
    org.opencontainers.image.version="1.0.4"

# 设置环境变量
ENV LANG="C.UTF-8" \
    S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    S6_CMD_WAIT_FOR_SERVICES=1 \
    PYTHONUNBUFFERED=1

# 复制根文件系�?COPY rootfs /

# 安装依赖
RUN apk add --no-cache python3 py3-pip iptables && \
    pip3 install --no-cache-dir requests

# 创建目录
RUN mkdir -p /app/templates

# 复制文件
COPY *.py /app/
COPY templates /app/templates
COPY run.sh /

# 设置权限
RUN chmod a+x /app/*.py \
    && chmod a+x /run.sh \
    && chmod a+x /etc/s6-overlay/s6-rc.d/symi-proxy/run \
    && chmod a+x /etc/s6-overlay/s6-rc.d/symi-proxy/finish

WORKDIR /app

# 健康检�?HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD wget --quiet --tries=1 --spider http://localhost:8088 || exit 1

