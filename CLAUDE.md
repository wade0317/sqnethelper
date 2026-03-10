# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

`sqnethelper` 是一个用于管理阿里云ECS实例的Python CLI工具，支持自动VPN配置。提供一键创建ECS实例、安装VPN协议（Xray、Reality、IPSec）并生成SingBox客户端配置。

## 开发命令

### 环境配置
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### 测试运行
```bash
# 直接运行CLI
python -m sqnethelper --help

# 测试配置功能
python -m sqnethelper config

# 详细输出测试
python -m sqnethelper list --verbose
```

### 构建打包
```bash
# 清理旧构建文件
rm -rf build/ dist/ sqnethelper.egg-info/

# 构建包
python -m build
# 或者
python setup.py sdist bdist_wheel

# 安装构建依赖（如需要）
pip install --upgrade pip build twine wheel
```

### 发布
```bash
# 检查包
python -m twine check dist/*

# 上传到PyPI
python -m twine upload dist/*
```

## 架构设计

### 核心组件

- **`cli.py`** - 基于Click的CLI界面，包含命令：setup, config, create, list, delete, autodel, addvpn
- **`SqNetHelper.py`** - 主要协调类，使用静态方法统筹所有操作
- **`ConfigManager.py`** - 单例配置管理器，在`~/.sqnethelper/config.json`存储凭证和设置
- **`ECSManager.py`** - 阿里云ECS实例生命周期管理
- **`VPCManager.py`** - VPC、安全组和网络资源管理
- **`ShellHelper.py`** - SSH连接和远程命令执行
- **`SqLog.py`** - 集中式日志管理，支持控制台和WebSocket输出
- **`SqUtils.py`** - 工具函数，处理VPN配置解析和SingBox配置生成
- **`resources.py`** - 资源管理，处理模板文件加载

### 数据流

1. **配置阶段**: 用户凭证通过ConfigManager单例存储
2. **创建阶段**: SqNetHelper → ECSManager (创建实例) → VPCManager (配置网络) → ShellHelper (安装VPN)
3. **管理阶段**: CLI命令使用SqNetHelper协调ECS和VPC操作

### 配置信息

`ConfigManager.py`中的默认配置（实际值）：
- 实例类型：`ecs.t6-c4m1.large` (4核CPU, 1GB内存)
- 默认区域：`cn-hangzhou`
- 系统镜像：`debian_12_6_x64_20G_alibase_20240711.vhd`
- 磁盘：20GB高效云盘（`cloud_efficiency`）
- 带宽：出网40Mbps（`PayByTraffic`），入网200Mbps
- VPN端口：Xray TCP (3000)、Reality (443)、SingBox SS (8080)
- 默认登录：root/Root1234
- 配置文件：`~/.sqnethelper/config.json`

### VPN协议支持

`addvpn` 命令当前支持：
- **IPSec VPN** - 传统VPN，兼容性好
- **Xray TCP/Reality** - 高性能代理协议
- SingBox 协议（SS/Reality）代码已实现但在 `addvpn` 命令中被注释掉

### 单例模式注意

`ConfigManager` 和 `SqLog` 均使用单例模式。测试时若需重置 `ConfigManager`，需手动设置 `ConfigManager._instance = None`。全局日志实例为 `SQLOG`（从 `SqLog.py` 导入）。

## 开发说明

- 使用阿里云Python SDK（`aliyun-python-sdk-*`）进行ECS/VPC操作
- 通过paramiko进行SSH操作以远程安装VPN
- 配置以JSON格式持久化在用户主目录
- 使用Click框架构建交互式CLI
- 所有实例自动标记以便管理和清理
- `resources.py` 管理 `sing-box_template.json` 的加载，按优先级尝试 `importlib.resources` → `pkg_resources` → 相对路径