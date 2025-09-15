# sqnethelper

阿里云ECS实例管理工具，支持一键创建VPN服务器。

## 🚀 快速安装

```bash
# 推荐：使用pipx安装
pipx install sqnethelper

# 或使用pip安装
pip install sqnethelper
```

## 💡 快速使用

```bash
# 1. 配置阿里云凭证
sqnethelper setup

# 2. 一键创建VPN服务器（1小时后自动销毁）
sqnethelper create

# 3. 查看实例
sqnethelper list
```

## 📋 全部命令

```bash
sqnethelper --help      # 查看帮助
sqnethelper setup       # 配置阿里云凭证
sqnethelper config      # 修改配置（区域/实例类型）
sqnethelper create      # 创建实例并安装VPN
sqnethelper list        # 列出所有实例
sqnethelper delete      # 删除实例
sqnethelper autodel     # 修改自动释放时间
sqnethelper addvpn      # 为现有实例添加VPN
```

## 🔧 开发

### 快速开始

```bash
# 克隆并安装
git clone https://github.com/weishq/sqnethelper.git
cd sqnethelper
pip install -e .

# 测试运行
python -m sqnethelper --help
```

### 发布新版本

```bash
# 1. 更新setup.py中的版本号
# 2. 构建和发布
source venv/bin/activate
rm -rf build/ dist/ *.egg-info/
python -m build
python -m twine upload dist/*
```

## 📄 许可证

MIT License
