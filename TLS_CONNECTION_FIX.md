# 解决 TLS 连接问题的指南

如果您在尝试添加 Symi Proxy 仓库时遇到 TLS 连接问题，可以尝试以下解决方案：

## 方案一：配置 Home Assistant 使用代理

1. 在 Home Assistant 配置文件 `configuration.yaml` 中添加以下内容：

```yaml
http:
  proxy_address: http://您的代理服务器IP:端口
  proxy_ssl: false  # 如果代理服务器使用HTTPS，设置为true
```

2. 重启 Home Assistant

## 方案二：使用 SSH 隧道

如果您有可以访问 GitHub 的服务器，可以通过 SSH 隧道方式解决：

1. 在可以访问 GitHub 的服务器上执行：

```bash
ssh -R 3000:github.com:443 homeassistant@您的Home_Assistant_IP
```

2. 在 Home Assistant 的 `/etc/hosts` 文件中添加：

```
127.0.0.1 github.com
```

## 方案三：使用网络加速服务

1. 修改 Home Assistant 的 DNS 设置，使用国内加速的 DNS 服务器
2. 使用代理软件或VPN服务

## 方案四：手动安装插件

如果以上方法都不起作用，您可以手动安装插件：

1. 下载 release 包 (https://github.com/symi-daguo/symi-proxy/releases/tag/v1.0.1)
2. 通过 Home Assistant 的文件管理器上传到 `/addons` 目录
3. 在命令行中解压文件并安装

## 检查连接

您可以在 Home Assistant 终端中运行以下命令来测试连接：

```bash
curl -v https://github.com
```

如果看到 "Connected to github.com" 和 "SSL connection using TLS" 等信息，说明连接正常。 