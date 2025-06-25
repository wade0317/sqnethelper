import json
import time
import base64
from sqnethelper.SqLog import SQLOG

from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkecs.request.v20140526.ImportKeyPairRequest import ImportKeyPairRequest
from aliyunsdkecs.request.v20140526.DescribeKeyPairsRequest import DescribeKeyPairsRequest
from aliyunsdkecs.request.v20140526.DeleteKeyPairsRequest import DeleteKeyPairsRequest


from aliyunsdkvpc.request.v20160428.CreateVpcRequest import CreateVpcRequest
from aliyunsdkvpc.request.v20160428.DescribeVpcsRequest import DescribeVpcsRequest
from aliyunsdkvpc.request.v20160428.DeleteVpcRequest import DeleteVpcRequest

from aliyunsdkvpc.request.v20160428.CreateVSwitchRequest import CreateVSwitchRequest
from aliyunsdkvpc.request.v20160428.DescribeVSwitchesRequest import DescribeVSwitchesRequest
from aliyunsdkvpc.request.v20160428.DeleteVSwitchRequest import DeleteVSwitchRequest

from aliyunsdkecs.request.v20140526.CreateSecurityGroupRequest import CreateSecurityGroupRequest
from aliyunsdkecs.request.v20140526.DeleteSecurityGroupRequest import DeleteSecurityGroupRequest
from aliyunsdkecs.request.v20140526.DescribeSecurityGroupsRequest import DescribeSecurityGroupsRequest


from aliyunsdkecs.request.v20140526.AuthorizeSecurityGroupRequest import AuthorizeSecurityGroupRequest
from aliyunsdkecs.request.v20140526.AuthorizeSecurityGroupEgressRequest import AuthorizeSecurityGroupEgressRequest
from aliyunsdkecs.request.v20140526.DescribeSecurityGroupAttributeRequest import DescribeSecurityGroupAttributeRequest

from aliyunsdkecs.request.v20140526.DescribeInstanceTypesRequest import DescribeInstanceTypesRequest
from aliyunsdkecs.request.v20140526.DescribePriceRequest import DescribePriceRequest
from aliyunsdkecs.request.v20140526.DescribeAvailableResourceRequest import DescribeAvailableResourceRequest
from aliyunsdkecs.request.v20140526.DescribeDisksRequest import DescribeDisksRequest


