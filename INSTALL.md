# sqnethelper 安装指南

## 系统要求

- Python 3.6 或更高版本 (推荐 3.9+)
- 阿里云账号和API凭证 (Access Key/Secret)
- macOS/Linux/Windows 系统

## 安装方式

### 方式一：从 PyPI 安装 (推荐)

```bash
pip install sqnethelper
```

### 方式二：从源码安装

1. 克隆仓库：
```bash
git clone <repository_url>
cd sqnethelper
```

2. 创建虚拟环境：
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或者 .venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 安装包：
```bash
pip install -e .
```

### 方式三：使用预构建的 Wheel 包

```bash
pip install dist/sqnethelper-0.2.5-py3-none-any.whl
```

## 首次配置

安装完成后，需要配置阿里云凭证：

```bash
sqnethelper setup
```

按提示输入：
- Access Key ID
- Access Secret
- 选择操作区域

## 验证安装

```bash
# 查看版本
sqnethelper --version

# 查看帮助
sqnethelper --help

# 列出ECS实例
sqnethelper list
```

## 常见问题

### 1. 权限错误
确保有足够的权限访问 `~/.sqnethelper/` 目录

### 2. 网络连接问题
检查网络连接和防火墙设置

### 3. API凭证问题
确认Access Key和Secret正确，且有ECS和VPC权限

## 支持的功能

- ECS实例管理（创建、删除、列表）
- VPN协议安装（xray、IPSec）
- 自动释放时间设置
- 区域配置管理 