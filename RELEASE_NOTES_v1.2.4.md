# Symi Proxy v1.2.4 发布说明

## 🔧 加密库修复版本

### 关键修复

#### 1. **修复Home Assistant容器加密库问题**
- **问题**: Home Assistant容器中缺少加密库，导致SSR连接失败
- **解决**: 在Dockerfile中添加了必要的加密库依赖
  ```dockerfile
  RUN apk add --no-cache python3 py3-pip bash jq curl wget gcc musl-dev libffi-dev && \
      pip3 install --no-cache-dir requests pyyaml pycryptodome cryptography
  ```

#### 2. **修复SSR连接逻辑**
- **问题**: 当加密库不可用时，错误地降级为普通TCP连接到SSR服务器
- **解决**: 当加密库不可用时正确返回错误，避免无效连接

#### 3. **添加编译依赖**
- 添加了 `gcc musl-dev libffi-dev` 用于编译加密库
- 确保在Alpine Linux容器中能正确编译和安装加密库

### 重要说明

⚠️ **这个版本专门修复了Home Assistant环境中的问题**
- 解决了"加密库不可用"的警告
- 现在SSR节点应该能正常工作
- 支持完整的SSR协议加密和混淆

### 升级指南

1. **更新插件**: 在Home Assistant中重新安装或更新插件
2. **重启插件**: 让新的Dockerfile生效
3. **测试连接**: 检查是否还有"加密库不可用"的警告

### 技术细节

- **版本**: v1.2.4
- **基础镜像**: Alpine 3.17
- **Python版本**: 3.x
- **新增依赖**: pycryptodome, cryptography
- **编译工具**: gcc, musl-dev, libffi-dev

### 已知问题

- 网络连接问题可能导致GitHub推送失败（网络环境相关）
- 首次安装可能需要更长时间（需要编译加密库）

---

**感谢您的耐心！这次是真正针对Home Assistant环境的修复！** 🚀
