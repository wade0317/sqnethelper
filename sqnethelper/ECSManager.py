import json
import time
import base64
import os
import sys
from sqnethelper.SqLog import SQLOG
from sqnethelper.SqUtils import SqUtils

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkecs.request.v20140526.CreateInstanceRequest import CreateInstanceRequest
from aliyunsdkecs.request.v20140526.StartInstanceRequest import StartInstanceRequest
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkecs.request.v20140526.StopInstanceRequest import StopInstanceRequest
from aliyunsdkecs.request.v20140526.DeleteInstanceRequest import DeleteInstanceRequest
from aliyunsdkecs.request.v20140526.CreateCommandRequest import CreateCommandRequest
from aliyunsdkecs.request.v20140526.InvokeCommandRequest import InvokeCommandRequest
from aliyunsdkecs.request.v20140526.RunCommandRequest import RunCommandRequest
from aliyunsdkecs.request.v20140526.DescribeInvocationResultsRequest import DescribeInvocationResultsRequest
from aliyunsdkecs.request.v20140526.DescribeRegionsRequest import DescribeRegionsRequest
from aliyunsdkecs.request.v20140526.DescribeZonesRequest import DescribeZonesRequest
from aliyunsdkecs.request.v20140526.AllocatePublicIpAddressRequest import AllocatePublicIpAddressRequest
from aliyunsdkecs.request.v20140526.ModifyInstanceAttributeRequest import ModifyInstanceAttributeRequest
from aliyunsdkecs.request.v20140526.AttachKeyPairRequest import AttachKeyPairRequest
from aliyunsdkecs.request.v20140526.ModifyInstanceAutoReleaseTimeRequest import ModifyInstanceAutoReleaseTimeRequest
from aliyunsdkecs.request.v20140526.CreateImageRequest import CreateImageRequest
from aliyunsdkecs.request.v20140526.DescribeImagesRequest import DescribeImagesRequest
from aliyunsdkecs.request.v20140526.DeleteImageRequest import DeleteImageRequest

