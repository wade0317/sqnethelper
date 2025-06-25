
import struct
import json
import gzip
import io
from datetime import datetime, timezone

class SqUtils:

    # with open(output_file, 'w', encoding='utf-8') as f:
    #     json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def utc_to_local_time(utc_time_str):
        """
        将UTC时间字符串转换为本地时间字符串
        
        Args:
            utc_time_str: UTC时间字符串，格式如 "2024-12-29T15:30:00Z" 或 "N/A"
            
        Returns:
            本地时间字符串，格式如 "2024-12-29 23:30:00" 或原字符串（如果是"N/A"等）
        """
        if not utc_time_str or utc_time_str == 'N/A':
            return utc_time_str
            
        try:
            # 解析UTC时间字符串
            if utc_time_str.endswith('Z'):
                # 移除Z后缀，添加UTC时区信息
                utc_time_str = utc_time_str[:-1] + '+00:00'
            
            # 解析为datetime对象
            utc_dt = datetime.fromisoformat(utc_time_str)
            
            # 如果没有时区信息，假设为UTC
            if utc_dt.tzinfo is None:
                utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            
            # 转换为本地时间
            local_dt = utc_dt.astimezone()
            
            # 格式化为易读的本地时间字符串
            return local_dt.strftime('%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            # 如果转换失败，返回原字符串
            return utc_time_str
    
    @staticmethod
    def read_varbin(reader):
        try:
            length_bytes = reader.read(2)
            if len(length_bytes) < 2:
                print(f"Warning: Expected 2 bytes for length, got {len(length_bytes)}")
                return None
            length = struct.unpack('>H', length_bytes)[0]
            data = reader.read(length)
            if len(data) < length:
                print(f"Warning: Expected {length} bytes of data, got {len(data)}")
                return None
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                return data.hex()
        except Exception as e:
            print(f"Error in read_varbin: {e}")
            return None
    
    @staticmethod
    def write_varbin(writer, data):
        if isinstance(data, str):
            encoded = data.encode('utf-8')
        elif isinstance(data, bytes):
            encoded = data
        else:
            raise ValueError("Data must be str or bytes")
        writer.write(struct.pack('>H', len(encoded)))
        writer.write(encoded)

    @staticmethod
    def bpf_to_json(bpf_file, json_file):
        with open(bpf_file, 'rb') as f:
            data = f.read()
        
        reader = io.BytesIO(data)
        
        try:
            # Read message type
            message_type = reader.read(1)
            if not message_type:
                raise ValueError("Could not read message type")
            message_type = message_type[0]
            if message_type != 3:  # MessageTypeProfileContent
                raise ValueError(f"Invalid message type: {message_type}")
            
            # Read version
            version_bytes = reader.read(1)
            if not version_bytes:
                raise ValueError("Could not read version")
            version = version_bytes[0]
            
            # Read gzipped content
            gzip_reader = gzip.GzipFile(fileobj=reader)
            content = {}
            
            content['name'] = SqUtils.read_varbin(gzip_reader)
            if content['name'] is None:
                raise ValueError("Could not read name")
            
            type_bytes = gzip_reader.read(4)
            if len(type_bytes) < 4:
                raise ValueError(f"Expected 4 bytes for type, got {len(type_bytes)}")
            content['type'] = struct.unpack('>i', type_bytes)[0]
            
            content['config'] = SqUtils.read_varbin(gzip_reader)
            if content['config'] is None:
                raise ValueError("Could not read config")
            
            if content['type'] != 0:  # Not ProfileTypeLocal
                content['remotePath'] = SqUtils.read_varbin(gzip_reader)
                if content['remotePath'] is None:
                    raise ValueError("Could not read remotePath")
            
            if content['type'] == 2 or (version == 0 and content['type'] != 0):  # ProfileTypeRemote
                auto_update_bytes = gzip_reader.read(1)
                if not auto_update_bytes:
                    raise ValueError("Could not read autoUpdate")
                content['autoUpdate'] = struct.unpack('>?', auto_update_bytes)[0]
                
                if version >= 1:
                    interval_bytes = gzip_reader.read(4)
                    if len(interval_bytes) < 4:
                        raise ValueError(f"Expected 4 bytes for autoUpdateInterval, got {len(interval_bytes)}")
                    content['autoUpdateInterval'] = struct.unpack('>i', interval_bytes)[0]
                
                last_updated_bytes = gzip_reader.read(8)
                if len(last_updated_bytes) < 8:
                    raise ValueError(f"Expected 8 bytes for lastUpdated, got {len(last_updated_bytes)}")
                content['lastUpdated'] = struct.unpack('>q', last_updated_bytes)[0]
            
            with open(json_file, 'w') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            
            print("Successfully converted BPF to JSON")
        
        except Exception as e:
            print(f"Error in bpf_to_json: {e}")
            print(f"Current position in file: {reader.tell()}")
            raise

    @staticmethod
    def json_to_bpf(json_file, bpf_file):
        with open(json_file, 'r') as f:
            content = json.load(f)
        
        buffer = io.BytesIO()
        buffer.write(struct.pack('B', 3))  # MessageTypeProfileContent
        buffer.write(struct.pack('B', 1))  # Version
        
        gzip_writer = gzip.GzipFile(fileobj=buffer, mode='wb')
        
        SqUtils.write_varbin(gzip_writer, content['name'])
        gzip_writer.write(struct.pack('>i', content['type']))
        SqUtils.write_varbin(gzip_writer, content['config'])
        
        if content['type'] != 0:  # Not ProfileTypeLocal
            SqUtils.write_varbin(gzip_writer, content['remotePath'])
        
        if content['type'] == 2:  # ProfileTypeRemote
            gzip_writer.write(struct.pack('>?', content['autoUpdate']))
            gzip_writer.write(struct.pack('>i', content['autoUpdateInterval']))
            gzip_writer.write(struct.pack('>q', content['lastUpdated']))
        
        gzip_writer.close()
        
        with open(bpf_file, 'wb') as f:
            f.write(buffer.getvalue())

    @staticmethod
    def parse_vpn_output_and_generate_singbox_config(vpn_output, server_ip, protocol, port):
        """
        解析VPN安装输出并生成SingBox客户端配置
        
        Args:
            vpn_output: VPN安装后的输出文本
            server_ip: 服务器IP地址
            protocol: 协议类型 (vless, vmess, ss等)
            port: 端口号
            
        Returns:
            dict: SingBox outbounds配置
        """
        import re
        import uuid
        
# 调试输出已移动到新的配置文件读取方法
        # print(f"🔧 开始解析VPN输出 - 协议: {protocol}, 端口: {port}")
        
        outbounds = []
        
        # 根据协议类型生成不同的配置
        # 首先尝试从输出中解析通用信息
        uuid_match = re.search(r'UUID:\s*([a-f0-9-]+)', vpn_output, re.IGNORECASE)
        
        # 也尝试解析用户ID字段（VMess和VLESS都可能使用）
        if not uuid_match:
            uuid_match = re.search(r'用户ID\s*\(id\)\s*=\s*([a-f0-9-]+)', vpn_output, re.IGNORECASE)
        
        uuid_str = uuid_match.group(1) if uuid_match else str(uuid.uuid4())
        
        if protocol == "reality":
            # 解析Reality相关信息
            public_key_match = re.search(r'PublicKey:\s*([A-Za-z0-9_-]+)', vpn_output, re.IGNORECASE)
            # 尝试多种ServerName格式
            server_name_match = re.search(r'ServerName:\s*([^\s]+)', vpn_output, re.IGNORECASE)
            if not server_name_match:
                server_name_match = re.search(r'SNI \(serverName\)\s*=\s*([^\s]+)', vpn_output, re.IGNORECASE)
            # 尝试多种PublicKey格式  
            if not public_key_match:
                public_key_match = re.search(r'公钥 \(Public key\)\s*=\s*([A-Za-z0-9_-]+)', vpn_output, re.IGNORECASE)
            
            public_key = public_key_match.group(1) if public_key_match else "zXiW5la-0PbaGNKd8QXDzSuPsS1nhbIaR1P9pf-KRWU"
            server_name = server_name_match.group(1) if server_name_match else "aws.amazon.com"
            
            # 使用协议+IP格式的tag
            tag_name = f"reality-{server_ip.replace('.', '-')}"
            
            vless_config = {
                "type": "vless",
                "tag": tag_name,
                "server": server_ip,
                "server_port": port,
                "uuid": uuid_str,
                "flow": "xtls-rprx-vision",
                "tls": {
                    "enabled": True,
                    "server_name": server_name,
                    "utls": {
                        "enabled": True,
                        "fingerprint": "chrome"
                    },
                    "reality": {
                        "enabled": True,
                        "public_key": public_key
                    }
                }
            }
            outbounds.append(vless_config)
            
        elif protocol == "tcp":
            # 检查是否是VMess协议（根据输出内容判断）
            if re.search(r'VMess-TCP|协议 \(protocol\)\s*=\s*vmess', vpn_output, re.IGNORECASE):
                # Xray VMess TCP协议
                tag_name = f"vmess-{server_ip.replace('.', '-')}"
                vmess_tcp_config = {
                    "type": "vmess",
                    "tag": tag_name,
                    "server": server_ip,
                    "server_port": port,
                    "uuid": uuid_str,
                    "security": "auto",
                    "network": "tcp"
                }
                outbounds.append(vmess_tcp_config)
            else:
                # VLESS TCP协议
                tag_name = f"vless-{server_ip.replace('.', '-')}"
                vless_tcp_config = {
                    "type": "vless",
                    "tag": tag_name,
                    "server": server_ip,
                    "server_port": port,
                    "uuid": uuid_str,
                    "flow": "",
                    "packet_encoding": "xudp",
                    "transport": {
                        "type": "tcp"
                    }
                }
                outbounds.append(vless_tcp_config)
            
        elif protocol == "ss":
            # SingBox Shadowsocks相关信息
            password_match = re.search(r'password:\s*([^\s]+)', vpn_output, re.IGNORECASE)
            method_match = re.search(r'method:\s*([^\s]+)', vpn_output, re.IGNORECASE)
            
            password = password_match.group(1) if password_match else "auto-generated-password"
            method = method_match.group(1) if method_match else "aes-256-gcm"
            
            # 使用协议+IP格式的tag
            tag_name = f"ss-{server_ip.replace('.', '-')}"
            
            ss_config = {
                "type": "shadowsocks",
                "tag": tag_name,
                "server": server_ip,
                "server_port": port,
                "method": method,
                "password": password
            }
            outbounds.append(ss_config)
            
        else:
            # 默认处理：如果输出中包含Reality相关信息，生成Reality配置
            public_key_match = re.search(r'PublicKey:\s*([A-Za-z0-9_-]+)', vpn_output, re.IGNORECASE)
            # 尝试多种PublicKey格式
            if not public_key_match:
                public_key_match = re.search(r'公钥 \(Public key\)\s*=\s*([A-Za-z0-9_-]+)', vpn_output, re.IGNORECASE)
            
            if public_key_match:
                # 有PublicKey，生成Reality配置
                server_name_match = re.search(r'ServerName:\s*([^\s]+)', vpn_output, re.IGNORECASE)
                if not server_name_match:
                    server_name_match = re.search(r'SNI \(serverName\)\s*=\s*([^\s]+)', vpn_output, re.IGNORECASE)
                
                public_key = public_key_match.group(1)
                server_name = server_name_match.group(1) if server_name_match else "aws.amazon.com"
                
                # 使用协议+IP格式的tag
                tag_name = f"reality-{server_ip.replace('.', '-')}"
                
                vless_config = {
                    "type": "vless",
                    "tag": tag_name,
                    "server": server_ip,
                    "server_port": port,
                    "uuid": uuid_str,
                    "flow": "xtls-rprx-vision",
                    "tls": {
                        "enabled": True,
                        "server_name": server_name,
                        "utls": {
                            "enabled": True,
                            "fingerprint": "chrome"
                        },
                        "reality": {
                            "enabled": True,
                            "public_key": public_key
                        }
                    }
                }
                outbounds.append(vless_config)
            else:
                # 没有PublicKey，生成普通的VLESS TCP配置
                tag_name = f"vless-{server_ip.replace('.', '-')}"
                vless_config = {
                    "type": "vless",
                    "tag": tag_name,
                    "server": server_ip,
                    "server_port": port,
                    "uuid": uuid_str,
                    "flow": "",
                    "packet_encoding": "xudp",
                    "transport": {
                        "type": "tcp"
                    }
                }
                outbounds.append(vless_config)
        
        # 生成完整的outbounds配置
        if outbounds:
            # 创建selector配置
            selector_config = {
                "type": "selector",
                "tag": "proxy",
                "outbounds": [config["tag"] for config in outbounds],
                "default": outbounds[0]["tag"]
            }
            
            result = {
                "outbounds": [selector_config] + outbounds
            }
            
            return result
        
        return None

    @staticmethod
    def format_singbox_config_output(singbox_config):
        """
        格式化SingBox配置为美观的JSON输出
        
        Args:
            singbox_config: SingBox配置字典
            
        Returns:
            str: 格式化的JSON字符串
        """
        if not singbox_config:
            return "无法生成SingBox配置"
        
        return json.dumps(singbox_config, indent=4, ensure_ascii=False)
                

             
    

