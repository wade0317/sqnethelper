import click
import json
import asyncio
import threading
from sqnethelper.SqLog import SQLOG, LogLevel
from sqnethelper.SqNetHelper import SqNetHelper
from sqnethelper.ConfigManager import ConfigManager
from sqnethelper.SqUtils import SqUtils
from importlib.metadata import version



SQLOG.set_log_level(LogLevel.INFO)
SQLOG.set_console_output()
# SQLOG.set_websocket_output()

    
SQLOG.info("Hello, SqNetHelper!")

@click.group()
@click.version_option(version=version("sqnethelper"), prog_name="sqnethelper")
def cli():
    pass

@cli.command()
@click.option('--access-key', prompt=True, help='阿里云Access Key')
@click.option('--access-secret', prompt=True, help='阿里云Access Secret')
@click.option('--verbose', is_flag=True, help='打印输出log')
def setup(access_key, access_secret, verbose):
    """设置阿里云账号凭证"""
    if verbose:
        SQLOG.set_log_level(LogLevel.DEBUG)
        pass

    result = SqNetHelper.setup(access_key, access_secret)
    click.echo(result)

    # 重新加载配置
    config = ConfigManager()
    config.load_config()  # 确保重新加载配置
    if not config.is_configured():
        SQLOG.error("❌ 未设置阿里云访问凭证!")
        SQLOG.info("🔧 请先运行以下命令设置阿里云Access Key和Secret:")
        SQLOG.info("   sqnethelper setup")
        return False

    regions = SqNetHelper.list_regions()
    if not regions:
        click.echo("Error: 获取region列表失败!")
        return False

    region_dict = {region['RegionId']: region['LocalName'] for region in regions}
    output = ["Available regions:"]
    region_choices = []
    for i, (region_id, local_name) in enumerate(region_dict.items(), start=1):
        region_choices.append(region_id)
        output.append(f"{i}. {local_name} ({region_id})")

    click.echo("\n".join(output))
    if region_choices:
        choice = click.prompt("请选择需要操作的region序号：", type=int)
        if choice < 1 or choice > len(region_choices):
            click.echo("Error: 无效选择!")
            return False
        selected_region_id = region_choices[choice - 1]
        result = SqNetHelper.set_region(selected_region_id)
        if result:
            click.echo("设置region: 成功!")
        else:
            click.echo("设置region:{selected_region_id} 失败!")

