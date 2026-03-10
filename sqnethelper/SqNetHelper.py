import time
import os
from pathlib import Path
from datetime import datetime, timedelta
import click
from sqnethelper.ECSManager import ECSManager
from sqnethelper.VPCManager import VPCManager
from sqnethelper.ConfigManager import ConfigManager
from sqnethelper.ShellHelper import ShellHelper
from sqnethelper.SqLog import SQLOG


class SqNetHelper:

    @staticmethod
    def setup(access_key, access_secret):
        config = ConfigManager()
        config.set_config(
            access_key=access_key,
            access_secret=access_secret
        )
        return "配置已保存"

    @staticmethod
    def list_instances():
        config = ConfigManager()
        if not config.is_configured():
            SQLOG.error(f"请先设置阿里云凭证!")
            return None
        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        instances_result = ecs_manager.list_instances()
        return instances_result

    @staticmethod
    def list_regions():
        config = ConfigManager()
        if not config.is_configured():
            SQLOG.error(f"请先设置阿里云凭证!")
            return None
        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        return ecs_manager.get_regions()



    @staticmethod
    def set_region(selected_region_id):

        config = ConfigManager()
        config.set_config(
            region=selected_region_id
        )

        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        zones = ecs_manager.get_zones()
        zone_id = zones[0]['ZoneId']
        config.set_config(
            zone_id=zone_id
        )

        SQLOG.info(f"地区: {config.region}")
        SQLOG.info(f"可用区: {zone_id}")

        # 让用户输入vCPU和内存大小
        SQLOG.info("\n配置实例规格参数")

        # 获取vCPU数量
        cpu_count = click.prompt(
            "请输入vCPU核数",
            type=click.IntRange(1, 128),
            default=config.instance_cpu_count,
            show_default=True
        )

        # 获取内存大小
        memory_size = click.prompt(
            "请输入内存大小(GB)",
            type=click.FloatRange(0.5, 1024.0),
            default=config.instance_memory_size,
            show_default=True
        )

        SQLOG.info(f"\n已选择: {cpu_count}核CPU, {memory_size}GB内存")

        # 让用户输入实例名称前缀
        instance_name = click.prompt(
            "\n请输入实例名称前缀",
            type=str,
            default="sqnetecs-",
            show_default=True
        )
        # 确保以-结尾
        if not instance_name.endswith('-'):
            instance_name += '-'

        # 让用户输入安全组名称前缀
        security_group_name = click.prompt(
            "请输入安全组名称前缀",
            type=str,
            default="sqgroup-",
            show_default=True
        )
        # 确保以-结尾
        if not security_group_name.endswith('-'):
            security_group_name += '-'

        # 保存用户选择的配置
        config.set_config(
            instance_cpu_count=cpu_count,
            instance_memory_size=memory_size,
            instance_name=instance_name,
            security_group_name=security_group_name
        )

        vpcmanager = VPCManager(config.access_key, config.access_secret, config.region)

        # 获取可用的实例规格
        SQLOG.info(f"开始获取实例规格，CPU数量: {cpu_count}, 内存大小: {memory_size}")
        instance_type_info = vpcmanager.get_available_instance_types_with_price(zone_id=zone_id, cpu_count=cpu_count, memory_size=memory_size)
        SQLOG.info(f"获取到的实例规格数量: {len(instance_type_info)}")

        if len(instance_type_info) > 0:
            # 总是显示所有可用规格，让用户选择
            SQLOG.info(f"\n可用的实例规格:")
            for idx, (instance_type, price) in enumerate(instance_type_info, 1):
                # 解析实例规格名称以获取CPU和内存信息
                parts = instance_type.split('.')
                if len(parts) >= 3:
                    spec_info = parts[2]  # 例如: c4m1
                    # 尝试解析CPU和内存
                    import re
                    match = re.match(r'c(\d+)m(\d+)', spec_info)
                    if match:
                        cpu_count = match.group(1)
                        memory_gb = match.group(2)
                        SQLOG.info(f"{idx}. {instance_type} ({cpu_count}核CPU, {memory_gb}GB内存) - 价格: {price}")
                    else:
                        SQLOG.info(f"{idx}. {instance_type} - 价格: {price}")
                else:
                    SQLOG.info(f"{idx}. {instance_type} - 价格: {price}")

            # 获取用户选择
            if len(instance_type_info) == 1:
                SQLOG.info(f"只有一个实例规格可用，是否使用？")
                if click.confirm(f"使用 {instance_type_info[0][0]}?", default=True):
                    instance_type = instance_type_info[0][0]
                    SQLOG.info(f"已选择实例规格: {instance_type}")
                else:
                    SQLOG.error("用户取消选择")
                    return False
            else:
                choice = click.prompt(f"请选择实例规格序号", type=click.IntRange(1, len(instance_type_info)))
                instance_type = instance_type_info[choice - 1][0]
                SQLOG.info(f"已选择实例规格: {instance_type}")
            
            config.set_config(
                instance_type=instance_type
            )
        else:
            SQLOG.warning(f"当前区域没有可用的实例规格，使用默认值: {config.instance_type}")

        SQLOG.info(f"创建虚拟机实例规格为: {config.instance_type}")
        
        # 获取并选择系统镜像
        SQLOG.info("\n获取可用的系统镜像...")
        images = ecs_manager.get_public_images()
        SQLOG.info(f"获取到的系统镜像数量: {len(images) if images else 0}")

        if images:
            # 总是显示所有可用镜像，让用户选择
            SQLOG.info(f"\n可用的系统镜像:")
            for idx, (image_id, image_name, os_name, version) in enumerate(images, 1):
                SQLOG.info(f"{idx}. {image_name} (ID: {image_id})")

            # 获取用户选择
            if len(images) == 1:
                SQLOG.info(f"只有一个系统镜像可用，是否使用？")
                if click.confirm(f"使用 {images[0][1]}?", default=True):
                    image_id = images[0][0]
                    SQLOG.info(f"已选择系统镜像: {images[0][1]}")
                else:
                    SQLOG.error("用户取消选择")
                    return False
            else:
                choice = click.prompt(f"请选择系统镜像序号", type=click.IntRange(1, len(images)))
                image_id = images[choice - 1][0]
                SQLOG.info(f"已选择系统镜像: {images[choice - 1][1]}")
            
            config.set_config(image_id=image_id)
        else:
            SQLOG.warning(f"无法获取系统镜像列表，使用默认镜像: {config.image_id}")
            
        SQLOG.info(f"系统镜像ID: {config.image_id}")

        disks_resources = vpcmanager.get_available_disk_categories(zone_id=zone_id, insance_type=config.instance_type)

        # 按优先级顺序选择磁盘类型：cloud_efficiency > cloud_essd_entry > cloud_essd
        disk_priority = ["cloud_efficiency", "cloud_essd_entry", "cloud_essd"]
        disk_selected = False

        for disk_type in disk_priority:
            for item in disks_resources:
                if item.get("Value") == disk_type and item.get("Status") == "Available":
                    disk_selected = True
                    # 安全地获取 Min 值，如果不存在则使用默认值 20
                    min_size = item.get("Min", 20)
                    config.set_config(
                        instance_disk_category=item["Value"],
                        instance_disk_size=max(min_size, 20)
                    )
                    SQLOG.info(f"选择磁盘类型: {disk_type}")
                    break  # 找到符合条件的就退出内层循环
            if disk_selected:  # 如果已经设置了磁盘类型，就退出外层循环
                break

        # 如果没有找到任何可用的磁盘类型，使用默认值
        if not disk_selected:
            SQLOG.warning("未找到可用的磁盘类型，使用默认配置: cloud_efficiency")
            config.set_config(
                instance_disk_category="cloud_efficiency",
                instance_disk_size=20
            )

        SQLOG.info(f"创建虚拟机磁盘类型为: {config.instance_disk_category}, 磁盘大小为: {config.instance_disk_size}")
       
        security_group_id = None
        vpc_id = None
        vswitch_id = None
        
        # 检查阿里云是否已存在密钥对
        key_name = vpcmanager.is_key_pair_exist_with_name("sqssh-")
        if key_name:
            user_home = os.path.expanduser('~')
            private_key_path = os.path.join(user_home, '.ssh', 'id_rsa')  
            config.set_config(
                ssh_keypair_name=key_name,
                ssh_local_path=private_key_path
            )
            SQLOG.info("云端已存在SSH密钥对: ", key_name)
        else:
            # 获取或创建本机SSH密钥
            private_key_path, content = ShellHelper.get_local_ssh_key_content()
            if private_key_path and content:
                time_str = time.strftime('%m%d-%H-%M-%S', time.localtime())
                key_name = f"sqssh-{time_str}"
                key_name = vpcmanager.import_ssh_key(key_name, content)
                if key_name:
                    config.set_config(
                        ssh_keypair_name=key_name,
                        ssh_local_path=private_key_path
                    )
                    SQLOG.info("✅ SSH密钥对上传成功: ", key_name)
                    SQLOG.info(f"   本地私钥: {private_key_path}")
                else:
                    SQLOG.error("❌ SSH密钥对上传失败")
            else:
                SQLOG.error("❌ 获取本机SSH密钥失败")
        
        
        if vpcmanager.is_security_group_exist(config.security_group_id):
            security_group_id = config.security_group_id
            SQLOG.info("已存在安全组: ", security_group_id)
            pass
        else:
            security_group_id = vpcmanager.is_security_group_exist_with_name(config.security_group_name)
            if security_group_id:
                SQLOG.info("已存在安全组: ", security_group_id)

        if security_group_id:
            vpc_id = vpcmanager.get_vpc_id_by_security_group_id(security_group_id)
            if vpc_id:
                SQLOG.info("已存在专有网络: ", vpc_id)
                vswitch_id = vpcmanager.get_vswitche_id_by_vpc_id(vpc_id)
                if vswitch_id:
                    SQLOG.info("已存在虚拟交换机: ", vswitch_id)
                else:
                    vswitch_id = vpcmanager.create_vswitch(vpc_id, zone_id) 
                    SQLOG.info("创建虚拟交换机成功: ", vswitch_id)

        if security_group_id and vpc_id and vswitch_id:
            pass 
        else:
            vpc_id = vpcmanager.is_vpc_exist_with_name(config.vpc_name)
            if not vpc_id:
                try:
                    vpc_id = vpcmanager.create_vpc()
                except Exception as e:
                    if "Forbidden.RAM" in str(e) or "not authorized" in str(e):
                        SQLOG.error("\n❌ VPC创建权限不足")
                        SQLOG.error("解决方案：")
                        SQLOG.error("1. 如果使用RAM子账号，请添加以下权限：")
                        SQLOG.error("   - AliyunVPCFullAccess (VPC完全访问权限)")
                        SQLOG.error("   - AliyunECSFullAccess (ECS完全访问权限)")
                        SQLOG.error("2. 或者在阿里云控制台手动创建VPC和安全组")
                        SQLOG.error("3. 然后重新运行本工具，它会自动使用已存在的资源")
                    else:
                        SQLOG.error(f"创建VPC失败: {str(e)}")
                    return False
            if not vpc_id:
                SQLOG.info("创建专有网络失败！")
                return False

            SQLOG.info("创建专有网络成功: ", vpc_id)
            time.sleep(5)
            vswitch_id = vpcmanager.get_vswitche_id_by_vpc_id(vpc_id)
            if not vswitch_id:
                vswitch_id = vpcmanager.create_vswitch(vpc_id, zone_id) 
                pass
            if not vpc_id:
                SQLOG.info("创建虚拟交换机失败！")
                return False  

            SQLOG.info("创建虚拟交换机成功: ", vswitch_id)  
            security_group_id = vpcmanager.create_security_group(vpc_id, config.security_group_name)
            if not security_group_id:
                SQLOG.info("创建安全组失败！")
                return False
            SQLOG.info("创建安全组成功: ", security_group_id)

        if security_group_id:
            vpcmanager.add_security_group_rule(security_group_id, config)
                
        if security_group_id and vpc_id and vswitch_id:
            config.set_config(
                security_group_id=security_group_id,
                vpc_id=vpc_id,
                vswitch_id=vswitch_id
            )
            pass

         
        return True

    @staticmethod
    def create_instance(config):

        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        instance_details = ecs_manager.create_instance(config)
        if instance_details is None:
            SQLOG.debug("创建实例失败")
            return None
            
        instance_id = instance_details['InstanceId']
        if instance_id is None:
            SQLOG.debug("创建实例失败!")
            return None
        SQLOG.info("创建虚拟机成功: ", instance_id)
        time.sleep(2) 
        
        # ECS绑定密码
        ret = ecs_manager.reset_instance_password(instance_id, config.instance_login_password)
        if not ret:
            SQLOG.debug("设置实例密码失败")
            return None
        
        SQLOG.debug("设置实例密码成功!")
        ssh_attach_ret = False
        if config.ssh_keypair_name:
            vpcmanager = VPCManager(config.access_key, config.access_secret, config.region)
            if vpcmanager.is_key_pair_exist(config.ssh_keypair_name):
                ssh_attach_ret = ecs_manager.attach_key_pair(instance_id, config.ssh_keypair_name)
                if ssh_attach_ret :
                    SQLOG.debug("绑定ssh成功")
                    ssh_attach_ret = True
                    pass
                
        # 分配公网 IP
        hostname = ecs_manager.allocate_public_ip(instance_id)
        if hostname is None:
            SQLOG.error("分配公网 IP 失败")
            return None
        SQLOG.info(f"分配公网IP成功: {hostname}")
        # 启动 ECS 实例
        ecs_manager.start_instance(instance_id)
        # 等待实例状态为 Running
        ecs_manager.wait_instance_status(instance_id, 'Running')
        
        #1小时后自动释放
        SqNetHelper.modify_auto_release_time(config, instance_id, 60)
        return instance_details
        
    @staticmethod
    def confirm_delete_instance(instance_id):
        config = ConfigManager()
        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        return ecs_manager.delete_instance(instance_id)
    
    @staticmethod
    def modify_auto_release_time(config, instance_id, time_min_delay):
        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)

        if time_min_delay == 0:
            # 取消自动释放，传递空字符串给API
            SQLOG.info(f"取消自动释放时间")
            return ecs_manager.modify_instance_auto_release_time(instance_id, "")
        else:
            # 计算UTC时间：当前UTC时间 + 指定分钟数
            from datetime import datetime, timedelta, timezone
            utc_now = datetime.now(timezone.utc)
            auto_release_time = (utc_now + timedelta(minutes=time_min_delay)).strftime('%Y-%m-%dT%H:%M:%SZ')
            SQLOG.info(f"设置自动释放时间(UTC): {auto_release_time}")
            return ecs_manager.modify_instance_auto_release_time(instance_id, auto_release_time)
        
    

    @staticmethod
    def install_vpn_unified(config, instance_id):
        SQLOG.info(f"正在安装 VPN...")
        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        shell_script = "wget -qO- https://raw.githubusercontent.com/wade0317/Xray/main/install.sh | bash"
        command_response = ecs_manager.run_command(instance_id, shell_script, timeout=600)
        if not command_response:
            SQLOG.error("❌ 执行安装脚本失败!")
            return
        invoke_id = command_response['InvokeId']
        res_details = ecs_manager.describe_invocation_results(instance_id, invoke_id, 120, 5)
        res_info = ecs_manager.base64_decode(res_details.get("Output", ""))
        SQLOG.info(res_info)

    @staticmethod
    def install_ipsec_vpn(config, instance_id):
        SQLOG.info(f"正在安装 ipsec vpn ...")
        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        # 执行shell脚本
        shell_script = """
        #!/bin/bash
        
        wget https://get.vpnsetup.net -O vpn.sh && sudo VPN_IPSEC_PSK='{VPN_IPSEC_PSK}' VPN_USER='{VPN_USER}' VPN_PASSWORD='{VPN_PASSWORD}' bash vpn.sh
        
        """.format(VPN_IPSEC_PSK='greatpsk', VPN_USER='greatvpn', VPN_PASSWORD='greatpass')
        command_response = ecs_manager.run_command(instance_id, shell_script)
        invoke_id = command_response['InvokeId']
        res_details = ecs_manager.describe_invocation_results(instance_id, invoke_id, 100, 6)
        res_info = ecs_manager.base64_decode(res_details.get("Output",""))
        
        SQLOG.info(res_info)
            
    @staticmethod
    def install_singbox_protocol(config, instance_id, protocol, port):
        SQLOG.info(f"正在安装 {protocol}协议, 端口 {port}...")
        
        # 先添加防火墙端口规则
        vpcmanager = VPCManager(config.access_key, config.access_secret, config.region)
        if config.security_group_id:
            vpcmanager.add_vpn_port_rule(config.security_group_id, port)
        
        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        # 执行shell脚本
        shell_script = """
        #!/bin/bash
        echo "🔧 开始安装SingBox {protocol}协议，端口 {port}..."
        
        # 设置UTF-8环境变量和PATH
        export LC_CTYPE=en_US.UTF-8
        export LC_ALL=en_US.UTF-8
        export LANG=en_US.UTF-8
        export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
        
        # 设置环境变量控制默认协议和端口（在所有情况下都设置）
        export SINGBOX_DEFAULT_PROTOCOL="{protocol}"
        export SINGBOX_DEFAULT_PORT="{port}"
        
        # 检查是否存在233boy SingBox脚本的标志性文件
        if [ -d "/etc/sing-box" ] && [ "$(ls -A /etc/sing-box 2>/dev/null)" ]; then
            echo "✅ 检测到233boy SingBox已安装，添加新协议..."
            # 确保PATH包含常见目录
            export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
            
            # 直接使用233boy脚本添加协议
            if command -v sb &> /dev/null; then
                sb add {protocol} {port}
            elif [ -f "/usr/local/bin/sb" ]; then
                /usr/local/bin/sb add {protocol} {port}
            else
                # 如果找不到sb命令，尝试重新安装
                echo "📥 检测到配置文件但无法找到命令，重新安装SingBox..."
                wget -qO- https://raw.githubusercontent.com/wade0317/sing-box/refs/heads/main/install.sh | bash > /dev/null 2>&1
            fi
        else
            echo "📥 正在下载和安装SingBox..."
            wget -qO- https://raw.githubusercontent.com/wade0317/sing-box/refs/heads/main/install.sh | bash > /dev/null 2>&1
        fi
        
        # 安装二维码工具
        if ! command -v qrencode &> /dev/null; then
            echo "📦 安装二维码生成工具..."
            sudo apt-get update -y > /dev/null 2>&1
            sudo apt-get install qrencode -y --quiet > /dev/null 2>&1
        fi
        
        echo "📱 生成二维码..."
        # 确保能找到sb命令来生成二维码
        if command -v sb &> /dev/null; then
            sb qr {protocol}-{port}
        elif [ -f "/usr/local/bin/sb" ]; then
            /usr/local/bin/sb qr {protocol}-{port}
        else
            echo "⚠️  无法找到sb命令，跳过二维码生成"
        fi
        
        echo "🎉 SingBox {protocol}协议安装完成!"
        """.format(protocol=protocol, port=port)
        command_response = ecs_manager.run_command(instance_id, shell_script)
        invoke_id = command_response['InvokeId']
        res_details = ecs_manager.describe_invocation_results(instance_id, invoke_id, 100, 6)
        res_info = ecs_manager.base64_decode(res_details.get("Output",""))
        SQLOG.info(res_info)
        
        # 使用配置文件读取方式生成SingBox配置
        SqNetHelper.generate_singbox_config_from_files(config, instance_id, protocol, port, 'sing-box')
        
    @staticmethod
    def install_xray_protocol(config, instance_id, protocol, port):
        SQLOG.info(f"正在安装 {protocol}协议, 端口 {port}...")
        
        # 先添加防火墙端口规则
        vpcmanager = VPCManager(config.access_key, config.access_secret, config.region)
        if config.security_group_id:
            vpcmanager.add_vpn_port_rule(config.security_group_id, port)
        
        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        # 执行shell脚本
        shell_script = """
        #!/bin/bash
        echo "🔧 开始安装Xray {protocol}协议，端口 {port}..."
        
        # 设置UTF-8环境变量和PATH
        export LC_CTYPE=en_US.UTF-8
        export LC_ALL=en_US.UTF-8
        export LANG=en_US.UTF-8
        export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
        
        # 设置环境变量控制默认协议和端口（在所有情况下都设置）
        export XRAY_DEFAULT_PROTOCOL="{protocol}"
        export XRAY_DEFAULT_PORT="{port}"
        
        # 检查是否存在233boy Xray脚本的标志性文件
        if [ -d "/etc/xray" ] && [ "$(ls -A /etc/xray 2>/dev/null)" ]; then
            echo "✅ 检测到233boy Xray已安装，添加新协议..."
            # 确保PATH包含常见目录
            export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
            
            # 直接使用233boy脚本添加协议
            if command -v xray &> /dev/null; then
                xray add {protocol} {port}
            elif [ -f "/usr/local/bin/xray" ]; then
                /usr/local/bin/xray add {protocol} {port}
            else
                # 如果找不到xray命令，尝试重新安装
                echo "📥 检测到配置文件但无法找到命令，重新安装Xray..."
                wget -qO- https://raw.githubusercontent.com/wade0317/Xray/refs/heads/main/install.sh | bash
            fi
        else
            echo "📥 正在下载和安装Xray..."
            wget -qO- https://raw.githubusercontent.com/wade0317/Xray/refs/heads/main/install.sh | bash
        fi
        
        # 安装二维码工具
        if ! command -v qrencode &> /dev/null; then
            echo "📦 安装二维码生成工具..."
            sudo apt-get update -y > /dev/null 2>&1
            sudo apt-get install qrencode -y --quiet > /dev/null 2>&1
        fi
        
        echo "📱 生成二维码..."
        # 确保能找到xray命令来生成二维码
        if command -v xray &> /dev/null; then
            xray qr {protocol}-{port}
        elif [ -f "/usr/local/bin/xray" ]; then
            /usr/local/bin/xray qr {protocol}-{port}
        else
            echo "⚠️  无法找到xray命令，跳过二维码生成"
        fi
        
        echo "🎉 Xray {protocol}协议安装完成!"
        """.format(protocol=protocol, port=port)
        command_response = ecs_manager.run_command(instance_id, shell_script)
        invoke_id = command_response['InvokeId']
        res_details = ecs_manager.describe_invocation_results(instance_id, invoke_id, 100, 6)
        res_info = ecs_manager.base64_decode(res_details.get("Output",""))
        SQLOG.info(res_info)
        
        # 直接读取Xray配置文件生成SingBox配置
        SqNetHelper.generate_singbox_config_from_files(config, instance_id, protocol, port, 'xray')
    
    @staticmethod
    def generate_singbox_config_from_files(config, instance_id, protocol, port, engine_type='xray'):
        """直接读取配置文件生成SingBox配置
        
        Args:
            engine_type: 'xray' 或 'sing-box' 指定配置文件的来源
        """
        from sqnethelper.SqLog import SQLOG
        from sqnethelper.ECSManager import ECSManager
        
        SQLOG.info(f"📖 正在生成SingBox客户端配置...")
        
        # 获取实例的公网IP
        server_ip = SqNetHelper.get_instance_public_ip(config, instance_id)
        if not server_ip:
            SQLOG.error("❌ 无法获取服务器IP地址，跳过SingBox配置生成")
            return
        
        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        
        # 根据引擎类型选择配置文件路径
        if engine_type == 'xray':
            shell_script = f"""
            #!/bin/bash
            echo "🔍 查找Xray配置文件..."
            
            # 优先查找 /etc/xray/conf/ 目录中的配置文件
            if [ -d "/etc/xray/conf" ]; then
                # 233boy脚本的命名格式：VMess-TCP-3000.json
                # 首先尝试匹配标准格式：协议-传输层-端口.json
                config_file=$(find /etc/xray/conf -name "*{protocol.upper()}-*-{port}.json" 2>/dev/null | head -1)
                
                # 如果没找到，尝试协议+端口的组合
                if [ -z "$config_file" ]; then
                    config_file=$(find /etc/xray/conf -name "*{protocol.upper()}*{port}*.json" 2>/dev/null | head -1)
                fi
                
                # 如果没找到大写，尝试小写
                if [ -z "$config_file" ]; then
                    config_file=$(find /etc/xray/conf -name "*{protocol.lower()}*{port}*.json" 2>/dev/null | head -1)
                fi
                
                # 如果还没找到，尝试只匹配端口
                if [ -z "$config_file" ]; then
                    config_file=$(find /etc/xray/conf -name "*{port}*.json" 2>/dev/null | head -1)
                fi
            else
                # 如果 conf 目录不存在，查找 /etc/xray/ 目录
                config_file=$(find /etc/xray -name "*{protocol}*{port}*.json" 2>/dev/null | head -1)
            fi
            
            if [ -z "$config_file" ]; then
                echo "❌ 未找到匹配的配置文件"
                echo "📋 现有配置文件:"
                ls -la /etc/xray/conf/ 2>/dev/null || ls -la /etc/xray/ 2>/dev/null
            else
                echo "✅ 找到配置文件: $config_file"
                echo "📄 配置文件内容:"
                cat "$config_file"
            fi
            """
        else:  # sing-box
            shell_script = f"""
            #!/bin/bash
            echo "🔍 查找SingBox配置文件..."
            
            # 233boy SingBox脚本配置文件路径
            if [ -d "/etc/sing-box/conf" ]; then
                # 查找匹配的配置文件
                config_file=$(find /etc/sing-box/conf -name "*{protocol.upper()}-*-{port}.json" 2>/dev/null | head -1)
                
                # 如果没找到，尝试协议+端口的组合
                if [ -z "$config_file" ]; then
                    config_file=$(find /etc/sing-box/conf -name "*{protocol.upper()}*{port}*.json" 2>/dev/null | head -1)
                fi
                
                # 如果没找到大写，尝试小写
                if [ -z "$config_file" ]; then
                    config_file=$(find /etc/sing-box/conf -name "*{protocol.lower()}*{port}*.json" 2>/dev/null | head -1)
                fi
                
                # 如果还没找到，尝试只匹配端口
                if [ -z "$config_file" ]; then
                    config_file=$(find /etc/sing-box/conf -name "*{port}*.json" 2>/dev/null | head -1)
                fi
            else
                # 查找 /etc/sing-box/ 目录
                config_file=$(find /etc/sing-box -name "*{protocol}*{port}*.json" 2>/dev/null | head -1)
            fi
            
            if [ -z "$config_file" ]; then
                echo "❌ 未找到匹配的配置文件"
                echo "📋 现有配置文件:"
                ls -la /etc/sing-box/conf/ 2>/dev/null || ls -la /etc/sing-box/ 2>/dev/null
            else
                echo "✅ 找到配置文件: $config_file"
                echo "📄 配置文件内容:"
                cat "$config_file"
            fi
            """
        
        command_response = ecs_manager.run_command(instance_id, shell_script)
        invoke_id = command_response['InvokeId']
        res_details = ecs_manager.describe_invocation_results(instance_id, invoke_id, 30, 3)
        res_info = ecs_manager.base64_decode(res_details.get("Output",""))
        
        # 尝试从配置文件内容中解析JSON
        import json
        import re
        
        # 查找JSON内容
        json_match = re.search(r'\{.*\}', res_info, re.DOTALL)
        if json_match:
            try:
                json_content = json_match.group(0)
                config_data = json.loads(json_content)
                
                if engine_type == 'xray':
                    # Xray配置文件处理
                    singbox_config = SqNetHelper.convert_xray_to_singbox_config(config_data, server_ip, protocol, port)
                else:
                    # SingBox配置文件处理
                    singbox_config = SqNetHelper.convert_singbox_inbound_to_outbound(config_data, server_ip, protocol, port)
                
                if singbox_config:
                    SQLOG.great("🔧 SingBox客户端配置:")
                    SQLOG.great("=" * 60)
                    
                    from sqnethelper.SqUtils import SqUtils
                    formatted_config = SqUtils.format_singbox_config_output(singbox_config)
                    
                    # 按行输出配置，以便正确显示
                    for line in formatted_config.split('\n'):
                        SQLOG.info(line)
                    
                    SQLOG.great("=" * 60)
                    SQLOG.info("💡 将上述配置复制到SingBox客户端的outbounds部分")
                    
                    # 生成完整的SingBox配置文件
                    SqNetHelper.generate_complete_singbox_config(singbox_config, server_ip, protocol, port)
                else:
                    SQLOG.error(f"❌ 无法从{engine_type.upper()}配置生成SingBox配置")
                    
            except json.JSONDecodeError as e:
                SQLOG.error(f"❌ 配置解析失败，使用备用方式...")
                # 回退到原来的方法
                SqNetHelper.generate_and_display_singbox_config(config, instance_id, protocol, port, res_info)
        else:
            SQLOG.error("❌ 未找到配置文件，使用备用方式...")
            # 回退到原来的方法  
            SqNetHelper.generate_and_display_singbox_config(config, instance_id, protocol, port, res_info)
    
    @staticmethod
    def convert_xray_to_singbox_config(xray_config, server_ip, protocol, port):
        """将Xray配置转换为SingBox配置"""
        from sqnethelper.SqLog import SQLOG
        
        try:
            outbounds = []
            
            # 从inbounds中找到匹配端口的配置
            target_inbound = None
            for inbound in xray_config.get('inbounds', []):
                inbound_port = inbound.get('port')
                # 确保端口类型匹配（可能是字符串或数字）
                if inbound_port == port or inbound_port == int(port) or str(inbound_port) == str(port):
                    target_inbound = inbound
                    break
            
            if not target_inbound:
                SQLOG.error(f"❌ 未找到端口{port}的inbound配置")
                return None
            
            # 获取协议和设置
            xray_protocol = target_inbound.get('protocol', '')
            settings = target_inbound.get('settings', {})
            stream_settings = target_inbound.get('streamSettings', {})
            
            # 根据协议转换配置
            if xray_protocol == 'vmess':
                # 获取第一个用户的UUID
                users = settings.get('clients', [])
                if users:
                    user_uuid = users[0].get('id', '')
                    SQLOG.info(f"✅ 获取到{xray_protocol.upper()}配置，UUID: {user_uuid[:8]}...")
                    
                    # 获取网络类型
                    network = stream_settings.get('network', 'tcp')
                    
                    tag_name = f"vmess-{server_ip.replace('.', '-')}"
                    vmess_config = {
                        "type": "vmess",
                        "tag": tag_name,
                        "server": server_ip,
                        "server_port": port,
                        "uuid": user_uuid,
                        "security": "auto",
                        "network": network
                    }
                    
                    # 添加传输层配置
                    if network == 'ws':
                        ws_settings = stream_settings.get('wsSettings', {})
                        vmess_config['transport'] = {
                            "type": "ws",
                            "path": ws_settings.get('path', '/'),
                            "headers": ws_settings.get('headers', {})
                        }
                    elif network == 'h2':
                        h2_settings = stream_settings.get('httpSettings', {})
                        vmess_config['transport'] = {
                            "type": "http",
                            "path": h2_settings.get('path', '/'),
                            "host": h2_settings.get('host', [])
                        }
                    elif network == 'grpc':
                        grpc_settings = stream_settings.get('grpcSettings', {})
                        vmess_config['transport'] = {
                            "type": "grpc",
                            "service_name": grpc_settings.get('serviceName', '')
                        }
                    
                    # 处理TLS
                    tls_settings = stream_settings.get('tlsSettings', {})
                    if tls_settings:
                        vmess_config['tls'] = {
                            "enabled": True,
                            "server_name": tls_settings.get('serverName', server_ip)
                        }
                    
                    outbounds.append(vmess_config)
                    
            elif xray_protocol == 'vless':
                # 获取第一个用户的UUID
                users = settings.get('clients', [])
                if users:
                    user_uuid = users[0].get('id', '')
                    user_flow = users[0].get('flow', '')
                    SQLOG.info(f"✅ 获取到{xray_protocol.upper()}配置，UUID: {user_uuid[:8]}...")
                    
                    tag_name = f"vless-{server_ip.replace('.', '-')}"
                    vless_config = {
                        "type": "vless",
                        "tag": tag_name,
                        "server": server_ip,
                        "server_port": port,
                        "uuid": user_uuid,
                        "flow": user_flow
                    }
                    
                    # 处理Reality或TLS
                    tls_settings = stream_settings.get('tlsSettings', {})
                    reality_settings = stream_settings.get('realitySettings', {})
                    
                    if reality_settings:
                        # Reality配置
                        # 从serverNames数组中获取第一个非空的serverName
                        server_names = reality_settings.get('serverNames', [])
                        server_name = 'aws.amazon.com'  # 默认值
                        for name in server_names:
                            if name and name.strip():
                                server_name = name.strip()
                                break
                        
                        vless_config['tls'] = {
                            "enabled": True,
                            "server_name": server_name,
                            "utls": {
                                "enabled": True,
                                "fingerprint": "chrome"
                            },
                            "reality": {
                                "enabled": True,
                                "public_key": reality_settings.get('publicKey', '')
                            }
                        }
                    elif tls_settings:
                        # 普通TLS配置
                        vless_config['tls'] = {
                            "enabled": True,
                            "server_name": tls_settings.get('serverName', server_ip)
                        }
                    
                    outbounds.append(vless_config)
            
            if outbounds:
                # 创建selector配置
                main_outbound = outbounds[0]
                tag_name = main_outbound['tag']
                
                selector_config = {
                    "type": "selector",
                    "tag": "proxy",
                    "outbounds": [tag_name],
                    "default": tag_name
                }
                
                return {
                    "outbounds": [selector_config] + outbounds
                }
            else:
                return None
                
        except Exception as e:
            SQLOG.error(f"❌ 转换Xray配置失败: {str(e)}")
            return None
    
    @staticmethod
    def get_instance_public_ip(config, instance_id):
        """获取实例的公网IP地址"""
        ecs_manager = ECSManager(config.access_key, config.access_secret, config.region)
        instance_array = ecs_manager.list_instances()
        for instance in instance_array:
            if instance['InstanceId'] == instance_id:
                return instance.get('PublicIpAddress', '')
        return None
    
    @staticmethod
    def generate_and_display_singbox_config(config, instance_id, protocol, port, vpn_output):
        """生成并显示SingBox客户端配置"""
        from sqnethelper.SqUtils import SqUtils
        
        # 获取实例的公网IP
        server_ip = SqNetHelper.get_instance_public_ip(config, instance_id)
        if not server_ip:
            SQLOG.error("❌ 无法获取服务器IP地址，跳过SingBox配置生成")
            return
        
        # 生成SingBox配置
        singbox_config = SqUtils.parse_vpn_output_and_generate_singbox_config(
            vpn_output, server_ip, protocol, port
        )
        
        if singbox_config:
            SQLOG.great("🔧 SingBox客户端配置:")
            SQLOG.great("=" * 60)
            formatted_config = SqUtils.format_singbox_config_output(singbox_config)
            
            # 按行输出配置，以便正确显示
            for line in formatted_config.split('\n'):
                SQLOG.info(line)
            
            SQLOG.great("=" * 60)
            SQLOG.info("💡 将上述配置复制到SingBox客户端的outbounds部分")
            
            # 生成完整的SingBox配置文件
            SqNetHelper.generate_complete_singbox_config(singbox_config, server_ip, protocol, port)
        else:
            SQLOG.error("❌ 无法生成SingBox配置")
    
    @staticmethod
    def generate_complete_singbox_config(outbound_config, server_ip, protocol, port):
        """生成完整的SingBox配置文件并保存到工作目录"""
        import json
        import os
        from datetime import datetime
        
        try:
            # 读取模板文件
            from sqnethelper.resources import load_template
            template_config = load_template()
            
            # 获取新的outbound配置
            new_outbound = outbound_config['outbounds'][1]  # 跳过selector，获取实际的协议配置
            new_tag = new_outbound['tag']
            
            # 检查是否已存在相同tag的outbound
            existing_outbounds = template_config['outbounds']
            updated = False
            
            # 移除示例配置 example_out
            existing_outbounds[:] = [outbound for outbound in existing_outbounds 
                                   if outbound.get('tag') != 'example_out']
            
            # 更新或添加outbound
            for i, outbound in enumerate(existing_outbounds):
                if outbound.get('tag') == new_tag:
                    # 更新现有配置
                    existing_outbounds[i] = new_outbound
                    updated = True
                    SQLOG.info(f"🔄 更新现有配置: {new_tag}")
                    break
            
            if not updated:
                # 添加新的outbound（在dns-out之前插入）
                dns_index = next((i for i, outbound in enumerate(existing_outbounds) 
                                if outbound.get('tag') == 'dns-out'), len(existing_outbounds))
                existing_outbounds.insert(dns_index, new_outbound)
            
            # 更新selector的outbounds列表，移除example_out并添加新tag
            for outbound in existing_outbounds:
                if outbound.get('type') == 'selector' and outbound.get('tag') == 'proxy':
                    # 移除example_out
                    if 'example_out' in outbound['outbounds']:
                        outbound['outbounds'].remove('example_out')
                    # 添加新tag
                    if new_tag not in outbound['outbounds']:
                        outbound['outbounds'].append(new_tag)
                    # 设置默认选择
                    outbound['default'] = new_tag
                    break
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sing-box_config_{protocol}_{port}_{timestamp}.json"
            
            # 保存配置文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(template_config, f, indent=4, ensure_ascii=False)
            
            SQLOG.great(f"📁 SingBox配置文件已保存: {filename}")
            SQLOG.info("💡 可直接导入SingBox客户端使用")
            
        except Exception as e:
            SQLOG.error(f"❌ 生成SingBox配置文件失败: {str(e)}")
            SQLOG.debug(f"错误详情: {e}")
        
    
    @staticmethod
    def exe_shell_command(hostname, config, use_key_login, shell_script, verbose=False):
        result = False
        try:
            if use_key_login:       
                result = ShellHelper.ssh_connect_and_execute_with_key(hostname, config.instance_login_name, config.ssh_local_path, shell_script, verbose=verbose)
            else:
                result = ShellHelper.ssh_connect_and_execute_with_password(hostname, config.instance_login_name, config.instance_login_password, shell_script, verbose=verbose)
            return result
        except Exception as e:
            SQLOG.error(f"安装v2ray VPN时发生错误: {str(e)}")
            return result
        
    @staticmethod
    def convert_singbox_inbound_to_outbound(singbox_config, server_ip, protocol, port):
        """将SingBox inbound配置转换为SingBox outbound配置"""
        from sqnethelper.SqLog import SQLOG
        
        try:
            outbounds = []
            
            # 从inbounds中找到匹配端口的配置
            target_inbound = None
            for inbound in singbox_config.get('inbounds', []):
                inbound_port = inbound.get('listen_port', inbound.get('port'))
                # 确保端口类型匹配
                if inbound_port == port or inbound_port == int(port) or str(inbound_port) == str(port):
                    target_inbound = inbound
                    break
            
            if not target_inbound:
                SQLOG.error(f"❌ 未找到端口{port}的inbound配置")
                return None
            
            # 获取协议和设置
            inbound_type = target_inbound.get('type', '')
            SQLOG.info(f"📋 解析到的SingBox协议: {inbound_type}")
            
            # 直接转换inbound为outbound（移除监听相关配置，添加服务器信息）
            outbound_config = dict(target_inbound)
            
            # 移除inbound特有的配置
            outbound_config.pop('listen', None)
            outbound_config.pop('listen_port', None)
            outbound_config.pop('port', None)
            outbound_config.pop('sniff', None)
            outbound_config.pop('sniff_override_destination', None)
            
            # 添加outbound特有的配置
            outbound_config['server'] = server_ip
            outbound_config['server_port'] = port
            
            # 设置tag
            tag_name = f"{inbound_type}-{server_ip.replace('.', '-')}"
            outbound_config['tag'] = tag_name
            
            # 如果有users配置，提取第一个用户的信息
            users = outbound_config.get('users', [])
            if users and len(users) > 0:
                user = users[0]
                if 'uuid' in user:
                    outbound_config['uuid'] = user['uuid']
                    SQLOG.info(f"🔑 找到UUID: {user['uuid']}")
                if 'password' in user:
                    outbound_config['password'] = user['password']
                # 移除users配置
                outbound_config.pop('users', None)
            
            outbounds.append(outbound_config)
            
            if outbounds:
                # 创建selector配置
                main_outbound = outbounds[0]
                tag_name = main_outbound['tag']
                
                selector_config = {
                    "type": "selector",
                    "tag": "proxy",
                    "outbounds": [tag_name],
                    "default": tag_name
                }
                
                return {
                    "outbounds": [selector_config] + outbounds
                }
            else:
                return None
                
        except Exception as e:
            SQLOG.error(f"❌ 转换SingBox配置失败: {str(e)}")
            return None
        