# Home Assistant Add-on: Symi Proxy

一个支持订阅功能的代理服务器，专为Home Assistant OS (HassOS)设计，可以访问长城防火墙外部世界。

作者：symi-daguo
邮箱：303316404@qq.com

## 关于

本Add-on启动后，将在本地开放一个端口（默认为7088）。

在浏览器中配置hassio的ip与此端口，作为proxy，可以访问墙外世界。

## 新增功能

### 订阅功能

- 支持添加订阅地址，自动获取和更新节点
- 支持自定义更新间隔（默认24小时更新一次）
- 支持手动添加自定义节点
- 提供Web界面，方便管理节点和查看状态

## 配置选项

### 选项

- `local_port`: 本地代理端口（默认：7088）
- `subscription_url`: 订阅地址URL（可选）
- `subscription_update_interval`: 订阅更新间隔，单位小时（默认：24）
- `default_node`: 默认使用的节点（auto表示自动选择最快节点）
- `custom_nodes`: 自定义节点列表
  - `name`: 节点名称
  - `address`: 节点地址
  - `port`: 节点端口

## 使用方法

1. 在Home Assistant中安装此Add-on
2. 配置订阅地址或添加自定义节点
3. 启动Add-on
4. 在浏览器中配置代理服务器（地址：hassio的IP，端口：7088）
5. 通过Home Assistant界面访问Web管理界面，查看节点状态

## 订阅格式说明

本插件支持多种订阅格式，以下是支持的格式示例：

### JSON格式

```json
{
  "name": "示例订阅",
  "description": "这是一个示例订阅文件",
  "nodes": [
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
}
```

### 文本格式

```
# 每行一个节点，格式为：名称|地址|端口 或 地址:端口 名称
节点1|server1.example.com|7088
节点2|server2.example.com|7088
server3.example.com:7088 节点3
```

### Base64编码

订阅内容可以是Base64编码的JSON或文本格式，系统会自动尝试解码。

## 自定义节点

除了使用订阅，您还可以在配置中直接添加自定义节点：

```yaml
custom_nodes:
  - name: "我的节点1"
    address: "myserver.example.com"
    port: 7088
  - name: "我的节点2"
    address: "myserver2.example.com"
    port: 7088
```

## 定期更新

系统会根据配置的更新间隔自动更新订阅内容。您也可以在Web界面中手动触发更新。

## 节点选择

- 设置`default_node`为`auto`时，系统会自动选择延迟最低的节点
- 您也可以在Web界面中手动选择特定节点
- 如果当前节点连接失败，系统会自动切换到其他可用节点