@cli.command()
@click.option('--region', is_flag=True, help='配置region')
@click.option('--verbose', is_flag=True, help='打印输出log')
def config(region, verbose):
    """修改当前账号的网络配置"""
    if verbose:
        SQLOG.set_log_level(LogLevel.DEBUG)
        pass

    config = ConfigManager()
    if not config.is_configured():
        SQLOG.error("❌ 未设置阿里云访问凭证!")
        SQLOG.info("🔧 请先运行以下命令设置阿里云Access Key和Secret:")
        SQLOG.info("   sqnethelper setup")
        return False

    # 如果没有任何参数，显示当前配置
    if not region:
        SQLOG.great("当前配置信息:")
        SQLOG.great("=" * 50)
        
        # 基本配置
        SQLOG.great("📋 基本配置:")
        SQLOG.info(f"  Access Key: {config.access_key[:8]}****{config.access_key[-4:] if len(config.access_key) > 12 else '****'}")
        SQLOG.info(f"  Access Secret: ****")
        SQLOG.info(f"  Region: {config.region}")
        SQLOG.info(f"  Zone ID: {config.zone_id}")
        
        # 实例配置
        SQLOG.great("🖥️  实例配置:")
        SQLOG.info(f"  实例名称前缀: {config.instance_name}")
        SQLOG.info(f"  实例类型: {config.instance_type}")
        SQLOG.info(f"  CPU核数: {config.instance_cpu_count}")
        SQLOG.info(f"  内存大小: {config.instance_memory_size}GB")
        SQLOG.info(f"  磁盘类型: {config.instance_disk_category}")
        SQLOG.info(f"  磁盘大小: {config.instance_disk_size}GB")
        SQLOG.info(f"  镜像ID: {config.image_id}")
        
        # 网络配置
        SQLOG.great("🌐 网络配置:")
        SQLOG.info(f"  出网带宽: {config.internet_bandwidth_out}Mbps")
        SQLOG.info(f"  入网带宽: {config.internet_bandwidth_in}Mbps")
        SQLOG.info(f"  计费方式: {config.internet_charge_type}")
        SQLOG.info(f"  VPC名称前缀: {config.vpc_name}")
        SQLOG.info(f"  VPC ID: {config.vpc_id if config.vpc_id else '未设置'}")
        SQLOG.info(f"  虚拟交换机名称前缀: {config.vswitch_name}")
        SQLOG.info(f"  虚拟交换机ID: {config.vswitch_id if config.vswitch_id else '未设置'}")
        SQLOG.info(f"  安全组名称前缀: {config.security_group_name}")
        SQLOG.info(f"  安全组ID: {config.security_group_id if config.security_group_id else '未设置'}")
        
        # 登录配置
        SQLOG.great("🔐 登录配置:")
        SQLOG.info(f"  登录用户名: {config.instance_login_name}")
        SQLOG.info(f"  登录密码: ****")
        SQLOG.info(f"  SSH密钥对名称: {config.ssh_keypair_name if config.ssh_keypair_name else '未设置'}")
        SQLOG.info(f"  SSH本地私钥路径: {config.ssh_local_path if config.ssh_local_path else '未设置'}")
        
        # VPN配置
        SQLOG.great("🔒 VPN配置:")
        SQLOG.info(f"  VPN用户名: {config.vpn_name}")
        SQLOG.info(f"  VPN密码: ****")
        SQLOG.info(f"  VPN PSK: ****")
        
        # VPN端口配置
        SQLOG.great("🌐 VPN端口配置:")
        SQLOG.info(f"  Xray TCP端口: {config.xray_tcp_port}")
        SQLOG.info(f"  Xray Reality端口: {config.xray_reality_port}")
        SQLOG.info(f"  SingBox SS端口: {config.singbox_ss_port}")
        SQLOG.info(f"  SingBox Reality端口: {config.singbox_reality_port}")
        
        SQLOG.great("=" * 50)
        SQLOG.info("💡 使用 'sqnethelper config --region' 来修改region配置")
        return True

    if region:
        regions = SqNetHelper.list_regions()
        if not regions:
            click.echo("Error: 获取region列表失败!")
            return False
        
        region_dict = {region['RegionId']: region['LocalName'] for region in regions}
        output = ["Available regions:"]
        region_choices = []
        for i, (region_id, local_name) in enumerate(region_dict.items(), start=1):
            region_choices.append(region_id)
            output.append(f"{i}. {local_name} ({region_id})")

        click.echo("\n".join(output))
        if region_choices:
            choice = click.prompt("请选择需要操作的region序号：", type=int)
            if choice < 1 or choice > len(region_choices):
                click.echo("Error: 无效选择!")
                return False
            selected_region_id = region_choices[choice - 1]
            result = SqNetHelper.set_region(selected_region_id)
            if result:
                SQLOG.info(f"设置region: {selected_region_id}成功!")
            else:
                SQLOG.info("设置region:{selected_region_id} 失败!")


@cli.command()
@click.option('--verbose', is_flag=True, help='打印输出log')
def list(verbose):
    """列出所有网络服务器"""
    if verbose:
        SQLOG.set_log_level(LogLevel.DEBUG)
        pass

    config = ConfigManager()
    if not config.is_configured():
        SQLOG.error("❌ 未设置阿里云访问凭证!")
        SQLOG.info("🔧 请先运行以下命令设置阿里云Access Key和Secret:")
        SQLOG.info("   sqnethelper setup")
        return False
    instance_array = SqNetHelper.list_instances()
    SQLOG.great("创建的虚拟机列表:")
    
    # 检查实例列表是否为空或None
    if instance_array is None:
        SQLOG.error("❌ 无法获取虚拟机列表，请检查网络连接和配置!")
        return False
    
    # SQLOG.info(f"共有{len(instance_array)}个虚拟机!")
    if len(instance_array) > 0:
        i = 1
        for instance in instance_array:
            SQLOG.great(f"{i}. ID: {instance['InstanceId']}, 名称: {instance['Name']}, IP: {instance['PublicIpAddress']}, 状态: {instance['Status']}, 释放时间:{instance['AutoReleaseTime']}")
            i += 1

    return True