class ECSManager:

    def __init__(self, access_key, access_secret, region):
        self.client = AcsClient(access_key, access_secret, region)

    def get_regions(self):
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                describe_regions_request = DescribeRegionsRequest()
                describe_regions_request.set_action_name('DescribeRegions')
                describe_regions_response = self.client.do_action_with_exception(describe_regions_request)
                # SQLOG.info(json.loads(describe_regions_response))
                regions = json.loads(describe_regions_response)['Regions']['Region']
                if not regions:
                    return {}
                return regions
            except Exception as e:
                SQLOG.info(f"get_regions attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 等待2秒后重试
                else:
                    return None

    def get_zones(self):
        try:
            describe_regions_request = DescribeZonesRequest()
            describe_regions_request.set_action_name('DescribeZones')
            describe_regions_response = self.client.do_action_with_exception(describe_regions_request)

            zones = json.loads(describe_regions_response)['Zones']['Zone']

            if not zones:
                return {}

            return zones

        except Exception as e:
            SQLOG.info(f"get_zones: {str(e)}")
            return None

    def check_auto_release_time_ready(self, instance_id):
        detail = self.describe_instance_detail(instance_id=instance_id)
        if detail is not None:
            release_time = detail.get('AutoReleaseTime')
            return release_time

    def modify_instance_auto_release_time(self, instance_id, time_to_release):
        try:
            request = ModifyInstanceAutoReleaseTimeRequest()
            request.set_InstanceId(instance_id)
            if time_to_release is not None:
                request.set_AutoReleaseTime(time_to_release)
            self.client.do_action_with_exception(request)
            release_time = self.check_auto_release_time_ready(instance_id)
            return release_time
        except Exception as e:
            SQLOG.error(f"设置自动消耗时间失败: {str(e)}")
            return None
        
    def list_instances(self):
        try:
            describe_instances_request = DescribeInstancesRequest()
            describe_instances_request.set_PageSize(10)
            describe_instances_response = self.client.do_action_with_exception(describe_instances_request)
            instances = json.loads(describe_instances_response)['Instances']['Instance']

            if not instances:
                return []

            instance_array = []
            for instance in instances:
                instance_id = instance['InstanceId']
                instance_item = {
                    'InstanceId': instance_id,
                    'Name': instance['InstanceName'],
                    'Status': instance['Status'],
                    'PublicIpAddress': 'N/A'
                }
                if instance.get('PublicIpAddress', {}).get('IpAddress', ['']):
                    instance_item['PublicIpAddress'] = instance.get('PublicIpAddress', {}).get('IpAddress', [''])[0]  # 获取公网IP
                else:
                    instance_item['PublicIpAddress'] = 'N/A'
                
                # 转换UTC时间为本地时间
                utc_release_time = instance.get('AutoReleaseTime') or 'N/A'
                instance_item['AutoReleaseTime'] = SqUtils.utc_to_local_time(utc_release_time)
                
                instance_array.append(instance_item)

            return instance_array

            # instance_dict = []
            # for instance in instances:
            #     instance_id = instance['InstanceId']
            #     instance_dict[instance_id] = {
            #         'Name': instance['InstanceName'],
            #         'Status': instance['Status'],
            #         'PublicIpAddress': 'N/A'
            #     }
            #     if instance.get('PublicIpAddress', {}).get('IpAddress', ['']):
            #         instance_dict[instance_id]['PublicIpAddress'] = instance.get('PublicIpAddress', {}).get('IpAddress', [''])[0]  # 获取公网IP
            # return instance_dict

        except Exception as e:
            SQLOG.info(f"list_instances Error: {str(e)}")
            return None

    def create_instance(self, config):

        request = CreateInstanceRequest()
        request.set_InstanceType(config.instance_type)
        request.set_ImageId(config.image_id)
        request.set_SecurityGroupId(config.security_group_id)
        request.set_VSwitchId(config.vswitch_id)
        time_str = time.strftime('%m%d-%H-%M-%S', time.localtime())
        instance_name = config.instance_name + f"{time_str}"
        request.set_InstanceName(instance_name)
        request.set_InternetChargeType(config.internet_charge_type)
        request.set_IoOptimized('optimized')
        request.set_SystemDiskCategory(config.instance_disk_category)
        request.set_SystemDiskSize(config.instance_disk_size)  
        request.set_InternetMaxBandwidthOut(config.internet_bandwidth_out)  
        request.set_InternetMaxBandwidthIn(config.internet_bandwidth_in)  
            
        
        try:
            response = self.client.do_action_with_exception(request)
            instance_details = json.loads(response)
            return instance_details

        except Exception as e:
            SQLOG.error(f"创建远程虚拟机失败！")
            SQLOG.debug(f"{str(e)}")
            return None

    def start_instance(self, instance_id):
        try:
            request = StartInstanceRequest()
            request.set_InstanceId(instance_id)
            response = self.client.do_action_with_exception(request)
            SQLOG.debug(f"启动远程虚拟机: {instance_id}...")
            return True
        
        except Exception as e:
            SQLOG.error(f"远程虚拟机启动失败: {instance_id} ")
            SQLOG.debug(f"{str(e)}")
            return False

    def stop_instance(self, instance_id):
        try:
            request = StopInstanceRequest()
            request.set_InstanceId(instance_id)
            response = self.client.do_action_with_exception(request)
            SQLOG.info(f"停止远程虚拟机: {instance_id}...")
            return True
        
        except Exception as e:
            SQLOG.error(f"远程虚拟机停止失败: {instance_id} ")
            SQLOG.debug(f"{str(e)}")
            return False

    def delete_instance(self, instance_id):
        try:
            instance_status = self.get_instance_status(instance_id)
            SQLOG.debug(f"远程虚拟机 {instance_id} 状态: {instance_status}")  
            if instance_status == 'Stopped':
                pass
            elif instance_status == 'Stopping':
                time.sleep(3) 
            elif instance_status == 'Running':
                self.stop_instance(instance_id)  
                time.sleep(3) 
            self.wait_instance_status(instance_id, 'Stopped')

            # 删除ECS实例
            request = DeleteInstanceRequest()
            request.set_InstanceId(instance_id)
            request.set_Force(True)
            response = self.client.do_action_with_exception(request)

            SQLOG.info(f"删除远程虚拟机成功: {instance_id}...")
            return True
        
        except Exception as e:
            SQLOG.error(f"删除远程虚拟机停止失败: {instance_id} ")
            SQLOG.debug(f"{str(e)}")
            return False

    def allocate_public_ip(self, instance_id):
        request = AllocatePublicIpAddressRequest()
        request.set_accept_format('json')
        request.set_InstanceId(instance_id)

        try:
            response = self.client.do_action_with_exception(request)
            result = json.loads(response)
            return result['IpAddress']

        except (ClientException, ServerException) as e:
            SQLOG.error(f"分配虚拟机Public IP失败！")
            SQLOG.debug(f"{str(e)}")
            return None

    def attach_key_pair(self, instance_id, key_pair_name):
        
        # 创建请求对象
        request = AttachKeyPairRequest()
        request.set_accept_format('json')
        request.set_InstanceIds([instance_id])
        request.set_KeyPairName(key_pair_name)
        try:
            # 发送请求
            response = self.client.do_action_with_exception(request)
            result = json.loads(response)
            SQLOG.debug(f"绑定SSH密钥时成功！")
            return True
        except Exception as e:
            SQLOG.error(f"绑定SSH密钥时发生错误！")
            SQLOG.debug(f"{str(e)}")
            return False

    def reset_instance_password(self, instance_id, new_password):
        request = ModifyInstanceAttributeRequest()
        request.set_accept_format('json')
        request.set_InstanceId(instance_id)
        request.set_Password(new_password)

        try:
            response = self.client.do_action_with_exception(request)
            SQLOG.debug(f"修改虚拟机登录密码成功！")
            return new_password
        except Exception as e:
            SQLOG.error(f"修改虚拟机登录密码失败！")
            SQLOG.debug(f"{str(e)}")
            return None


    def wait_instance_status(self, instance_id, status):
        # status = 'Running'/'Stopped'
        try:
            while True:
                current_status = self.get_instance_status(instance_id)
                if current_status == status:
                    SQLOG.debug(f'等待虚拟机：{instance_id} 变成{status}状态 ')
                    break
                SQLOG.debug(f'等待虚拟机：{instance_id} 变成{status}状态 ')
                time.sleep(5)
        except Exception as e:
            raise e

    def describe_instance_detail(self, instance_id):

        request = DescribeInstancesRequest()
        request.set_InstanceIds([instance_id])
        try:
            response = self . client.do_action_with_exception(request)
            if response is not None:
                instance_list = json.loads(response)['Instances']['Instance']
                if len(instance_list) > 0:
                    return instance_list[0]
        except Exception as e:
            SQLOG.error(f"获取虚拟机状态失败！")
            SQLOG.debug(f"{str(e)}")
            return None  
        
    def get_instance_status(self, instance_id):
        try:
            details = self.describe_instance_detail(instance_id) 
            if details:
                return details['Status']
            return None
        except Exception as e:
            SQLOG.error(f"获取虚拟机状态失败！")
            SQLOG.debug(f"{str(e)}")
            return None

    def create_image(self, instance_id, image_name, image_description=''):
        request = CreateImageRequest()
        request.set_InstanceId(instance_id)
        request.set_ImageName(image_name)
        request.set_Description(image_description)

        try:
            response = client.do_action_with_exception(request)
            image_id = json.loads(response)['ImageId']
            SQLOG.info(f"镜像创建成功，镜像ID: {image_id}")
            return image_id
        except Exception as e:
            SQLOG.error(f"创建镜像时发生错误!")
            SQLOG.debug(f"{str(e)}")
            return None

    def is_image_exist(self, image_name):
        request = DescribeImagesRequest()
        request.set_ImageName(image_name)
        request.set_Status("Available")

        try:
            response = client.do_action_with_exception(request)
            images = json.loads(response)['Images']['Image']
            return len(images) > 0
        except Exception as e:
            SQLOG.error(f"检查镜像是否存在时发生错误!")
            SQLOG.debug(f"{str(e)}")
            return False

    def delete_image(self, image_id):
        request = DeleteImageRequest()
        request.set_ImageId(image_id)

        try:
            response = client.do_action_with_exception(request)
            SQLOG.info(f"镜像 {image_id} 删除成功")
            return True
        except Exception as e:
            SQLOG.error(f"删除镜像时发生错误: {str(e)}")
            SQLOG.debug(f"{str(e)}")
            return False

    def list_custom_images(self):
        client = AcsClient(access_key_id, access_key_secret, region_id)

        request = DescribeImagesRequest.DescribeImagesRequest()
        request.set_ImageOwnerAlias('self')  # 只列出自定义镜像
        request.set_Status("Available")  # 只列出可用的镜像
        request.set_PageSize(100)  # 每页显示的镜像数量，最大100

        custom_images = []
        page_number = 1

        while True:
            request.set_PageNumber(page_number)
            try:
                response = client.do_action_with_exception(request)
                images = json.loads(response)
                
                for image in images['Images']['Image']:
                    custom_images.append({
                        'ImageId': image['ImageId'],
                        'ImageName': image['ImageName'],
                        'CreationTime': image['CreationTime'],
                        'Size': image['Size']
                    })
                
                if len(custom_images) >= images['TotalCount']:
                    break
                
                page_number += 1
            except Exception as e:
                SQLOG.error(f"获取自定义镜像列表时发生错误!")
                SQLOG.debug(f"{str(e)}")
                break

        return custom_images
    
    def run_command(self, instance_id, command, timeout=300):
        request = RunCommandRequest()
        request.set_InstanceIds([instance_id])
        request.set_Type("RunShellScript")
        request.set_CommandContent(command)
        request.set_Timeout(timeout)
        
        result = None
        try:
            response = self.client.do_action_with_exception(request)
            result = json.loads(response)
            SQLOG.debug(f"执行命令: {command}")
        except Exception as e:
            SQLOG.error(f"执行命令发生错误: {str(e)}")
            SQLOG.debug(f"{str(e)}")
            return None
        return result
    
    def base64_decode(self, content, code='utf-8'):
        if sys.version_info.major == 2:
            return base64.b64decode(content)
        else:
            return base64.b64decode(content).decode(code)
        
    def describe_invocation_results(self, instance_id, invoke_id, wait_count = 30, wait_interval = 10):

        response_detail = None
        for i in range(wait_count):
            status = None
            output = None
            try:
                request = DescribeInvocationResultsRequest()
                request.set_InstanceId(instance_id)
                request.set_InvokeId(invoke_id)
                response = self.client.do_action_with_exception(request)
                response_detail = json.loads(response)["Invocation"]["InvocationResults"]["InvocationResult"][0]
                status = response_detail.get("InvocationStatus","")
                # output = self.base64_decode(response_detail.get("Output",""))
                
                SQLOG.debug(f"命令执行状态为:{status}")
                
                # 显示等待进度
                elapsed_time = (i + 1) * wait_interval
                if status in ["Running", "Pending"]:
                    SQLOG.info(f"⏳ 正在安装VPN软件... 已等待 {elapsed_time} 秒 (状态: {status})")
                elif status == "Stopping":
                    SQLOG.info(f"🔄 命令即将完成... (状态: {status})")
                    
            except Exception as e:
                SQLOG.error(f"获取命令执行结果发生错误: {str(e)}")
                SQLOG.debug(f"{str(e)}")
                pass
                     
            if status not in ["Running","Pending","Stopping"]:
                if status == "Success":
                    SQLOG.info(f"✅ VPN安装完成! (耗时: {elapsed_time} 秒)")
                elif status == "Failed":
                    SQLOG.error(f"❌ VPN安装失败! (状态: {status})")
                break
            
            time.sleep(wait_interval)
        
        return response_detail
    
    

        