class VPCManager:

    def __init__(self, access_key, access_secret, region):
        self.vpc_cidr_block = '172.16.0.0/12'
        self.vswitch_cidr_block = '172.23.128.0/20'
        self.client = AcsClient(access_key, access_secret, region)
        


    def get_available_instance_types_with_price(self, zone_id, cpu_count = 2, memory_size = 0.5):
        # 创建请求对象
        request = DescribeAvailableResourceRequest()
        # 设置请求参数
        request.set_DestinationResource("InstanceType")
        # request.set_IoOptimized("optimized")
        request.set_ZoneId(zone_id)
        # request.set_Cores(cpu_count)
        request.set_Memory(memory_size)
        

        # 发送请求
        response = self.client.do_action_with_exception(request)
        resources = json.loads(response)
        # 解析实例类型
        instance_types = []
        from_res = resources['AvailableZones']['AvailableZone'][0]['AvailableResources']['AvailableResource']
        for resource in from_res:
            for instance_category in resource['SupportedResources']['SupportedResource']:
                if instance_category["Status"] == "Available":
                    instance_types.append(instance_category)
                
        instance_types_price = [] 
        if  len(instance_types) ==1:
            instance_types_price.append((instance_types[0]["Value"], "1.0"))
            return instance_types_price
        
        
        for item in instance_types:
            instance_type = item["Value"]
            
            price_request = DescribePriceRequest()
            price_request.set_ResourceType("instance")
            price_request.set_InstanceType(instance_type)
            price_request.set_InstanceNetworkType("vpc")
            price_request.set_PriceUnit("Month")
            price_request.set_Amount(1)
            price_request.set_ZoneId(zone_id)
            # price_request.set_Platform("Linux")
            # price_request.set_OfferingType("AllUpfront")
            # price_request.set_Scope("OnDemand")
            
                
            try:
                price_response = self.client.do_action_with_exception(price_request)                        
                price_info = json.loads(price_response)
                price = price_info['PriceInfo']['Price']['OriginalPrice']
                instance_types_price.append((instance_type, price))
            
            except Exception as e:
                SQLOG.debug(f"获取实例类型价格失败: {str(instance_type)}")
                SQLOG.debug(f"失败原因: {str(e)}")
                instance_types_price.append((instance_type, 10000.0))
                continue
            
            
        instance_types_price.sort(key=lambda x: x[1])

        return instance_types_price    
        
        
    def get_instance_types_with_price(self, zone_id, cpu_count = 2, memory_size = 1.0):
        
        # 获取实例类型
        instance_type_request = DescribeInstanceTypesRequest()
        instance_type_request.set_MaximumCpuCoreCount(cpu_count)
        instance_type_request.set_MaximumMemorySize(memory_size)
        # instance_type_request.set_ZoneId(zone_id)
        try:
            response = self.client.do_action_with_exception(instance_type_request)
            instance_types = json.loads(response)
            # 筛选符合条件的实例类型
            specific_types = []
            for instance_type in instance_types['InstanceTypes']['InstanceType']:
                if instance_type['CpuCoreCount'] == cpu_count and instance_type['MemorySize'] == memory_size:
                    specific_types.append(instance_type['InstanceTypeId'])
            # 获取价格信息
            instance_prices = []
            for instance_type in specific_types:
                price_request = DescribePriceRequest()
                price_request.set_InstanceType(instance_type)
                price_request.set_PriceUnit("Hour")
                price_request.set_Amount(1)
                price_response = self.client.do_action_with_exception(price_request)
                price_info = json.loads(price_response)

                price = price_info['PriceInfo']['Price']['OriginalPrice']
                instance_prices.append((instance_type, price))

            # 按价格排序
            instance_prices.sort(key=lambda x: x[1])
            return instance_prices
        except Exception as e:
            SQLOG.info(f"获取实例类型时发生错误: {str(e)}")
            return None
        
    def get_available_disk_categories(self, zone_id, insance_type):
        # 创建请求对象
        request = DescribeAvailableResourceRequest()
        
        # 设置请求参数
        request.set_DestinationResource("SystemDisk")
        request.set_ResourceType("instance")
        request.set_ZoneId(zone_id)
        request.set_InstanceType(insance_type)
        
        # 发送请求
        response = self.client.do_action_with_exception(request)
        resources = json.loads(response)
        # 解析实例类型
        disk_types = []
        for resource in resources['AvailableZones']['AvailableZone'][0]['AvailableResources']['AvailableResource']:
            for disk_category in resource['SupportedResources']['SupportedResource']:
                disk_types.append(disk_category)
        
        
        return disk_types
        
    def import_ssh_key(self, key_pair_name, public_key_body):
        request = ImportKeyPairRequest()
        request.set_accept_format('json')
        request.set_KeyPairName(key_pair_name)
        request.set_PublicKeyBody(public_key_body)

        try:
            response = self.client.do_action_with_exception(request)
            result = json.loads(response)
            SQLOG.debug(f"SSH密钥 '{key_pair_name}' 已成功导入。密钥对ID: {result['KeyPairName']}")
            return result['KeyPairName']
        except Exception as e:
            SQLOG.debug(f"导入SSH密钥时发生错误: {str(e)}")
            return None

    def is_key_pair_exist(self, key_pair_name):
        
        request = DescribeKeyPairsRequest()
        request.set_accept_format('json')
        try:
            response = self.client.do_action_with_exception(request)
            result = json.loads(response)
            key_pairs = result.get('KeyPairs', {}).get('KeyPair', [])
            exists = len(key_pairs) > 0
            SQLOG.debug(f"SSH密钥 '{key_pair_name}' {'存在' if exists else '不存在'}")
            return exists
        except Exception as e:
            SQLOG.debug(f"检查SSH密钥是否存在时发生错误: {str(e)}")
            return False
        
    def is_key_pair_exist_with_name(self, key_pair_name):
        request = DescribeKeyPairsRequest()
        request.set_accept_format('json')
    
        try:
            response = self.client.do_action_with_exception(request)
            result = json.loads(response)
            key_pairs = result.get('KeyPairs', {}).get('KeyPair', [])
            for key_pair in key_pairs:
                if key_pair['KeyPairName'].startswith(key_pair_name):
                    SQLOG.debug(f"存在SSH密钥对'{key_pair['KeyPairName']}'")
                    return key_pair['KeyPairName']
            return None  
        
        except Exception as e:
            SQLOG.debug(f"检查SSH密钥是否存在时发生错误: {str(e)}")
            return False

    def delete_key_pair(self, key_pair_name):
        request = DeleteKeyPairsRequest()
        request.set_accept_format('json')
        request.set_KeyPairName(key_pair_name)

        try:
            self.client.do_action_with_exception(request)
            key_pairs = result.get('KeyPairs', {}).get('KeyPair', [])
            SQLOG.debug(f"SSH密钥 '{key_pair_name}' 已成功删除")
            if len(key_pairs) > 0:
                return True
            else:
                return False
        except Exception as e:
            SQLOG.info(f"删除SSH密钥时发生错误: {str(e)}")
            return False

    def list_vpc(self):
        request = DescribeVpcsRequest()
        response = self.client.do_action_with_exception(request)
        vpcs = json.loads(response)['Vpcs']['Vpc']
        return vpcs

    def create_vpc(self):
        SQLOG.info("create_vpc")
        vpc_request = CreateVpcRequest()
        time_str = time.strftime('%m%d-%H-%M-%S', time.localtime())
        vpc_name = f"sqvpc-{time_str}"
        vpc_request.set_CidrBlock(self.vpc_cidr_block)
        vpc_request.set_VpcName(vpc_name)
        vpc_response = self.client.do_action_with_exception(vpc_request)
        vpc_id = json.loads(vpc_response)['VpcId']
        return vpc_id

    def is_vpc_exist_with_name(self, vpc_name):
        request = DescribeVpcsRequest()
        request.set_accept_format('json')

        try:
            response = self.client.do_action_with_exception(request)
            vpcs = json.loads(response)['Vpcs']['Vpc']
            for vpc in vpcs:
                if vpc['VpcName'].startswith(vpc_name):
                    return vpc['VpcId']
            return None        
        except Exception as e:
            SQLOG.info(f"检查VPC '{vpc_id}' 是否存在时发生错误: {str(e)}")
            return False

    def is_vpc_exist(self, vpc_id):

        if vpc_id is None:
            return False

        request = DescribeVpcsRequest()
        request.set_accept_format('json')
        request.set_VpcId(vpc_id)
        try:
            response = self.client.do_action_with_exception(request)
            vpcs = json.loads(response)['Vpcs']['Vpc']
            
            if len(vpcs) > 0:
                vpc = vpcs[0]  # 由于我们指定了VPC ID，应该只有一个结果
                return True
            else:
                SQLOG.info(f"VPC '{vpc_id}' 不存在。")
                return False
        
        except Exception as e:
            SQLOG.info(f"检查VPC '{vpc_id}' 是否存在时发生错误: {str(e)}")
            return None


    def delete_vpc(self, vpc_id):
        request = DeleteVpcRequest()
        request.set_VpcId(vpc_id)
        try:
            self.client.do_action_with_exception(request)
            SQLOG.info(f"VPC {vpc_id} 已成功删除")
            return True
        except Exception as e:
            SQLOG.info(f"删除VPC {vpc_id} 时发生错误: {str(e)}")
            return False

    def create_vswitch(self, vpc_id, zone_id):
        time_str = time.strftime('%m%d-%H-%M-%S', time.localtime())
        vswitch_name = f"sqvsw-{time_str}"
        request = CreateVSwitchRequest()
        request.set_VpcId(vpc_id)
        request.set_VSwitchName(vswitch_name)
        request.set_ZoneId(zone_id)
        request.set_CidrBlock(self.vswitch_cidr_block)
        try:
            response = self.client.do_action_with_exception(request)
            vswitch_id = json.loads(response)['VSwitchId']
            return vswitch_id
        except Exception as e:
            SQLOG.info(f"创建VPC时发生错误: {str(e)}")
            return None

    def is_vswitch_exist_with_name(self, vswitch_name):
        request = DescribeVSwitchesRequest()
        request.set_accept_format('json')
        
        try:
            response = self.client.do_action_with_exception(request)
            vswitches = json.loads(response)['VSwitches']['VSwitch']
            for vswitch in vswitches:
                if vswitch['VSwitchName'].startswith(vswitch_name):
                    SQLOG.info(f"找到以 'sqvs-' 开头的 VSwitch，名称为 '{vswitch['VSwitchName']}'，ID 为 {vswitch['VSwitchId']}")
                    return vswitch['VSwitchId']
            
            SQLOG.info(f"VSwitch '{vswitch_name}' 不存在")
            return None
        except Exception as e:
            SQLOG.info(f"检查 VSwitch '{vswitch_name}' 是否存在时发生错误: {str(e)}")
            return None

    def get_vswitche_id_by_vpc_id(self, vpc_id):
        request = DescribeVSwitchesRequest()
        request.set_accept_format('json')
        request.set_VpcId(vpc_id)
        try:
            response = self.client.do_action_with_exception(request)
            vswitches = json.loads(response)['VSwitches']['VSwitch']
            if vswitches:
                # SQLOG.info(f"在VPC '{vpc_id}' 中找到以下VSwitch:")
                for vswitch in vswitches:
                    # SQLOG.info(f"VSwitch ID: {vswitch['VSwitchId']}, 名称: {vswitch['VSwitchName']}, 可用区: {vswitch['ZoneId']}, CIDR: {vswitch['CidrBlock']}")
                    return vswitch['VSwitchId']
            else:
                SQLOG.info(f"在VPC '{vpc_id}' 中没有找到任何VSwitch")
                return None
        
        except Exception as e:
            SQLOG.info(f"获取VPC '{vpc_id}' 的VSwitch时发生错误: {str(e)}")
            return None

    def is_vswitch_exist(self, vswitch_id):
        if vswitch_id is None:
            return False
        if vswitch_id == '':
            return False

        request = DescribeVSwitchesRequest()
        request.set_accept_format('json')
        request.set_VSwitchId(vswitch_id)
        
        try:
            response = self.client.do_action_with_exception(request)
            vswitches = json.loads(response)['VSwitches']['VSwitch']
            exists = len(vswitches) > 0
            SQLOG.info(f"VSwitch '{vswitch_id}' {'存在' if exists else '不存在'}")
            return exists
        except Exception as e:
            SQLOG.info(f"检查 VSwitch '{vswitch_id}' 是否存在时发生错误: {str(e)}")
            return False

    def delete_vswitch(self, vswitch_id):
        request = DeleteVSwitchRequest()
        request.set_VSwitchId(vswitch_id)
        try:
            self.client.do_action_with_exception(request)
            SQLOG.info(f"交换机 {vswitch_id} 已成功删除")
            return True
        except Exception as e:
            SQLOG.info(f"删除交换机 {vswitch_id} 时发生错误: {str(e)}")
            return False



    def list_security_group(self):
        request = DescribeSecurityGroupsRequest()
        try:
            response = self.client.do_action_with_exception(request)
            security_groups = json.loads(response)['SecurityGroups']['SecurityGroup']
            return security_groups
        except Exception as e:
            SQLOG.info(f"获取安全组列表时发生错误: {str(e)}")
            return None

    def create_security_group(self, vpc_id):
        time_str = time.strftime('%m%d-%H-%M-%S', time.localtime())
        security_group_name = f"sqgroup-{time_str}"
        security_group_request = CreateSecurityGroupRequest()
        security_group_request.set_SecurityGroupName(security_group_name)
        security_group_request.set_VpcId(vpc_id)
        try:
            security_group_response = self.client.do_action_with_exception(security_group_request)
            security_group_id = json.loads(security_group_response)['SecurityGroupId']
            return security_group_id
        except Exception as e:
            SQLOG.info(f"创建安全组时发生错误: {str(e)}")
            return None

    def is_security_group_exist(self, security_group_id):
        if security_group_id is None:
            return False
        if security_group_id == '':
            return False

        request = DescribeSecurityGroupsRequest()
        request.set_SecurityGroupIds([security_group_id])
        try:
            response = self.client.do_action_with_exception(request)
            security_groups = json.loads(response)['SecurityGroups']['SecurityGroup']
            return len(security_groups) > 0
        except Exception as e:
            SQLOG.info(f"检查安全组是否存在时发生错误: {str(e)}")
            return False

    def is_security_group_exist_with_name(self, security_group_name):
        request = DescribeSecurityGroupsRequest()
        request.set_accept_format('json')
        
        try:
            response = self.client.do_action_with_exception(request)
            security_groups = json.loads(response)['SecurityGroups']['SecurityGroup']
            
            for group in security_groups:
                if group['SecurityGroupName'].startswith(security_group_name):
                    SQLOG.info(f"安全组 '{security_group_name}' 存在，ID 为 {group['SecurityGroupId']}")
                    return group['SecurityGroupId']
            SQLOG.info(f"安全组 '{security_group_name}' 不存在")
            return None
        except Exception as e:
            SQLOG.info(f"检查安全组 '{security_group_name}' 是否存在时发生错误: {str(e)}")
            return None

    def get_vpc_id_by_security_group_id(self, security_group_id):
        request = DescribeSecurityGroupAttributeRequest()
        request.set_accept_format('json')
        request.set_SecurityGroupId(security_group_id)
        
        try:
            response = self.client.do_action_with_exception(request)
            security_group_info = json.loads(response)
            vpc_id = security_group_info.get('VpcId')
            if vpc_id:
                # SQLOG.info(f"安全组 '{security_group_id}' 属于VPC '{vpc_id}'")
                return vpc_id
            else:
                # SQLOG.info(f"安全组 '{security_group_id}' 不属于任何VPC（可能是经典网络）")
                return None
        
        except Exception as e:
            SQLOG.info(f"获取安全组 '{security_group_id}' 的VPC ID时发生错误: {str(e)}")
            return None


    def delete_security_group(self, security_group_id):
        request = DeleteSecurityGroupRequest()
        request.set_SecurityGroupId(security_group_id)
        try:
            self.client.do_action_with_exception(request)
            SQLOG.info(f"安全组 {security_group_id} 已成功删除")
            return True
        except Exception as e:
            SQLOG.info(f"删除安全组 {security_group_id} 时发生错误: {str(e)}")
            return False


    def is_security_group_accept_rule_exist(self, security_group_id, protocol, port_range):
        request = DescribeSecurityGroupAttributeRequest()
        request.set_SecurityGroupId(security_group_id)
        request.set_Direction('ingress')
        
        try:
            response = self.client.do_action_with_exception(request)
            rules = json.loads(response)['Permissions']['Permission']
            
            for rule in rules:
                if (rule['IpProtocol'] == protocol and 
                    rule['PortRange'] == port_range and 
                    rule['Policy'] == 'Accept'):
                    
                    SQLOG.info(f"入方向规则 (协议: {protocol}, 端口: {port_range}) 已存在")
                    return True
            
            SQLOG.info(f"入方向规则 (协议: {protocol}, 端口: {port_range}) 不存在")
            return False
        except Exception as e:
            SQLOG.info(f"检查安全组规则时发生错误: {str(e)}")
            return False

    def add_security_group_accept_rule(self, security_group_id, protocol, port_range, accept='Accept', source_cidr_ip='0.0.0.0/0'):
        rule_req = AuthorizeSecurityGroupRequest()
        rule_req.set_SecurityGroupId(security_group_id)
        rule_req.set_SourceCidrIp(source_cidr_ip)
        rule_req.set_IpProtocol(protocol)
        rule_req.set_Policy(accept)
        rule_req.set_Priority(1)
        rule_req.set_PortRange(port_range)
        
        try:
            self.client.do_action_with_exception(rule_req)
            SQLOG.info(f"成功添加入方向规则 (协议: {protocol}, 端口范围: {port_range})")
            return True
        except Exception as e:
            SQLOG.info(f"添加入方向规则时发生错误: {str(e)}")
            return False

    def is_security_group_accept_rule_egress_exist(self, security_group_id, protocol, port_range, accept='Accept'):
        request = DescribeSecurityGroupAttributeRequest()
        request.set_SecurityGroupId(security_group_id)
        request.set_Direction('egress')
        
        try:
            response = self.client.do_action_with_exception(request)
            rules = json.loads(response)['Permissions']['Permission']
            
            for rule in rules:
                if (rule['IpProtocol'] == protocol and 
                    rule['PortRange'] == port_range and 
                    rule['Policy'] == accept):
                    SQLOG.info(f"出方向规则 (协议: {protocol}, 端口范围: {port_range}) 已存在")
                    return True
            
            # SQLOG.info(f"出方向规则 (协议: {protocol}, 端口范围: {port_range}) 不存在")
            return False
        except Exception as e:
            # SQLOG.info(f"检查安全组出方向规则时发生错误: {str(e)}")
            return False

    def add_security_group_accept_egress_rule(self, security_group_id, protocol, port_range, accept='accept', dest_cidr_ip='0.0.0.0/0'):
        rule_req = AuthorizeSecurityGroupEgressRequest()
        rule_req.set_SecurityGroupId(security_group_id)
        rule_req.set_DestCidrIp(dest_cidr_ip)
        rule_req.set_IpProtocol(protocol)
        rule_req.set_Policy(accept)
        rule_req.set_Priority(1)
        rule_req.set_PortRange(port_range)
        
        try:
            self.client.do_action_with_exception(rule_req)
            SQLOG.info(f"添加出方向规则 (协议: {protocol}, 端口范围: {port_range})")
            return True
        except Exception as e:
            SQLOG.info(f"添加出方向规则时发生错误: (协议: {protocol}, 端口范围: {port_range} {str(e)}")
            return False


    def add_security_group_rule(self, security_group_id, config=None):
        """添加安全组规则，包括基础规则和VPN端口规则"""
        
        # 基础规则
        if not self.is_security_group_accept_rule_exist(security_group_id, 'TCP', '22/22'):
            self.add_security_group_accept_rule(security_group_id, 'TCP', '22/22')

        # IPsec VPN规则
        if not self.is_security_group_accept_rule_exist(security_group_id, 'UDP', '500/500'):
            self.add_security_group_accept_rule(security_group_id, 'UDP', '500/500')

        if not self.is_security_group_accept_rule_exist(security_group_id, 'UDP', '4500/4500'):
            self.add_security_group_accept_rule(security_group_id, 'UDP', '4500/4500')

        # HTTP/HTTPS规则
        if not self.is_security_group_accept_rule_exist(security_group_id, 'TCP', '443/443'):
            self.add_security_group_accept_rule(security_group_id, 'TCP', '443/443')

        if not self.is_security_group_accept_rule_exist(security_group_id, 'TCP', '80/80'):
            self.add_security_group_accept_rule(security_group_id, 'TCP', '80/80')
            
        # VPN端口规则（从配置中读取）
        if config:
            vpn_ports = [
                config.xray_tcp_port,
                config.xray_reality_port,
                config.singbox_ss_port,
                config.singbox_reality_port
            ]
            
            # 去重端口列表
            unique_ports = list(set(vpn_ports))
            
            for port in unique_ports:
                port_rule = f'{port}/{port}'
                if not self.is_security_group_accept_rule_exist(security_group_id, 'TCP', port_rule):
                    self.add_security_group_accept_rule(security_group_id, 'TCP', port_rule)
                    SQLOG.info(f"✅ 已添加VPN端口规则: TCP {port}")
        else:
            # 如果没有配置对象，使用默认端口
            default_ports = ['3000/3000', '8080/8080', '5432/5432']
            for port_rule in default_ports:
                if not self.is_security_group_accept_rule_exist(security_group_id, 'TCP', port_rule):
                    self.add_security_group_accept_rule(security_group_id, 'TCP', port_rule)
            
        # ICMP规则
        if not self.is_security_group_accept_rule_exist(security_group_id, 'ICMP', '-1/-1'):
            self.add_security_group_accept_rule(security_group_id, 'ICMP', '-1/-1')

        # 出站规则
        if not self.is_security_group_accept_rule_egress_exist(security_group_id, 'ALL', '-1/-1'):
            self.add_security_group_accept_egress_rule(security_group_id, 'ALL', '-1/-1')

    def add_vpn_port_rule(self, security_group_id, port):
        """为指定端口添加安全组规则"""
        port_rule = f'{port}/{port}'
        if not self.is_security_group_accept_rule_exist(security_group_id, 'TCP', port_rule):
            success = self.add_security_group_accept_rule(security_group_id, 'TCP', port_rule)
            if success:
                SQLOG.info(f"✅ 已为VPN添加防火墙端口规则: TCP {port}")
                return True
            else:
                SQLOG.error(f"❌ 添加防火墙端口规则失败: TCP {port}")
                return False
        else:
            SQLOG.info(f"📋 防火墙端口规则已存在: TCP {port}")
            return True

    