@cli.command()
@click.option('--verbose', is_flag=True, help='打印输出log')
def create(verbose):
    """创建新的ECS实例"""
    if verbose:
        SQLOG.set_log_level(LogLevel.DEBUG)
        pass
    config = ConfigManager()
    if not config.is_configured():
        SQLOG.error("❌ 未设置阿里云访问凭证!")
        SQLOG.info("🔧 请先运行以下命令设置阿里云Access Key和Secret:")
        SQLOG.info("   sqnethelper setup")
        SQLOG.info("💡 如果还没有阿里云账号，请访问 https://www.aliyun.com 注册")
        return False
    
    instance_details = SqNetHelper.create_instance(config)
    
    if instance_details and instance_details.get('InstanceId'):
        instance_id = instance_details.get('InstanceId')
        # SqNetHelper.install_singbox_protocol(config, instance_id, 'reality', 443)
        # SqNetHelper.install_xray_protocol(config, instance_id, 'reality', 5432)
        # port = click.prompt(f"请输入端口号 (默认: {config.xray_tcp_port})", type=int, default=config.xray_tcp_port)
        # SQLOG.info(f"🔧 正在安装 Xray TCP协议，端口: {port}...")
        # port=config.xray_tcp_port
        # SqNetHelper.install_xray_protocol(config, instance_id, 'tcp', port)
        
        # SqNetHelper.install_singbox_protocol(config, instance_id, 'ss', 80)
    else:
        SQLOG.error("创建实例失败!")

@cli.command()
@click.option('--verbose', is_flag=True, help='打印输出log')
def autodel(verbose):
    """修改远程虚拟机自动释放的时间"""
    if verbose:
        SQLOG.set_log_level(LogLevel.DEBUG)
        pass
    
    config = ConfigManager()
    if not config.is_configured():
        SQLOG.error("❌ 未设置阿里云访问凭证!")
        SQLOG.info("🔧 请先运行以下命令设置阿里云Access Key和Secret:")
        SQLOG.info("   sqnethelper setup")
        return False

    instance_array = SqNetHelper.list_instances()
    SQLOG.great("创建的虚拟机列表:")
    
    # 检查实例列表是否为空或None
    if instance_array is None:
        SQLOG.error("❌ 无法获取虚拟机列表，请检查网络连接和配置!")
        return False
    
    # SQLOG.info(f"共有{len(instance_array)}个虚拟机!")
    if len(instance_array) > 0:
        i = 1
        for instance in instance_array:
            SQLOG.great(f"{i}. ID: {instance['InstanceId']}, 名称: {instance['Name']}, IP: {instance['PublicIpAddress']}, 状态: {instance['Status']}, 释放时间:{instance['AutoReleaseTime']}")
            i += 1


        SQLOG.great(f"请输入需要销毁的虚拟机序号:")
        choice = click.prompt("", type=int)

        if choice < 1 or choice > len(instance_array):
            SQLOG.error("错误: 无效选择!")
            return False
        else:
            instance_id = instance_array[choice - 1]['InstanceId']
            SQLOG.great(f"请输入自动删除的时间间隔(分钟),输入0取消自动释放,大于5分钟设置自动释放:")
            time_min_delay = click.prompt("", type=int)

            if time_min_delay != 0 and time_min_delay < 5:
                SQLOG.error("错误: 时间间隔必须为0(取消)或大于5分钟!")
                return False
                
            result = SqNetHelper.modify_auto_release_time(config, instance_id, time_min_delay)
            if result:
                if time_min_delay == 0:
                    SQLOG.great(f"✅ 已成功取消自动释放！")
                    SQLOG.great(f"远程虚拟机 {instance_id} 的自动释放已被取消")
                else:
                    from datetime import datetime, timedelta
                    local_release_time = (datetime.now() + timedelta(minutes=time_min_delay)).strftime('%Y-%m-%d %H:%M:%S')
                    SQLOG.great(f"✅ 设置成功！")
                    SQLOG.great(f"远程虚拟机 {instance_id} 将在 {time_min_delay} 分钟后自动释放")
                    SQLOG.great(f"预计释放时间(本地时间): {local_release_time}")
                SQLOG.info("请运行 'sqnethelper list' 查看更新后的释放时间")
            else:
                if time_min_delay == 0:
                    SQLOG.error(f"❌ 远程虚拟机{instance_id}取消自动释放失败!")
                else:
                    SQLOG.error(f"❌ 远程虚拟机{instance_id}设置自动释放时间失败!")
            
            
