#!/usr/bin/env python3
import sys
sys.path.append('sqnethelper')

from sqnethelper.SqUtils import SqUtils

# 模拟VPN输出
vpn_output = """
使用协议: VMess-TCP
-------------- VMess-TCP-3000.json -------------
协议 (protocol) 	= vmess
地址 (address) 		= 47.239.83.52
端口 (port) 		= 3000
用户ID (id) 		= e32e1e06-e925-4e3f-84c9-b3cb6616e9de
传输协议 (network) 	= tcp
伪装类型 (type) 	= none

警告! 首次安装请查看脚本帮助文档: https://233boy.com/xray/xray-script/

------------- 链接 (URL) -------------
vmess://eyJ2IjoyLCJwcyI6IjIzM2JveS10Y3AtNDcuMjM5LjgzLjUyIiwiYWRkIjoiNDcuMjM5LjgzLjUyIiwicG9ydCI6IjMwMDAiLCJpZCI6ImUzMmUxZTA2LWU5MjUtNGUzZi04NGM5LWIzY2I2NjE2ZTlkZSIsImFpZCI6IjAiLCJuZXQiOiJ0Y3AiLCJ0eXBlIjoibm9uZSIsInBhdGgiOiIifQ==
"""

print("调试UUID解析过程:")
print("=" * 60)

# 调用解析函数
result = SqUtils.parse_vpn_output_and_generate_singbox_config(
    vpn_output, "47.239.83.52", "tcp", 3000
)

print("解析结果:")
print(result)

# 检查解析的UUID
if result and 'outbounds' in result and len(result['outbounds']) > 1:
    outbound = result['outbounds'][1]  # 获取实际配置
    uuid_in_config = outbound.get('uuid', 'None')
    print(f"\n配置中的UUID: {uuid_in_config}")
    
    # 验证这个UUID是从输出中解析的还是新生成的
    expected_uuid = "e32e1e06-e925-4e3f-84c9-b3cb6616e9de"
    if uuid_in_config == expected_uuid:
        print("✅ UUID匹配！正确从VPN输出解析")
    else:
        print(f"❌ UUID不匹配！期望: {expected_uuid}, 实际: {uuid_in_config}")
else:
    print("❌ 无法获取配置或解析失败") 