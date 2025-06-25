import os
import json
from sqnethelper.SqLog import SqLog

class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.CONFIG_DIR = os.path.expanduser('~/.sqnethelper')
        self.CONFIG_FILE = os.path.join(self.CONFIG_DIR, 'config.json')
        
        # Default values
        self.defaults = {
            'access_key': '',
            'access_secret': '',
            'region': 'cn-hangzhou',
            'zone_id': '',
            'key_pair_name':'sqnet-sshkey',
            'instance_name': 'sqnetecs-',
            'instance_type': 'ecs.t6-c2m1.large',
            'instance_disk_category':'cloud_efficiency', #cloud_efficiency
            'instance_disk_size':20,
            'instance_cpu_count':2,
            'instance_memory_size':0.5,
            'ssh_keypair_name': '',
            'ssh_local_path': '',
            'instance_login_name': 'root',
            'instance_login_password': 'Root1234',
            'internet_bandwidth_out':40,
            'internet_bandwidth_in':200,
            'internet_charge_type':'PayByTraffic',            
            'image_id': 'debian_12_6_x64_20G_alibase_20240711.vhd',
            'security_group_name':'sqgroup-',
            'security_group_id': '',
            'vswitch_name':'sqvsw-',
            'vswitch_id': '',
            'vpc_name':'sqvpc-',
            'vpc_id': '',
            'vpn_psk':'greatpsk',
            'vpn_name':'greatvpn',
            'vpn_password':'greatpass',
            # VPN端口配置
            'xray_tcp_port': 3000,
            'xray_reality_port': 443,
            'singbox_ss_port': 8080,
            'singbox_reality_port': 443,
        }

        self.config = self.defaults.copy()
        self.load_config()

    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                file_config = json.load(f)
                # Update config with file values, keeping defaults for missing keys
                self.config.update(file_config)

    def save_config(self):
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

    def set_config(self, **kwargs):
        self.config.update(kwargs)
        self.save_config()

    def is_configured(self):
        return bool(self.config['access_key'] and self.config['access_secret'])


    def get_config(self, key):
        return self.config.get(key, self.defaults.get(key))

    # Add property for each config item
    @property
    def access_key(self):
        return self.get_config('access_key')

    @property
    def access_secret(self):
        return self.get_config('access_secret')

    @property
    def region(self):
        return self.get_config('region')

    @property
    def key_pair_name(self):
        return self.get_config('key_pair_name')

    @property
    def zone_id(self):
        return self.get_config('zone_id')

    @property
    def instance_name(self):
        return self.get_config('instance_name')

    @property
    def instance_type(self):
        return self.get_config('instance_type')

    @property
    def instance_disk_category(self):
        return self.get_config('instance_disk_category')

    @property
    def instance_disk_size(self):
        return self.get_config('instance_disk_size')
    
    @property
    def instance_cpu_count(self):
        return self.get_config('instance_cpu_count')
    
    @property
    def instance_memory_size(self):
        return self.get_config('instance_memory_size')

    @property
    def internet_bandwidth_out(self):
        return self.get_config('internet_bandwidth_out')

    @property
    def internet_bandwidth_in(self):
        return self.get_config('internet_bandwidth_in')

    @property
    def internet_charge_type(self):
        return self.get_config('internet_charge_type')

    @property
    def ssh_keypair_name(self):
        return self.get_config('ssh_keypair_name')
    
    @property
    def ssh_local_path(self):
        return self.get_config('ssh_local_path')

    @property
    def instance_login_name(self):
        return self.get_config('instance_login_name')

    @property
    def instance_login_password(self):
        return self.get_config('instance_login_password')

    @property
    def image_id(self):
        return self.get_config('image_id')

    @property
    def security_group_name(self):
        return self.get_config('security_group_name')

    @property
    def security_group_id(self):
        return self.get_config('security_group_id')

    @property
    def vswitch_name(self):
        return self.get_config('vswitch_name')

    @property
    def vswitch_id(self):
        return self.get_config('vswitch_id')

    @property
    def vpc_name(self):
        return self.get_config('vpc_name')

    @property
    def vpc_id(self):
        return self.get_config('vpc_id')

    @property
    def vpn_psk(self):
        return self.get_config('vpn_psk')

    @property
    def vpn_name(self):
        return self.get_config('vpn_name')

    @property
    def vpn_password(self):
        return self.get_config('vpn_password')

    @property
    def xray_tcp_port(self):
        return self.get_config('xray_tcp_port')

    @property
    def xray_reality_port(self):
        return self.get_config('xray_reality_port')

    @property
    def singbox_ss_port(self):
        return self.get_config('singbox_ss_port')

    @property
    def singbox_reality_port(self):
        return self.get_config('singbox_reality_port')
    
    def get_protocol_default_port(self, protocol):
        """
        根据协议名称获取默认端口
        
        Args:
            protocol: 协议名称 (tcp, reality, ss等)
            
        Returns:
            int: 默认端口号
        """
        port_mapping = {
            'tcp': self.xray_tcp_port,
            'reality': self.xray_reality_port, 
            'ss': self.singbox_ss_port,
            'shadowsocks': self.singbox_ss_port,
            'vmess': self.xray_tcp_port,
            'vless': self.xray_reality_port,
        }
        return port_mapping.get(protocol, 443)  # 默认443端口


