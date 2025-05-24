# Symi Proxy

Home Assistant OS的代理管理插件，支持订阅地址和节点选择。

## 版本更新

当前版本：1.2.4

## 最新更新内容

### 1.2.4 版本 (2025年5月24日) - 加密库修复版本 🔧
- **修复Dockerfile**: 在Home Assistant容器中安装加密库
- **修复SSR连接**: 解决"加密库不可用"问题
- **生产就绪**: 现在SSR节点应该能正常工作了

### 1.2.0 版本 (2025年5月24日) - 重大修复版本 🔥
- **修复核心问题**: 解决"能查看节点信息但实际没有连上网络"的问题
  - 添加了缺失的代理服务器实现
  - 实现真正的网络代理功能
  - 支持HTTP CONNECT代理协议
- **新增诊断工具**:
  - Web界面测试连接功能
  - 全面的诊断脚本 (`diagnose.py`)
  - 连接测试脚本 (`test_proxy.py`)
- **增强稳定性**:
  - 多线程连接处理
  - 自动故障切换
  - 更好的错误处理和日志记录

## 安装说明

1. 在Home Assistant中添加此仓库：https://github.com/symi-daguo/symi-proxy
2. 安装Symi Proxy插件
3. 配置您的订阅URL或自定义节点
4. 启动插件

## 详细配置说明

### 快速配置
插件提供了简化的配置界面，只需填写以下信息即可快速启动：

1. **订阅URL**：填入您的订阅地址，例如 `https://rss.rss-node.com/link/rjzfONPggKdGMI1B?mu`
2. **使用自定义节点**：如果您想使用自定义节点而不是订阅，请开启此选项
3. **自定义节点信息**：如果开启了自定义节点，请填写节点详细信息

### 订阅URL
在配置页面中填入您的订阅URL，插件会自动解析并获取节点信息。支持的订阅格式包括：

- **SSR订阅**：
  - Base64编码的SSR链接列表
  - 标准的SSR订阅格式

- **Shadowsocks订阅**：
  - Base64编码的SS链接列表
  - 支持新旧两种SS URL格式

- **Clash订阅**：
  - YAML格式的Clash配置
  - JSON格式的Clash配置
  - 自动提取SS和SSR节点

- **其他格式**：
  - JSON格式的节点配置
  - 纯文本格式（每行一个节点）

### 自定义节点
如果您不使用订阅，可以开启"使用自定义节点"选项，然后填写节点信息。

#### 快速配置方法
您可以直接复制以下配置信息，粘贴到配置界面的"自定义节点"文本框中：

```json
{
  "server": "d3.alibabamysql.com",
  "server_port": 7001,
  "password": "di15PV",
  "method": "chacha20-ietf",
  "protocol": "auth_aes128_md5",
  "protocol_param": "72291:gMe1NM",
  "obfs": "tls1.2_ticket_auth",
  "obfs_param": "90f3b72291.www.gov.hk"
}
```

或者您也可以直接复制以下完整配置（包含更多参数）：

```json
{
  "server": "d3.alibabamysql.com",
  "local_address": "127.0.0.1",
  "local_port": 1080,
  "timeout": 300,
  "workers": 1,
  "server_port": 7001,
  "password": "di15PV",
  "method": "chacha20-ietf",
  "obfs": "tls1.2_ticket_auth",
  "obfs_param": "90f3b72291.www.gov.hk",
  "protocol": "auth_aes128_md5",
  "protocol_param": "72291:gMe1NM"
}
```

#### 手动配置字段说明
如果您需要手动配置，以下是各字段的说明：
- `server`: 服务器地址，例如 `d3.alibabamysql.com`
- `server_port`: 服务器端口，例如 `7001`
- `password`: 密码，例如 `di15PV`
- `method`: 加密方式，例如 `chacha20-ietf`
- `protocol`: 协议，例如 `auth_aes128_md5`
- `protocol_param`: 协议参数，例如 `72291:gMe1NM`
- `obfs`: 混淆方式，例如 `tls1.2_ticket_auth`
- `obfs_param`: 混淆参数，例如 `90f3b72291.www.gov.hk`

可选字段：
- `local_address`: 本地监听地址，默认 `127.0.0.1`
- `local_port`: 本地监听端口，默认 `1080`
- `timeout`: 超时时间（秒），默认 `300`
- `workers`: 工作线程数，默认 `1`

### 端口设置
- `local_port`: 本地代理端口，默认7088
- `web_port`: Web管理界面端口，默认8123

## 使用说明

1. 安装并启动插件后，访问 `http://your-homeassistant:8123` 进入Web管理界面
2. 在界面中可以查看所有节点状态、选择节点、更新订阅
3. 选择节点后，插件会自动启动代理服务
4. 在Home Assistant中配置网络使用此代理，即可正常访问网络

## 功能特点
- 支持多种订阅格式
  - SSR订阅
  - Shadowsocks订阅
  - Clash订阅
  - JSON格式配置
- 支持自定义节点配置
  - 支持直接复制粘贴JSON配置
  - 支持手动填写各项参数
- 提供Web界面进行管理
- 自动更新订阅
- 自动检测节点可用性
- 自动选择最佳节点

## 问题排查

如果遇到"安装加载项失败"错误，请确认：
1. 您的Home Assistant可以访问互联网
2. Alpine Linux仓库可以正常访问

如果插件安装成功但无法连接网络：
1. 检查订阅URL是否有效
2. 检查节点是否可用（在Web界面中可以查看节点状态）
3. 检查Home Assistant网络配置是否正确使用了代理

## 联系方式

如有问题，请在GitHub仓库提交Issue。