@cli.command()
@click.option('--verbose', is_flag=True, help='打印输出log')
def delete(verbose):
    """删除网络服务器"""
    if verbose:
        SQLOG.set_log_level(LogLevel.DEBUG)
        pass

    config = ConfigManager()
    if not config.is_configured():
        SQLOG.error("❌ 未设置阿里云访问凭证!")
        SQLOG.info("🔧 请先运行以下命令设置阿里云Access Key和Secret:")
        SQLOG.info("   sqnethelper setup")
        return False
    instance_array = SqNetHelper.list_instances()
    SQLOG.great("创建的虚拟机列表:")
    
    # 检查实例列表是否为空或None
    if instance_array is None:
        SQLOG.error("❌ 无法获取虚拟机列表，请检查网络连接和配置!")
        return False
    
    # SQLOG.info(f"共有{len(instance_array)}个虚拟机!")
    if len(instance_array) > 0:
        i = 1
        for instance in instance_array:
            SQLOG.great(f"{i}. ID: {instance['InstanceId']}, 名称: {instance['Name']}, IP: {instance['PublicIpAddress']}, 状态: {instance['Status']}, 释放时间:{instance['AutoReleaseTime']}")
            i += 1


        SQLOG.great(f"请输入需要销毁的虚拟机序号:")
        choice = click.prompt("", type=int)

        if choice < 1 or choice > len(instance_array):
            SQLOG.error("错误: 无效选择!")
            return False
        else:
            instance_id = instance_array[choice - 1]['InstanceId']
            SQLOG.info(f"正在销毁虚拟机: {instance_id}")
            result = SqNetHelper.confirm_delete_instance(instance_id)
            if result:
                SQLOG.info(f"销毁虚拟机: {instance_id} 成功!")
            else:
                SQLOG.error(f"销毁虚拟机: {instance_id} 失败!")


@cli.command()
@click.option('--verbose', is_flag=True, help='打印输出log')
def addvpn(verbose):
    """安装VPN协议 - 支持IPsec、Xray、SingBox等多种协议"""
    if verbose:
        SQLOG.set_log_level(LogLevel.DEBUG)
        pass

    config = ConfigManager()
    if not config.is_configured():
        SQLOG.error("❌ 未设置阿里云访问凭证!")
        SQLOG.info("🔧 请先运行以下命令设置阿里云Access Key和Secret:")
        SQLOG.info("   sqnethelper setup")
        return False
    instance_array = SqNetHelper.list_instances()
    SQLOG.great("创建的虚拟机列表:")
    
    # 检查实例列表是否为空或None
    if instance_array is None:
        SQLOG.error("❌ 无法获取虚拟机列表，请检查网络连接和配置!")
        return False
    
    if len(instance_array) > 0:
        i = 1
        for instance in instance_array:
            SQLOG.great(f"{i}. ID: {instance['InstanceId']}, 名称: {instance['Name']}, IP: {instance['PublicIpAddress']}, 状态: {instance['Status']}, 释放时间:{instance['AutoReleaseTime']}")
            i += 1

        SQLOG.great(f"请输入需要操作的虚拟机序号:")
        vm_choice = click.prompt("", type=int)

        if vm_choice < 1 or vm_choice > len(instance_array):
            SQLOG.error("错误: 无效选择!")
            return False
        else:
            instance_id = instance_array[vm_choice - 1]['InstanceId']
            SqNetHelper.install_vpn_unified(config, instance_id)
            

                
# @cli.command()
# def delete_all():
#     """删除当前所有资源"""

if __name__ == '__main__':
    cli()



# # 主程序示例
# if __name__ == "__main__":
#     SQLOG.set_console_output()
#     SQLOG.set_websocket_output()

#     # 模拟定期发送消息
#     async def send_periodic_message():
#         while True:
#             await asyncio.sleep(5)
#             SQLOG.info("Periodic message")

#     # 运行WebSocket服务器和定期发送消息
#     loop = asyncio.get_event_loop()
#     loop.create_task(send_periodic_message())
#     loop.run_forever()



