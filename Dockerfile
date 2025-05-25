FROM alpine:3.17

# 设置标签
LABEL \
    io.hass.name="Symi Proxy" \
    io.hass.description="Symi Proxy with subscription support for Home Assistant OS" \
    io.hass.version="1.2.4" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386" \
    maintainer="Symi Proxy Team" \
    org.opencontainers.image.title="Symi Proxy" \
    org.opencontainers.image.description="Symi Proxy with subscription support for Home Assistant OS" \
    org.opencontainers.image.licenses="Apache 2.0" \
    org.opencontainers.image.url="https://github.com/symi-daguo/symi-proxy" \
    org.opencontainers.image.source="https://github.com/symi-daguo/symi-proxy" \
    org.opencontainers.image.documentation="https://github.com/symi-daguo/symi-proxy/blob/master/README.md" \
    org.opencontainers.image.version="1.2.4"

# 设置环境变量
ENV LANG="C.UTF-8" \
    PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apk add --no-cache python3 py3-pip bash jq curl wget

# 安装Python依赖 - 分步安装以便调试
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir requests pyyaml

# 安装加密库依赖 - 需要编译工具
RUN apk add --no-cache gcc musl-dev libffi-dev python3-dev && \
    pip3 install --no-cache-dir pycryptodome cryptography && \
    apk del gcc musl-dev libffi-dev python3-dev

# 创建目录
RUN mkdir -p /app/templates

# 复制文件
COPY *.py /app/
COPY run.sh /

# 设置权限
RUN chmod a+x /app/*.py \
    && chmod a+x /run.sh

WORKDIR /app

# 健康检查 - 给程序足够的启动时间
HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8123 || exit 1

# 启动命令
CMD ["/run.sh"]