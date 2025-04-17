# Home Assistant Add-on: Symi Proxy

一个支持订阅功能的代理服务器，专为Home Assistant OS (HassOS)设计，可以访问长城防火墙外部世界。

## 版本信息
当前版本: 1.0.5

## 安装方法

1. 在Home Assistant中，进入**设置** -> **加载项** -> **加载项商店**
2. 点击右上角的三点菜单，选择**仓库**
3. 添加仓库URL：`https://github.com/symi-daguo/symi-proxy`
4. 添加成功后，刷新页面，在加载项商店中找到并安装Symi Proxy

## 关于

本Add-on启动后，将在本地开放一个端口（默认为7088）。

在浏览器中配置hassio的ip与此端口，作为proxy，可以访问墙外世界。

## 功能

- 支持添加订阅地址，自动获取和更新节点
- 支持自定义更新间隔（默认24小时更新一次）
- 支持手动添加自定义节点
- 提供Web界面，方便管理节点和查看状态

## 配置选项

- `local_port`: 本地代理端口（默认：7088）
- `subscription_url`: 订阅地址URL（可选）
- `subscription_update_interval`: 订阅更新间隔，单位小时（默认：24）
- `default_node`: 默认使用的节点（auto表示自动选择最快节点）
- `custom_nodes`: 自定义节点列表

## 使用方法

1. 在Home Assistant中安装此Add-on
2. 在Add-on配置页面中设置订阅地址或添加自定义节点
3. 启动Add-on
4. 在浏览器中配置代理服务器（地址：hassio的IP，端口：7088）
5. 通过Home Assistant界面访问Web管理界面，查看节点状态

## 订阅地址

您可以使用以下格式的订阅地址：

```
https://example.com/api/v1/client/subscribe?token=您的订阅令牌
```

请将上述URL中的`您的订阅令牌`替换为您获取的实际订阅令牌。

## 支持的订阅格式

本插件支持多种订阅格式：

### 1. SSR/SS格式（推荐）

```json
{
  "server": "server1.example.com",
  "server_port": 7088,
  "password": "password123",
  "method": "rc4-md5",
  "obfs": "plain",
  "obfs_param": "example.com",
  "protocol": "auth_aes128_md5",
  "protocol_param": "12345:abcde"
}
```

或多节点格式：

```json
[
  {
    "name": "节点1",
    "server": "server1.example.com",
    "server_port": 7088,
    "password": "password123",
    "method": "rc4-md5",
    "obfs": "plain",
    "obfs_param": "example.com",
    "protocol": "auth_aes128_md5",
    "protocol_param": "12345:abcde"
  },
  {
    "name": "节点2",
    "server": "server2.example.com",
    "server_port": 7088,
    "password": "password456",
    "method": "rc4-md5",
    "obfs": "plain",
    "protocol": "auth_aes128_md5"
  }
]
```

### 2. 简单格式

```json
[
  {
    "name": "节点1",
    "address": "server1.example.com",
    "port": 7088
  },
  {
    "name": "节点2",
    "address": "server2.example.com",
    "port": 7088
  }
]
```

### 3. 文本格式

每行一个节点，支持以下格式：
```
节点1|server1.example.com|7088
节点2|server2.example.com|7088
server3.example.com:7088 节点3
```

### 4. Base64编码格式

支持将上述文本或JSON格式进行Base64编码后的订阅。

## 手动添加节点

1. 在Home Assistant中，进入**设置** -> **加载项** -> **Symi Proxy**
2. 点击**配置**选项卡
3. 在`custom_nodes`部分添加您的节点信息：

   ### SSR格式（推荐）
   ```yaml
   custom_nodes:
     - server: "server.example.com"
       server_port: 7088
       password: "password123"
       method: "rc4-md5"
       obfs: "plain"
       obfs_param: "example.com"
       protocol: "auth_aes128_md5"
       protocol_param: "12345:abcde"
   ```

   ### 简单格式
   ```yaml
   custom_nodes:
     - name: "节点名称"
       address: "节点地址"
       port: 7088
   ```

4. 点击**保存**并重启插件

## 节点管理

- 系统会根据配置的更新间隔自动更新订阅内容
- 设置`default_node`为`auto`时，系统会自动选择延迟最低的节点
- 如果当前节点连接失败，系统会自动切换到其他可用节点

## 更新历史

### 1.0.5
- 修复Docker镜像访问问题
- 简化容器结构，直接使用Alpine基础镜像
- 移除复杂的S6 Overlay，提高兼容性

### 1.0.4
- 修复Docker镜像问题
- 更新为2025年Home Assistant标准格式
- 增强SSR/SS节点支持

### 1.0.3
- 支持SSR/SS节点格式
- 改进订阅解析

### 1.0.2
- 完善订阅支持文档
- 增加模板目录

### 1.0.1
- 首次发布版本
