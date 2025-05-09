FROM alpine:3.17

# 设置标签
LABEL \
    io.hass.name="Symi Proxy" \
    io.hass.description="Symi Proxy with subscription support for Home Assistant OS" \
    io.hass.version="1.1.6" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386" \
    maintainer="Symi Proxy Team" \
    org.opencontainers.image.title="Symi Proxy" \
    org.opencontainers.image.description="Symi Proxy with subscription support for Home Assistant OS" \
    org.opencontainers.image.licenses="Apache 2.0" \
    org.opencontainers.image.url="https://github.com/symi-daguo/symi-proxy" \
    org.opencontainers.image.source="https://github.com/symi-daguo/symi-proxy" \
    org.opencontainers.image.documentation="https://github.com/symi-daguo/symi-proxy/blob/master/README.md" \
    org.opencontainers.image.version="1.1.6"

# 设置环境变量
ENV LANG="C.UTF-8" \
    PYTHONUNBUFFERED=1

# 安装依赖 - 使用多个镜像源以提高成功率
RUN set -x && \
    # 尝试官方源
    (apk update || true) && \
    # 如果失败，尝试阿里云镜像源
    (echo "https://mirrors.aliyun.com/alpine/v3.17/main" > /etc/apk/repositories && \
     echo "https://mirrors.aliyun.com/alpine/v3.17/community" >> /etc/apk/repositories && \
     apk update) && \
    # 安装所需软件包
    apk add --no-cache python3 py3-pip bash jq curl wget && \
    # 尝试多个pip源安装依赖
    (pip3 install --no-cache-dir requests pyyaml || \
     pip3 install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple requests pyyaml || \
     pip3 install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple requests pyyaml)

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

