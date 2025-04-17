ARG BUILD_FROM
FROM $BUILD_FROM

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

# 启动命令
CMD ["/app/main.py"]
