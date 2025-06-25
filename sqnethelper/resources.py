import json
import os
try:
    # Python 3.9+
    from importlib.resources import files
    HAS_IMPORTLIB_RESOURCES = True
except ImportError:
    try:
        # Python 3.7+
        from importlib_resources import files
        HAS_IMPORTLIB_RESOURCES = True
    except ImportError:
        # Fallback to pkg_resources
        import pkg_resources
        HAS_IMPORTLIB_RESOURCES = False

def get_template_path():
    """获取模板文件的路径"""
    try:
        if HAS_IMPORTLIB_RESOURCES:
            # 使用现代的importlib.resources
            template_file = files('sqnethelper') / 'sing-box_template.json'
            if hasattr(template_file, 'as_posix'):
                return str(template_file)
            else:
                # 对于较老版本的importlib_resources
                import tempfile
                with template_file.open('rb') as f:
                    content = f.read()
                # 创建临时文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                    tmp.write(content.decode('utf-8'))
                    return tmp.name
        else:
            # Fallback to pkg_resources
            return pkg_resources.resource_filename('sqnethelper', 'sing-box_template.json')
    except:
        # 如果失败，尝试相对路径（开发模式）
        current_dir = os.path.dirname(__file__)
        template_path = os.path.join(current_dir, 'sing-box_template.json')
        if os.path.exists(template_path):
            return template_path
        
        # 最后尝试当前工作目录
        fallback_path = 'sing-box_template.json'
        if os.path.exists(fallback_path):
            return fallback_path
        
        return None

def load_template():
    """加载SingBox配置模板"""
    try:
        if HAS_IMPORTLIB_RESOURCES:
            # 直接从包中读取
            template_file = files('sqnethelper') / 'sing-box_template.json'
            content = template_file.read_text(encoding='utf-8')
            return json.loads(content)
        else:
            # Fallback方法
            template_path = get_template_path()
            if not template_path or not os.path.exists(template_path):
                raise FileNotFoundError("找不到SingBox配置模板文件")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        # 最后的fallback：尝试从当前目录和包目录读取
        for path in ['sing-box_template.json', 
                     os.path.join(os.path.dirname(__file__), 'sing-box_template.json')]:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        raise FileNotFoundError(f"找不到SingBox配置模板文件: {e}")

def get_template_content():
    """获取模板文件的字符串内容"""
    template_path = get_template_path()
    if not template_path or not os.path.exists(template_path):
        raise FileNotFoundError("找不到SingBox配置模板文件")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read() 