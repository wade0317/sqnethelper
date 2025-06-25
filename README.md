# sqnethelper - 阿里云ECS助手工具

这是一个用于管理阿里云ECS实例的命令行工具。您可以使用此工具快速创建、管理ECS实例，自动安装VPN协议，并生成SingBox客户端配置。

## ✨ 主要功能

- 🚀 **一键创建ECS实例**：自动创建、配置网络和安全组
- 🔒 **多协议VPN支持**：支持Reality、VMess、Shadowsocks等协议
- 📱 **SingBox配置生成**：自动生成完整的SingBox客户端配置文件
- ⏰ **自动释放管理**：设置实例自动销毁时间，避免忘记关机
- 🔧 **SSH密钥管理**：自动创建和管理SSH密钥对

## 📦 安装方式

### 方式一：使用pipx安装（推荐 - macOS）

pipx是安装Python命令行工具的最佳方式，它会为每个工具创建独立的虚拟环境。

#### 1. 安装pipx

```bash
# 使用Homebrew安装pipx（推荐）
brew install pipx

# 或者使用pip安装
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

#### 2. 使用pipx安装sqnethelper

```bash
pipx install sqnethelper
```

#### 3. 验证安装

```bash
sqnethelper --version
```

#### 4. pipx管理命令

```bash
# 升级到最新版本
pipx upgrade sqnethelper

# 强制重新安装
pipx install --force sqnethelper

# 卸载
pipx uninstall sqnethelper

# 查看已安装的包
pipx list
```

### 方式二：使用pip安装

#### 在虚拟环境中安装（推荐）

```bash
# 创建虚拟环境
python3 -m venv sqnethelper-env
source sqnethelper-env/bin/activate

# 安装sqnethelper
pip install sqnethelper
```

#### 用户级安装

```bash
pip install --user sqnethelper
```

### 方式三：从源码安装

```bash
git clone https://github.com/weishq/sqnethelper.git
cd sqnethelper
pip install -e .
```

## 🚀 快速开始

### 1. 设置阿里云凭证

首次使用需要配置阿里云Access Key和Secret：

```bash
sqnethelper setup
```

按提示输入您的阿里云Access Key和Secret。如果您还没有，请访问 [阿里云控制台](https://ram.console.aliyun.com/manage/ak) 创建。

### 2. 一键创建VPN服务器

```bash
sqnethelper create
```

这个命令会：
- 自动创建ECS实例（默认1小时后自动销毁）
- 配置安全组和网络
- 安装Xray VPN协议
- 生成SingBox客户端配置文件

### 3. 查看现有实例

```bash
sqnethelper list
```

## 📋 命令参考

### 基础命令

```bash
# 查看帮助
sqnethelper --help

# 查看版本
sqnethelper --version

# 设置阿里云凭证
sqnethelper setup

# 查看/修改配置
sqnethelper config
sqnethelper config --region  # 修改区域设置
```

### 实例管理

```bash
# 创建新实例（自动安装VPN）
sqnethelper create

# 列出所有实例
sqnethelper list

# 修改自动释放时间
sqnethelper autodel

# 删除实例
sqnethelper delete
```

### VPN管理

```bash
# 为现有实例添加VPN协议
sqnethelper addvpn
```

### 网络说明

- 默认创建的安全组只开放必要端口
- 支持IPv4和IPv6双栈网络
- 自动配置合适的带宽和流量

## 💻 开发者文档

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/weishq/sqnethelper.git
cd sqnethelper

# 创建开发环境
python3 -m venv dev-env
source dev-env/bin/activate

# 安装开发依赖
pip install -e .
pip install build twine
```

### 代码测试

```bash
# 运行基本测试
python -m sqnethelper --help

# 测试配置功能
python -m sqnethelper config

# 测试连接（需要配置阿里云凭证）
python -m sqnethelper list
```

### 编译和发布

#### 1. 更新版本号

在发布前，需要更新 `setup.py` 中的版本号：

```python
# setup.py
version="0.2.9",  # 更新这里的版本号
```

#### 2. 清理旧的构建文件

```bash
# 删除旧的构建文件
rm -rf build/ dist/ sqnethelper.egg-info/
```

#### 3. 构建包

```bash
# 使用build模块构建
python -m build

# 或者使用传统方式
python setup.py sdist bdist_wheel
```

构建完成后会在 `dist/` 目录下生成：
- `sqnethelper-x.x.x.tar.gz` （源码包）
- `sqnethelper-x.x.x-py3-none-any.whl` （wheel包）

#### 4. 发布到PyPI

```bash
# 发布到正式PyPI
python -m twine upload dist/*

# 或者先发布到测试PyPI
python -m twine upload --repository testpypi dist/*
```

#### 5. 一键发布脚本

创建 `scripts/publish.sh` 脚本：

```bash
#!/bin/bash
set -e

echo "🚀 开始发布 sqnethelper..."

# 检查是否在正确的目录
if [ ! -f "setup.py" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 获取当前版本号
VERSION=$(python setup.py --version)
echo "📦 当前版本: $VERSION"

# 确认发布
read -p "确认发布版本 $VERSION? (y/N): " confirm
if [[ $confirm != [yY] ]]; then
    echo "❌ 发布已取消"
    exit 0
fi

# 清理旧文件
echo "🧹 清理旧的构建文件..."
rm -rf build/ dist/ sqnethelper.egg-info/

# 构建包
echo "🔨 构建包..."
python -m build

# 检查包
echo "🔍 检查包..."
python -m twine check dist/*

# 发布到PyPI
echo "📤 发布到PyPI..."
python -m twine upload dist/*

echo "✅ 发布完成! 版本 $VERSION 已上传到PyPI"
echo "📥 用户可以使用以下命令更新:"
echo "   pip install --upgrade sqnethelper"
echo "   pipx upgrade sqnethelper"
```

#### 6. 发布后验证

```bash
# 检查PyPI页面
open https://pypi.org/project/sqnethelper/

# 测试安装新版本
pip install --upgrade sqnethelper
sqnethelper --version
```

### 开发流程

1. **开发新功能**
   ```bash
   git checkout -b feature/new-feature
   # 开发代码...
   git commit -m "feat: 添加新功能"
   ```

2. **测试验证**
   ```bash
   python -m sqnethelper --help
   # 运行各种测试...
   ```

3. **更新版本和文档**
   ```bash
   # 更新setup.py中的版本号
   # 更新CHANGELOG.md
   # 更新README.md（如需要）
   ```

4. **发布新版本**
   ```bash
   git tag v0.2.9
   git push origin main --tags
   ./scripts/publish.sh
   ```

### 项目结构

```
sqnethelper/
├── sqnethelper/          # 主包目录
│   ├── __init__.py
│   ├── __main__.py       # 命令行入口
│   ├── cli.py           # CLI界面
│   ├── ConfigManager.py # 配置管理
│   ├── ECSManager.py    # ECS实例管理
│   ├── VPCManager.py    # VPC网络管理
│   ├── ShellHelper.py   # Shell脚本助手
│   ├── SqNetHelper.py   # 核心逻辑
│   └── resources.py     # 资源配置
├── sing-box/            # SingBox脚本
├── Xray/               # Xray脚本
├── setup.py            # 包配置
├── requirements.txt    # 依赖列表
├── README.md          # 项目文档
└── CHANGELOG.md       # 更新日志
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

- [阿里云ECS文档](https://help.aliyun.com/product/25365.html)
- [SingBox官方文档](https://sing-box.sagernet.org/)
- [Xray官方文档](https://xtls.github.io/)
