ARG BUILD_FROM
FROM $BUILD_FROM

LABEL io.hass.version="1.0.2" \
      io.hass.type="addon" \
      io.hass.arch="armhf|armv7|aarch64|amd64|i386"

ENV LANG C.UTF-8

# 安装依赖
RUN apk add --no-cache python3 py3-pip iptables && \
    pip3 install --no-cache-dir requests

# 创建目录
RUN mkdir -p /app/templates

# 复制文件
COPY *.py /app/

# 设置权限
RUN chmod a+x /app/*.py

WORKDIR /app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD wget --quiet --tries=1 --spider http://localhost:8088 || exit 1

# 启动命令
CMD ["/app/main.py"]
