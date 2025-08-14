import os
import yaml

class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            if isinstance(value, dict):
                setattr(self, key, Config(value))
            else:
                setattr(self, key, value)


def load_config():
    file_path = os.environ.get('CONFIG_PATH', "./conf/svc/config.yml")
    with open(file_path, 'r') as file:
        config_dict = yaml.safe_load(file)
    return Config(config_dict)

def get_env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ['1', 'true', 'yes', 'on']

config = load_config()
algo_config = config.algorithm
service_config = config.service

# 优先从环境变量中获取，如果不存在，检查配置文件
ZUOYI_API_KEY = os.getenv("ZUOYI_API_KEY", getattr(service_config, 'zuoyi_api_key', "1234567890"))

# 东方会演示模式
IS_DEMO_MODE = get_env_bool("IS_DEMO_MODE", getattr(service_config, 'is_demo_mode', False))

# 手机端问诊结束是否需要直接跳转到医生工作站
DIRECT_TO_DOCTOR_WORKSTATION = os.getenv("DIRECT_TO_DOCTOR_WORKSTATION", getattr(service_config, 'direct_to_doctor_workstation', True))
DOCTOR_WORKSTATION_URL = os.getenv("DOCTOR_WORKSTATION_URL", getattr(service_config, 'doctor_workstation_url', "https://pre.pc.zhongshan-doctor.inf-health.cn"))

# AI 的开场白
PROLOGUE = os.getenv("PROLOGUE", getattr(service_config, 'prologue', "您好，我是复旦大学附属中山医院观心门诊医生。请问您有什么不舒服？"))